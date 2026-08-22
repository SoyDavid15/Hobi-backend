import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY"),
)

supabase_admin = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
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


def get_user_hobbies(user_id: str) -> list[str]:
    res = supabase_admin.table("user_hobbies").select("hobby_id").eq("user_id", user_id).execute()
    if not res or not res.data:
        return []
    return [row["hobby_id"] for row in res.data]


def get_daily_challenge(user_id: str, challenge_date: str) -> str | None:
    res = (
        supabase_admin.table("daily_challenges")
        .select("challenge")
        .eq("user_id", user_id)
        .eq("challenge_date", challenge_date)
        .maybe_single()
        .execute()
    )
    if res and res.data:
        return res.data.get("challenge")
    return None


def save_daily_challenge(user_id: str, challenge_date: str, hobby_id: str, challenge: str) -> None:
    supabase_admin.table("daily_challenges").insert(
        {"user_id": user_id, "challenge_date": challenge_date, "hobby_id": hobby_id, "challenge": challenge}
    ).execute()


@router.get("")
def get_hobbies(user_id: str = Depends(get_current_user)):
    try:
        hobbies = get_user_hobbies(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar hobbies: {e}")
    return {"hobbies": hobbies}


@router.post("/{hobby_id}")
def add_hobby(hobby_id: str, user_id: str = Depends(get_current_user)):
    try:
        supabase_admin.table("user_hobbies").insert({"user_id": user_id, "hobby_id": hobby_id}).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar hobby: {e}")
    return {"success": True}


@router.delete("/{hobby_id}")
def remove_hobby(hobby_id: str, user_id: str = Depends(get_current_user)):
    try:
        supabase_admin.table("user_hobbies").delete().eq("user_id", user_id).eq("hobby_id", hobby_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar hobby: {e}")
    return {"success": True}