import sys
from pathlib import Path
import os
import json
from dotenv import load_dotenv

import streamlit as st

# Load environment variables from .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.rag_pipeline import RAGConfig, RAGPipeline

HISTORY_FILE = ROOT_DIR / "chat_history.json"

# Page Configuration
st.set_page_config(
    page_title="AI Knowledge Base",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, premium look
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 1.5rem !important;
        border-radius: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    .stChatMessage[data-testid="user-message"] {
        background-color: #1e1e1e !important;
    }
    .stChatMessage[data-testid="assistant-message"] {
        background-color: transparent !important;
    }
    
    /* Chat Input */
    .stChatInput {
        border-radius: 1.5rem !important;
        border: 1px solid #333 !important;
        background-color: #1e1e1e !important;
        color: #fff !important;
    }
    .stChatInput:focus-within {
        border-color: #4a90e2 !important;
        box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2) !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #238636;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background-color: #2ea043;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Typography */
    h1, h2, h3 {
        color: #ffffff;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    /* Code Blocks */
    code {
        background-color: #2d333b !important;
        color: #adbac7 !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> RAGPipeline:
    # Use dynamic top_k=10 but filter with strict threshold (0.6 distance = 40% similarity)
    # This allows 1-10 results depending on relevance.
    return RAGPipeline(rag_config=RAGConfig(top_k=10, score_threshold=0.6))


def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(messages):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2)
    except Exception as e:
        print(f"Failed to save history: {e}")

def main() -> None:
    # --- Session State Management ---
    if "messages" not in st.session_state:
        st.session_state.messages = load_history()

    # --- Sidebar ---
    with st.sidebar:
        st.title("Settings & Tools")
        st.markdown("Manage your knowledge base connection.")
        
        if st.button("🔄 Sync/Refresh Data"):
            with st.spinner("Syncing latest data (this invalidates old embeddings)..."):
                # Clear existing index in memory to ensure clean slate with new embeddings
                pipeline = get_pipeline()
                pipeline.store.data = {} 
                pipeline.store._save()
                
                try:
                    docs = pipeline.run_full_ingestion()
                    st.success(f"✅ Synced {len(docs)} documents. (Index rebuilt)")
                except Exception as e:
                    st.error(f"Sync failed: {e}")
        
        st.info("💡 **Tip:** Add pages to Notion or files to Drive, then click Sync to update.")

        st.markdown("---")
        st.header("📜 Chat History")
        
        # New Chat / Clear History
        if st.button("➕ New Chat"):
            st.session_state.messages = []
            save_history([])
            st.rerun()

        # List previous questions
        # Filter for user messages to show in history list
        user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
        if user_msgs:
            for i, msg in enumerate(reversed(user_msgs), 1):
                # Truncate long questions
                display_text = (msg["content"][:40] + '..') if len(msg["content"]) > 40 else msg["content"]
                st.caption(f"{i}. {display_text}")
        else:
            st.caption("No history yet.")

    # --- Main Chat Interface ---
    st.markdown('<h1 style="text-align: center; margin-bottom: 2rem;">✨ AI Personal Assistant</h1>', unsafe_allow_html=True)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your projects, notes, or docs..."):
        # 1. User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare history for the model
                history_for_model = []
                for msg in st.session_state.messages[:-1]:
                    if msg.get("role") in ("user", "assistant"):
                        history_for_model.append({
                            "role": msg["role"], 
                            "content": msg["content"]
                        })

                pipeline = get_pipeline()
                
                # Try-catch to handle potential caching issues
                try:
                    answer, retrieved = pipeline.answer_question(
                        question=prompt,
                        history=history_for_model
                    )
                except TypeError:
                    # Fallback for cached objects
                    st.cache_resource.clear()
                    pipeline = get_pipeline()
                    answer, retrieved = pipeline.answer_question(
                        question=prompt,
                        history=history_for_model
                    )
                
                # Format sources for display
                sources_md = ""
                if retrieved:
                    sources_md = "\n\n---\n**📚 Sources:**\n"
                    seen_sources = set()
                    for chunk in retrieved: # Show all valid retrieved sources
                        meta = chunk.metadata or {}
                        title = meta.get("title") or "Untitled"
                        if title not in seen_sources:
                            url = meta.get("url")
                            link = f"[{title}]({url})" if url else title
                            sources_md += f"- {link}\n"
                            seen_sources.add(title)

                full_response = answer + sources_md
                st.markdown(full_response)
                
        # 3. Add to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        # Save to file
        save_history(st.session_state.messages)

if __name__ == "__main__":
    main()
