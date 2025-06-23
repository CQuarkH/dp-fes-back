# Dockerfile
FROM python:3.11-slim

# ▸ Evita archivos .pyc y salidas bufferizadas
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ▸ Carpeta de trabajo
WORKDIR /app

# ▸ Añadimos /app y /app/src al PYTHONPATH  ⇐  🆕
ENV PYTHONPATH=/app:/app/src

# ▸ Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ▸ Código fuente
COPY . .

# ▸ Carpeta para uploads
RUN mkdir -p /app/uploads

# ▸ Puerto de la API
EXPOSE 8000

# ▸ Comando de arranque
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
