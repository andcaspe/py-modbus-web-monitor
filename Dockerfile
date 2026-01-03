FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN rm -rf /app/src/modbus_web_monitor/web
COPY --from=frontend-builder /app/frontend/dist /app/src/modbus_web_monitor/web

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["modbus-web-monitor", "--host", "0.0.0.0", "--port", "8000"]
