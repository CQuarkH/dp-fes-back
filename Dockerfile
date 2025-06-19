# Dockerfile
FROM python:3.11-slim

# Variables de entorno para que Python no genere archivos .pyc ni bufferice salidas
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear carpeta de uploads
RUN mkdir -p /app/uploads

# Puerto que expone Uvicorn
EXPOSE 8000

# Comando por defecto
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
