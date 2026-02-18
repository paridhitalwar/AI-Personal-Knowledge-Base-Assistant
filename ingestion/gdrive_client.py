from pathlib import Path
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource

from app.config import settings


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _get_credentials(token_path: Path, client_secrets_path: Path) -> Credentials:
    """Obtain Google API credentials, running the browser flow if needed."""
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_path.exists():
                raise FileNotFoundError(
                    f"Google Client Secrets file not found at: {client_secrets_path}\n"
                    "Please download 'credentials.json' from Google Cloud Console "
                    "and save it to this path."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path),
                SCOPES,
            )
            print("Launching Google Auth Flow...")
            print("If your browser does not open automatically, look for a URL below:")
            creds = flow.run_local_server(port=0)
        
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with token_path.open("w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


import json
import tempfile
import streamlit as st

def get_drive_service() -> Resource:
    """Create a Google Drive API service client."""
    # Check if we are on Streamlit Cloud and have secrets configured specially
    if "google_json" in st.secrets and "content" in st.secrets["google_json"]:
        # Write the secret content to a temporary file (simplest way to satisfy existing patterns)
        # OR use from_client_config directly. Let's use from_client_config.
        
        client_config = json.loads(st.secrets["google_json"]["content"])
        
        # Token handling for cloud is tricky because we can't write to disk easily.
        # Ideally, we should also store the TOKEN in secrets, but for now let's try standard flow.
        # If token doesn't exist, we might need a different auth strategy (Service Account).
        # But assuming user wants to auth once:
        
        creds = None
        # Try to load token from secrets if available
        if "google_token" in st.secrets and "content" in st.secrets["google_token"]:
             token_json = json.loads(st.secrets["google_token"]["content"])
             creds = Credentials.from_authorized_user_info(token_json, SCOPES)
             
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # On Cloud, we can't pop up a browser window easily. 
                # We need to print the URL to logs and user must click it.
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob" # For copy-paste auth method
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                print(f"Please go to this URL: {auth_url}")
                st.link_button("Login to Google", auth_url) # Show button in UI
                
                if not st.secrets.get("is_headless", False):
                     # If interactive, ask for code. But Streamlit is async.
                     # This is hard to do in one pass.
                     # Better strategy: user auths locally, gets token.json, and pastes token specific content into secrets.
                     st.error("On Streamlit Cloud, you must provide a pre-authorized token in secrets. Run locally first to generate token.json, then copy its content to secrets as [google_token] content='...'")
                     raise ValueError("Missing Google Token in Secrets for Cloud deployment.")

        return build("drive", "v3", credentials=creds)

    # Fallback to local file strategy
    client_secrets = Path(settings.google_client_secrets_path).resolve()
    token_path = client_secrets.parent / "token.json"
    
    # Ensure parent directory exists for token
    token_path.parent.mkdir(parents=True, exist_ok=True)

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

