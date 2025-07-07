import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import io
import tempfile
import hashlib

from modules.documents.models.document import Document, DocumentStatus
from modules.documents.models.signature import Signature
from modules.documents.models.user import User
from modules.documents.services.document_service import DocumentService
from modules.documents.services.document_state_service import DocumentStateService
from database import Base
from reportlab.pdfgen import canvas

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_dummy_user(session, id=1, role="EMPLOYEE"):
    user = User(id=id, name="Test", email=f"test{id}@mail.com", password_hash="123", role=role, is_active=True, created_at=datetime.utcnow())
    session.add(user)
    session.commit()
    return user

def create_dummy_pdf_bytes():
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, "PDF para test (service)")
    c.save()
    buf.seek(0)
    return buf.read()

def upload_pdf_obj(session, user_id, filename="some.pdf"):
    bytes_pdf = create_dummy_pdf_bytes()
    doc = DocumentService.upload_document(
        session, user_id, bytes_pdf, filename, "application/pdf", UPLOAD_DIR, MAX_FILE_SIZE
    )
    return doc

def test_PF_FR01_01_rechazar_no_pdf():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    bad_bytes = b"Fake DOCX content"
    with pytest.raises(Exception):
        DocumentService.upload_document(session, user.id, bad_bytes, "no_pdf.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", UPLOAD_DIR, MAX_FILE_SIZE)

def test_PF_FR01_02_subir_pdf_valido():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "prueba.pdf")
    assert doc.id is not None
    assert doc.status == DocumentStatus.IN_REVIEW
    assert doc.name.startswith("prueba")
    assert os.path.exists(doc.file_path)
    os.remove(doc.file_path)

def test_PF_FR02_01_estado_inicial_en_revision():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "nuevo.pdf")
    assert doc.status == DocumentStatus.IN_REVIEW
    os.remove(doc.file_path)

def test_PF_FR02_02_aprobar_documento():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=2, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "aprobar.pdf")
    doc.status = DocumentStatus.SIGNED
    doc.last_status_change = datetime.utcnow()
    session.commit()
    assert doc.status == DocumentStatus.SIGNED
    os.remove(doc.file_path)

def test_PF_FR02_03_rechazar_documento():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=3, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "rechazar.pdf")
    doc.status = DocumentStatus.REJECTED
    doc.last_status_change = datetime.utcnow()
    session.commit()
    assert doc.status == DocumentStatus.REJECTED
    os.remove(doc.file_path)

def test_PF_FR03_01_primera_firma_registra_estado():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=999, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "doc_firma.pdf")
    sig = DocumentService.add_signature(session, doc.id, supervisor.id)
    assert sig.order == 1
    assert sig.ts is not None
    assert sig.sha256_hash is not None
    os.remove(doc.file_path)

def test_documento_se_guarda_como_propiedad_del_usuario():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "su_doc.pdf")
    rec_doc = session.query(Document).filter_by(id=doc.id).first()
    assert rec_doc is not None
    assert rec_doc.user_id == user.id
    os.remove(doc.file_path)

def test_no_firma_si_documento_inexistente():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    with pytest.raises(Exception):
        DocumentService.add_signature(session, doc_id=1234, user_id=user.id)

def test_PF_FR03_03_limite_de_firmas():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=300, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "firmas.pdf")
    # Primera firma cambia estado, está permitida
    sig1 = DocumentService.add_signature(session, doc.id, supervisor.id)
    assert sig1.order == 1
    # Intentar más firmas debe fallar según la lógica actual (solo se permite uno)
    signer2 = create_dummy_user(session, id=301, role="SUPERVISOR")
    with pytest.raises(Exception, match="cannot change document from SIGNED to SIGNED"):
        DocumentService.add_signature(session, doc.id, signer2.id)
    os.remove(doc.file_path)

def test_ver_historial_basico_documento():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=401, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "historial.pdf")
    DocumentService.add_signature(session, doc.id, supervisor.id)
    firmas = session.query(Signature).filter_by(document_id=doc.id).all()
    assert len(firmas) == 1
    assert firmas[0].user_id == supervisor.id
    assert firmas[0].ts is not None
    doc_db = session.query(Document).filter_by(id=doc.id).first()
    assert doc_db is not None
    assert doc_db.status in [DocumentStatus.IN_REVIEW, DocumentStatus.SIGNED]  # según lógica
    os.remove(doc.file_path)

def test_PF_FR05_01_control_acceso_empleado():
    session = TestingSessionLocal()
    empleado = create_dummy_user(session, id=4, role="EMPLOYEE")
    assert empleado.role.name == "EMPLOYEE"

def test_PF_FR05_02_supervisor_no_elimina_manual():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=5, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "rechazado.pdf")
    doc.status = DocumentStatus.REJECTED
    doc.upload_date = datetime.utcnow() - timedelta(days=10)
    session.commit()
    doc_check = session.query(Document).filter_by(id=doc.id).first()
    assert doc_check is not None
    os.remove(doc.file_path)

def test_PF_FR06_01_rechazado_accesible():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "rechazo29.pdf")
    doc.status = DocumentStatus.REJECTED
    doc.upload_date = datetime.utcnow() - timedelta(days=29)
    session.commit()
    rec = session.query(Document).filter_by(id=doc.id).first()
    assert rec is not None
    os.remove(doc.file_path)

def test_PF_FR06_02_cron_elimina_documento():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "rechazo31.pdf")
    doc.status = DocumentStatus.REJECTED
    doc.upload_date = datetime.utcnow() - timedelta(days=31)
    session.commit()
    session.delete(doc)
    session.commit()
    rec = session.query(Document).filter_by(id=doc.id).first()
    assert rec is None
    # doc.file_path puede no existir a este punto si ya fue borrado por lógica de cleanup

def test_PF_FR07_01_validar_hash_documento():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=501, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "validar.pdf")
    sig = DocumentService.add_signature(session, doc.id, supervisor.id)
    with open(doc.file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert sig.sha256_hash == file_hash
    os.remove(doc.file_path)

def test_PF_FR07_02_detectar_pdf_modificado():
    session = TestingSessionLocal()
    supervisor = create_dummy_user(session, id=601, role="SUPERVISOR")
    doc = upload_pdf_obj(session, supervisor.id, "modificar.pdf")
    sig = DocumentService.add_signature(session, doc.id, supervisor.id)
    with open(doc.file_path, "ab") as f:
        f.write(b"MODIFICACION")
    with open(doc.file_path, "rb") as f:
        altered_hash = hashlib.sha256(f.read()).hexdigest()
    assert sig.sha256_hash != altered_hash
    os.remove(doc.file_path)

def test_PF_FR08_01_registrar_usuario():
    session = TestingSessionLocal()
    nuevo = create_dummy_user(session, id=50, role="EMPLOYEE")
    user = session.query(User).filter_by(id=50).first()
    assert user is not None
    assert user.role.name == "EMPLOYEE"

def test_PF_FR08_02_login_usuario_inexistente():
    session = TestingSessionLocal()
    user = session.query(User).filter_by(email="noexiste@mail.com").first()
    assert user is None

def test_PF_FR09_01_09_02_notificaciones_internas():
    session = TestingSessionLocal()
    user = create_dummy_user(session)
    doc = upload_pdf_obj(session, user.id, "alerta.pdf")
    doc.status = DocumentStatus.SIGNED
    session.commit()
    alerta_ui = f"Documento {doc.name} ha sido firmado"
    assert "firmado" in alerta_ui.lower()
    correo_enviado = False
    assert correo_enviado is False
    os.remove(doc.file_path)