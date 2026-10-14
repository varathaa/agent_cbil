import streamlit as st

import config
import db
from agent import run_agent

st.set_page_config(page_title="CIBIL Check Agent", page_icon="??")
st.title("CIBIL Check Agent")
st.caption("Ask e.g. *Check CIBIL for customer C1001* or *CIBIL details for mobile 9876543210*")

with st.sidebar:
    st.markdown(f"**Model:** `{config.OLLAMA_MODEL}`")
    if st.button("Test DB connection"):
        if db.check_connection():
            st.success("Oracle connected")
        else:
            st.error("Oracle connection failed")
    if st.button("Clear chat"):
        st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("record"):
            with st.expander("Database record"):
                st.json(msg["record"])

if prompt := st.chat_input("Enter customer ID or mobile number to check CIBIL"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Fetching details and analysing..."):
            try:
                answer, record = run_agent(prompt)
            except Exception as e:
                answer, record = f"Error: {e}", {}
        st.markdown(answer)
        if record:
            with st.expander("Database record"):
                st.json(record, expanded=True)
    st.session_state.messages.append({"role": "assistant", "content": answer, "record": record})
