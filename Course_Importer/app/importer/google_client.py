import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "./course-importer-key.json")
    return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)

def get_sheets_service():
    return build("sheets", "v4", credentials=get_credentials())

def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())