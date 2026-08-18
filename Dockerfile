FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY rag/ rag/
COPY knowledge/ knowledge/
COPY index.html styles.css app-web.js ./

EXPOSE 8000

CMD ["python", "server.py"]
