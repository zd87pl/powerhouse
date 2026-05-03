FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Run the API
EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "services.instill_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
