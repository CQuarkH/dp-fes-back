import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from create_tables import crear_tablas
from database import SessionLocal

from modules.documents.job import start_deletion_job
from modules.documents.models import User, UserRole
from modules.documents.services import DocumentService
from modules.notifications.controllers.notification_controller import router as notification_router
from modules.documents.controllers.document_controller     import router as document_router

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
    """Crea usuarios."""
    with SessionLocal() as session:
        if session.query(User).count() > 0:
            print("✅ Datos de prueba ya existen")
            return

        empleado = User(
            name="Juan Pérez",
            email="juan@empresa.com",
            role=UserRole.EMPLOYEE
        )
        supervisor = User(
            name="Ana García",
            email="ana@empresa.com",
            role=UserRole.SUPERVISOR
        )
        admin = User(
            name="Carlos López",
            email="carlos@empresa.com",
            role=UserRole.ADMIN
        )
        session.add_all([empleado, supervisor, admin])
        session.commit()

        print("✅ Datos de prueba creados:")
        print(f"   - Usuarios: {empleado.name}, {supervisor.name}, {admin.name}")

app = FastAPI(
    title="Mi Aplicación",
    description="API para gestión de documentos y notificaciones",
    version="1.0.0",
    lifespan=lifespan
)

# Routers
app.include_router(notification_router, prefix="/notifications", tags=["notifications"])
app.include_router(document_router,     prefix="/documents",    tags=["documents"])

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


