import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY"),
)

router = APIRouter(prefix="/hobbies", tags=["hobbies"])


def get_current_user(authorization: str = Header(..., alias="Authorization")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        res = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    if not res.user:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    return res.user.id


@router.get("")
def get_hobbies(user_id: str = Depends(get_current_user)):
    res = supabase.table("user_hobbies").select("hobby_id").eq("user_id", user_id).execute()
    return {"hobbies": [row["hobby_id"] for row in res.data]}


@router.post("/{hobby_id}")
def add_hobby(hobby_id: str, user_id: str = Depends(get_current_user)):
    supabase.table("user_hobbies").insert({"user_id": user_id, "hobby_id": hobby_id}).execute()
    return {"success": True}


@router.delete("/{hobby_id}")
def remove_hobby(hobby_id: str, user_id: str = Depends(get_current_user)):
    supabase.table("user_hobbies").delete().eq("user_id", user_id).eq("hobby_id", hobby_id).execute()
    return {"success": True}