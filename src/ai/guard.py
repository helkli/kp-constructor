"""Guard-слой: цены, сроки, ПДн, парсинг ответа модели.

Отвечает за критерии готовности:
- A2: модель не выдумывает цены (sanitize_prices);
- A3: нет цены -> «цена уточняется» (sanitize_prices, price.py);
- A9: логи без персональных данных (depersonalize);
- сроки: модель не придумывает сроки, отличные от брифа (ensure_deadline / sanitize_dates_in_text).
"""
from __future__ import annotations

import re

from src.ai.errors import AIResponseError

PRICE_PLACEHOLDER = "цена уточняется"

# --- Денежные суммы вида «12 000 ₽», «1500 руб», «3 500,50 рублей» ---
# Важно: после «₽» НЕ ставим \b — символ валюты не «словесный», граница не сработает.
_CURRENCY_RE = re.compile(
    r"(?<![\d])(?P<amount>\d{1,3}(?:[\s\u00A0\u202F\u02BC']\d{3})*(?:[.,]\d{1,2})?|\d+)"
    r"\s*(?:₽|руб(?:лей|ля|ль)?\.?)",
    re.IGNORECASE,
)


def normalize_amount(raw: str) -> float:
    """Приводит сумму к числу: '12 000' -> 12000.0, '1 500,50' -> 1500.5."""
    s = raw.replace("\u00A0", " ").replace(" ", "").replace("'", "")
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return -1.0


def find_price_violations(text: str, allowed: set[float]) -> list[dict]:
    """Все суммы в тексте, которых нет в «разрешённых» (прайс + бюджет брифа)."""
    allowed = set(float(x) for x in allowed)
    violations = []
    for m in _CURRENCY_RE.finditer(text):
        amt = normalize_amount(m.group("amount"))
        if amt not in allowed:
            violations.append({"old": m.group(0), "amount": amt})
    return violations


def sanitize_prices(text: str, allowed: set[float]) -> tuple[str, list[dict]]:
    """Заменяет выдуманные суммы на «цена уточняется», разрешённые оставляет.

    Возвращает (очищенный текст, список фиксов).
    """
    allowed = set(float(x) for x in allowed)
    fixes: list[dict] = []
    out: list[str] = []
    last = 0
    for m in _CURRENCY_RE.finditer(text):
        amt = normalize_amount(m.group("amount"))
        out.append(text[last : m.start()])
        if amt in allowed:
            out.append(m.group(0))
        else:
            fixes.append({"old": m.group(0), "new": PRICE_PLACEHOLDER})
            out.append(PRICE_PLACEHOLDER)
        last = m.end()
    out.append(text[last:])
    return "".join(out), fixes


# --- Сроки и даты ---
_DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b")
_MONTH_YEAR_RE = re.compile(
    r"\b(?:января?|февраля?|марта?|апреля?|мая|июня?|июля?|августа?|сентября?|"
    r"октября?|ноября?|декабря?)\s*\d{2,4}\b",
    re.IGNORECASE,
)
_PERIOD_RE = re.compile(
    r"\b(?:[1-9]|[12]\d|3[0-6])\s*(?:час(?:а|ов)?\s*(?:рабоч(?:их)?\s*)?|"
    r"(?:рабоч(?:их)?\s*)?дн(?:ей|я)?|день|недел(?:ю|и|я|ь)?|"
    r"месяц(?:а|ев|ам)?|мес\.?\b|год(?:а|ов|ам)?|квартал[а-я]*)\b",
    re.IGNORECASE,
)


def extract_deadline_tokens(text: str) -> list[str]:
    """Все фрагменты, похожие на сроки/даты (для сверки с брифом)."""
    tokens: list[str] = []
    for regex in (_DATE_RE, _MONTH_YEAR_RE, _PERIOD_RE):
        tokens += [m.group(0) for m in regex.finditer(text)]
    return tokens


def ensure_deadline(text: str, deadline: str) -> tuple[str, list[dict]]:
    """Если срок из брифа задан — придуманные моделью сроки заменяются на формулировку брифа."""
    dl = " ".join(deadline.split())
    out = text
    fixes: list[dict] = []
    for tok in extract_deadline_tokens(out):
        if dl.lower() in tok.lower() or tok.lower() in dl.lower():
            continue
        out = out.replace(tok, dl)
        fixes.append({"old": tok, "new": dl})
    return out, fixes


def sanitize_dates_in_text(text: str, deadline: str) -> tuple[str, list[dict]]:
    """Без срока в брифе — придуманные даты заменяются на «срок уточняется»."""
    if deadline and deadline.strip():
        return ensure_deadline(text, deadline)
    out = text
    fixes: list[dict] = []
    for tok in extract_deadline_tokens(out):
        out = out.replace(tok, "срок уточняется")
        fixes.append({"old": tok, "new": "срок уточняется"})
    return out, fixes


# --- Персональные данные (для логов и промпта) ---
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(
    r"(?<![\d])(?:\+7|8)\s?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)
# Номера документов: непрерывные (ИНН/ОГРН/паспорт без пробелов) и формата «1234 567890».
_LONGNUM_RE = re.compile(r"(?<![\d])\d{4,}(?:[\s\u00A0-]?\d{3,})+(?![\d])")


def depersonalize(text: str) -> str:
    """Маскирует ПДн: e-mail, телефоны, длинные номера документов.

    Применяется к промпту перед отправкой модели и к промпту/ответу перед записью в лог.
    """
    out = _EMAIL_RE.sub("[e-mail удалён]", text)
    out = _PHONE_RE.sub("[телефон удалён]", out)
    out = _LONGNUM_RE.sub("[номер документа удалён]", out)
    return out


# --- Парсинг ответа модели по разделам ---
_HEADER_RE = re.compile(r"^\s*(?:#{1,6}\s+(.+?)|(\d{1,2})[.)]\s+(.+?))\s*$")
_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|^\s*```[ \t]*$", re.MULTILINE)


def _norm_header(s: str) -> str:
    return re.sub(r"[^\wа-яё 0-9]", "", s.lower()).strip()


def parse_sections(
    raw: str,
    expected_headers: list[str],
    require_all: bool = True,
) -> list[dict]:
    """Разбирает ответ модели на разделы по заголовкам шаблона.

    - Заголовки ожидаются в формате «## Название» (или «1. Название»).
    - Отсутствующие/лишние разделы -> AIResponseError (требование ТЗ FR-5, A10).
    """
    text = _CODE_FENCE_RE.sub("", raw or "").strip()
    if not text:
        raise AIResponseError("Модель вернула пустой ответ. Повторите генерацию.")

    segments: list[tuple[str, list[str]]] = []
    cur_header: str | None = None
    cur_body: list[str] = []

    def flush() -> None:
        if cur_header:
            segments.append((cur_header, cur_body[:]))

    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            header = (m.group(1) or m.group(3) or "").strip()
            if header:
                flush()
                cur_header = header
                cur_body = []
                continue
        if cur_header is not None:
            cur_body.append(line)
    flush()

    if not segments:
        raise AIResponseError(
            "Не удалось разобрать ответ модели по разделам. Повторите генерацию.",
            detail="Ответ не содержит заголовков разделов.",
        )

    expected = {_norm_header(h): h for h in expected_headers}
    matched: dict[str, str] = {}  # канонический заголовок -> тело

    for header, body in segments:
        hn = _norm_header(header)
        hit = expected.get(hn)
        if hit is None:
            for en, exp in expected.items():
                if en in hn or hn in en:
                    hit = exp
                    break
        if hit is None:
            raise AIResponseError(
                "Модель добавила раздел, отсутствующий в шаблоне. Повторите генерацию.",
                detail=f"Неизвестный раздел: {header}",
            )
        matched[hit] = "\n".join(body).strip()

    if require_all:
        missing = [h for h in expected_headers if h not in matched]
        if missing:
            raise AIResponseError(
                "Модель заполнила не все разделы шаблона. Повторите генерацию.",
                detail=f"Не заполнено: {', '.join(missing)}",
            )

    result = []
    for exp in expected_headers:
        body = matched.get(exp)
        if body is not None:
            result.append({"header": exp, "body": body})
        elif not require_all:
            continue
    return result