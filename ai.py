import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

model = "gemini-3.5-flash-lite"
prompt = "Eres una app de retos diarios basados en pasatiempos para personas que se quieren alejar del doomscroll. Devuelve una respuesta corta en maximo 2 lineas. No uses lenguaje de programacion ni markdown. El reto debe ser corto, concreto y fotografiable: una accion visual que el usuario pueda demostrar tomandole una foto al completarla."

HOBBY_PROMPTS = {
    "Deporte": "Dame únicamente un micro-reto físico muy sencillo y seguro para hacer hoy.",
    "Musica": "Dame únicamente un micro-reto musical sencillo para practicar hoy.",
    "Videojuegos": "Dame únicamente un micro-reto de gaming saludable y corto para hoy.",
    "Arte": "Dame únicamente un micro-reto artístico sencillo y rápido para hoy.",
    "Lectura": "Dame únicamente un micro-reto de lectura corto y agradable para hoy.",
    "Cocina": "Dame únicamente un micro-reto culinario sencillo, seguro y casero para hoy.",
}

FALLBACK_CHALLENGES = {
    "Deporte": "Haz 15 sentadillas suaves y estira tus piernas frente a una ventana.",
    "Musica": "Escucha tu canción favorita completa prestando atención a cada instrumento.",
    "Videojuegos": "Organiza tu espacio de juego o repasa una estrategia mental.",
    "Arte": "Haz un garabato rápido en una hoja en blanco inspirándote en lo que ves.",
    "Lectura": "Lee 5 páginas de un libro que tengas a la mano.",
    "Cocina": "Prepara un vaso de agua con limón o un té saludable.",
}


def get_message(hobby: str, date_str: str | None = None, period: str | None = None) -> str:
    extra = HOBBY_PROMPTS.get(
        hobby,
        f"Dame únicamente un micro-reto de {hobby} corto y fácil de hacer para hoy.",
    )
    if date_str and period in ("AM", "PM"):
        period_label = "mañana" if period == "AM" else "tarde"
        extra += (
            f". Contexto: hoy es {date_str}, turno de la {period_label}. "
            "Propon un reto distinto a los de días y turnos anteriores, evita repetir actividades."
        )
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=prompt + " " + extra,
            config=types.GenerateContentConfig(temperature=0.8),
        )
        if response and response.text:
            return "\n".join(response.text.strip().splitlines()[:2])
    except Exception as e:
        print(f"Error generando con Gemini para {hobby}: {e}")

    return FALLBACK_CHALLENGES.get(hobby, "Toma una foto a algo que te inspire hoy y sonríe.")