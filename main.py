import os
import random
from datetime import date, datetime
from dotenv import load_dotenv
import uvicorn
from fastapi import Depends, FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai import get_message
from pydantic import BaseModel, Field
from hobbies import (
    complete_daily_challenge,
    get_completed_challenges,
    get_current_user,
    get_daily_challenge,
    get_user_hobbies,
    router as hobbies_router,
    save_daily_challenge,
    validate_date,
)
from social import router as social_router

load_dotenv()

app = FastAPI()

# CORS configurado de forma segura (restringido a orígenes permitidos o Azure app por defecto)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "https://hobi-csc4gqdaahejgbgh.centralus-01.azurewebsites.net",
        "http://localhost:8081",
        "http://localhost:19006",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(hobbies_router)
app.include_router(social_router)


def get_current_period() -> str:
    """Return 'AM' if before noon, 'PM' otherwise (server time fallback)."""
    return "AM" if datetime.now().hour < 12 else "PM"


class CompleteChallengeRequest(BaseModel):
    photo_url: str = Field(..., min_length=10)
    challenge_date: str | None = None
    period: str | None = None


@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/message")
def message(
    user_id: str = Depends(get_current_user),
    client_date: str | None = Query(None, description="Client local date YYYY-MM-DD"),
    period: str | None = Query(None, description="AM or PM"),
):
    today = client_date or date.today().isoformat()
    validate_date(today)
    current_period = period if period in ("AM", "PM") else get_current_period()

    cached = get_daily_challenge(user_id, today, current_period)
    if cached:
        return {
            "message": cached.get("challenge"),
            "is_completed": cached.get("is_completed", False),
            "photo_url": cached.get("photo_url"),
            "challenge_date": cached.get("challenge_date", today),
            "period": current_period,
        }
    hobbies = get_user_hobbies(user_id)
    if not hobbies:
        return {
            "message": "Aun no tienes hobbies seleccionados. Entra a Ajustes y elige tus pasatiempos para recibir tu reto diario.",
            "is_completed": False,
            "photo_url": None,
            "challenge_date": today,
            "period": current_period,
        }
    rng = random.Random(f"{user_id}:{today}:{current_period}")
    hobby = rng.choice(hobbies)
    challenge = get_message(hobby, today, current_period)
    try:
        save_daily_challenge(user_id, today, current_period, hobby, challenge)
    except Exception:
        cached = get_daily_challenge(user_id, today, current_period)
        if cached:
            return {
                "message": cached.get("challenge"),
                "is_completed": cached.get("is_completed", False),
                "photo_url": cached.get("photo_url"),
                "challenge_date": cached.get("challenge_date", today),
                "period": current_period,
            }
    return {
        "message": challenge,
        "is_completed": False,
        "photo_url": None,
        "challenge_date": today,
        "period": current_period,
    }

@app.get("/challenges/history")
def challenge_history(user_id: str = Depends(get_current_user)):
    history = get_completed_challenges(user_id)
    return {"history": history}

@app.post("/challenges/complete")
def complete_challenge(body: CompleteChallengeRequest, user_id: str = Depends(get_current_user)):
    today = body.challenge_date or date.today().isoformat()
    validate_date(today)
    current_period = body.period if body.period in ("AM", "PM") else get_current_period()
    updated = complete_daily_challenge(user_id, today, current_period, body.photo_url)
    feedback = updated.get("ai_feedback") if isinstance(updated, dict) else None
    return {"success": True, "challenge": updated, "feedback": feedback}


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("WEBSITES_PORT", "8000")))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
