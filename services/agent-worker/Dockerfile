FROM python:3.12-slim

RUN adduser --disabled-password --no-create-home appuser

WORKDIR /app
COPY agent-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# shared must be on the Python path so `from shared.oidc_client import ...` resolves
COPY shared/ ./shared/
COPY agent-worker/app/ ./app/

USER appuser
EXPOSE 8080
CMD ["python", "-m", "app.main"]
