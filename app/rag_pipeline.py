from dataclasses import dataclass
from typing import List, Optional

from ingestion.gdrive_ingestor import ingest_gdrive
from ingestion.notion_ingestor import ingest_notion
from ingestion.chunking import chunk_documents
from llm.groq_client import GroqClient
from llm.prompts import build_system_prompt, build_user_prompt
from models.document import Document, RetrievedChunk
from vector_store.chroma_store import ChromaStore
from vector_store.retriever import RetrievalConfig, Retriever


@dataclass
class RAGConfig:
    top_k: int = 5
    score_threshold: Optional[float] = None


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline."""

    def __init__(self, rag_config: Optional[RAGConfig] = None) -> None:
        self.store = ChromaStore()
        self.retriever = Retriever(
            store=self.store,
            config=RetrievalConfig(
                top_k=(rag_config.top_k if rag_config else 5),
                score_threshold=(rag_config.score_threshold if rag_config else None),
            ),
        )
        self.llm = GroqClient()
        self.rag_config = rag_config or RAGConfig()

    def run_full_ingestion(self) -> List[Document]:
        """Ingest from Notion and Google Drive, index into Chroma."""
        documents: List[Document] = []
        # Ingest from both sources (if configured)
        documents.extend(ingest_notion())
        documents.extend(ingest_gdrive())

        # Chunk and upsert
        chunks = chunk_documents(documents)
        self.store.upsert_chunks(chunks)
        return documents

    def answer_question(
        self,
        question: str,
        history: List[dict] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> tuple[str, List[RetrievedChunk]]:
        """Retrieve relevant chunks and generate an answer via Groq."""
        retrieved = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        system_prompt = build_system_prompt()
        user_content = build_user_prompt(question, retrieved)

        try:
            answer = self.llm.chat(
                system_prompt=system_prompt, 
                user_content=user_content,
                history=history
            )
        except TypeError:
            # Fallback for stale objects: force reload module and re-instantiate
            import importlib
            import llm.groq_client
            importlib.reload(llm.groq_client)
            from llm.groq_client import GroqClient
            
            print("Warning: Stale GroqClient detected. Module reloaded.")
            self.llm = GroqClient() 
            answer = self.llm.chat(
                system_prompt=system_prompt, 
                user_content=user_content,
                history=history
            )
        return answer, retrieved

