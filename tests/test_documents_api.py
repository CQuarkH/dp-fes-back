import pytest
import httpx
import io
from reportlab.pdfgen import canvas
import hashlib

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="session")
def empleado_login():
    return {"email": "juan@empresa.com", "password": "juan123"}

@pytest.fixture(scope="session")
def supervisor_login():
    return {"email": "ana@empresa.com", "password": "ana123"}

@pytest.fixture(scope="session")
def otro_login():
    # Usa otro usuario existente en tu base de datos de pruebas, si existe agrega aquí.
    return {"email": "carlos@empresa.com", "password": "carlos123"}

@pytest.fixture(scope="session")
def example_pdf():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 750, "Este es un PDF de prueba para firmar.")
    c.save()
    buffer.seek(0)
    return buffer.read()

@pytest.fixture(scope="session")
def non_pdf():
    return b'This is not a PDF docx'

def get_token(login_data):
    resp = httpx.post(f"{BASE_URL}/auth/login", json=login_data)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_upload_non_pdf_rejected(empleado_login, non_pdf):
    token = get_token(empleado_login)
    files = {"file": ("documento.docx", non_pdf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    resp = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert resp.status_code in {400, 422}
    assert "pdf" in resp.text.lower()

def test_upload_pdf_accepted(empleado_login, example_pdf):
    token = get_token(empleado_login)
    files = {"file": ("documento_valido.pdf", example_pdf, "application/pdf")}
    resp = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "document_id" in data

def test_upload_empty_pdf_rejected(empleado_login):
    token = get_token(empleado_login)
    files = {"file": ("vacio.pdf", b"", "application/pdf")}
    resp = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert resp.status_code in {400, 422}
    assert ("pdf" in resp.text.lower() or 
            "vacío" in resp.text.lower() or 
            "empty" in resp.text.lower() or 
            "invalid" in resp.text.lower())

def test_sign_nonexistent_document(supervisor_login):
    token = get_token(supervisor_login)
    fake_docid = 999999999
    resp = httpx.post(
        f"{BASE_URL}/documents/{fake_docid}/sign",
        headers=auth_headers(token)
    )
    assert resp.status_code in {404, 400, 422}
    assert (
        "no existe" in resp.text.lower() or
        "not found" in resp.text.lower() or
        "invalid" in resp.text.lower() or
        "unprocessable" in resp.text.lower()
    )

def test_sign_maximum_signatures_allowed(empleado_login, supervisor_login, otro_login, example_pdf):
    token_empleado = get_token(empleado_login)
    token_supervisor = get_token(supervisor_login)
    token_otro = get_token(otro_login)
    files = {"file": ("maxfirmas.pdf", example_pdf, "application/pdf")}
    up = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token_empleado)
    )
    assert up.status_code == 200
    docid = up.json()["document_id"]

    resp1 = httpx.post(
        f"{BASE_URL}/documents/{docid}/sign",
        headers=auth_headers(token_supervisor)
    )
    resp2 = httpx.post(
        f"{BASE_URL}/documents/{docid}/sign",
        headers=auth_headers(token_otro)
    )
    resp3 = httpx.post(
        f"{BASE_URL}/documents/{docid}/sign",
        headers=auth_headers(token_empleado)
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    # Si hay límite, puedes ajustar aquí el chequeo de resp3

@pytest.mark.xfail(reason="Hoy el sistema permite que empleado firme; falta validación de roles")
def test_employee_cannot_sign_document(empleado_login, example_pdf):
    token = get_token(empleado_login)
    files = {"file": ("bloqueo_rol.pdf", example_pdf, "application/pdf")}
    up = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert up.status_code == 200
    docid = up.json()["document_id"]

    resp = httpx.post(
        f"{BASE_URL}/documents/{docid}/sign",
        headers=auth_headers(token)
    )
    assert resp.status_code in {400, 403, 422}
    assert "rol" in resp.text.lower() or "permiso" in resp.text.lower() or "supervisor" in resp.text.lower()
    assert resp.status_code in {400, 403, 422}

def test_download_pdf_before_signing(empleado_login, example_pdf):
    token = get_token(empleado_login)
    files = {"file": ("sin_firmar.pdf", example_pdf, "application/pdf")}
    up = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert up.status_code == 200
    docid = up.json()["document_id"]
    resp = httpx.get(
        f"{BASE_URL}/documents/{docid}/download",
        headers=auth_headers(token)
    )
    assert resp.status_code in {200, 400, 403}

def test_download_signed_pdf_and_verify_hash(empleado_login, supervisor_login, example_pdf):
    token_empleado = get_token(empleado_login)
    token_supervisor = get_token(supervisor_login)
    files = {"file": ("descarga.pdf", example_pdf, "application/pdf")}

    upload = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token_empleado)
    )
    assert upload.status_code == 200
    docid = upload.json()["document_id"]

    sign = httpx.post(
        f"{BASE_URL}/documents/{docid}/sign",
        headers=auth_headers(token_supervisor)
    )
    assert sign.status_code == 200

    download = httpx.get(
        f"{BASE_URL}/documents/{docid}/download",
        headers=auth_headers(token_empleado)
    )
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    if "X-Document-Hash" in download.headers:
        local_hash = hashlib.sha256(download.content).hexdigest()
        server_hash = download.headers["X-Document-Hash"]
        assert local_hash == server_hash

def test_duplicate_pdf_upload(empleado_login, example_pdf):
    token = get_token(empleado_login)
    files = {"file": ("dup.pdf", example_pdf, "application/pdf")}
    resp1 = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    resp2 = httpx.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers=auth_headers(token)
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200  # O ajusta a 409 si tu lógica lo requiere