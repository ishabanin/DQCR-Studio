FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system dqcr && useradd --system --gid dqcr --create-home dqcr

ARG FW_INSTALL_MODE=local
ARG FW_PACKAGE_SPEC=

COPY backend/pyproject.toml ./pyproject.toml
COPY FTRepCBR.Workflow.FW /opt/fw-src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN if [ "$FW_INSTALL_MODE" = "package" ] && [ -n "$FW_PACKAGE_SPEC" ]; then \
      pip install --no-cache-dir "$FW_PACKAGE_SPEC"; \
    else \
      pip install --no-cache-dir /opt/fw-src; \
    fi
RUN pip install --no-cache-dir .

COPY backend/app ./app
RUN chown -R dqcr:dqcr /app

USER dqcr

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
