FROM python:3.12-slim
WORKDIR /app
COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt
COPY . .
ENV PSI_LOG_DESTINATION=stdout PSI_LOG_FORMAT=json PSI_ENVIRONMENT=local
CMD ["python", "scripts/serve_skills.py"]
