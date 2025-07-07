from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from modules.documents.services.document_service import DocumentService
import os
import io
from PyPDF2 import PdfReader

router = APIRouter(
    tags=["documents"]  
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = "uploads"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_document(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "El archivo debe ser un PDF")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "La extensión debe ser .pdf")
    contents = await file.read()
    file_size = len(contents) 
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, "El tamaño máximo es 10 MB")
    try:
        reader = PdfReader(io.BytesIO(contents))
        _ = reader.pages
    except Exception:
        raise HTTPException(400, "PDF inválido o dañado")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    doc = DocumentService.upload_document(db, user_id, file.filename, file_path, file_size)
    return {"message": "Documento subido correctamente", "document_id": doc.id}