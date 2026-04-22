import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import secretmanager

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

TOKEN_PATH = "/tmp/google_oauth_token.json"
PROJECT_ID = "arctic-sentry-467317-s7"
SECRET_NAME = "GOOGLE_OAUTH_TOKEN"


def _fetch_token_from_secret():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    with open(TOKEN_PATH, "w") as f:
        f.write(response.payload.data.decode("UTF-8"))


def get_credentials() -> Credentials:
    if not os.path.exists(TOKEN_PATH):
        _fetch_token_from_secret()
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token back to Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}"
        client.add_secret_version(
            request={"parent": parent, "payload": {"data": creds.to_json().encode()}}
        )
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def get_sheets_service():
    return build("sheets", "v4", credentials=get_credentials())


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())