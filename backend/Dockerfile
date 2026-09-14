FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin ledger \
    && mkdir -p /data \
    && chown ledger:ledger /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY set_password.py .

ENV PYTHONUNBUFFERED=1 \
    LEDGER_DB_PATH=/data/app.db

USER ledger
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
