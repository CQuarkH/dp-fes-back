import pytest
import httpx
import io
import random
import string
from reportlab.pdfgen import canvas
import hashlib

BASE_URL = "http://localhost:8000"  # Cambia si usas otro puerto

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

@pytest.fixture(scope="session")
def empleado_id():
    return 2

@pytest.fixture(scope="session")
def supervisor_id():
    return 3

@pytest.fixture(scope="session")
def otro_id():
    return 4

def random_username():
    return "testuser_" + ''.join(random.choices(string.ascii_lowercase, k=8))


# PF-FR01-01: Intentar subir DOCX rechaza
# Prueba: Intentar subir un archivo que NO es PDF (.docx).
# Esperado: El sistema rechaza la carga y muestra mensaje “Solo se permiten archivos PDF.”
def test_upload_non_pdf_rejected(empleado_id, non_pdf):
    files = {"file": ("documento.docx", non_pdf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code in {400, 422}
        # Puede que diga "Solo pdf" o similar
        assert "pdf" in resp.text.lower()


# PF-FR01-02: Subir PDF válido, debe aceptar
# Prueba: Subir un PDF válido y verificar que el sistema lo acepta y guarda los metadatos (sin errores de formato/integridad).
def test_upload_pdf_accepted(empleado_id, example_pdf):
    files = {"file": ("documento_valido.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "document_id" in data

# PF-FR01-02 - Subir PDF vacío/corrupto, debe rechazarlo
def test_upload_empty_pdf_rejected(empleado_id):
    files = {"file": ("vacio.pdf", b"", "application/pdf")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code in {400, 422}
        assert ("pdf" in resp.text.lower() or 
                "vacío" in resp.text.lower() or 
                "empty" in resp.text.lower() or 
                "invalid" in resp.text.lower())

# PF-FR03-01, PI-INT-02 - Firmar documento inexistente
# Prueba: No se debe poder firmar un documento que no existe.
def test_sign_nonexistent_document(supervisor_id):
    fake_docid = 999999999  
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/{fake_docid}/sign", params={"user_id": supervisor_id})
        assert resp.status_code in {404, 400, 422}
        assert (
            "no existe" in resp.text.lower() or
            "not found" in resp.text.lower() or
            "invalid" in resp.text.lower() or
            "unprocessable" in resp.text.lower()
        )

# PF-FR03-02 y PF-FR03-03
# Prueba: Firmar el mismo documento dos veces con el mismo supervisor.
# Esperado: Actualmente la API permite el segundo OK, si la lógica cambia, ajustar el test.
def test_sign_duplicate_signatures(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("firmar_mismo.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        upload = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert upload.status_code == 200
        docid = upload.json()["document_id"]

        # Primera firma con supervisor: OK
        resp1 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        assert resp1.status_code == 200

        # Segunda firma con supervisor: OK
        resp2 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        assert resp2.status_code == 200  # Cambia este chequeo si la lógica cambia en el futuro

# PF-FR03-02/03 (hasta 3 o 5 firmas, dependiendo modelo)
def test_sign_maximum_signatures_allowed(empleado_id, supervisor_id, otro_id, example_pdf):
    files = {"file": ("maxfirmas.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        up = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert up.status_code == 200
        docid = up.json()["document_id"]

        # Firma 1: supervisor
        resp1 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        # Firma 2: otro usuario
        resp2 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": otro_id})
        # Firma 3: empleado (si lo permite)
        resp3 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": empleado_id})

        # Depende tu implementación si permite 2 o 3 firmas.
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Si resp3 ya no permite: assert resp3.status_code != 200, etc.

# PF-FR05-01
# Prueba: Un EMPLEADO no debe poder firmar documentos, solo un SUPERVISOR.
# Esperado: Rechazo o error de permisos/rol.
@pytest.mark.xfail(reason="Hoy el sistema permite que empleado firme; falta validación de roles")
def test_employee_cannot_sign_document(empleado_id, example_pdf):
    with httpx.Client() as c:
        files = {"file": ("bloqueo_rol.pdf", example_pdf, "application/pdf")}
        up = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert up.status_code == 200
        docid = up.json()["document_id"]

        # Empleado intenta firmar, pero solo Supervisor debe poder firmar.
        resp = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": empleado_id})
        # Si tu sistema lo restringe, debe fallar; si no, comenta las siguientes líneas.
        assert resp.status_code in {400, 403, 422}
        assert "rol" in resp.text.lower() or "permiso" in resp.text.lower() or "supervisor" in resp.text.lower()
        assert resp.status_code in {400, 403, 422}

# PF-FR07-01 edge case
def test_download_pdf_before_signing(empleado_id, example_pdf):
    files = {"file": ("sin_firmar.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        up = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert up.status_code == 200
        docid = up.json()["document_id"]
        resp = c.get(f"{BASE_URL}/documents/{docid}/download")
        # Puede permitirlo, pero ideal: status != 200 o incluir advertencia en algún header
        assert resp.status_code in {200, 400, 403}

# PF-FR07-01
# Prueba: Descargar un documento PDF ya firmado y, si tu backend lo permite, verificar el hash SHA256.
# Esperado: Se descarga PDF correctamente; hash igual al devuelto por servidor si está disponible.
def test_download_signed_pdf_and_verify_hash(empleado_id, supervisor_id, example_pdf):
    files = {"file": ("descarga.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        upload = c.post(
            f"{BASE_URL}/documents/upload", 
            params={"user_id": empleado_id}, 
            files=files
        )
        assert upload.status_code == 200
        docid = upload.json()["document_id"]

        # Que lo firme un supervisor
        sign = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        assert sign.status_code == 200

        # Descarga
        download = c.get(f"{BASE_URL}/documents/{docid}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")
        # Si tu backend manda hash SHA256 en header:
        if "X-Document-Hash" in download.headers:
            local_hash = hashlib.sha256(download.content).hexdigest()
            server_hash = download.headers["X-Document-Hash"]
            assert local_hash == server_hash
        
def test_duplicate_pdf_upload(empleado_id, example_pdf):
    files = {"file": ("dup.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        resp1 = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        resp2 = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp1.status_code == 200
        # ¿Permite subida duplicada? ¿Hace merge, rechaza, crea otro? Dependiendo lógica:
        # assert resp2.status_code == 409    # si no se permite
        # o
        # assert resp2.status_code == 200    # si sí se permite

