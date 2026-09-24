FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://packagefeedproxy.microsoft.io/pypi/simple/
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN python -m venv .venv && .venv/bin/pip install --no-cache-dir .
RUN useradd -r app
USER app
EXPOSE 8787
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787", "--timeout-graceful-shutdown", "5"]
