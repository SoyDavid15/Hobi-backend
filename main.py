import os
import random
from datetime import date, datetime
from dotenv import load_dotenv
import uvicorn
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from ai import get_message
from pydantic import BaseModel
from hobbies import (
    complete_daily_challenge,
    get_completed_challenges,
    get_current_user,
    get_daily_challenge,
    get_user_hobbies,
    router as hobbies_router,
    save_daily_challenge,
)

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hobbies_router)


def get_current_period() -> str:
    """Return 'AM' if before noon, 'PM' otherwise (server time fallback)."""
    return "AM" if datetime.now().hour < 12 else "PM"


class CompleteChallengeRequest(BaseModel):
    photo_url: str
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
    current_period = body.period if body.period in ("AM", "PM") else get_current_period()
    updated = complete_daily_challenge(user_id, today, current_period, body.photo_url)
    return {"success": True, "challenge": updated}


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("WEBSITES_PORT", "8000")))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)