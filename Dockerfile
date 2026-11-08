FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface PYTHONPATH=/opt/smt
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# Keep PyTorch CPU-only to avoid downloading CUDA libraries in the image.
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu; \
    else pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu; fi
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi
RUN --mount=type=secret,id=proxy_ca,required=false \
    git init /opt/smt && \
    if [ -s /run/secrets/proxy_ca ]; then GIT_SSL_CAINFO=/run/secrets/proxy_ca git -C /opt/smt fetch --depth 1 https://github.com/antoniorv6/SMT.git 20d8240c47b4a1851e9a5aa5a0ca3d0ddbc16da8; \
    else git -C /opt/smt fetch --depth 1 https://github.com/antoniorv6/SMT.git 20d8240c47b4a1851e9a5aa5a0ca3d0ddbc16da8; fi && \
    git -C /opt/smt checkout FETCH_HEAD
COPY src ./src
RUN mkdir -p /cache/huggingface /input /output
ENTRYPOINT ["python", "/app/src/main.py"]
CMD ["--help"]
