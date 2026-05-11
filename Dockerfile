FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aeo/ ./aeo/

EXPOSE 8000

CMD ["uvicorn", "aeo.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
