FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# When built in a managed proxy environment, pass its CA as BuildKit secret
# proxy_ca. On ordinary hosts the platform trust store is used as usual.
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu; \
    else pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu; fi
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi
RUN --mount=type=secret,id=proxy_ca,required=false \
    git init /opt/copisteria && \
    if [ -s /run/secrets/proxy_ca ]; then GIT_SSL_CAINFO=/run/secrets/proxy_ca git -C /opt/copisteria fetch --depth 1 https://github.com/kobimusic/copisteria.git c685f280914d91a694494588d9f6a376d7917eba; \
    else git -C /opt/copisteria fetch --depth 1 https://github.com/kobimusic/copisteria.git c685f280914d91a694494588d9f6a376d7917eba; fi && \
    git -C /opt/copisteria checkout FETCH_HEAD && \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir /opt/copisteria; \
    else pip install --no-cache-dir /opt/copisteria; fi
COPY src ./src
RUN mkdir -p /cache/copisteria-models /input /output && ln -s /cache/copisteria-models /opt/copisteria/models
ENTRYPOINT ["python", "/app/src/main.py"]
CMD ["--help"]
