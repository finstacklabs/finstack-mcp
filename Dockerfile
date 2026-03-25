FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/
COPY README.md .
COPY LICENSE .

RUN pip install --no-cache-dir -e ".[hosted]"

# Environment
ENV FINSTACK_HOST=0.0.0.0
ENV FINSTACK_PORT=8000
ENV FINSTACK_TRANSPORT=streamable-http
ENV FINSTACK_LOG_LEVEL=INFO

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "finstack.server", "--transport", "streamable-http"]
