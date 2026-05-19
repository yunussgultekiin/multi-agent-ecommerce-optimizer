FROM python:3.12-slim

ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV NUMBA_DISABLE_JIT=1
ENV U2NET_HOME=/tmp/.u2net

RUN adduser --disabled-password --no-create-home appuser

WORKDIR /app
COPY agent-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir "rembg[cpu]" onnxruntime pillow
RUN mkdir -p /tmp/numba_cache /tmp/.u2net && chmod -R 777 /tmp/numba_cache /tmp/.u2net

RUN python -c "from rembg import new_session; new_session('u2net')" \
    && echo "u2net model baked successfully" \
    && chmod -R 777 /tmp/.u2net

COPY shared/ ./shared/
COPY agent-worker/app/ ./app/
COPY agent-worker/data/ ./data/

RUN mkdir -p /home/appuser/.cache/chroma /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /home/appuser

ENV HOME=/home/appuser
ENV XDG_CACHE_HOME=/home/appuser/.cache
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface
ENV ANONYMIZED_TELEMETRY=False
ENV CHROMA_TELEMETRY=False

USER appuser

RUN python3 -c "\
import chromadb; \
client = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False)); \
col = client.get_or_create_collection('warmup'); \
col.add(ids=['w'], documents=['warmup']); \
client.delete_collection('warmup'); \
print('Chroma ONNX model cached')" \
    || echo "Chroma ONNX model cache skipped — will download at runtime"

EXPOSE 8080
CMD ["python", "-m", "app.main"]