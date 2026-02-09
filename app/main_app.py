import sys
from pathlib import Path
import os
from dotenv import load_dotenv

import streamlit as st

# Load environment variables from .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Ensure project root is on sys.path so that `app` and sibling packages can be imported
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.rag_pipeline import RAGConfig, RAGPipeline
from vector_store.retriever import RetrievalConfig


@st.cache_resource(show_spinner=False)
def get_pipeline(top_k: int, score_threshold: float | None) -> RAGPipeline:
    rag_config = RAGConfig(
        top_k=top_k,
        score_threshold=score_threshold,
    )
    return RAGPipeline(rag_config=rag_config)


def ensure_session_state() -> None:
    if "history" not in st.session_state:
        st.session_state["history"] = []


def main() -> None:
    st.set_page_config(
        page_title="AI Personal Knowledge Base Assistant",
        layout="wide",
    )

    ensure_session_state()

    st.title("AI Personal Knowledge Base Assistant")
    st.write(
        "Ask questions over your Notion pages and Google Drive documents. "
        "Answers are grounded in your indexed content using Retrieval-Augmented Generation (RAG)."
    )

    with st.sidebar:
        st.header("Settings")

        top_k = st.slider("Top K Results", min_value=1, max_value=10, value=5)
        use_threshold = st.checkbox("Use score threshold", value=False)
        threshold_val = (
            st.slider("Score threshold (distance)", min_value=0.0, max_value=2.0, value=1.0, step=0.05)
            if use_threshold
            else None
        )

        pipeline = get_pipeline(top_k=top_k, score_threshold=threshold_val)

        st.markdown("---")
        st.subheader("Index Management")
        if st.button("Run full ingestion & indexing"):
            with st.spinner("Ingesting from Notion and Google Drive, then indexing into Chroma..."):
                docs = pipeline.run_full_ingestion()
            st.success(f"Ingestion complete. Indexed {len(docs)} documents.")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Ask a question")
        question = st.text_area(
            "Your question",
            placeholder="e.g. What are my key project milestones next quarter?",
        )

        if st.button("Get answer", type="primary"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Retrieving context and querying Groq..."):
                    answer, retrieved = pipeline.answer_question(
                        question=question.strip(),
                        top_k=top_k,
                        score_threshold=threshold_val,
                    )

                st.session_state["history"].append(
                    {
                        "question": question.strip(),
                        "answer": answer,
                        "sources": retrieved,
                    }
                )

        # Show latest answer
        if st.session_state["history"]:
            last = st.session_state["history"][-1]
            st.markdown("### Latest Answer")
            st.markdown(last["answer"])

    with col_right:
        st.subheader("Retrieved Sources (latest)")

        if st.session_state["history"]:
            last = st.session_state["history"][-1]
            sources = last["sources"]
            if not sources:
                st.info("No sources retrieved yet. Try running ingestion or asking another question.")
            else:
                for i, chunk in enumerate(sources, start=1):
                    meta = chunk.metadata or {}
                    title = meta.get("title") or "Untitled"
                    source = meta.get("source") or "unknown"
                    url = meta.get("url") or ""
                    score = chunk.score

                    with st.expander(f"[Source {i}] {title} ({source}, score={score:.3f})"):
                        if url:
                            st.markdown(f"[Open in source]({url})")
                        st.write(chunk.content)
        else:
            st.info("Ask a question to see retrieved sources here.")

    st.markdown("---")
    st.subheader("Conversation History")
    if st.session_state["history"]:
        for idx, item in enumerate(reversed(st.session_state["history"]), start=1):
            st.markdown(f"**Q{idx}:** {item['question']}")
            st.markdown(f"**A{idx}:** {item['answer']}")
            st.markdown("---")
    else:
        st.write("No questions asked yet.")


if __name__ == "__main__":
    main()

