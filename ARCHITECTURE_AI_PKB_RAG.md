## AI Personal Knowledge Base Assistant (RAG) – Architecture & Design

This document describes the architecture and implementation blueprint for building an **AI Personal Knowledge Base Assistant** using **RAG**, with:

- **Sources**: Notion + Google Drive  
- **LLM**: Groq (chat/completion)  
- **Vector DB**: ChromaDB  
- **Embeddings**: Free, local models (e.g. `sentence-transformers`)  
- **Frontend**: Streamlit  
- **Language**: Python

---

## 1. High-Level Overview

### 1.1 Goals

- **Centralized personal knowledge base** pulling from Notion and Google Drive.
- **RAG-based Q&A**: LLM answers questions grounded in your documents.
- **Interactive UI** via Streamlit, with:
  - Search and chat interface
  - Source document preview and citations
  - Controls for refresh / re-indexing data

### 1.2 Core Components

- **Ingestion & Normalization Layer**
  - Notion fetcher (pages, databases)
  - Google Drive fetcher (Docs, PDFs, text files)
  - Normalization into a common `Document` schema

- **Indexing & Vector Store Layer**
  - Text splitting / chunking
  - Free embedding model (e.g. `sentence-transformers/all-MiniLM-L6-v2` or `BAAI/bge-small-en-v1.5`)
  - ChromaDB collections with metadata

- **RAG Orchestration Layer**
  - Retrieval (top-k, score threshold)
  - Prompt construction (system + context + user question)
  - Groq LLM call for final answer

- **Application Layer (Streamlit)**
  - UI for:
    - Ask questions
    - View retrieved context
    - Trigger re-ingest / re-index
  - Session history for conversations

- **Configuration & Utilities**
  - `.env` for API keys and config
  - Logging, error handling, simple caching

---

## 2. Architecture Diagram (Conceptual)

Textual representation of the architecture:

- **User (Browser)**
  - ⇅ HTTP/WebSocket
- **Streamlit App (Python)**
  - **UI Components**
    - Sidebar settings (model options, retrieval parameters)
    - Main chat panel (question, answer, citations)
    - Indexing controls
  - **RAG Controller**
    - `query_pipeline(question)`:
      - Validate input
      - Call `retriever.retrieve(question)` → contexts
      - Build prompt → `GroqClient.chat(prompt, contexts)`
      - Return answer + contexts
  - **Ingestion Controller**
    - `run_full_ingestion()`
    - `run_incremental_ingestion()`
- **Ingestion Layer**
  - **NotionClient**
    - Fetch pages / databases via Notion API
  - **GoogleDriveClient**
    - List files in configured folders
    - Download + parse content (Docs, PDFs, text)
  - **Normalization**
    - Convert each item to `Document` object:
      - `id`, `source`, `source_id`, `title`, `text`, `created_at`, `updated_at`, `url/path`, `tags`…
- **Indexing Layer**
  - **Chunker**
    - Split `Document.text` into overlapping chunks
  - **EmbeddingModel**
    - Local, free embeddings using `sentence-transformers`
  - **VectorStore (ChromaDB)**
    - Collections per source or unified `personal_kb`
    - Store `chunk_id`, `document_id`, `content`, `metadata`, `embedding`
- **LLM Layer**
  - **GroqClient**
    - Encapsulates calls to Groq LLM (chat/completion endpoint)
    - Adds retry, logging, error handling

---

## 3. Data Model & Schemas

### 3.1 Document Schema (Logical)

**Fields**

- **id**: unique internal ID (UUID)
- **source**: `"notion"` or `"gdrive"`
- **source_id**: original ID (Notion page ID, Drive file ID)
- **title**: human-readable title
- **text**: full plain-text content (no chunking)
- **created_at**, **updated_at**
- **url**: Notion page URL or Google Drive share link
- **path**: for Drive, logical folder path
- **tags**: optional list of labels
- **metadata_raw**: optional raw metadata from source

This `Document` exists in memory or in a local metadata store (e.g. a simple SQLite file or JSON cache).

### 3.2 Chunk Schema (Stored in ChromaDB)

Per chunk, store:

- **id**: unique chunk ID (e.g. `"{doc_id}::chunk_{n}"`)
- **document_id**: link back to `Document.id`
- **content**: the chunked text
- **metadata**:
  - `source` (`notion` / `gdrive`)
  - `title`
  - `url`
  - `path` (for GDrive)
  - `source_id`
  - `chunk_index`
  - `created_at`, `updated_at`
  - any custom tags

---

## 4. Ingestion & Indexing

### 4.1 Notion Ingestion

#### 4.1.1 Auth & Access

- Create Notion internal integration.
- Obtain **Notion API key**.
- Share relevant pages/databases with the integration.
- Store in `.env` as `NOTION_API_KEY`.

#### 4.1.2 Scope

- Option 1: configure specific database IDs and page IDs in `.env`.
- Option 2: search via Notion API for all pages with a tag/property.

#### 4.1.3 Process

- Fetch each configured page/database.
- Flatten the content into plain text:
  - Title, headings, paragraph blocks, lists, tables (as text).
- Normalize into `Document` objects.

#### 4.1.4 Implementation Primitives

- **`NotionClient`**
  - `list_pages()` / `list_databases()`
  - `fetch_page_content(page_id) -> str`
- **`NotionIngestor`**
  - `ingest() -> List[Document]`

### 4.2 Google Drive Ingestion

#### 4.2.1 Auth & Access

- Create a Google Cloud project.
- Enable Google Drive API.
- Create OAuth 2.0 client credentials.
- Local token stored after first device auth flow.
- Store client secrets path in `.env`, e.g. `GOOGLE_CLIENT_SECRETS_PATH`.

#### 4.2.2 Scope

- Specific folders (e.g. `GDRIVE_ROOT_FOLDER_ID`).
- File types:
  - Google Docs (export as text).
  - PDFs (use `pdfplumber` / `pypdf` to extract).
  - Plain text (`.txt`, `.md`, `.rst`).
  - Optionally: `.docx` via `python-docx`.

#### 4.2.3 Process

- Walk target folders recursively.
- For each allowed file:
  - Export or download content.
  - Extract text using appropriate parser.
- Normalize into `Document` objects.

#### 4.2.4 Implementation Primitives

- **`GoogleDriveClient`**
  - `list_files(folder_id)` with mime filters.
  - `download_file(file_id, mime_type)`.
  - `export_google_doc_to_text(file_id)`.
- **`GoogleDriveIngestor`**
  - `ingest() -> List[Document]`

### 4.3 Text Chunking

#### 4.3.1 Goal

Create semantically coherent chunks that fit into LLM context, with some overlap for continuity.

#### 4.3.2 Strategy

- Use a character-based splitter (e.g. 500–1000 tokens equivalent; 800–1500 characters as a heuristic) with:
  - **Chunk size**: ~800–1200 tokens (or ~3000–4000 characters).
  - **Chunk overlap**: ~10–20% to preserve continuity.
- Respect sentence boundaries when possible using `nltk` or `spacy` (optional).

#### 4.3.3 Implementation Primitive

- `TextChunker`
  - `split_document(doc: Document) -> List[Chunk]`

### 4.4 Embeddings (Free Models)

#### 4.4.1 Requirements

- Use free, local embedding model (no paid API).

#### 4.4.2 Recommended Models

- **`sentence-transformers/all-MiniLM-L6-v2`**
  - Small, fast, good English performance.
- Alternative:
  - `BAAI/bge-small-en-v1.5` (very strong RAG performance, still small).

#### 4.4.3 Implementation Primitive

- `EmbeddingModel`
  - Initialized with chosen model name.
  - `embed_texts(texts: List[str]) -> List[vector]`.

### 4.5 ChromaDB Indexing

#### 4.5.1 Setup

- Local persistent ChromaDB, e.g. under `./chroma_db/`.
- Single collection:
  - Name: `personal_kb`.
- Embedding function: wrapper around `EmbeddingModel`.

#### 4.5.2 Index Build Process

Input: list of `Document` objects (from ingestion).

For each document:

- Chunk into `Chunk` objects.
- Compute embeddings for each chunk.
- Upsert into Chroma:
  - `ids`.
  - `embeddings`.
  - `metadatas`.
  - `documents` = chunk content.

#### 4.5.3 Deduplication / Upsert Strategy

- Use stable `id` pattern:
  - `"{source}_{source_id}_chunk_{index}"` or `"{doc_id}::chunk_{index}"`.
- Before upserting, optionally delete all chunks for a document to avoid duplicates (or rely on id overwrite).

---

## 5. Retrieval & RAG Flow

### 5.1 Retrieval

**Inputs**

- User question `q`.

**Steps**

- Compute embedding for `q` using the same embedding model.
- Query Chroma collection:
  - `top_k`: default 5 (configurable).
  - Optional `score_threshold`: e.g. 0.2–0.3.
- Retrieve results:
  - `content` (chunk text).
  - `metadata` (title, url, source, etc.).
  - Similarity scores.

**Implementation Primitive**

- `Retriever`
  - `retrieve(query: str, top_k: int = 5) -> List[RetrievedChunk]`.

### 5.2 Prompt Construction

#### 5.2.1 System Prompt

Explain assistant role:

- RAG answer, cite sources, admit when unknown, use retrieved context only.

#### 5.2.2 Context Formatting

For each retrieved chunk:

- Add section:
  - `Source: {title} (from {source}, url: {url})`
  - `Content: """{content}"""`.

Truncate if necessary to fit model context window.

#### 5.2.3 User Prompt

Wrap the user question and instructions:

- Ask model to:
  - Answer concisely.
  - Use bullet points when appropriate.
  - Add references like `[Source 1]`, `[Source 2]`.

### 5.3 Calling Groq LLM

#### 5.3.1 Groq Setup

- Create Groq account, obtain **API key**.
- Store in `.env` as `GROQ_API_KEY`.
- Use Groq Python SDK or HTTP calls.
- Select a suitable model:
  - e.g. `"llama-3.1-8b-instant"` or other available free-tier model (check Groq docs).

#### 5.3.2 Implementation Primitive

- `GroqClient`
  - Initialized with API key and default model name.
  - `generate_answer(system_prompt, context, question) -> str`.

### 5.4 Answer Post-processing

**Combine**

- LLM answer text.
- Mapping of citations (which chunk corresponds to which `[Source n]`).

**Return to UI**

- Text answer.
- List of referenced sources with clickable URLs.

---

## 6. Streamlit Application Design

### 6.1 UI Layout

#### 6.1.1 Sidebar

- **Configuration**
  - Groq model choice (if multiple).
  - `top_k` retrieval (slider 1–10).
  - Score threshold (optional slider).
- **Indexing Controls**
  - Button: “Rebuild Index”.
  - Button: “Update Index (Incremental)”.
  - Status indicators: last index time, number of docs/chunks.
- **Source Filters**
  - Toggles: include/exclude Notion, Google Drive.

#### 6.1.2 Main Area

- **Header**
  - Title: “AI Personal Knowledge Base Assistant”.
  - Short description / usage tips.
- **Query Input**
  - Text input for question.
  - Optional advanced options: include conversation history toggle.
- **Answer Display**
  - Assistant answer (markdown).
  - Citations referencing source list.
- **Sources Panel**
  - Expandable list of retrieved chunks:
    - Title, snippet, similarity score, source, url.
    - “Show full chunk” toggle.
- **Conversation History**
  - Collapsible previous Q&A pairs in current session.

### 6.2 App State & Caching

- Use `st.session_state` to hold:
  - Conversation history.
  - Latest retrieved contexts.
  - Config parameters (top_k, threshold).
- Use `@st.cache_resource` or `@st.cache_data` to cache:
  - Loaded embedding model.
  - Chroma client / collection.
  - Possibly documents metadata (but be mindful of invalidation when re-indexing).

---

## 7. Project Structure (Recommended)

A minimal but structured layout:

- **`app/`**
  - `main_app.py` – Streamlit entry point.
  - `config.py` – configuration and `.env` loading.
  - `rag_pipeline.py` – orchestration of retrieval + LLM.
- **`ingestion/`**
  - `notion_client.py`.
  - `notion_ingestor.py`.
  - `gdrive_client.py`.
  - `gdrive_ingestor.py`.
  - `chunking.py`.
- **`vector_store/`**
  - `chroma_store.py`.
  - `embeddings.py`.
  - `retriever.py`.
- **`llm/`**
  - `groq_client.py`.
  - `prompts.py`.
- **`models/`**
  - `document.py` – dataclasses for `Document`, `Chunk`, `RetrievedChunk`.
- **`scripts/`**
  - `build_index.py` – CLI to build index without UI.
  - `update_index.py` – CLI for incremental updates.
- **Root files**
  - `requirements.txt`.
  - `.env.example`.
  - `README.md`.
  - `ARCHITECTURE_AI_PKB_RAG.md` (this file).

---

## 8. Configuration & Environment

### 8.1 `.env` Variables (Example)

**Core**

- `GROQ_API_KEY=...`

**Notion**

- `NOTION_API_KEY=...`
- `NOTION_PAGE_IDS=id1,id2,...`
- `NOTION_DATABASE_IDS=id1,id2,...`

**Google Drive**

- `GOOGLE_CLIENT_SECRETS_PATH=./secrets/client_secrets.json`
- `GDRIVE_ROOT_FOLDER_IDS=folderid1,folderid2`

**Embeddings**

- `EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2`

**Chroma**

- `CHROMA_PERSIST_DIR=./chroma_db`
- `CHROMA_COLLECTION_NAME=personal_kb`

---

## 9. Setup & Installation Guide (High-Level)

### 9.1 Prerequisites

**System**

- Python 3.10+ recommended.

**Accounts**

- Groq account + API key.
- Notion account + internal integration.
- Google account + GCP project with Drive API enabled.

### 9.2 Steps

1. **Create Project**
   - Create a new Python project directory.
   - Add the folder structure described above.
2. **Create Virtual Environment**
   - Use `python -m venv .venv` (or `conda`).
3. **Install Dependencies (to be defined later in `requirements.txt`)**
   - Core:
     - `streamlit`
     - `python-dotenv`
     - `pydantic` or `dataclasses-json` (optional)
   - RAG:
     - `chromadb`
     - `sentence-transformers`
     - `torch` (CPU version)
   - Notion:
     - `notion-client` (official SDK) or `notion-sdk-py`
   - Google Drive:
     - `google-api-python-client`
     - `google-auth-httplib2`
     - `google-auth-oauthlib`
   - Parsing:
     - `pdfplumber` or `pypdf`
     - `python-docx` (optional)
   - Groq:
     - `groq` (official SDK if available) or `requests` / `httpx`.
4. **Configure `.env`**
   - Copy `.env.example` → `.env`.
   - Fill in API keys, folder/page IDs, model names.
5. **Initialize Google Drive OAuth**
   - Run a small helper script (later) to obtain `token.json` for Drive API.
   - Follow browser prompt, grant permissions, store token.
6. **Build Initial Index**
   - Run `python scripts/build_index.py` (after implementation).
   - Ingest Notion and Google Drive.
   - Chunk and compute embeddings.
   - Populate ChromaDB.
7. **Launch Streamlit App**
   - Run `streamlit run app/main_app.py` (after implementation).
   - Open the local URL to interact.

---

## 10. End-to-End Flow Walkthrough

### 10.1 Index Build (Offline or On-Demand)

1. **Start ingestion**
   - Call Notion ingestor → list pages/databases → fetch content → create `Document`s.
   - Call Google Drive ingestor → traverse folders → fetch + parse files → create `Document`s.
2. **Chunk documents**
   - Pass each `Document` to `TextChunker` → `Chunk` list.
3. **Embed chunks**
   - Use `EmbeddingModel` to embed chunk texts.
4. **Upsert to Chroma**
   - Upsert `ids`, `embeddings`, `metadatas`, and `contents`.
5. **Persist**
   - ChromaDB persists to disk at `CHROMA_PERSIST_DIR`.

### 10.2 User Query (Online in Streamlit)

1. **User question**
   - Entered in Streamlit input box.
2. **Retrieve context**
   - `Retriever.retrieve(question, top_k)`.
   - Get top-k relevant chunks with metadata.
3. **Compose prompt**
   - Build system and context sections with chunk contents and citations.
   - Add user question.
4. **LLM call**
   - `GroqClient.generate_answer(...)`.
   - Receive answer from Groq LLM.
5. **Display**
   - Show answer in main panel.
   - Show list of sources with clickable links and metadata.
   - Append Q&A to conversation history.

---

## 11. Extensibility & Future Enhancements

- **Multi-user support**
  - Add user identity and per-user collections or metadata filters.
- **Additional sources**
  - Email, Slack, GitHub, etc.
- **Scheduling**
  - Periodic re-ingestion/indexing via cron or task scheduler.
- **Advanced retrieval**
  - Reranking (e.g. using cross-encoder, still free/open-source).
  - Hybrid search (BM25 + embeddings).
- **Advanced UI**
  - File/source selection per query.
  - Per-query temperature and style controls.

---

## 12. Next Steps (Before Coding)

- Decide exact embedding model (e.g. `all-MiniLM-L6-v2` vs `bge-small-en-v1.5`).
- Decide which Notion pages / Drive folders to include initially.
- Confirm OS-specific paths for `CHROMA_PERSIST_DIR` and `GOOGLE_CLIENT_SECRETS_PATH`.
- Then start implementing modules following this architecture (this file is design-only; full implementation comes later).

