# create_tables.py
from database import engine, Base
# Importa todos los modelos para que se registren con Base
from modules.documents.models.user import User
from modules.documents.models.document import Document

def crear_tablas():
    """Crea todas las tablas en la base de datos"""
    print("🔍 Tablas a crear:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente!")

if __name__ == "__main__":
    crear_tablas()
