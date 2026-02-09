from datetime import datetime
from typing import List

from notion_client.errors import APIResponseError

from ingestion.notion_client import get_notion_client, list_database_ids, list_page_ids
from models.document import Document


def _extract_text_from_page(page: dict) -> str:
    """Placeholder for extracting rich text content from a Notion page.

    For an initial version, we can concatenate simple text properties and titles.
    A more complete implementation would fetch and flatten block content.
    """
    properties = page.get("properties", {})
    parts: List[str] = []

    for prop in properties.values():
        prop_type = prop.get("type")
        if prop_type == "title":
            for t in prop.get("title", []):
                text = t.get("plain_text") or ""
                if text:
                    parts.append(text)
        elif prop_type == "rich_text":
            for t in prop.get("rich_text", []):
                text = t.get("plain_text") or ""
                if text:
                    parts.append(text)

    return "\n".join(parts)


def ingest_notion() -> List[Document]:
    """Ingest configured Notion pages and database entries into Document objects."""
    client = get_notion_client()
    documents: List[Document] = []

    # Individual pages
    for page_id in list_page_ids():
        try:
            page = client.pages.retrieve(page_id=page_id)
        except APIResponseError:
            continue

        title = page.get("properties", {}).get("Name", {}).get("title", [])
        title_text = "".join(t.get("plain_text", "") for t in title) if title else "Untitled"
        content = _extract_text_from_page(page)

        documents.append(
            Document(
                id=f"notion_page_{page_id}",
                source="notion",
                source_id=page_id,
                title=title_text,
                text=content,
                created_at=datetime.fromisoformat(
                    page["created_time"].replace("Z", "+00:00")
                )
                if page.get("created_time")
                else None,
                updated_at=datetime.fromisoformat(
                    page["last_edited_time"].replace("Z", "+00:00")
                )
                if page.get("last_edited_time")
                else None,
                url=page.get("url"),
                metadata_raw=page,
            )
        )

    # Database entries (simple approach: first page of results)
    for db_id in list_database_ids():
        try:
            query = client.databases.query(database_id=db_id)
        except APIResponseError:
            continue

        for row in query.get("results", []):
            row_id = row.get("id")
            title = row.get("properties", {}).get("Name", {}).get("title", [])
            title_text = "".join(t.get("plain_text", "") for t in title) if title else "Untitled"
            content = _extract_text_from_page(row)

            documents.append(
                Document(
                    id=f"notion_db_{db_id}_{row_id}",
                    source="notion",
                    source_id=row_id or "",
                    title=title_text,
                    text=content,
                    created_at=datetime.fromisoformat(
                        row["created_time"].replace("Z", "+00:00")
                    )
                    if row.get("created_time")
                    else None,
                    updated_at=datetime.fromisoformat(
                        row["last_edited_time"].replace("Z", "+00:00")
                    )
                    if row.get("last_edited_time")
                    else None,
                    url=row.get("url"),
                    metadata_raw=row,
                )
            )

    return documents

