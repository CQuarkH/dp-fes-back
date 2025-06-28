from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from modules.auth.controllers.auth_controller import get_current_user
from modules.auth.schemas.auth_schemas import UserResponse  # Ajusta el import según tu esquema
from modules.documents.services.document_service import DocumentService
import os
import io
from PyPDF2 import PdfReader

router = APIRouter(tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = "uploads"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@router.get("")
async def get_user_documents(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Obtiene todos los documentos del usuario autenticado.
    """
    documents = DocumentService.get_documents_by_user(session=db, user_id=current_user.id)
    return {"documents": documents}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    # Leer el contenido del archivo
    contents = await file.read()
    
    # El servicio maneja toda la lógica
    doc = DocumentService.upload_document(
        session=db,
        user_id=current_user.id,
        file_contents=contents,
        filename=file.filename,
        content_type=file.content_type,
        upload_dir=UPLOAD_DIR,
        max_file_size=MAX_FILE_SIZE
    )

    return {"message": "Documento subido correctamente", "document_id": doc.id}

@router.post("/{document_id}/reject")
async def reject_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Rechaza un documento y cambia su estado a REJECTED.
    """
    try:
        DocumentService.reject_document(session=db, document_id=document_id, user_id=current_user.id)
        return {"message": "Documento rechazado correctamente"}
    except ValueError as e:
        raise HTTPException(400, str(e))
