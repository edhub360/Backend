from typing import Optional

def transform_row(row: dict) -> Optional[dict]:
    title = row.get("course_title", "").strip()
    if not title:
        return None  # skip rows with no title

    def safe_int(val):
        try:
            return int(val) if val and str(val).strip() else None
        except (ValueError, TypeError):
            return None

    return {
        "course_title":        title,
        "course_desc":         row.get("course_desc", "").strip() or None,
        "course_duration":     safe_int(row.get("course_duration")),
        "course_complexity":   row.get("course_complexity", "").strip() or None,
        "course_owner":        row.get("course_owner", "").strip() or None,
        "course_url":          row.get("course_url", "").strip() or None,
        "course_redirect_url": row.get("course_redirect_url", "").strip() or None,
        "course_image_url":    row.get("course_image_url", "").strip() or None,
        "course_credit":       safe_int(row.get("course_credit")),
    }