from pathlib import Path
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource

from app.config import settings


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _get_credentials(token_path: Path, client_secrets_path: Path) -> Credentials:
    """Obtain Google API credentials, running the browser flow if needed."""
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # type: ignore[name-defined]
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with token_path.open("w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


def get_drive_service() -> Resource:
    """Create a Google Drive API service client."""
    client_secrets = Path(settings.google_client_secrets_path)
    token_path = client_secrets.parent / "token.json"
    creds = _get_credentials(token_path=token_path, client_secrets_path=client_secrets)
    return build("drive", "v3", credentials=creds)


def list_files_in_folders(service: Resource, folder_ids: List[str]) -> List[dict]:
    """List files in the given root folders (non-recursive placeholder)."""
    files: List[dict] = []
    for folder_id in folder_ids:
        query = f"'{folder_id}' in parents and trashed = false"
        results = (
            service.files()
            .list(q=query, fields="files(id, name, mimeType, parents)")
            .execute()
        )
        files.extend(results.get("files", []))
    return files

