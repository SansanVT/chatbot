import os
from fastapi import Header, HTTPException

async def verificar_token(x_token: str = Header(None)):
    token_maestro = os.getenv("ADMIN_SECRET_TOKEN")
    if x_token != token_maestro:
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado: El token de seguridad es inválido o no fue proporcionado."
        )
    return x_token