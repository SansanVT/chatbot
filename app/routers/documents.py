from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
from pathlib import Path

router = APIRouter(prefix="/documents", tags=["Documentos"])

# Definimos la ruta de destino
UPLOAD_DIR = Path("data_storage/raw_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/ingest")
async def ingest_document(
    document_id: int = Form(...),
    tipo: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Generamos el nombre: ID_NombreOriginal.ext
        file_name = f"{document_id}_{file.filename}"
        file_path = UPLOAD_DIR / file_name

        # Guardar físicamente
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "success",
            "message": f"Documento {document_id} recibido en el cerebro.",
            "path_local": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")