"""Страница 4 · История КП: список версий, открытие в редакторе."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.app_state import (
    get_storage,
    render_sidebar,
    set_brief,
    set_proposal,
)
from src.proposal import Proposal, Section

st.set_page_config(page_title="4 · История", page_icon="📚", layout="wide")
render_sidebar()
storage = get_storage()

st.title("4 · История КП")

proposals = storage.list_proposals()
if not proposals:
    st.info("История пока пуста. Сгенерируйте первое КП на странице «1 · Бриф».")
    st.stop()

st.caption(f"Всего версий: {len(proposals)}")

_ppl = {p["id"]: p for p in proposals}
cols = st.columns([1, 4])
sel_id = cols[0].selectbox(
    "Выберите версию",
    options=[p["id"] for p in proposals],
    format_func=lambda pid: (
        f"v{_ppl[pid]['version']} · {_ppl[pid]['client'][:40]} · "
        f"{_ppl[pid]['created_at']} · {_ppl[pid]['status']}"
    ),
)
proposal_row = _ppl[sel_id]

if cols[1].button("📝 Открыть в редакторе", type="primary"):
    brief_row = storage.get_brief(proposal_row["brief_id"])
    brief_data = {
        "client": brief_row.get("client", ""),
        "task": brief_row.get("task", ""),
        "service_ids": brief_row.get("service_ids", []),
        "deadline": brief_row.get("deadline", ""),
        "budget": brief_row.get("budget", ""),
        "id": brief_row.get("id"),
    }
    from src.brief import Brief

    set_brief(Brief(**brief_data))
    set_proposal(
        Proposal(
            id=proposal_row["id"],
            brief_id=proposal_row["brief_id"],
            version=proposal_row["version"],
            status=proposal_row["status"],
            sections=[Section(**s) for s in Proposal.sections_from_json(proposal_row["sections_json"])],
            pricing=Proposal.pricing_from_json(proposal_row["pricing_json"]),
            created_at=proposal_row["created_at"],
        )
    )
    st.switch_page("pages/2_Черновик.py")

st.divider()
st.subheader("Список версий")
table_data = {
    "ID": [p["id"] for p in proposals],
    "Клиент": [p["client"] for p in proposals],
    "Версия": [f"v{p['version']}" for p in proposals],
    "Дата": [p["created_at"] for p in proposals],
    "Статус": [p["status"] for p in proposals],
}
st.table(table_data)

with st.expander("Подробнее о выбранной версии"):
    st.write(f"**Клиент:** {proposal_row['client']}")
    st.write(f"**Версия:** v{proposal_row['version']}")
    st.write(f"**Дата:** {proposal_row['created_at']}")
    st.write(f"**Статус:** {proposal_row['status']}")
    secs = Proposal.sections_from_json(proposal_row["sections_json"])
    for sec in secs:
        st.markdown(f"**{sec['header']}**")
        st.write(sec["body"][:600] + ("…" if len(sec["body"]) > 600 else ""))