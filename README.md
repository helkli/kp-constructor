# 🤖 AI-конструктор коммерческих предложений

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-68%20passed%20|%201%20skipped-2E7D32?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-0B7A4B.svg)](LICENSE)
[![Язык: Русский](https://img.shields.io/badge/язык-Русский-F5A623.svg)](https://ru.wikipedia.org/wiki/Русский_язык)

> **Бриф → черновик КП по шаблону → правка человеком → PDF.**
> Веб-приложение для сервисной компании. Менеджер описывает задачу клиента —
> ИИ собирает черновик коммерческого предложения по разделам шаблона, человек
> проверяет и правит текст, выгружает PDF, **дословно совпадающий** с отредактированной
> версией.

**Ключевая идея:** цены в КП формирует **только код** из прайса услуг. Модели запрещено
придумывать суммы и сроки — даже если она «забывает» правило, guard-слой заменяет
всё лишнее на «цена уточняется».

---

## 📸 Скриншоты

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/01_home.png" alt="Главная — дашборд"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/02_brief.png" alt="Бриф с валидацией"></td>
</tr>
<tr>
<td colspan="2" align="center"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/03_draft.png" alt="Редактор черновика по разделам"></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/04_preview.png" alt="Предпросмотр и PDF"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/05_history.png" alt="История версий КП"></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/06_settings_price.png" alt="Настройки: прайс услуг"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/07_settings_ai.png" alt="Настройки: проверка подключения к ИИ"></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/08_settings_deploy.png" alt="Настройки: развёртывание"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/helkli/kp-constructor/main/docs/screenshots/10_mobile_history.png" alt="Мобильный вид"></td>
</tr>
</table>

---

## 🎯 Что решает

Сервисные компании (ИТ-поддержка, аутсорс, услуги) тратят **часы** на подготовку каждого КП:
менеджер собирает текст вручную, вставляет цены, оформляет PDF. Результат — медленно,
цены «приблизительные», структура КП у каждого своя.

**Роли в приложении:**

| Роль | Возможности |
|------|-------------|
| **Менеджер** | Заполняет бриф → генерирует черновик → правит по разделам → выгружает PDF |
| **Руководитель** | Ведёт прайс услуг и шаблон структуры КП, проверяет подключение к ИИ |

---

## ⚡ Возможности MVP

- 📋 **Бриф** — клиент, задача, услуги из прайса, сроки; бюджет опционален.
- ✅ **Валидация до вызова ИИ** — пустые обязательные поля блокируют генерацию, ключ не тратится.
- 🤖 **Генерация по разделам шаблона** — GigaChat или YandexGPT, переключается в `.env`.
- 💰 **Цены — только из прайса кодом** — выдуманные моделью суммы заменяются на «цена уточняется».
- 📝 **Редактор черновика** — правка по разделам, перегенерация раздела или всего КП, версии.
- 📄 **Предпросмотр и PDF** — reportlab, корректная кириллица через TTF-шрифт.
- 📚 **История КП** — все версии с датой и статусом (черновик / финал).
- ⚙️ **Настройки (роль «Руководитель»)** — прайс, шаблон структуры, живая проверка ИИ.
- 🚀 **Развёртывание по-русски** — готовые `Dockerfile`, `requirements.txt`, `packages.txt`, `secrets.toml`.
- 📱 **Адаптивная вёрстка** — корректная работа на телефоне.

---

## 🔐 Безопасность (главные правила проекта)

| Правило | Реализация |
|---------|------------|
| Ключи — только в `.env` | `src/config.py` читает окружение; в коде ключей нет, `.env` в `.gitignore` |
| Ключ не попадает в браузер | Запросы к ИИ выполняются на сервере приложения |
| ИИ не выдумывает цены | `src/ai/guard.py`: `sanitize_prices` заменяет суммы, которых нет в прайсе/брифе |
| ИИ не выдумывает сроки | `ensure_deadline` / `sanitize_dates_in_text` подставляют срок из брифа |
| ПДн не уходят в модель и логи | `depersonalize` маскирует e-mail, телефоны, номера документов |
| Ошибки понятны, бриф не теряется | `friendly_message()` без ключей и деталей + сохранение брифа в сессии |

---

## 🚀 Быстрый старт

```bash
# 1. Настройки и ключ
cp .env.example .env          # Windows: copy .env.example .env

# 2. Зависимости
pip install -r requirements.txt

# 3. Запуск
streamlit run app.py
```

Приложение откроется на `http://localhost:8501`.

### Демо-данные (по желанию)

```bash
python scripts/seed_demo.py   # наполняет БД примерами КП для витрины
```

### Настройка ИИ-провайдера

**YandexGPT** (по умолчанию в проекте):

```env
AI_PROVIDER=yandex
YANDEX_API_KEY=<ключ>
YANDEX_FOLDER_ID=<каталог b1g…>
YANDEX_MODEL=yandexgpt-lite
AI_TIMEOUT=60
```

Как получить ключи:
1. Аккаунт и платёжный аккаунт на [console.yandex.cloud](https://console.yandex.cloud).
2. Создать каталог → в «Обзоре» взять **ID каталога** (`b1g…`) → это `YANDEX_FOLDER_ID`.
3. «Сервисные аккаунты» → создать аккаунт → выдать на каталог роль
   **`ai.languageModels.user`**.
4. В сервисном аккаунте «Создать новый ключ → **API-ключ**» (показывается один раз).

**GigaChat** (альтернатива):

```env
AI_PROVIDER=gigachat
GIGACHAT_API_KEY=<base64 от client_id:client_secret>
```

Ключ собирается скриптом:

```bash
python scripts/make_gigachat_key.py <client_id> <client_secret> --write-env
```

### Проверка подключения к ИИ

Из терминала:

```bash
python scripts/test_ai.py
```

Из приложения: страница **«5 · Настройки»** (роль «Руководитель») → вкладка
**«🤖 Подключение к ИИ»** → кнопка «🔌 Проверить подключение».

---

## 🧠 Как устроена генерация

```
Бриф (валидация)
      ↓
build_user_prompt()  ← промпт: бриф + услуги из прайса + разделы шаблона
      ↓
depersonalize()      ← маскирование ПДн ДО отправки в модель
      ↓
LLMProvider.complete()  ← YandexGPT | GigaChat (единый интерфейс)
      ↓
parse_sections()     ← разбор ответа по разделам шаблона
      ↓
sanitize_prices() / ensure_deadline()   ← защита от галлюцинаций
      ↓
Цены и сроки из прайса и брифа (только код)
      ↓
Предпросмотр → PDF (идентичен отредактированной версии)
```

Системный промпт прямо запрещает модели цены, сроки, контакты и реквизиты:

> **СТРОГИЕ ПРАВИЛА:** … НИКОГДА не указывай никакие цены, суммы, стоимость, тарифы…
> НИКОГДА не придумывай сроки и даты… Не выдумывай контактные данные…

---

## 🧪 Тесты

```bash
pytest -q          # 68 passed, 1 skipped
```

| Файл | Что проверяет |
|------|---------------|
| `tests/test_validation.py` | Валидация обязательных полей брифа |
| `tests/test_price_guard.py` | Замена выдуманных цен и сроков |
| `tests/test_service.py` | Сквозной сценарий: модель «галлюцинирует» → guard чинит |
| `tests/test_parsing.py` | Разбор ответа модели, типизация ошибок, `friendly_message` |
| `tests/test_pdf.py`, `tests/test_pdf_roundtrip.py` | PDF: кириллица и **совпадение с отредактированной версией** |
| `tests/test_storage.py` | SQLite, версии КП |
| `tests/test_ai_check.py` | Живая проверка подключения и подсказки по провайдерам |
| `tests/test_deploy.py` | В шаблонах развёртывания нет реальных ключей |

Пропускается только тест развёртывания в Docker — на машине без Docker.

---

## 📁 Структура проекта

```
fin_proekt/
├── app.py                  # точка входа Streamlit
├── pages/                  # 1_Бриф, 2_Черновик, 3_Предпросмотр, 4_История, 5_Настройки
├── src/
│   ├── ai/
│   │   ├── base.py         # абстракция LLM-провайдера + фабрика
│   │   ├── gigachat.py     # клиент GigaChat
│   │   ├── yandex.py       # клиент YandexGPT
│   │   ├── guard.py        # цены/сроки/ПДн/парсинг ответа
│   │   ├── errors.py       # типизированные ошибки + friendly_message
│   │   ├── prompts.py      # системный и пользовательский промпт
│   │   ├── service.py      # оркестрация генерации
│   │   └── check.py        # живая проверка подключения
│   ├── brief.py            # модель и валидация брифа
│   ├── proposal.py         # модель КП и версии
│   ├── template.py         # шаблон структуры КП
│   ├── price.py            # прайс — ЕДИНСТВЕННЫЙ источник цен
│   ├── pdf_export.py       # PDF (reportlab, кириллица)
│   ├── storage.py          # SQLite
│   ├── deploy.py           # файлы развёртывания
│   ├── app_state.py        # роли, сессия, адаптивный CSS
│   └── logging_util.py     # логи вызовов ИИ без ПДн
├── scripts/                # ключи GigaChat, тест ИИ, демо-данные
├── tests/                  # pytest
└── docs/                   # отчёт-кейс и скриншоты
```

---

## 🚀 Развёртывание

Встроенная кнопка **Deploy** в правом верхнем углу Streamlit скрыта настройкой
`client.toolbarMode = "viewer"` — её англоязычное меню зашито в код Streamlit и не
переводится. Вместо неё на странице **«5 · Настройки»** → вкладка **«🚀 Развёртывание»**
есть те же команды по-русски: скачать `requirements.txt`, `Dockerfile`, `packages.txt`
и шаблон `.streamlit/secrets.toml` (только плейсхолдеры — реальные ключи туда не попадают,
это проверяется тестом).

Поддерживается **Streamlit Community Cloud**: положите файлы в корень, секреты задайте
во вкладке «Secrets».

---

## 📄 Документация

- [`AGENTS.md`](AGENTS.md) — спецификация продукта и правила проекта.
- [`ТЗ.md`](ТЗ.md) — техническое задание.
- [`docs/case_report.md`](docs/case_report.md) — отчёт-кейс: проблема → MVP → реализация → проверка → развитие, и разбор работы ИИ.

---

## 📄 Лицензия

MIT
