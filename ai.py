from google.genai._gaos.types.interactions import audiocontent
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

model = "gemini-3.5-flash-lite"
prompt = "Eres una app de retos diarios basados en pasatiempos para personas que se quieren alejar del doomscroll. Devuelve una respuesta corta en maximo 2 lineas. No uses lenguaje de programacion ni markdown."

hobby = "Musica"

if hobby == "Deporte":
    contents = prompt + "Dame unicamente un reto deportivo corto y facil de hacer para hoy, con una rutina de 1 hora"
elif hobby == "Musica":
    contents = prompt + "Dame unicamente un reto de canto corto y facil de hacer para hoy, con una rutina de 1 hora"
elif hobby == "Videojuegos":
    contents = prompt + "Dame unicamente un reto de videojuegos corto y facil de hacer para hoy, con una rutina de 1 hora"
elif hobby == "Arte":
    contents = prompt + "Dame unicamente un reto artistico corto y facil de hacer para hoy, con una rutina de 1 hora"
elif hobby == "Lectura":
    contents = prompt + "Dame unicamente un reto de lectura corto y facil de hacer para hoy, con una rutina de 1 hora"
elif hobby == "Cocina":
    contents = prompt + "Dame unicamente un reto de cocina corto y facil de hacer para hoy, con una rutina de 1 hora"

def get_message():
    response = client.models.generate_content(model=model, contents=contents)
    return response.text

#get_message()