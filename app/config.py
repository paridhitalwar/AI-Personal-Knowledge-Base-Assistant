import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]

env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Application-wide configuration loaded from environment variables."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    notion_api_key: str = os.getenv("NOTION_API_KEY", "")
    notion_page_ids: list[str] = (
        os.getenv("NOTION_PAGE_IDS", "").split(",") if os.getenv("NOTION_PAGE_IDS") else []
    )
    notion_database_ids: list[str] = (
        os.getenv("NOTION_DATABASE_IDS", "").split(",")
        if os.getenv("NOTION_DATABASE_IDS")
        else []
    )

    google_client_secrets_path: str = os.getenv(
        "GOOGLE_CLIENT_SECRETS_PATH", "./secrets/client_secrets.json"
    )
    gdrive_root_folder_ids: list[str] = (
        os.getenv("GDRIVE_ROOT_FOLDER_IDS", "").split(",")
        if os.getenv("GDRIVE_ROOT_FOLDER_IDS")
        else []
    )

    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )

    chroma_persist_dir: Path = Path(
        os.getenv("CHROMA_PERSIST_DIR", str(ROOT_DIR / "chroma_db"))
    )
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "personal_kb")


settings = Settings()

