import os
import re
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import create_client
from ai import verify_challenge_photo

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

router = APIRouter(prefix="/hobbies", tags=["hobbies"])

VALID_HOBBIES = {"Musica", "Deporte", "Videojuegos", "Arte", "Lectura", "Cocina"}
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def validate_date(date_str: str) -> str:
    if not DATE_REGEX.match(date_str):
        raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")
    return date_str


def validate_photo_url(photo_url: str, user_id: str) -> str:
    if not photo_url or not isinstance(photo_url, str):
        raise HTTPException(status_code=400, detail="URL de foto inválida")
    # Asegurar que la URL apunta al bucket challenge-photos y pertenece estrictamente al user_id
    expected_prefix = f"{SUPABASE_URL}/storage/v1/object/public/challenge-photos/{user_id}/"
    if not photo_url.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="URL de foto no autorizada o inválida")
    return photo_url


def get_user_hobbies(user_id: str) -> list[str]:
    res = supabase_admin.table("user_hobbies").select("hobby_id").eq("user_id", user_id).execute()
    if not res or not res.data:
        return []
    return [row["hobby_id"] for row in res.data]


def get_daily_challenge(user_id: str, challenge_date: str, period: str = "AM") -> dict | None:
    validate_date(challenge_date)
    if period not in ("AM", "PM"):
        period = "AM"
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
    validate_date(challenge_date)
    if period not in ("AM", "PM"):
        period = "AM"
    if hobby_id not in VALID_HOBBIES and hobby_id != "General":
        hobby_id = "General"
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
    validate_date(challenge_date)
    if period not in ("AM", "PM"):
        period = "AM"
    validate_photo_url(photo_url, user_id)

    existing = get_daily_challenge(user_id, challenge_date, period)
    challenge_text = existing.get("challenge") if (existing and existing.get("challenge")) else "Reto completado con éxito"
    hobby_id = existing.get("hobby_id") if (existing and existing.get("hobby_id")) else "General"

    # Verificar con IA si la foto cumple el reto
    verification = verify_challenge_photo(challenge_text, photo_url)
    if not verification.get("is_valid", True):
        raise HTTPException(
            status_code=400,
            detail=verification.get("feedback", "La foto no parece coincidir con el reto asignado. Inténtalo de nuevo."),
        )

    ai_feedback = verification.get("feedback", "¡Reto completado con éxito!")

    payload = {
        "user_id": user_id,
        "challenge_date": challenge_date,
        "period": period,
        "photo_url": photo_url,
        "is_completed": True,
        "completed_at": "now()",
        "challenge": challenge_text,
        "hobby_id": hobby_id,
    }

    res = (
        supabase_admin.table("daily_challenges")
        .upsert(payload, on_conflict="user_id,challenge_date,period")
        .execute()
    )
    if res and res.data:
        result_row = res.data[0]
        result_row["ai_feedback"] = ai_feedback
        return result_row
    return {"success": True, "ai_feedback": ai_feedback}


def get_completed_challenges(user_id: str) -> list[dict]:
    res = (
        supabase_admin.table("daily_challenges")
        .select("id, challenge, is_completed, photo_url, challenge_date, hobby_id, period, completed_at, created_at")
        .eq("user_id", user_id)
        .not_.is_("photo_url", "null")
        .order("challenge_date", desc=True)
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
    if hobby_id not in VALID_HOBBIES:
        raise HTTPException(status_code=400, detail="Hobby inválido")
    try:
        supabase_admin.table("user_hobbies").insert({"user_id": user_id, "hobby_id": hobby_id}).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar hobby: {e}")
    return {"success": True}


@router.delete("/{hobby_id}")
def remove_hobby(hobby_id: str, user_id: str = Depends(get_current_user)):
    if hobby_id not in VALID_HOBBIES:
        raise HTTPException(status_code=400, detail="Hobby inválido")
    try:
        supabase_admin.table("user_hobbies").delete().eq("user_id", user_id).eq("hobby_id", hobby_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar hobby: {e}")
    return {"success": True}
