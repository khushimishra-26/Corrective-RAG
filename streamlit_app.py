import uuid
import streamlit as st

st.set_page_config(page_title="Interview Preparation Assistant", page_icon="📘", layout="wide")
st.title("Interview Preparation Assistant")
st.caption("CS Core Concepts · LangGraph · FAISS · Groq · Tavily")


# Import the backend once per server process (loads PDF, builds FAISS index, compiles graph)
@st.cache_resource(show_spinner="Loading PDF and building the vector index (first run only)...")
def load_rag():
    from rag_backend import rag
    return rag


rag = load_rag()

# ---------- session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

VERDICT_BADGE = {
    "CORRECT": "🟢 CORRECT (answered from the PDF)",
    "INCORRECT": "🔴 INCORRECT (answered from web search)",
    "AMBIGUOUS": "🟡 AMBIGUOUS (PDF + web search)",
}


def render_details(d: dict):
    """Show the intermediate graph state for one answer."""
    with st.expander("How this answer was produced"):
        st.markdown(f"**Verdict:** {VERDICT_BADGE.get(d['verdict'], d['verdict'])}")
        st.markdown(f"**Reason:** {d['reason']}")
        if d.get("web_query"):
            st.markdown(f"**Web query:** `{d['web_query']}`")
        st.markdown(f"**Sentences kept after filtering:** {len(d['kept_strips'])} / {len(d['strips'])}")
        if d["kept_strips"]:
            st.text_area("Refined context", "\n".join(d["kept_strips"]), height=200,
                         key=f"ctx-{d['id']}")
        if d.get("web_sources"):
            st.markdown("**Web sources:**")
            for s in d["web_sources"]:
                st.markdown(f"- [{s['title'] or s['url']}]({s['url']})")


# ---------- sidebar ----------
with st.sidebar:
    st.header("Session")
    st.code(st.session_state.thread_id[:8], language=None)
    if st.button("🗑️ New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# ---------- chat history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("details"):
            render_details(m["details"])

# ---------- new question ----------
question = st.chat_input("Ask a question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving, evaluating and refining..."):
            try:
                result = rag.invoke(
                    {
                        "question": question,
                        "docs": [],
                        "good_docs": [],
                        "verdict": "",
                        "reason": "",
                        "strips": [],
                        "kept_strips": [],
                        "refined_context": "",
                        "web_query": "",
                        "web_docs": [],
                        "answer": "",
                    },
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()

        answer = result["answer"]
        st.markdown(answer)

        details = {
            "id": str(uuid.uuid4()),
            "verdict": result["verdict"],
            "reason": result["reason"],
            "web_query": result.get("web_query", ""),
            "strips": result["strips"],
            "kept_strips": result["kept_strips"],
            "web_sources": [
                {"title": d.metadata.get("title", ""), "url": d.metadata.get("url", "")}
                for d in result.get("web_docs", [])
            ] if result["verdict"] != "CORRECT" else [],
        }
        render_details(details)

    st.session_state.messages.append({"role": "assistant", "content": answer, "details": details})