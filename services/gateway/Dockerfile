FROM python:3.12-slim

WORKDIR /app

# Install gateway deps.
COPY services/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the packages the gateway imports at runtime.
COPY services ./services
COPY skills ./skills

EXPOSE 8000
CMD ["uvicorn", "services.gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
