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
    # 1) Validación de MIME y extensión
    if file.content_type != "application/pdf":
        raise HTTPException(400, "El archivo debe ser un PDF")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "La extensión debe ser .pdf")

    # 2) Leer contenido y validar tamaño
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "El tamaño máximo es 10 MB")

    # 3) Verificar integridad del PDF
    try:
        reader = PdfReader(io.BytesIO(contents))
        _ = reader.pages
    except Exception:
        raise HTTPException(400, "PDF inválido o dañado")

    # 4) Guardar en disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # 5) Persistir metadatos pasando current_user.id
    doc = DocumentService.upload_document(
        session= db,
        user_id= current_user.id,
        name= file.filename,
        file_path= file_path,
        file_size= file.size
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
