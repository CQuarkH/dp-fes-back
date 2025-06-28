import pytest
import httpx
import hashlib
from time import sleep

BASE_URL = "http://localhost:8000"  # Ajústalo si usas otro puerto/url

@pytest.fixture(scope="session")
def example_pdf():
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF"
    )

@pytest.fixture(scope="session")
def non_pdf():
    return b'This is not a PDF docx'

@pytest.fixture(scope="session")
def empleado_id():
    # Debe existir en la BD: Juan (id=2 según tu código)
    return 2

@pytest.fixture(scope="session")
def supervisor_id():
    # Debe existir en la BD: Ana (id=3 según tu código)
    return 3

# --- Pruebas Funcionales ---

def test_PF_FR01_01_rechaza_docx(empleado_id, non_pdf):
    files = {"file": ("doc_no.pdf", non_pdf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code == 400
        assert "PDF" in resp.text or "solo se permiten archivos pdf" in resp.text.lower()

def test_PF_FR01_02_subir_pdf_valido(empleado_id, example_pdf):
    files = {"file": ("documento_valido.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code == 200
        assert isinstance(resp.json().get("document_id"), int)

def test_PF_FR02_01_estado_en_revision_automatico(empleado_id, example_pdf):
    files = {"file": ("estado_revision.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        upload = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        docid = upload.json()["document_id"]
        details = c.get(f"{BASE_URL}/documents/{docid}")
        assert details.status_code == 200
        assert details.json()['status'] == "IN_REVIEW"

def test_PF_FR02_02_supervisor_firma_y_estado_firmado(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("firma_supervisor.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        docid = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files).json()["document_id"]
        resp = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        assert resp.status_code == 200
        info = c.get(f"{BASE_URL}/documents/{docid}")
        assert info.json()["status"] == "SIGNED"

def test_PF_FR02_03_supervisor_rechaza_y_estado_rechazado(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("rechazado.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        docid = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files).json()["document_id"]
        reject = c.post(f"{BASE_URL}/documents/{docid}/reject", params={"user_id": supervisor_id})
        assert reject.status_code == 200
        info = c.get(f"{BASE_URL}/documents/{docid}")
        assert info.json()["status"] == "REJECTED"

def test_PF_FR03_01_firma_estado_persistente(empleado_id, supervisor_id, example_pdf):
    # Sube, Supervisor firma, estado correcto
    files = {"file": ("firmaz.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        docid = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files).json()["document_id"]
        # Firma 1
        c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        info = c.get(f"{BASE_URL}/documents/{docid}")
        assert info.json()["status"] in ("SIGNED", "IN_REVIEW")  # Según tu flujo

def test_PF_FR03_02_limite_de_firmas(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("5firmas.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        docid = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files).json()["document_id"]
        signers = [supervisor_id, empleado_id, 4, 5, 6, 7]
        for i, uid in enumerate(signers):
            resp = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": uid})
            if i < 5:
                assert resp.status_code == 200
            else:
                assert resp.status_code in (400, 422)
                assert "5 firmas" in resp.text.lower() or "límite" in resp.text.lower()

# --- Pruebas de Integración ---

def test_PF_FR04_01_historial_documento(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("historial.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        docid = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files).json()["document_id"]
        c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        resp = c.get(f"{BASE_URL}/documents/{docid}/history")
        assert resp.status_code == 200
        eventos = resp.json()
        assert any("subida" in e.get("tipo", "").lower() or "upload" in e.get("tipo", "").lower() for e in eventos)
        assert any("firma" in e.get("tipo", "").lower() for e in eventos) 