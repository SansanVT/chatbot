from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services.rag_service import buscar_informacion 
# Importamos el escudo desde el main
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class PreguntaUsuario(BaseModel):
    texto: str
    usuario_id: str
    prompt_maestro: str  

@router.post("/chat/enviar")
@limiter.limit("15/minute")
async def conversar(request: Request, entrada: PreguntaUsuario):
    try:
        resultado = buscar_informacion(entrada.texto, entrada.usuario_id, entrada.prompt_maestro)
        
        return {
            "respuesta": resultado['respuesta'],
            "usuario": entrada.usuario_id,
            "is_recognized": resultado['is_recognized'],
            "fuente": "Cerebro RAG UTTEC"
        }
        
    except Exception as e:
        if "429" in str(e):
            return {"respuesta": "El cerebro del bot necesita un pequeño descanso. Intenta de nuevo en unos minutos.", "is_recognized": False}
        return {"respuesta": "Error interno en el servidor Python.", "error": str(e)}