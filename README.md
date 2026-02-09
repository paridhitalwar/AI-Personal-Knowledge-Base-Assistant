# Personal Knowledge Base RAG System

A Retrieval-Augmented Generation (RAG) system that integrates with Notion and Google Drive to provide intelligent question-answering over your personal documents.

## Features

- **Multi-source ingestion**: Import documents from Notion pages/databases and Google Drive
- **Semantic search**: Uses embeddings to find relevant document chunks
- **AI-powered answers**: Leverages Groq LLM for context-aware responses
- **Streamlit interface**: Clean, interactive web UI
- **Local processing**: Embeddings and vector storage handled locally

## Setup

### Prerequisites

- Python 3.8+
- Notion API key
- Google Cloud credentials (for Drive access)
- Groq API key

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Copy `.env.example` to `.env` (or create `.env` file)
2. Add your API keys and configuration:
   ```env
   GROQ_API_KEY=your_groq_api_key
   NOTION_API_KEY=your_notion_api_key
   NOTION_PAGE_IDS=page_id_1,page_id_2
   NOTION_DATABASE_IDS=db_id_1,db_id_2
   GOOGLE_CLIENT_SECRETS_PATH=./secrets/client_secrets.json
   GDRIVE_ROOT_FOLDER_IDS=folder_id_1,folder_id_2
   ```

### Running the App

```bash
streamlit run app/main_app.py
```

## Usage

1. **Index documents**: Run the build script to ingest your documents
   ```bash
   python scripts/build_index.py
   ```

2. **Ask questions**: Use the Streamlit interface to ask questions about your documents

3. **Manage sources**: Configure which Notion pages/databases and Google Drive folders to index

## Architecture

- `app/`: Main application logic and Streamlit UI
- `ingestion/`: Document ingestion from Notion and Google Drive
- `vector_store/`: ChromaDB for vector storage and retrieval
- `llm/`: Groq client for LLM interactions
- `models/`: Data models for documents and chunks
- `scripts/`: Utility scripts for building and updating indices

## Deployment

### Streamlit Community Cloud

1. Push your code to GitHub
2. Connect your repository to [Streamlit Community Cloud](https://share.streamlit.io/)
3. Set up environment variables in the Streamlit app settings
4. Deploy!

### Environment Variables for Deployment

Make sure to set these in your deployment environment:
- `GROQ_API_KEY`
- `NOTION_API_KEY` 
- `NOTION_PAGE_IDS`
- `NOTION_DATABASE_IDS`
- `GOOGLE_CLIENT_SECRETS_PATH` (if using Drive)
- `GDRIVE_ROOT_FOLDER_IDS` (if using Drive)

## License

MIT License
