# Deployment Guide

This guide covers production deployment of the Urology Data Platform.

## Architecture Overview

The platform consists of:
- **FastAPI Backend** - API server handling authentication, data processing, and AI integrations
- **PostgreSQL** - Primary database for patient data and metadata
- **Milvus** - Vector database for semantic search
- **MinIO** - Object storage for uploaded files (lab results, documents)
- **Streamlit UI** - Web interface for clinicians

## Prerequisites

- Docker and Docker Compose
- Domain with SSL certificate (for production HTTPS)
- API keys for AI services (Anthropic Claude, OpenAI)

## Environment Variables

Create a `.env` file with the following configuration:

```bash
# Database
DATABASE_URL=postgresql://urology:SECURE_PASSWORD@postgres:5432/urology_db

# Security (MUST change in production)
SECRET_KEY=generate-a-secure-64-char-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TOKEN_ISSUER=urology-data-platform
TOKEN_AUDIENCE=urology-data-platform-api

# AI Services
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
VOYAGE_API_KEY=pa-xxx  # Optional, for medical embeddings

# Milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=SECURE_ACCESS_KEY
MINIO_SECRET_KEY=SECURE_SECRET_KEY
MINIO_BUCKET=urology-files
MINIO_SECURE=false  # Set to true if using HTTPS
```

### Generating a Secure Secret Key

```bash
openssl rand -hex 32
```

## Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: urology-backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MILVUS_HOST=milvus
      - MILVUS_PORT=19530
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      milvus:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: urology-postgres
    environment:
      POSTGRES_USER: urology
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: urology_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U urology -d urology_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  milvus-etcd:
    image: quay.io/coreos/etcd:v3.5.5
    container_name: urology-milvus-etcd
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    restart: unless-stopped

  milvus-minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    container_name: urology-milvus-minio
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - milvus_minio_data:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  milvus:
    image: milvusdb/milvus:v2.4.0
    container_name: urology-milvus
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: milvus-etcd:2379
      MINIO_ADDRESS: milvus-minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"
    depends_on:
      - milvus-etcd
      - milvus-minio
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: urology-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    command: server /data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

volumes:
  postgres_data:
  etcd_data:
  milvus_minio_data:
  milvus_data:
  minio_data:
```

## Backend Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash

# Copy dependency files
COPY pyproject.toml pixi.toml pixi.lock ./

# Install Python dependencies
RUN /root/.pixi/bin/pixi install --frozen

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["/root/.pixi/bin/pixi", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Deployment Steps

### 1. Prepare the Server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

### 2. Clone and Configure

```bash
git clone <repository-url> /opt/urology-platform
cd /opt/urology-platform

# Create and configure .env file
cp .env.example .env
nano .env  # Edit with production values
```

### 3. Start Services

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Run database migrations
docker compose -f docker-compose.prod.yml exec backend \
    pixi run alembic upgrade head

# Check logs
docker compose -f docker-compose.prod.yml logs -f backend
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy"}
```

## HTTPS with Nginx Reverse Proxy

For production, use Nginx with Let's Encrypt SSL:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Database Backups

### Automated Daily Backups

Create `/opt/backup-urology.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/opt/backups/urology
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker exec urology-postgres pg_dump -U urology urology_db | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
0 2 * * * /opt/backup-urology.sh >> /var/log/urology-backup.log 2>&1
```

## Monitoring

### Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic health check |
| `GET /api/search/stats` | Vector search status |

### Log Locations

- Backend logs: `docker compose logs backend`
- PostgreSQL logs: `docker compose logs postgres`
- Milvus logs: `docker compose logs milvus`

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check connectivity
docker compose exec backend python -c "from src.core.database import engine; print(engine.connect())"
```

### Milvus Connection Issues

```bash
# Check Milvus health
curl http://localhost:9091/healthz

# Check etcd is running
docker compose logs milvus-etcd
```

### MinIO Issues

```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# Access MinIO console (development only)
# Open http://localhost:9001 in browser
```

## Scaling Considerations

For high availability:

1. **Database**: Use managed PostgreSQL (AWS RDS, GCP Cloud SQL)
2. **Vector DB**: Use Milvus cluster mode or managed Zilliz Cloud
3. **Object Storage**: Use S3 or compatible cloud storage
4. **Load Balancing**: Deploy multiple backend instances behind a load balancer
5. **Caching**: Add Redis for session caching if needed

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure SECRET_KEY (64+ characters)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (only expose ports 80, 443)
- [ ] Set up database backups
- [ ] Enable logging and monitoring
- [ ] Review API access controls
- [ ] Disable MinIO console in production
