FROM python:3.12-slim

RUN adduser --disabled-password --no-create-home appuser

WORKDIR /app
COPY broker-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY broker-worker/app/ ./app/
COPY broker-worker/migrations/ ./migrations/
COPY broker-worker/alembic.ini .

USER appuser
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]