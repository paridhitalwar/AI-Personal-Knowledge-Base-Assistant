from typing import List

from notion_client import Client

from app.config import settings


def get_notion_client() -> Client:
    """Create a Notion client using the API key from settings."""
    if not settings.notion_api_key:
        raise RuntimeError("NOTION_API_KEY is not set in the environment.")
    return Client(auth=settings.notion_api_key)


def list_page_ids() -> List[str]:
    """Return configured page IDs from settings."""
    return [pid.strip() for pid in settings.notion_page_ids if pid.strip()]


def list_database_ids() -> List[str]:
    """Return configured database IDs from settings."""
    return [did.strip() for did in settings.notion_database_ids if did.strip()]

