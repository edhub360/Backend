def validate_pagination(page: int, limit: int, max_page_limit: int = 100):
    if page < 1:
        raise ValueError("Page must be >= 1")
    if limit < 1 or limit > max_page_limit:
        raise ValueError(f"Limit must be in [1, {max_page_limit}]")
