# src/main.py
from modules.documents.job import start_deletion_job
from modules.documents.services import DocumentService
from modules.documents.models import User, UserRole, DocumentStatus
from create_tables import crear_tablas
from database import SessionLocal
import time

def main():
    print("🚀 Iniciando aplicación...")

    crear_tablas()
    print("✅ Tablas creadas exitosamente")

    # Iniciar el job de auto-eliminación
    start_deletion_job()
    print("✅ Job de auto-eliminación iniciado")

    # Crear algunos datos de prueba
    crear_datos_prueba()

    # Mantener la aplicación corriendo
    try:
        print("📊 Aplicación corriendo... (Ctrl+C para detener)")
        while True:
            time.sleep(60)  # Esperar 1 minuto
            print("⏰ Aplicación activa...")
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo aplicación...")

def crear_datos_prueba():
    """Crea usuarios y documentos de prueba"""
    with SessionLocal() as session:
        # Verificar si ya existen usuarios
        if session.query(User).count() > 0:
            print("✅ Datos de prueba ya existen")
            return

        # Crear usuarios
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

        # Crear documento de prueba
        documento = DocumentService.sign_document(
            session,
            empleado.id,
            "Contrato_Prueba.pdf",
            "/uploads/contrato_prueba.pdf"
        )

        print(f"✅ Datos de prueba creados:")
        print(f"   - Usuarios: {empleado.nombre}, {supervisor.nombre}, {admin.nombre}")
        print(f"   - Documento: {documento.nombre} (Estado: {documento.estado.value})")

if __name__ == "__main__":
    main()
