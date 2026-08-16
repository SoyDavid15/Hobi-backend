import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

model = "gemini-3.5-flash-lite"
prompt = "Eres una app de retos diarios basados en pasatiempos para personas que se quieren alejar del doomscroll. Devuelve una respuesta corta en maximo 2 lineas. No uses lenguaje de programacion ni markdown. El reto debe ser corto, concreto y fotografiable: una accion visual que el usuario pueda demostrar tomandole una foto al completarla."

HOBBY_PROMPTS = {
    "Deporte": "Dame unicamente un reto deportivo corto y facil de hacer para hoy, con una rutina de 1 hora",
    "Musica": "Dame unicamente un reto de canto corto y facil de hacer para hoy, con una rutina de 1 hora",
    "Videojuegos": "Dame unicamente un reto de videojuegos corto y facil de hacer para hoy, con una rutina de 1 hora",
    "Arte": "Dame unicamente un reto artistico corto y facil de hacer para hoy, con una rutina de 1 hora",
    "Lectura": "Dame unicamente un reto de lectura corto y facil de hacer para hoy, con una rutina de 1 hora",
    "Cocina": "Dame unicamente un reto de cocina corto y facil de hacer para hoy, con una rutina de 1 hora",
}


def get_message(hobby: str) -> str:
    extra = HOBBY_PROMPTS.get(
        hobby,
        f"Dame unicamente un reto de {hobby} corto y facil de hacer para hoy, con una rutina de 1 hora",
    )
    client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    response = client.models.generate_content(
        model=model,
        contents=prompt + extra,
        config=types.GenerateContentConfig(temperature=0),
    )
    return "\n".join(response.text.strip().splitlines()[:2])