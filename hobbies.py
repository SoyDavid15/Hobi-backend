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


def get_daily_challenge(user_id: str, challenge_date: str, period: str = "AM") -> dict | None:
    res = (
        supabase_admin.table("daily_challenges")
        .select("id, challenge, is_completed, photo_url, challenge_date, hobby_id, period, created_at, completed_at")
        .eq("user_id", user_id)
        .eq("challenge_date", challenge_date)
        .eq("period", period)
        .maybe_single()
        .execute()
    )
    if res and res.data:
        return res.data
    return None


def save_daily_challenge(user_id: str, challenge_date: str, period: str, hobby_id: str, challenge: str) -> None:
    supabase_admin.table("daily_challenges").insert(
        {
            "user_id": user_id,
            "challenge_date": challenge_date,
            "period": period,
            "hobby_id": hobby_id,
            "challenge": challenge,
            "is_completed": False,
        }
    ).execute()


def complete_daily_challenge(user_id: str, challenge_date: str, period: str, photo_url: str) -> dict | None:
    res = (
        supabase_admin.table("daily_challenges")
        .update({
            "photo_url": photo_url,
            "is_completed": True,
            "completed_at": "now()",
        })
        .eq("user_id", user_id)
        .eq("challenge_date", challenge_date)
        .eq("period", period)
        .execute()
    )
    if res and res.data:
        return res.data[0]
    return None


def get_completed_challenges(user_id: str) -> list[dict]:
    res = (
        supabase_admin.table("daily_challenges")
        .select("id, challenge, is_completed, photo_url, challenge_date, hobby_id, period, completed_at, created_at")
        .eq("user_id", user_id)
        .eq("is_completed", True)
        .order("challenge_date", desc=True)
        .order("period", desc=True)
        .execute()
    )
    if not res or not res.data:
        return []
    return res.data


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