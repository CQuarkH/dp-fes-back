import hashlib
import io
import os

from PyPDF2 import PdfReader
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.signature import Signature
from modules.documents.models.user import User
from modules.documents.services.document_state_service import DocumentStateService
from datetime import datetime
from modules.documents.models.user import UserRole

class DocumentService:

    @staticmethod
    def get_documents_by_user(session: Session, user_id: int) -> list[Document]:
        """
        Obtiene todos los documentos de un usuario
        """
        user = session.get(User, user_id)
        
        if user.role in [UserRole.SUPERVISOR, UserRole.INSTITUTIONAL_MANAGER]:
            return session.query(Document).all()
        
        else:
            return session.query(Document).filter(Document.user_id == user_id).all()


    @staticmethod
    def add_signature(session: Session, document_id: int, user_id: int) -> Signature:
        """Añade una firma simple con límite de 5 por documento y calcula hash."""
        # 1) Cargar entidad
        doc = session.get(Document, document_id)
        user = session.get(User, user_id)
        if not doc or not user:
            raise ValueError("Documento o usuario no existe")

        # 2) Límite de 5 firmas
        existing = doc.signatures
        if len(existing) >= 5:
            raise ValueError("Máximo de 5 firmas alcanzado")

        # 3) Leer archivo y calcular SHA‑256
        with open(doc.file_path, "rb") as f:
            data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()

        # 4) Determinar orden (1..n)
        next_order = (max([s.order for s in existing]) + 1) if existing else 1

        # 5) Crear firma
        sig = Signature(
            document_id=document_id,
            user_id=user_id,
            ts=datetime.utcnow(),
            order=next_order,
            sha256_hash=sha256
        )
        session.add(sig)
       
        DocumentStateService.change_document_state(
                session, document_id, user_id, DocumentStatus.SIGNED
            )
        session.commit()
        return sig

    @staticmethod
    def upload_document(
        session: Session, 
        user_id: int, 
        file_contents: bytes, 
        filename: str, 
        content_type: str,
        upload_dir: str,
        max_file_size: int = 10 * 1024 * 1024  # 10 MB por defecto
    ) -> Document:
        """
        Procesa y guarda un documento completo:
        - Valida el archivo
        - Determina nombre único
        - Guarda archivo físico
        - Crea registro en BD
        """
        
        # 1) Validaciones
        DocumentService._validate_file(file_contents, filename, content_type, max_file_size)
        
        # 2) Determinar nombre único
        unique_name = DocumentService._get_unique_filename(session, user_id, filename)
        
        # 3) Crear directorio si no existe
        os.makedirs(upload_dir, exist_ok=True)
        
        # 4) Guardar archivo físico
        file_path = os.path.join(upload_dir, unique_name)
        with open(file_path, "wb") as f:
            f.write(file_contents)
        
        # 5) Crear registro en BD
        document = Document(
            name=unique_name,
            file_path=file_path,
            file_size=len(file_contents),
            status=DocumentStatus.IN_REVIEW,
            user_id=user_id,
            upload_date=datetime.utcnow()
        )
        session.add(document)
        session.commit()
        
        return document
    
    @staticmethod
    def _validate_file(file_contents: bytes, filename: str, content_type: str, max_file_size: int):
        """Valida el archivo subido"""
        
        # Validar MIME type
        if content_type != "application/pdf":
            raise HTTPException(400, "El archivo debe ser un PDF")
        
        # Validar extensión
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(400, "La extensión debe ser .pdf")
        
        # Validar tamaño
        if len(file_contents) > max_file_size:
            raise HTTPException(400, f"El tamaño máximo es {max_file_size // (1024*1024)} MB")
        
        # Validar integridad del PDF
        try:
            reader = PdfReader(io.BytesIO(file_contents))
            _ = reader.pages
        except Exception:
            raise HTTPException(400, "PDF inválido o dañado")
    
    @staticmethod
    def _get_unique_filename(session: Session, user_id: int, original_name: str) -> str:
        """Determina el nombre único que se usará para el archivo"""
        
        # Separar nombre y extensión
        base, ext = os.path.splitext(original_name)
        
        # Consultar documentos existentes del usuario con el mismo nombre base
        existing_names = (
            session.query(Document.name)
            .filter(
                Document.user_id == user_id,
                or_(
                    Document.name == original_name,  # Nombre exacto
                    Document.name.ilike(f"{base}_%{ext}")  # Con sufijo _n
                )
            )
            .all()
        )
        existing = [row[0] for row in existing_names]
        
        # Si no hay duplicados, usar el nombre original
        if not existing:
            return original_name
        
        # Extraer sufijos _n ya usados
        used_numbers = set()
        
        for existing_name in existing:
            if existing_name == original_name:
                # El nombre original sin sufijo existe
                used_numbers.add(0)  # Consideramos que el original es _0
            elif existing_name.startswith(f"{base}_") and existing_name.endswith(ext):
                # Extraer el número del sufijo
                try:
                    # Obtener la parte entre "base_" y "ext"
                    start_idx = len(base) + 1  # Longitud de "base_"
                    end_idx = len(existing_name) - len(ext) if ext else len(existing_name)
                    
                    if end_idx > start_idx:
                        number_str = existing_name[start_idx:end_idx]
                        number = int(number_str)
                        used_numbers.add(number)
                except (ValueError, IndexError):
                    # Si no se puede extraer el número, ignorar
                    continue
        
        # Encontrar el siguiente número disponible
        next_num = 1
        while next_num in used_numbers:
            next_num += 1
        
        return f"{base}_{next_num}{ext}"

    @staticmethod
    def sign_document(session: Session, document_id: int, user_id: int) -> Document:
        """
        Sign a document (change to SIGNED)
        """
        return DocumentStateService.change_document_status(
            session, document_id, user_id, DocumentStatus.SIGNED
        )

    @staticmethod
    def reject_document(session: Session, document_id: int, user_id: int) -> Document:
        """
        Reject a document (change to REJECTED)
        """
        return DocumentStateService.change_document_state(
            session, document_id, user_id, DocumentStatus.REJECTED
        )
