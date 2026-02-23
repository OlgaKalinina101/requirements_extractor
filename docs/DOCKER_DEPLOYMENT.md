# 🚀 Production Deployment Guide

Complete guide for deploying PDF Requirements Extractor as a containerized service.

## Overview

The system consists of 3 Docker containers:
- **PostgreSQL** - Database (port 5433 → 5432)
- **API (Backend)** - FastAPI server (port 8000)
- **Frontend** - Vue.js + Nginx (port 8080)

---

## Prerequisites

### Required Software

```bash
# Docker
docker --version  # >= 20.10

# Docker Compose
docker-compose --version  # >= 2.0
```

### System Requirements

- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk:** 10 GB free space
- **CPU:** 2 cores minimum

---

## Quick Start (Single Command)

```bash
# 1. Clone repository
git clone <repository_url>
cd test2

# 2. Create .env file
cp .env.example .env
# Edit .env and add API keys

# 3. Start all services
docker-compose up -d --build

# 4. Wait for services to start (30-60 seconds)
docker-compose logs -f

# 5. Open in browser
http://localhost:8080
```

---

## Detailed Setup

### Step 1: Prepare Environment

```bash
# Create .env file
cat > .env << EOF
# AI API Keys (at least one required)
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Database (default values, change for production)
POSTGRES_USER=requirements_user
POSTGRES_PASSWORD=requirements_pass_CHANGE_ME
POSTGRES_DB=requirements_db

# Database URL (for API container)
DATABASE_URL=postgresql://requirements_user:requirements_pass_CHANGE_ME@postgres:5432/requirements_db
EOF

# Edit with your actual API keys
nano .env
```

---

### Step 2: Build Images

```bash
# Build all images
docker-compose build

# Or build separately
docker-compose build postgres  # Uses official postgres:16-alpine
docker-compose build api       # Builds from Dockerfile
docker-compose build frontend  # Builds from Dockerfile.frontend
```

**What happens:**
- **PostgreSQL:** Downloads official image (~80 MB)
- **API:** 
  - Installs Python 3.11 + dependencies (~500 MB)
  - Copies source code
  - Creates directories
- **Frontend:**
  - Stage 1: `npm ci` + `npm run build` (~200 MB)
  - Stage 2: Copies dist/ to nginx (~50 MB)

**Total build time:** 5-10 minutes (first time)

---

### Step 3: Start Services

```bash
# Start in background
docker-compose up -d

# Start with logs (for debugging)
docker-compose up

# Check status
docker-compose ps
```

**Expected output:**
```
NAME                              STATUS         PORTS
requirements-extractor-db         Up (healthy)   0.0.0.0:5433->5432/tcp
requirements-extractor-api        Up (healthy)   0.0.0.0:8000->8000/tcp
requirements-extractor-frontend   Up             0.0.0.0:8080->80/tcp
```

---

### Step 4: Initialize Database

Database tables are created automatically on first API start (via SQLAlchemy).

**Manual initialization (if needed):**
```bash
# Option 1: Use init script from container
docker exec -it requirements-extractor-api python scripts/init_db_docker.py

# Option 2: Run Alembic migrations
docker exec -it requirements-extractor-api alembic upgrade head

# Verify tables
docker exec -it requirements-extractor-api python scripts/check_db.py
```

---

### Step 5: Verify Deployment

```bash
# Check logs
docker-compose logs api
docker-compose logs frontend

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8080/health

# Test API
curl http://localhost:8000/api/documents
```

**Expected responses:**
```json
// /health
{"status": "healthy"}

// /api/documents
[]  // Empty array (no documents yet)
```

---

## Access URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:8080 | Main UI |
| **API** | http://localhost:8000 | Backend API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **PostgreSQL** | localhost:5433 | Database (external) |

---

## Configuration

### Environment Variables

#### `.env` file:
```bash
# AI API Keys
OPENROUTER_API_KEY=sk-or-v1-...    # OpenRouter API key
DEEPSEEK_API_KEY=sk-...            # DeepSeek API key (optional)

# Database
POSTGRES_USER=requirements_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=requirements_db

# Database URL (for API)
DATABASE_URL=postgresql://requirements_user:secure_password_here@postgres:5432/requirements_db
```

#### Change ports (if needed):
```yaml
# docker-compose.yml
services:
  api:
    ports:
      - "9000:8000"  # Change 9000 to desired port
  
  frontend:
    ports:
      - "8090:80"    # Change 8090 to desired port
```

---

## Data Persistence

### Volumes

```yaml
volumes:
  postgres_data:      # Database data (persistent)
  data:               # Uploaded PDFs (persistent)
  logs:               # Application logs (persistent)
```

**Location on host:**
```bash
# Check volume location
docker volume inspect test2_postgres_data
docker volume inspect test2_data
docker volume inspect test2_logs

# Backup data
docker run --rm -v test2_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/db_backup.tar.gz /data
```

---

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 api
```

### Container Stats

```bash
# Real-time stats
docker stats

# Disk usage
docker system df
```

### Health Checks

```bash
# Check container health
docker inspect requirements-extractor-api | grep -A5 Health

# API health endpoint
curl http://localhost:8000/health
```

---

## Maintenance

### Start/Stop

```bash
# Stop all services
docker-compose stop

# Start all services
docker-compose start

# Restart specific service
docker-compose restart api

# Stop and remove containers
docker-compose down
```

### Update Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Or rebuild only changed service
docker-compose up -d --build api
```

### Backup Database

```bash
# Create backup
docker exec requirements-extractor-db pg_dump -U requirements_user requirements_db > backup.sql

# Restore backup
docker exec -i requirements-extractor-db psql -U requirements_user requirements_db < backup.sql
```

### Clean Up

```bash
# Remove containers and volumes
docker-compose down -v

# Remove unused images
docker image prune -a

# Remove all unused data
docker system prune -a --volumes
```

---

## Troubleshooting

### Issue: API container exits immediately

**Check logs:**
```bash
docker-compose logs api
```

**Common causes:**
- Missing API keys in `.env`
- Database connection failed
- Port 8000 already in use

**Solution:**
```bash
# Check .env file
cat .env

# Check if port is free
netstat -an | grep 8000

# Restart with logs
docker-compose up api
```

---

### Issue: Frontend shows "Connection refused"

**Check:**
```bash
# Is API running?
curl http://localhost:8000/health

# Check nginx logs
docker-compose logs frontend

# Check nginx config
docker exec requirements-extractor-frontend cat /etc/nginx/conf.d/default.conf
```

**Solution:**
```bash
# Restart frontend
docker-compose restart frontend
```

---

### Issue: Database connection failed

**Check:**
```bash
# Is PostgreSQL running?
docker-compose ps postgres

# Check health
docker exec requirements-extractor-db pg_isready -U requirements_user

# Check logs
docker-compose logs postgres
```

**Solution:**
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Wait for healthy status
docker-compose ps
```

---

### Issue: Out of disk space

**Check:**
```bash
docker system df
docker volume ls
```

**Solution:**
```bash
# Clean old data
docker system prune -a --volumes

# Remove specific volumes
docker volume rm test2_data
```

---

## Production Recommendations

### Security

1. **Change default passwords**
   ```bash
   # Generate strong password
   openssl rand -base64 32
   
   # Update .env
   POSTGRES_PASSWORD=<generated_password>
   ```

2. **Use secrets** (Docker Swarm/Kubernetes)
   ```yaml
   services:
     api:
       secrets:
         - openrouter_api_key
   
   secrets:
     openrouter_api_key:
       external: true
   ```

3. **Limit network access**
   ```yaml
   services:
     postgres:
       ports: []  # Remove external port
   ```

4. **Enable HTTPS**
   - Use Let's Encrypt + Certbot
   - Update nginx.conf for SSL

---

### Performance

1. **Resource limits**
   ```yaml
   services:
     api:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 4G
   ```

2. **Scale services**
   ```bash
   docker-compose up -d --scale api=3
   ```

3. **Enable caching** (Redis)
   ```yaml
   services:
     redis:
       image: redis:alpine
   ```

---

### Monitoring

1. **Add Prometheus + Grafana**
   ```yaml
   services:
     prometheus:
       image: prom/prometheus
   ```

2. **Centralized logging** (ELK stack)

3. **Uptime monitoring** (Uptime Kuma)

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and push
        run: |
          docker-compose build
          docker-compose push
      
      - name: Deploy to server
        run: |
          ssh user@server "cd /app && docker-compose pull && docker-compose up -d"
```

---

## Summary

✅ **3 containers:** PostgreSQL, API, Frontend  
✅ **1 command:** `docker-compose up -d`  
✅ **Auto dependencies:** npm, pip, postgres  
✅ **Persistent data:** Volumes for DB, uploads, logs  
✅ **Health checks:** Automatic restart on failure  
✅ **Production-ready:** HTTPS, secrets, monitoring  

**Access:** http://localhost:8080 🚀
