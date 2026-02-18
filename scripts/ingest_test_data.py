import sys
from pathlib import Path
from datetime import datetime

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from models.document import Document
from ingestion.chunking import chunk_documents
from vector_store.chroma_store import ChromaStore

def main():
    """Ingest test data into the vector store."""
    
    # Read test document
    test_file = root_dir / "test_data.txt"
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create document
    doc = Document(
        id="test_doc_1",
        source="test",
        source_id="test_data.txt",
        title="Test RAG Document",
        text=content,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        url=str(test_file),
        metadata_raw={"source": "test_file"}
    )
    
    # Chunk and index
    chunks = chunk_documents([doc])
    store = ChromaStore()
    store.upsert_chunks(chunks)
    
    print(f"Successfully indexed {len(chunks)} chunks from test document")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
