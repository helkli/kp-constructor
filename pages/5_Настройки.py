"""Страница 5 · Настройки (роль «Руководитель»): прайс услуг, шаблон КП, проверка ИИ."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import config, deploy
from src.app_state import (
    DIRECTOR,
    get_storage,
    is_director,
    render_sidebar,
)
from src.price import price_number_label
from src.ai.check import check_ai_connection, connection_hints

st.set_page_config(page_title="5 · Настройки", page_icon="⚙️", layout="wide")
render_sidebar()
storage = get_storage()

st.title("5 · Настройки")

if not is_director():
    st.error(
        f"Доступ только для роли «{DIRECTOR}». Переключите роль в сайдбаре."
    )
    st.stop()

tab_price, tab_template, tab_ai, tab_deploy = st.tabs(
    [
        "💲 Прайс услуг",
        "📐 Шаблон структуры КП",
        "🤖 Подключение к ИИ",
        "🚀 Развёртывание",
    ]
)

# ================= ПРАЙС =================
with tab_price:
    services = storage.list_services(active_only=False)
    st.subheader("Прайс услуг")
    st.table(
        {
            "ID": [s["id"] for s in services],
            "Услуга": [s["name"] for s in services],
            "Цена": [price_number_label(s["price"], s.get("unit") or "") for s in services],
            "Активна": ["да" if s["active"] else "нет" for s in services],
        }
    )

    mode = st.radio("Действие", ["➕ Добавить услугу", "✏️ Изменить услугу"], horizontal=True)
    if mode.startswith("➕"):
        with st.form("add_service"):
            name = st.text_input("Название услуги")
            price = st.text_input(
                "Цена (₽), пусто = «цена уточняется»", placeholder="12000"
            )
            unit = st.text_input("Единица (опционально)", placeholder="мес / рабочее место")
            active = st.checkbox("Активна", value=True)
            save = st.form_submit_button("Сохранить услугу")
        if save:
            if not name.strip():
                st.error("Укажите название услуги.")
            else:
                storage.upsert_service(name, price_or_none(price), unit, active)
                st.success(f"Услуга «{name.strip()}» добавлена.")
                st.rerun()
    else:
        by_id = {s["id"]: s for s in services}
        sel_sid = st.selectbox(
            "Выберите услугу",
            options=list(by_id.keys()),
            format_func=lambda sid: by_id[sid]["name"],
        )
        chosen = by_id[sel_sid]
        with st.form("edit_service"):
            name = st.text_input("Название", value=chosen["name"])
            price = st.text_input(
                "Цена (₽), пусто = «цена уточняется»",
                value=("" if chosen["price"] is None else str(chosen["price"])),
            )
            unit = st.text_input("Единица", value=chosen.get("unit") or "")
            active = st.checkbox("Активна", value=bool(chosen["active"]))
            save = st.form_submit_button("Сохранить изменения")
        if save:
            storage.upsert_service(name, price_or_none(price), unit, active, sel_sid)
            st.success("Изменения сохранены.")
            st.rerun()
    st.caption(
        "Мягкая деактивация: услуга пропадает из брифа, но исторические КП остаются "
        "валидными."
    )

# ================= ШАБЛОН =================
with tab_template:
    tmpl = storage.get_active_template()
    st.subheader(f"Шаблон: {tmpl['name']}")
    st.caption(
        "Разделы с инструкциями для модели. Изменения применяются к следующим "
        "генерациям."
    )

    sections = tmpl["sections"]
    for i, sec in enumerate(sections):
        with st.expander(f"{i + 1}. {sec['header']}", expanded=True):
            sec["header"] = st.text_input("Заголовок", value=sec["header"], key=f"tpl_h_{i}")
            sec["instruction"] = st.text_area(
                "Инструкция для модели", value=sec["instruction"], height=80,
                key=f"tpl_i_{i}",
            )
            st.markdown("---")

    c_add, c_save, c_up, c_down = st.columns([1, 1, 1, 1])
    if c_add.button("➕ Добавить раздел после последнего"):
        sections.append({"header": "Новый раздел", "instruction": "Опишите раздел."})
        st.rerun()
    if c_up.button("⬆ Поднять последний"):
        if len(sections) > 1:
            sections[-1], sections[-2] = sections[-2], sections[-1]
            st.rerun()
    if c_down.button("⬇ Опустить первый"):
        if len(sections) > 1:
            sections[0], sections[1] = sections[1], sections[0]
            st.rerun()
    if c_save.button("💾 Сохранить шаблон", type="primary"):
        cleaned = [
            {"header": s["header"].strip(), "instruction": s["instruction"].strip()}
            for s in sections
            if s["header"].strip()
        ]
        if not cleaned:
            st.error("Шаблон не может быть пустым.")
        else:
            storage.save_template(tmpl["name"], cleaned)
            st.success("Шаблон сохранён.")


# ================= ПОДКЛЮЧЕНИЕ К ИИ =================
with tab_ai:
    st.subheader("Проверка подключения к ИИ")
    st.caption(
        "Отправляет короткий тестовый запрос к модели и показывает результат. "
        "Ключи и персональные данные не выводятся."
    )
    st.write(
        f"Провайдер из .env: **{config.AI_PROVIDER}** · "
        f"таймаут: {int(config.AI_TIMEOUT)} с на запрос"
    )
    if st.button("🔌 Проверить подключение", type="primary"):
        with st.spinner("Отправляю тестовый запрос к модели…"):
            result = check_ai_connection()
        if result["ok"]:
            st.success(
                f"Подключение работает: {result['provider']} (модель: {result['model']})."
            )
            st.write(f"Ответ модели: *«{result['answer']}»*")
        elif result["error_type"] == "NotConfigured":
            st.error(result["error_message"])
        else:
            st.error(
                f"{result['error_message']} "
                f"([{result['error_type']}])"
            )
            if result["error_detail"]:
                with st.expander("Технические детали ответа API"):
                    st.code(result["error_detail"][:2000], language="text")
            st.info(connection_hints(result["provider"]).replace("\n", "  \n"))


# ================= РАЗВЁРТЫВАНИЕ =================
with tab_deploy:
    st.subheader("Файлы для развёртывания — на русском")
    st.caption(
        "Встроенная кнопка «Deploy» в правом верхнем углу Streamlit скрыта "
        "настройкой `client.toolbarMode=\"viewer\"`: её англоязычное меню зашито "
        "в код Streamlit и не переводится. Ниже — те же команды по-русски: "
        "скачайте нужные файлы и положите в корень проекта."
    )
    st.info(
        "Streamlit Community Cloud сам генерирует requirements.txt, Dockerfile и "
        "packages.txt, если их нет. Секреты загружаются во вкладке «Secrets» "
        "настроек приложения в облаке — их формат соответствует "
        "`.streamlit/secrets.toml`."
    )

    for name, factory in deploy.DEPLOY_FILES.items():
        text = factory()
        state = (
            "✅ файл уже есть в проекте"
            if deploy.file_exists(name)
            else "файла в проекте нет — скачайте пример"
        )
        st.markdown(f"**`{name}`** — {state}")
        col_dl, col_show = st.columns([1, 3])
        fname = "secrets.toml" if name.endswith("secrets.toml") else name
        col_dl.download_button(
            f"📥 Скачать {fname}",
            data=text,
            file_name=fname,
            mime="text/plain",
            key=f"deploy_dl_{name.replace('.', '_').replace('/', '_')}",
        )
        with col_show.expander("Показать содержимое"):
            st.code(text, language="text")
        st.divider()

    st.caption(
        "Файл `.streamlit/secrets.toml` — это только пример с плейсхолдерами: "
        "скопируйте в него СВОИ значения из `.env`. Реальные ключи в репозиторий "
        "и в логи не попадают."
    )


def price_or_none(raw: str):
    """Цена из строки: пусто/мусор -> None (будет «цена уточняется»)."""
    raw = (raw or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None