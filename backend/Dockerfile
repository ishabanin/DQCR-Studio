FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system dqcr && useradd --system --gid dqcr --create-home dqcr

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
RUN chown -R dqcr:dqcr /app

USER dqcr

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
