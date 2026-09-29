"""Страница 3 · Предпросмотр и PDF.

PDF строится из prepare_document() — единого источника контента, поэтому
дословно совпадает с отредактированной версией (критерий A1).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.app_state import (
    get_brief,
    get_proposal,
    get_storage,
    render_sidebar,
    set_proposal,
)
from src.pdf_export import PdfFontError, create_pdf, prepare_document, safe_filename

st.set_page_config(page_title="3 · Предпросмотр и PDF", page_icon="📄", layout="wide")
render_sidebar()
storage = get_storage()

brief = get_brief()
proposal = get_proposal()

if proposal is None or brief is None:
    st.info("Сначала заполните бриф и сгенерируйте черновик.")
    if st.button("К брифу →", type="primary"):
        st.switch_page("pages/1_Бриф.py")
    st.stop()

doc = prepare_document(
    brief.client,
    proposal.version,
    proposal.created_at,
    [{"header": s.header, "body": s.body} for s in proposal.sections],
    proposal.pricing,
)

st.title("3 · Предпросмотр и PDF")
st.caption(
    f"Клиент: **{brief.client}** · версия **v{proposal.version}** · "
    f"статус: {'финал' if proposal.status == 'final' else 'черновик'}",
)

# --- Рендер так же, как в PDF ---
st.markdown("---")
st.markdown("## Коммерческое предложение")
st.markdown(f"**Клиент:** {doc['client']}")
st.markdown(f"**Версия:** v{doc['version']} · **Дата:** {doc['created_at']}")
st.markdown("---")

for sec in doc["sections"]:
    st.markdown(f"### {sec['header']}")
    for chunk in (sec["body"] or "").split("\n"):
        chunk = chunk.strip()
        if chunk:
            st.write(chunk)

if doc["pricing"]:
    st.markdown("### Состав работ и стоимость")
    st.table(
        {
            "Услуга": [r["name"] for r in doc["pricing"]],
            "Стоимость": [r["price_text"] for r in doc["pricing"]],
        }
    )

# --- Кнопки ---
st.divider()
c_pdf, c_back, c_final = st.columns([1, 1, 1])
try:
    pdf_bytes = create_pdf(doc)
    c_pdf.download_button(
        "⬇️ Скачать PDF",
        data=pdf_bytes,
        file_name=safe_filename(brief.client, proposal.version),
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
except PdfFontError as exc:
    c_pdf.error(str(exc))

if c_back.button("← В редактор", use_container_width=True):
    st.switch_page("pages/2_Черновик.py")

if c_final.button("✅ Отметить финалом", use_container_width=True):
    if proposal.id:
        storage.update_proposal_status(proposal.id, "final")
        proposal.status = "final"
        set_proposal(proposal)
        st.success("КП помечено как финальное.")
        st.rerun()