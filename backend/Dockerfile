FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 非rootユーザーで実行（コンテナ侵害時の被害を限定）
RUN useradd -r -s /bin/false appuser \
  && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "core.api:app", "--host", "0.0.0.0", "--port", "8000"]
