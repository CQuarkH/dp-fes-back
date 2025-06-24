import pytest
import httpx
import time
from datetime import datetime, timedelta
import hashlib
import os

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def empleado_id():
    # Ajusta si tu user_id es distinto
    return 1

@pytest.fixture(scope="session")
def supervisor_id():
    return 2

@pytest.fixture(scope="session")
def example_pdf():
    # Un PDF mínimo válido
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF"
    )


def test_PI_INT_01_subida_y_revision(empleado_id, example_pdf):
    # Simula subida por Empleado, debe quedar EN REVISION
    files = {"file": ("enRevision.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code==200
        docid = resp.json()["document_id"]

        # Consulta detalles, suponiendo existe endpoint
        resp2 = c.get(f"{BASE_URL}/documents/{docid}")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "IN_REVIEW"  # Estado textual que guarda tu modelo

def test_PI_INT_02_firma_y_cambio_de_estado(empleado_id, supervisor_id, example_pdf):
    # Flujos: empleado sube -> supervisor firma -> estado cambia a FIRMADO
    files = {"file": ("firmar.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        # 1) Empleado sube
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        assert resp.status_code==200
        docid = resp.json()["document_id"]

        # 2) Supervisor firma
        resp2 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})
        assert resp2.status_code == 200
        assert "Firma añadida" in resp2.json()["message"] or resp2.json().get("order") == 1

        # 3) Consulta status final (asume firmado tras la firma)
        resp3 = c.get(f"{BASE_URL}/documents/{docid}")
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "SIGNED"

def test_PI_INT_03_historial_firma_y_revision(empleado_id, supervisor_id, example_pdf):
    # Sube, firma y consulta historial 
    files = {"file": ("historial.pdf", example_pdf, "application/pdf")}
    with httpx.Client() as c:
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        docid = resp.json()["document_id"]

        c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})

        # Consulta historial (asume endpoint existe, debes adaptarlo)
        response_hist = c.get(f"{BASE_URL}/documents/{docid}/history")
        assert response_hist.status_code == 200
        eventos = response_hist.json()
        tipos = [e["tipo"].lower() for e in eventos]
        assert "subida" in tipos or "upload" in tipos
        assert "firma" in tipos or "signed" in tipos

def test_PI_INT_04_eliminado_por_cron(empleado_id, supervisor_id, example_pdf):
    # Crea y rechaza el documento. Fuerza fecha de rechazo a 31 días antes si puedes.
    with httpx.Client() as c:
        files = {"file": ("oldrechazado.pdf", example_pdf, "application/pdf")}
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        docid = resp.json()["document_id"]
        c.post(f"{BASE_URL}/documents/{docid}/reject", params={"user_id": supervisor_id})
        # --- Aquí deberías modificar la fecha de rechazo en la BD directamente, o testear este caso solo si simulas el tiempo ---
        # Simula CRON ejecutando job de eliminación
        c.post(f"{BASE_URL}/documents/cron/delete_old")
        # Intenta consultar
        r2 = c.get(f"{BASE_URL}/documents/{docid}")
        assert r2.status_code == 404 or "no encontrado" in r2.text.lower()

def test_PI_INT_05_flujo_completo(empleado_id, supervisor_id, example_pdf):
    # Sube, firma, descarga y valida hash PDF
    with httpx.Client() as c:
        files = {"file": ("descargar.pdf", example_pdf, "application/pdf")}
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        docid = resp.json()["document_id"]

        c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id": supervisor_id})

        # Descarga el documento firmado
        r3 = c.get(f"{BASE_URL}/documents/{docid}/download")
        assert r3.status_code == 200
        data = r3.content
        assert data[:6] == b"%PDF-1"

        # Hash local
        hash_local = hashlib.sha256(data).hexdigest()

        # Obtén la firma para comparar hash (asume endpoint o busca en la BD)
        r4 = c.get(f"{BASE_URL}/documents/{docid}/history")
        signatures = [e for e in r4.json() if e.get("tipo","").lower() == "firma"]
        assert signatures
        hash_bd = signatures[-1].get("hash", signatures[-1].get("sha256_hash"))
        assert hash_local == hash_bd

def test_UAT_04_limite_de_firmas(empleado_id, supervisor_id, example_pdf):
    # Limite de 5 firmas, la sexta debe fallar
    with httpx.Client() as c:
        files = {"file": ("5firmas.pdf", example_pdf, "application/pdf")}
        resp = c.post(f"{BASE_URL}/documents/upload", params={"user_id": empleado_id}, files=files)
        docid = resp.json()["document_id"]

        # Supon que tienes 5 user_ids únicos (ajusta si necesitas más)
        signers = [supervisor_id, empleado_id, 3, 4, 5, 6]
        for i, uid in enumerate(signers):
            r2 = c.post(f"{BASE_URL}/documents/{docid}/sign", params={"user_id":uid})
            if i < 5:
                assert r2.status_code == 200
            else:
                assert r2.status_code in (400, 422)
                assert "Máximo de 5 firmas" in r2.text or "firmas alcanzad" in r2.text