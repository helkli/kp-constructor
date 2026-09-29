"""Общие хелперы для Streamlit UI: хранилище, роли, состояние сессии."""
from __future__ import annotations

import streamlit as st

from src import config
from src.storage import Storage

ROLE_KEY = "app_role"
MANAGER = "Менеджер"
DIRECTOR = "Руководитель"
BRIEF_KEY = "brief"
PROPOSAL_KEY = "proposal"


@st.cache_resource
def get_storage() -> Storage:
    """Единственный экземпляр хранилища на всё приложение."""
    return Storage()


def get_role() -> str:
    return st.session_state.get(ROLE_KEY, MANAGER)


def is_director() -> bool:
    return get_role() == DIRECTOR


def get_brief():
    return st.session_state.get(BRIEF_KEY)


def set_brief(brief) -> None:
    st.session_state[BRIEF_KEY] = brief


def get_proposal():
    return st.session_state.get(PROPOSAL_KEY)


def set_proposal(proposal) -> None:
    st.session_state[PROPOSAL_KEY] = proposal


_MOBILE_CSS = """
<style>
/* Мобильная адаптация: Streamlit сам складывает columns в столбик и прячет
   сайдбар в бургер-меню, но таблицы без горизонтального скролла расползаются. */
@media (max-width: 820px) {
  .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  [data-testid="stTable"] { overflow-x: auto; max-width: 100%; }
  [data-testid="stTable"] table { min-width: 420px; width: 100%; }
  pre, div[data-testid="stCodeBlock"] { white-space: pre-wrap; word-break: break-word; }
  .stTitle { font-size: 1.6rem !important; }
}
</style>
"""


def inject_mobile_css() -> None:
    """Крошечный CSS для узких экранов (вызывается на каждой странице)."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def render_sidebar() -> None:
    """Роль + статус ИИ-провайдера в сайдбаре (виден на всех страницах)."""
    inject_mobile_css()
    idx = 0 if get_role() == MANAGER else 1
    role = st.sidebar.radio(
        "Роль",
        [MANAGER, DIRECTOR],
        index=idx,
        key="role_radio",
    )
    st.session_state[ROLE_KEY] = role

    st.sidebar.divider()
    provider = config.AI_PROVIDER
    ok = config.provider_configured()
    if ok:
        st.sidebar.success(f"ИИ: {provider} — ключ настроен")
    else:
        st.sidebar.warning(
            f"ИИ: {provider} — ключ не настроен. Добавьте ключ в .env "
            "(см. .env.example)."
        )
    st.sidebar.caption(f"Таймаут ИИ: {int(config.AI_TIMEOUT)} с на запрос")