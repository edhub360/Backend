from fastapi import Request, HTTPException

def get_current_user_id(request: Request) -> str:
    # For production, parse Firebase JWT
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(401, "User not authenticated")
    return user_id
