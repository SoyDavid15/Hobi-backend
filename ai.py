import os
import urllib.request
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

model = "gemini-1.5-flash"
prompt = (
    "Eres una app de retos diarios creativos y específicos basados en pasatiempos para personas que se quieren alejar del doomscroll. "
    "Devuelve una respuesta corta en máximo 2 líneas. No uses lenguaje de programación ni markdown. "
    "El reto debe ser ultra-específico, original, fácil de hacer en menos de 1 hora y realizarse completamente en casa o en un espacio cerrado y seguro "
    "(el usuario solo debe salir a la calle si expresamente lo desea por seguridad). "
    "Debe ser una acción visual concreta que el usuario pueda demostrar tomandole una foto al completarla."
)

HOBBY_PROMPTS = {
    "Deporte": "Dame un micro-reto físico creativo, dinámico y seguro para hacer en casa (máx 20 min, sin necesidad de salir a la calle).",
    "Musica": "Dame un micro-reto musical original y divertido para practicar en casa en menos de 30 minutos.",
    "Videojuegos": "Dame un micro-reto de gaming o análisis mental de videojuegos creativo y rápido para hacer en casa.",
    "Arte": "Dame un micro-reto artístico original y casero usando objetos cotidianos para completar en 30 minutos.",
    "Lectura": "Dame un micro-reto de lectura ágil y placentero (ej. leer un fragmento breve o artículo inspirador) para hacer en casa.",
    "Cocina": "Dame un micro-reto culinario casero, sencillo y seguro utilizando ingredientes comunes de la alacena.",
}

FALLBACK_CHALLENGES = {
    "Deporte": "Haz 15 sentadillas suaves y estira tus piernas frente a una ventana de casa.",
    "Musica": "Tararea o toca una melodía alegre durante 5 minutos usando cualquier objeto como percusión.",
    "Videojuegos": "Organiza tu espacio de juego o diseña mentalmente un nivel de tu videojuego favorito.",
    "Arte": "Haz un dibujo rápido en una hoja usando solo tres colores que tengas a la mano.",
    "Lectura": "Lee un capítulo corto o artículo interesante y destaca tu frase favorita.",
    "Cocina": "Prepara una infusión relajante o un snack saludable casero con lo que tengas.",
}


def get_message(hobby: str, date_str: str | None = None, period: str | None = None) -> str:
    extra = HOBBY_PROMPTS.get(
        hobby,
        f"Dame un micro-reto creativo de {hobby} fácil y seguro para hacer en casa hoy.",
    )
    if date_str and period in ("AM", "PM"):
        period_label = "mañana" if period == "AM" else "tarde"
        extra += (
            f". Contexto: hoy es {date_str}, turno de la {period_label}. "
            "Propon un reto distinto, original y específico, evitando repetir actividades."
        )
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=prompt + " " + extra,
            config=types.GenerateContentConfig(temperature=0.85),
        )
        if response and response.text:
            return "\n".join(response.text.strip().splitlines()[:2])
    except Exception as e:
        print(f"Error generando con Gemini para {hobby}: {e}")

    return FALLBACK_CHALLENGES.get(hobby, "Toma una foto a algo creativo en tu casa hoy y sonríe.")


def verify_challenge_photo(challenge_text: str, photo_url: str) -> dict:
    """Verifica mediante Gemini si la foto evidencia el cumplimiento del reto."""
    try:
        req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            image_bytes = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
    except Exception as e:
        print(f"Error descargando foto para verificación IA: {e}")
        return {
            "is_valid": True,
            "feedback": "¡Reto registrado con éxito! (Verificación offline)",
        }

    verification_prompt = (
        "Eres un juez de IA amigable, motivador pero justo para una aplicación de hábitos y bienestar. "
        f"El reto asignado al usuario es: '{challenge_text}'. "
        "Analiza la imagen adjunta y determina si muestra evidencia razonable de que el usuario ha cumplido o intentado cumplir el reto en casa o un espacio seguro. "
        "Responde estrictamente en formato de texto plano con dos líneas: "
        "Línea 1: VÁLIDO (si cumple razonablemente) o INVÁLIDO (si la foto no tiene ninguna relación con el reto o es completamente negra/inválida). "
        "Línea 2: Un mensaje corto, motivador y constructivo en español (máximo 1 o 2 frases) dando retroalimentación al usuario."
    )

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=[
                verification_prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=content_type),
            ],
            config=types.GenerateContentConfig(temperature=0.2),
        )
        if response and response.text:
            lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
            if lines:
                first_line = lines[0].upper()
                is_valid = "VÁLIDO" in first_line or "VALIDO" in first_line or "SI" in first_line
                if "INVÁLIDO" in first_line or "INVALIDO" in first_line or "NO" in first_line:
                    is_valid = False
                
                feedback = lines[1] if len(lines) > 1 else ("¡Gran trabajo completando el reto!" if is_valid else "La foto no parece coincidir con el reto. Inténtalo de nuevo.")
                return {
                    "is_valid": is_valid,
                    "feedback": feedback,
                }
    except Exception as e:
        print(f"Error en verificación Gemini con imagen: {e}")

    return {
        "is_valid": True,
        "feedback": "¡Reto completado con éxito!",
    }
