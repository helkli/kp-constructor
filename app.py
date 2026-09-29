"""AI-конструктор коммерческих предложений — точка входа.

Запуск: streamlit run app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from src.app_state import DIRECTOR, MANAGER, get_storage, render_sidebar

st.set_page_config(page_title="AI-конструктор КП", page_icon="🤖", layout="wide")
storage = get_storage()
render_sidebar()

st.title("🤖 AI-конструктор коммерческих предложений")
st.caption(
    "Сервисная компания · менеджер заполняет бриф — ИИ собирает черновик КП "
    "по шаблону — человек проверяет и выгружает PDF."
)

col1, col2, col3 = st.columns(3)
col1.metric("Брифов", len(storage.list_briefs()))
col2.metric("Версий КП", len(storage.list_proposals()))
col3.metric("Вызовов ИИ (лог)", storage._conn.execute("SELECT COUNT(*) FROM ai_logs").fetchone()[0])

st.divider()

st.subheader("Как это работает")
steps = [
    ("1 · Бриф", "Заполните клиента, задачу, услуги из прайса, сроки и бюджет. "
                 "Проверка обязательных полей до вызова ИИ."),
    ("2 · Черновик", "ИИ пишет текст по разделам шаблона. Цены и сроки подставляются "
                     "только кодом из прайса и брифа. Редактируйте вручную."),
    ("3 · Предпросмотр и PDF", "Проверьте итоговый вид и скачайте PDF, идентичный "
                               "отредактированной версии."),
    ("4 · История", "Все версии КП с датой и статусом."),
    ("5 · Настройки", f"Руководитель: прайс и шаблон структуры (доступно в роли «{DIRECTOR}»)."),
]
for i, (title, text) in enumerate(steps, 1):
    with st.expander(title, expanded=(i == 1)):
        st.write(text)

st.divider()
c1, c2 = st.columns([1, 1])
if c1.button("🚀 Начать — заполнить бриф", type="primary", use_container_width=True):
    st.switch_page("pages/1_Бриф.py")
if c2.button("📚 История КП", use_container_width=True):
    st.switch_page("pages/4_История.py")

st.caption(f"Текущая роль: {getattr(st.session_state, 'app_role', MANAGER)}. "
           f"Настройки шаблона и прайса доступны руководителю.")