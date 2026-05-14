FROM python:3.11-slim

WORKDIR /app

COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared common package and service code
COPY common/ ./common/
COPY auth-service/ .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8001}"]