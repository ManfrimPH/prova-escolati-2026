FROM python:3.12-slim
WORKDIR /app
RUN mkdir -p /data
VOLUME ["/data"]
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
