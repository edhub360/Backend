from fastapi import Request, HTTPException

def get_current_user_id(request: Request) -> str:
    # For production, parse Firebase JWT
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return None
    return user_id
