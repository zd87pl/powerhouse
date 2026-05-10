FROM python:3.11-slim

WORKDIR /app

# Install system deps + Node.js 20.x
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Vercel CLI globally
RUN npm install -g vercel@latest

# Copy app code
COPY . .

# Run the API
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "services.instill_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
