from google.auth import default
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    credentials, _ = default(scopes=SCOPES)
    return credentials

def get_sheets_service():
    return build("sheets", "v4", credentials=get_credentials())

def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())