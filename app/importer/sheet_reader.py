from app.importer.google_client import get_sheets_service
from app.importer.sheet_template import HEADERS

def read_course_rows(spreadsheet_id: str) -> list[dict]:
    sheets = get_sheets_service()

    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Courses!A1:Z"
    ).execute()

    rows = result.get("values", [])
    if not rows or len(rows) < 2:
        return []  # empty or header only

    header_row = rows[0]
    data_rows = rows[1:]

    courses = []
    for row in data_rows:
        # Pad short rows with empty strings
        padded = row + [""] * (len(header_row) - len(row))
        record = {header_row[i]: padded[i] for i in range(len(header_row))}
        courses.append(record)

    return courses