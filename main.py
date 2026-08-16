import random
from datetime import date

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai import get_message
from hobbies import (
    get_current_user,
    get_daily_challenge,
    get_user_hobbies,
    router as hobbies_router,
    save_daily_challenge,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hobbies_router)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/message")
def message(user_id: str = Depends(get_current_user)):
    today = date.today().isoformat()
    cached = get_daily_challenge(user_id, today)
    if cached:
        return {"message": cached}
    hobbies = get_user_hobbies(user_id)
    if not hobbies:
        return {"message": "Aun no tienes hobbies seleccionados. Entra a Ajustes y elige tus pasatiempos para recibir tu reto diario."}
    rng = random.Random(f"{user_id}:{today}")
    hobby = rng.choice(hobbies)
    challenge = get_message(hobby)
    try:
        save_daily_challenge(user_id, today, hobby, challenge)
    except Exception:
        cached = get_daily_challenge(user_id, today)
        if cached:
            return {"message": cached}
    return {"message": challenge}