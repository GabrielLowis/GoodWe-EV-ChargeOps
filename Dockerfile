FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY condocharge_ai condocharge_ai
COPY data data
COPY alembic.ini .
COPY tests tests
COPY scripts scripts
COPY pytest.ini pyproject.toml ./
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.bootstrap && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
