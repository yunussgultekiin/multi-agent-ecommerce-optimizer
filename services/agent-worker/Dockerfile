FROM python:3.12-slim

ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV NUMBA_DISABLE_JIT=1

RUN adduser --disabled-password --no-create-home appuser

WORKDIR /app
COPY agent-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir "rembg[cpu]" onnxruntime pillow
RUN mkdir -p /tmp/numba_cache && chmod -R 777 /tmp/numba_cache

RUN python -c "from rembg import new_session; new_session('u2net')" \
    && echo "u2net model baked successfully"

COPY shared/ ./shared/
COPY agent-worker/app/ ./app/

USER appuser
EXPOSE 8080
CMD ["python", "-m", "app.main"]