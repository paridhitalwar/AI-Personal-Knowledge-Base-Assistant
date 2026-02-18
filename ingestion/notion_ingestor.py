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


def _create_document_from_page(page: dict) -> Document:
    """Helper to convert a Notion page object into a Document."""
    page_id = page.get("id")
    
    # Try to find a title in properties
    title_text = "Untitled"
    properties = page.get("properties", {})
    
    # Common title keys in Notion: "Name", "title", "Page"
    # We iterate to find the property of type "title"
    for prop in properties.values():
        if prop.get("type") == "title":
            title_obj = prop.get("title", [])
            if title_obj:
                title_text = "".join(t.get("plain_text", "") for t in title_obj)
            break
            
    content = _extract_text_from_page(page)

    created_time = page.get("created_time")
    last_edited_time = page.get("last_edited_time")

    return Document(
        id=f"notion_{page_id}",
        source="notion",
        source_id=page_id,
        title=title_text,
        text=content,
        created_at=datetime.fromisoformat(created_time.replace("Z", "+00:00")) 
            if created_time else None,
        updated_at=datetime.fromisoformat(last_edited_time.replace("Z", "+00:00")) 
            if last_edited_time else None,
        url=page.get("url"),
        metadata_raw=page,
    )


def ingest_notion() -> List[Document]:
    """Ingest ALL Notion pages shared with the integration via Search API."""
    try:
        client = get_notion_client()
    except Exception as e:
        print(f"Skipping Notion ingestion: {e}")
        return []

    print("Fetching all accessible Notion pages (via Search API)...")
    documents: List[Document] = []
    
    has_more = True
    next_cursor = None
    
    while has_more:
        try:
            # Search returns all pages/databases the integration has access to
            response = client.search(start_cursor=next_cursor, page_size=100)
        except Exception as e:
            print(f"Error searching Notion: {e}")
            break
            
        results = response.get("results", [])
        for result in results:
            if result.get("object") == "page":
                try:
                    doc = _create_document_from_page(result)
                    documents.append(doc)
                except Exception as e:
                    print(f"Failed to process page {result.get('id')}: {e}")
            
        has_more = response.get("has_more")
        next_cursor = response.get("next_cursor")
        print(f"  Processed {len(documents)} pages so far...")
        
    print(f"Found {len(documents)} Notion pages.")
    return documents

