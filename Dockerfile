FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        fastapi==0.115.* \
        "uvicorn[standard]==0.30.*" \
        jinja2==3.1.* \
        httpx==0.27.* \
        psutil==6.* \
        pydantic==2.7.* \
        itsdangerous==2.2.* \
        bcrypt==4.2.* \
        python-multipart==0.0.9

COPY monitorr_ii ./monitorr_ii

RUN groupadd --gid 1000 monitorr 2>/dev/null || true \
    && useradd --uid 1000 --gid 1000 --system --no-create-home monitorr 2>/dev/null || true \
    && mkdir -p /config/icons \
    && chown -R 1000:1000 /config /app

USER 1000:1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "monitorr_ii.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
