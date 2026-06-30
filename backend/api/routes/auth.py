from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.auth import hash_password, verify_password, create_token, get_current_user
from backend.database.database import get_connection
from backend.logging_config import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (request.username,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(401, "Invalid username or password")

    user = dict(row)
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    token = create_token(user["id"], user["username"], user["role"])
    return {
        "access_token": token,
        "username": user["username"],
        "role": user["role"],
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    conn = get_connection()
    row = conn.execute("SELECT id, username, role, created_at FROM users WHERE id = ?", (user["user_id"],)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)
