from fastapi import FastAPI
import time
import uvicorn
from create_tables import crear_tablas
from modules.documents.job import start_deletion_job
from modules.documents.models import User, UserRole
from modules.documents.services import DocumentService
from database import SessionLocal
from modules.notifications.controllers.notification_controller import router as notification_router

app = FastAPI(
    title="Mi Aplicación",
    description="API para gestión de documentos y notificaciones",
    version="1.0.0"
)

# Incluir el router de notificaciones
app.include_router(notification_router, prefix="/notifications", tags=["notifications"])


@app.on_event("startup")
def startup_event():
    print("🚀 Iniciando aplicación...")
    # Crear tablas
    crear_tablas()
    print("✅ Tablas creadas exitosamente")
    # Iniciar job de auto-eliminación
    start_deletion_job()
    print("✅ Job de auto-eliminación iniciado")
    # Poblar datos de prueba
    crear_datos_prueba()


def crear_datos_prueba():
    """Crea usuarios y documentos de prueba"""
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

        documento = DocumentService.sign_document(
            session,
            empleado.id,
            "Contrato_Prueba.pdf",
            "/uploads/contrato_prueba.pdf"
        )

        print("✅ Datos de prueba creados:")
        print(f"   - Usuarios: {empleado.name}, {supervisor.name}, {admin.name}")
        print(f"   - Documento: {documento.name} (Estado: {documento.status.value})")


@app.on_event("shutdown")
def shutdown_event():
    print("🛑 Aplicación detenida")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
