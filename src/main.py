import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from create_tables import crear_tablas
from database import SessionLocal

from modules.documents.job import start_deletion_job
from modules.documents.models import User, UserRole
from modules.documents.services import DocumentService
from modules.auth.services.auth_service import AuthService
from modules.notifications.controllers.notification_controller import router as notification_router
from modules.documents.controllers.document_controller     import router as document_router
from modules.documents.controllers.signature_controller import router as signature_router
from modules.auth.controllers.auth_controller import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    print("🚀 Iniciando aplicación...")
    crear_tablas()
    print("✅ Tablas creadas exitosamente")
    start_deletion_job()
    print("✅ Job de auto-eliminación iniciado")
    _crear_datos_prueba()
    yield
    # --- Shutdown logic ---
    print("🛑 Aplicación detenida")

def _crear_datos_prueba():
    """Crea usuarios con contraseñas."""
    with SessionLocal() as session:
        if session.query(User).count() > 0:
            print("✅ Datos de prueba ya existen")
            return

        gestor = User(
            name="Gestor Institucional",
            email="gestor@empresa.com",
            password_hash=AuthService.get_password_hash("gestor123"),
            role=UserRole.INSTITUTIONAL_MANAGER,
            is_active=True
        )

        empleado = User(
            name="Juan Pérez",
            email="juan@empresa.com",
            password_hash=AuthService.get_password_hash("juan123"),
            role=UserRole.EMPLOYEE,
            is_active=True
        )
        supervisor = User(
            name="Ana García",
            email="ana@empresa.com",
            password_hash=AuthService.get_password_hash("ana123"),
            role=UserRole.SUPERVISOR,
            is_active=True
        )
        admin = User(
            name="Carlos López",
            email="carlos@empresa.com",
            password_hash=AuthService.get_password_hash("carlos123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        session.add_all([gestor, empleado, supervisor, admin])
        session.commit()

        print("✅ Datos de prueba creados:")
        print(f"   - Gestor: {gestor.email} / gestor123")
        print(f"   - Empleado: {empleado.email} / juan123")
        print(f"   - Supervisor: {supervisor.email} / ana123")
        print(f"   - Admin: {admin.email} / carlos123")

app = FastAPI(
    title="Sistema de Gestión de Documentos",
    description="API para gestión de documentos con firma digital",
    version="1.0.0",
    lifespan=lifespan
)

# Routers
app.include_router(auth_router)
app.include_router(notification_router, prefix="/notifications", tags=["notifications"])
app.include_router(document_router,     prefix="/documents",    tags=["documents"])
app.include_router(signature_router, prefix="/documents", tags=["documents"])

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
