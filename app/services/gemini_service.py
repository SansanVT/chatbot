import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("ERROR: No se encontró la GOOGLE_API_KEY en el archivo .env")

genai.configure(api_key=API_KEY)

generation_config = {
    "temperature": 0.7,          # Creatividad (0.0 es robot, 1.0 es poeta)
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,   # Límite de respuesta
}

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config=generation_config,
    system_instruction="Eres un asistente útil y amable de la universidad UTTEC. Tu objetivo es ayudar a los alumnos con respuestas claras y breves."
)

async def obtener_respuesta_gemini(texto_usuario: str):
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(texto_usuario)
        return response.text
    except Exception as e:
        print(f"Error en Gemini: {e}")
        return "Lo siento, mis neuronas están desconectadas momentáneamente. Intenta de nuevo."