# Imagen del servicio de IA (detector + comparador), solo CPU.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    TORCH_HOME=/app/.cache/torch

WORKDIR /app

# OpenCV (dependencia de Ultralytics) necesita estas bibliotecas del sistema.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# PyTorch de CPU: la rueda por defecto en Linux trae CUDA y pesa varios GB.
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision

COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# Descarga la red del comparador al construir, para no depender de internet al arrancar.
RUN python -c "from torchvision import models; models.resnet18(weights=models.ResNet18_Weights.DEFAULT)"

# Los pesos del detector NO van en la imagen: se montan en /app/pesos (docker-compose.yml).
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
