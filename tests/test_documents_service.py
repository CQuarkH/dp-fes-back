import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta


from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.signature import Signature
from modules.documents.models.user import User
from modules.documents.services.document_service import DocumentService
from modules.documents.services.document_state_service import DocumentStateService
from database import Base
import os
import tempfile

@pytest.fixture(autouse=True)
def clean_db():
    # Elimina y recrea todas las tablas entre tests
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# Configurar base de datos en memoria para pruebas unitarias
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def create_dummy_user(session, id=1, role="EMPLOYEE"):
    user = User(id=id, name="Test", email=f"test{id}@mail.com", password_hash="123", role=role, is_active=True, created_at=datetime.utcnow())
    session.add(user)
    session.commit()
    return user

def create_dummy_pdf():
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    temp.close()
    return temp.name

def test_PF_FR01_02_subir_pdf_valido():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    path = create_dummy_pdf()

    doc = DocumentService.upload_document(session, user.id, "prueba.pdf", path, os.path.getsize(path))

    assert doc.id is not None
    assert doc.status == DocumentStatus.IN_REVIEW
    assert doc.name == "prueba.pdf"
    os.remove(path)

def test_PF_FR03_03_limite_de_firmas():
    session = TestingSessionLocal()
    owner = create_dummy_user(session)
    path = create_dummy_pdf()

    doc = DocumentService.upload_document(session, owner.id, "firmas.pdf", path, os.path.getsize(path))

    for i in range(1, 6):
        signer = create_dummy_user(session, id=10+i)
        sig = DocumentService.add_signature(session, doc.id, signer.id)
        assert sig.order == i

    # Intentar una sexta firma
    signer6 = create_dummy_user(session, id=99)
    with pytest.raises(ValueError, match="Máximo de 5 firmas alcanzado"):
        DocumentService.add_signature(session, doc.id, signer6.id)

    os.remove(path)

def test_PF_FR03_01_primera_firma_registra_estado():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    path = create_dummy_pdf()
    doc = DocumentService.upload_document(session, user.id, "doc_firma.pdf", path, os.path.getsize(path))
    sig = DocumentService.add_signature(session, doc.id, user.id)

    assert sig.order == 1
    assert sig.ts is not None
    assert sig.sha256_hash is not None
    os.remove(path)

def test_documento_se_guarda_como_propiedad_del_usuario():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    path = create_dummy_pdf()

    doc = DocumentService.upload_document(session, user.id, "su_doc.pdf", path, os.path.getsize(path))

    rec_doc = session.query(Document).filter_by(id=doc.id).first()
    assert rec_doc is not None
    assert rec_doc.user_id == user.id

    os.remove(path)

def test_no_firma_si_documento_inexistente():
    session = TestingSessionLocal()
    user = create_dummy_user(session)

    with pytest.raises(Exception):
        DocumentService.add_signature(session, doc_id=1234, signer_id=user.id)   # doc_id que no existe

def test_ver_historial_basico_documento():
    session = TestingSessionLocal()
    empleado = create_dummy_user(session, id=1, role="EMPLOYEE")
    path = create_dummy_pdf()
    doc = DocumentService.upload_document(session, empleado.id, "historial.pdf", path, os.path.getsize(path))
    # Una firma
    DocumentService.add_signature(session, doc.id, empleado.id)

    # Revisa tablas relacionadas directamente
    from modules.documents.models.signature import Signature
    firmas = session.query(Signature).filter_by(document_id=doc.id).all()

    assert len(firmas) == 1
    assert firmas[0].user_id == empleado.id
    assert firmas[0].ts is not None

    # Evento de creación
    from modules.documents.models.document import Document
    doc_db = session.query(Document).filter_by(id=doc.id).first()
    assert doc_db is not None
    assert doc_db.status == DocumentStatus.IN_REVIEW

    os.remove(path)

    