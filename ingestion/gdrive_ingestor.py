from datetime import datetime
from io import BytesIO
from typing import List

from googleapiclient.http import MediaIoBaseDownload

from app.config import settings
from ingestion.gdrive_client import get_drive_service, list_files_in_folders
from models.document import Document


def _download_file_content(service, file_id: str) -> bytes:
    """Download raw file bytes from Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


def _export_google_doc_as_text(service, file_id: str) -> str:
    """Export a Google Doc to plain text."""
    request = service.files().export_media(fileId=file_id, mimeType="text/plain")
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue().decode("utf-8", errors="ignore")


def ingest_gdrive() -> List[Document]:
    """Ingest configured Google Drive folders into Document objects.

    This initial version focuses on Google Docs and simple text-like files.
    """
    root_ids = [fid.strip() for fid in settings.gdrive_root_folder_ids if fid.strip()]
    if not root_ids:
        return []

    service = get_drive_service()
    files = list_files_in_folders(service, root_ids)

    documents: List[Document] = []

    for file in files:
        file_id = file["id"]
        name = file.get("name", "Untitled")
        mime_type = file.get("mimeType", "")

        text_content = ""

        if mime_type == "application/vnd.google-apps.document":
            text_content = _export_google_doc_as_text(service, file_id)
        elif mime_type in ("text/plain", "text/markdown"):
            raw = _download_file_content(service, file_id)
            text_content = raw.decode("utf-8", errors="ignore")
        else:
            # Placeholder: other types (PDF, DOCX) can be added later.
            continue

        metadata = (
            service.files()
            .get(fileId=file_id, fields="id, name, mimeType, createdTime, modifiedTime, webViewLink, parents")
            .execute()
        )

        created_at = metadata.get("createdTime")
        modified_at = metadata.get("modifiedTime")

        documents.append(
            Document(
                id=f"gdrive_{file_id}",
                source="gdrive",
                source_id=file_id,
                title=name,
                text=text_content,
                created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_at
                else None,
                updated_at=datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
                if modified_at
                else None,
                url=metadata.get("webViewLink"),
                path="",
                metadata_raw=metadata,
            )
        )

    return documents

