import uuid
from pathlib import Path

import streamlit as st
from langgraph.types import Command

from doccopilot.graph import build_graph
from doccopilot.steps import JsonLLM

st.set_page_config(page_title="Doc Copilot", page_icon="📄")
st.title("Doc Copilot")
st.caption("Tell it what document you need. It asks for whatever is missing, checks the details with you, "
           "then writes the Word file. Supports experience letters, offer letters and mutual NDAs.")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph(JsonLLM())
    st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    st.session_state.chat = []
    st.session_state.started = False
    st.session_state.file = None

for role, text in st.session_state.chat:
    st.chat_message(role).write(text)

if st.session_state.file:
    path = Path(st.session_state.file)
    st.download_button("Download .docx", path.read_bytes(), file_name=path.name)
    if st.button("Start a new document"):
        for k in ["graph", "config", "chat", "started", "file"]:
            st.session_state.pop(k)
        st.rerun()

elif msg := st.chat_input("e.g. An experience letter for Sara Khan, data analyst at Northwind from Jan 2025"):
    graph, config = st.session_state.graph, st.session_state.config
    st.session_state.chat.append(("user", msg))
    with st.spinner("working..."):
        if not st.session_state.started:
            result = graph.invoke({"conversation": [msg]}, config)
            st.session_state.started = True
        else:
            result = graph.invoke(Command(resume=msg), config)
    if "__interrupt__" in result:
        st.session_state.chat.append(("assistant", result["__interrupt__"][0].value["question"]))
    else:
        st.session_state.chat.append(("assistant", result.get("message", "")))
        st.session_state.file = result.get("output_path")
    st.rerun()
