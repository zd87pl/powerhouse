# Powerhouse Railway Dockerfile — multi-stack generic
# Detects stack by presence of files and builds accordingly

FROM node:20-slim AS base
WORKDIR /app

# ─── Next.js / React ──────────────────────────────────────────────
FROM base AS nextjs
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
ENV PORT=3000
EXPOSE 3000
CMD ["npm", "start"]

# ─── FastAPI / Python ──────────────────────────────────────────────
FROM python:3.11-slim AS fastapi
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

# ─── Full-stack (Next.js frontend + FastAPI backend as one service) ───────
FROM base AS fullstack
COPY package*.json requirements.txt ./
RUN npm ci && pip install --no-cache-dir -r requirements.txt
COPY . .
RUN npm run build
ENV PORT=3000
EXPOSE 3000
CMD ["npm", "start"]
