from app.importer.google_client import get_sheets_service, get_drive_service
import os

HEADERS = [
    "course_title", "course_desc", "course_duration",
    "course_complexity", "course_owner", "course_url",
    "course_redirect_url", "course_image_url", "course_credit"
]

UPLOAD_FOLDER_ID = os.getenv("DRIVE_UPLOAD_FOLDER_ID")  # set in .env

def create_course_template(name: str = "Course Upload Template") -> dict:
    sheets = get_sheets_service()
    drive = get_drive_service()

    # Create spreadsheet
    spreadsheet = sheets.spreadsheets().create(body={
        "properties": {"title": name},
        "sheets": [{"properties": {"title": "Courses"}}]
    }).execute()

    spreadsheet_id = spreadsheet["spreadsheetId"]

    # Write header row
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Courses!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]}
    ).execute()

    # Bold the header row
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold"
            }
        }]}
    ).execute()

    # Move to upload folder
    if UPLOAD_FOLDER_ID:
        drive.files().update(
            fileId=spreadsheet_id,
            addParents=UPLOAD_FOLDER_ID,
            removeParents="root",
            fields="id, parents"
        ).execute()

    return {
        "spreadsheet_id": spreadsheet_id,
        "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "folder_id": UPLOAD_FOLDER_ID
    }