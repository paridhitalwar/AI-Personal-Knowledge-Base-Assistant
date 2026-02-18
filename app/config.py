import os
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]

env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Application-wide configuration loaded from environment variables or Streamlit secrets."""

    def _get(self, key: str, default: str = "") -> str:
        """Helper to get config from env or streamlit secrets."""
        val = os.getenv(key)
        if val:
            return val
        if "secrets" in dir(st) and key in st.secrets:
            return st.secrets[key]
        return default

    @property
    def groq_api_key(self) -> str:
        return self._get("GROQ_API_KEY")

    @property
    def notion_api_key(self) -> str:
        return self._get("NOTION_API_KEY")

    @property
    def notion_page_ids(self) -> list[str]:
        val = self._get("NOTION_PAGE_IDS")
        return val.split(",") if val else []

    @property
    def notion_database_ids(self) -> list[str]:
        val = self._get("NOTION_DATABASE_IDS")
        return val.split(",") if val else []

    @property
    def google_client_secrets_path(self) -> str:
        return self._get("GOOGLE_CLIENT_SECRETS_PATH", "./secrets/client_secrets.json")

    @property
    def gdrive_root_folder_ids(self) -> list[str]:
        val = self._get("GDRIVE_ROOT_FOLDER_IDS")
        return val.split(",") if val else []

    @property
    def embedding_model_name(self) -> str:
        return self._get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

    @property
    def chroma_persist_dir(self) -> Path:
        return Path(self._get("CHROMA_PERSIST_DIR", str(ROOT_DIR / "chroma_db")))

    @property
    def chroma_collection_name(self) -> str:
        return self._get("CHROMA_COLLECTION_NAME", "personal_kb")


settings = Settings()

