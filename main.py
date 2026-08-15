from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai import get_message
from hobbies import router as hobbies_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hobbies_router)

@app.get("/message")
def message():
    return get_message()