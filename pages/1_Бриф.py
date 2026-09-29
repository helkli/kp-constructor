"""Страница 1 · Бриф: форма с валидацией обязательных полей, запуск генерации."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import config
from src.ai.errors import AIError, friendly_message
from src.ai.service import generate_proposal_sections, services_for_brief_ids
from src.app_state import (
    BRIEF_KEY,
    get_brief,
    get_proposal,
    get_storage,
    render_sidebar,
    set_brief,
    set_proposal,
)
from src.brief import Brief, validate
from src.price import price_number_label
from src.proposal import Proposal, Section

st.set_page_config(page_title="1 · Бриф", page_icon="📋", layout="wide")
render_sidebar()
storage = get_storage()

st.title("1 · Бриф")

services = storage.list_services(active_only=True)
if not services:
    st.warning(
        "В прайсе нет активных услуг. Попросите руководителя добавить услуги на "
        "странице «5 · Настройки»."
    )
    st.stop()

service_options = {s["id"]: s for s in services}
service_labels = {
    s["id"]: f"{s['name']} — {price_number_label(s['price'], s.get('unit') or '')}"
    for s in services
}

prev = get_brief()
prev_ids = list(prev.service_ids) if prev else []

with st.form("brief_form", clear_on_submit=False):
    client = st.text_input(
        "Клиент *", value=(prev.client if prev else ""),
        placeholder="ООО «Ромашка»",
        help="Компания клиента",
    )
    task = st.text_area(
        "Задача клиента *", value=(prev.task if prev else ""), height=110,
        placeholder="Опишите задачу/проблему клиента",
    )
    selected = st.multiselect(
        "Услуги *",
        options=[s["id"] for s in services],
        default=prev_ids,
        format_func=lambda sid: service_labels[sid],
        help="Выбор из прайса. Если у услуги нет цены — в КП появится «цена уточняется».",
    )
    deadline = st.text_input(
        "Сроки *", value=(prev.deadline if prev else ""),
        placeholder="2 недели / до 30.06 / январь–март",
    )
    budget = st.text_input(
        "Бюджет (необязательно)", value=(prev.budget if prev else ""),
        placeholder="200 000 ₽",
        help="Указывается в КП только если заполнен.",
    )
    submitted = st.form_submit_button("🚀 Сгенерировать черновик КП", type="primary")

if not submitted:
    st.info(
        "Заполните бриф и нажмите «Сгенерировать». Сначала пройдёт валидация, и "
        "только потом — вызов ИИ."
    )
    st.stop()

brief = Brief(
    client=client.strip(),
    task=task.strip(),
    service_ids=[int(i) for i in selected],
    deadline=deadline.strip(),
    budget=budget.strip(),
)

errors = validate(brief)
if errors:
    st.error("Проверьте обязательные поля:")
    for e in errors:
        st.write(f"- {e}")
    st.stop()

if not config.provider_configured():
    st.error(
        "API-ключ ИИ не настроен. Скопируйте .env.example в .env, укажите "
        "AI_PROVIDER и ключ (GIGACHAT_API_KEY), затем перезапустите приложение."
    )
    st.stop()

selected_services = [service_options[sid] for sid in brief.service_ids]
with st.spinner("ИИ собирает черновик КП по разделам шаблона…"):
    try:
        result = generate_proposal_sections(
            storage, brief, selected_services
        )
    except AIError as exc:
        st.error(friendly_message(exc))
        set_brief(brief)  # не теряем бриф (критерий A10)
        st.stop()

brief.id = storage.create_brief(
    brief.client, brief.task, brief.deadline, brief.budget, brief.service_ids
)
set_brief(brief)

version = storage.next_version(brief.id)
proposal_id = storage.create_proposal(
    brief.id, version, "draft", result.sections, result.pricing
)
proposal = Proposal(
    id=proposal_id,
    brief_id=brief.id,
    version=version,
    status="draft",
    sections=[Section(**s) for s in result.sections],
    pricing=result.pricing,
    created_at="",
)
set_proposal(proposal)

if result.warnings:
    with st.expander("⚠️ Замечания guard-слоя"):
        for w in result.warnings:
            st.warning(w)

st.success("Черновик готов! Переходим в редактор…")
st.switch_page("pages/2_Черновик.py")