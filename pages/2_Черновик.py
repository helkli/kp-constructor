"""Страница 2 · Черновик: редактор разделов, версии, перегенерация."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.ai.errors import AIError, friendly_message
from src.ai.service import generate_proposal_sections, services_for_brief_ids
from src.app_state import (
    get_brief,
    get_proposal,
    get_storage,
    render_sidebar,
    set_proposal,
)
from src.proposal import Section

st.set_page_config(page_title="2 · Черновик", page_icon="📝", layout="wide")
render_sidebar()
storage = get_storage()

brief = get_brief()
proposal = get_proposal()

if proposal is None or brief is None:
    st.info("Сначала заполните бриф и сгенерируйте черновик.")
    if st.button("К брифу →", type="primary"):
        st.switch_page("pages/1_Бриф.py")
    st.stop()

st.title("2 · Черновик КП")
st.caption(
    f"Клиент: **{brief.client}** · версия **v{proposal.version}** · "
    f"статус: {'финал' if proposal.status == 'final' else 'черновик'}"
)

services = services_for_brief_ids(storage, brief.service_ids)

_revision = getattr(proposal, "revision", 0)


def _collect_edited_sections() -> None:
    """Переносит текст из виджетов редактора в proposal (сохранение правок)."""
    rev = getattr(proposal, "revision", 0)
    for i, sec in enumerate(proposal.sections):
        sec.body = st.session_state.get(f"draft_sec_{i}_r{rev}", sec.body)


def _bump_revision() -> None:
    proposal.revision = getattr(proposal, "revision", 0) + 1


# --- Редактор разделов ---
# Ключ виджета привязан к "ревизии" КП: после перегенерации revision растёт,
# виджеты создаются заново и показывают новый текст (иначе Streamlit оставляет
# устаревшее значение виджета в session_state).
regen_target = None
for i, sec in enumerate(proposal.sections):
    st.markdown(f"### {sec.header}")
    st.text_area(
        f"Содержимое: {sec.header}",
        value=sec.body,
        key=f"draft_sec_{i}_r{_revision}",
        height=140,
        label_visibility="collapsed",
    )
    col_gen, col_info = st.columns([1, 5])
    if col_gen.button("⟳ Перегенерировать раздел", key=f"regen_btn_{i}"):
        regen_target = sec.header
    if col_info.caption(f"Раздел {i + 1} из {len(proposal.sections)}"):
        pass
    if not sec.body.strip():
        st.warning("Раздел пуст. Нажмите «⟳ Перегенерировать раздел».")

if regen_target:
    # Сначала фиксируем правки во всех разделах, чтобы их не потерять.
    _collect_edited_sections()
    with st.spinner(f"Перегенерируем раздел «{regen_target}»…"):
        try:
            result = generate_proposal_sections(
                storage, brief, services, only_header=regen_target
            )
        except AIError as exc:
            st.error(friendly_message(exc))
        else:
            new_section = result.sections[0]
            for sec in proposal.sections:
                if sec.header == regen_target:
                    sec.body = new_section["body"]
            _bump_revision()
            set_proposal(proposal)
            st.toast(f"Раздел «{regen_target}» обновлён.")
    st.rerun()

# --- Действия ---
st.divider()
c_save, c_preview, c_final, c_up = st.columns([1, 1, 1, 1])

if c_save.button("💾 Сохранить новую версию", type="primary", use_container_width=True):
    _collect_edited_sections()
    new_version = storage.next_version(proposal.brief_id)
    new_id = storage.create_proposal(
        proposal.brief_id, new_version, "draft", proposal.sections, proposal.pricing
    )
    proposal.id = new_id
    proposal.version = new_version
    proposal.status = "draft"
    set_proposal(proposal)
    st.success(f"Сохранено как версия v{new_version} (история версий сохранена).")

if c_preview.button("📄 Предпросмотр и PDF", use_container_width=True):
    st.switch_page("pages/3_Предпросмотр.py")

if c_final.button("✅ Отметить финалом", use_container_width=True):
    if proposal.id:
        storage.update_proposal_status(proposal.id, "final")
        proposal.status = "final"
        set_proposal(proposal)
        st.success("КП помечено как финальное.")

if c_up.button("↻ Генерация заново (весь текст)", use_container_width=True):
    _collect_edited_sections()
    with st.spinner("ИИ перегенерирует весь черновик…"):
        try:
            result = generate_proposal_sections(storage, brief, services)
        except AIError as exc:
            st.error(friendly_message(exc))
        else:
            proposal.sections = [Section(**s) for s in result.sections]
            proposal.pricing = result.pricing
            new_version = storage.next_version(proposal.brief_id)
            new_id = storage.create_proposal(
                proposal.brief_id, new_version, "draft", proposal.sections, proposal.pricing
            )
            proposal.id = new_id
            proposal.version = new_version
            _bump_revision()
            set_proposal(proposal)
            st.toast("Черновик перегенерирован как новая версия.")
    st.rerun()