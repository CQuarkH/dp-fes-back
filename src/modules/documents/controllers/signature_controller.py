# src/modules/documents/controllers/signature_controller.py
import hashlib

from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from database import SessionLocal
from modules.documents.models import Document
from modules.documents.services.document_service import DocumentService

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/{document_id}/sign")
def sign_document(
    document_id: int,
    user_id:     int,
    db:          Session = Depends(get_db)
):
    """
    Añade una firma: hasta 5 por documento, guarda sha256.
    """
    try:
        sig = DocumentService.add_signature(db, document_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "message":       "Firma añadida",
        "signature_id":  sig.id,
        "order":         sig.order,
        "timestamp":     sig.ts,
        "sha256_hash":   sig.sha256_hash
    }

@router.get("/{document_id}/download")
def download_and_validate(document_id: int, db: Session = Depends(get_db)):
    """
    Devuelve el PDF si el hash coincide; si no, marca como inválido.
    """
    # 1) Obtener documento y última firma
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    if not doc.signatures:
        raise HTTPException(400, "Aún no tiene firmas")

    last_sig = doc.signatures[-1]

    # 2) Leer archivo y recalcular hash
    with open(doc.file_path, "rb") as f:
        data = f.read()
    current_hash = hashlib.sha256(data).hexdigest()

    if current_hash != last_sig.sha256_hash:
        raise HTTPException(400, "Integridad comprometida: hash no coincide")

    # 3) Devolver PDF
    return Response(content=data, media_type="application/pdf")
