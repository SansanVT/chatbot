import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import chat, documents
import os
from fastapi import Header, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Depends
from app.dependencies import verificar_token

load_dotenv()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Cerebro UTTEC Bot",
    description="API de IA para responder dudas escolares usando RAG.",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(chat.router)
app.include_router(documents.router)

origins = [
    "http://localhost",
    "http://127.0.0.1"
    # "https://coordinacioninglesuttec.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@limiter.limit("5/minute")
def health_check(request: Request):
    return {
        "estado": "activo 🟢",
        "modo": os.getenv("ENVIRONMENT"),
        "mensaje": "El sistema neuronal está listo."
    }

@app.post("/reload", dependencies=[Depends(verificar_token)])
@limiter.limit("10/minute")
async def reload_knowledge(request: Request):
    try:
        from app.services.rag_service import brain 
        brain.initialize_brain()
        return {"status": "success", "message": "Cerebro refrescado"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)