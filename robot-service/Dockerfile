FROM python:3.11-slim

WORKDIR /app

COPY robot-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared common package and service code
COPY common/ ./common/
COPY robot-service/ .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8002}"]