# 🚀 Quick Deployment

One-command deployment for PDF Requirements Extractor.

## TL;DR

```bash
# 1. Create .env with API keys
echo "OPENROUTER_API_KEY=your_key_here" > .env

# 2. Start everything
docker-compose up -d --build

# 3. Open browser
http://localhost:8080
```

---

## What Gets Installed Automatically

### ✅ PostgreSQL
- **Image:** `postgres:16-alpine` (~80 MB)
- **Downloaded:** Automatically from Docker Hub
- **No manual install needed!**

### ✅ Python Dependencies
- **Installed in:** API container during build
- **From:** `requirements.txt`
- **Includes:** FastAPI, SQLAlchemy, psycopg, etc.
- **No manual `pip install` needed!**

### ✅ Node.js Dependencies (pdfjs-dist)
- **Installed in:** Frontend container during build
- **Command:** `npm ci` (reads `package-lock.json`)
- **Includes:** pdfjs-dist, Vue 3, Vuetify, etc.
- **No manual `npm install` needed!**

---

## Build Process

### What happens when you run `docker-compose up --build`:

#### 1. PostgreSQL Container
```bash
# Docker pulls official image
docker pull postgres:16-alpine  # ~80 MB, takes 10-30 sec
```
**No configuration needed!**

---

#### 2. API Container (Backend)
```dockerfile
FROM python:3.11-slim              # Pull Python (~150 MB)
COPY requirements.txt .            # Copy deps list
RUN pip install -r requirements.txt  # Install ALL deps (~350 MB)
COPY . .                           # Copy source code
```

**Installed automatically:**
- ✅ fastapi
- ✅ uvicorn
- ✅ sqlalchemy
- ✅ psycopg[binary]
- ✅ alembic
- ✅ pymupdf
- ✅ python-docx
- ✅ httpx
- ... (all from requirements.txt)

**Total time:** 3-5 minutes  
**Total size:** ~500 MB

---

#### 3. Frontend Container
```dockerfile
# Stage 1: Build
FROM node:20-alpine                # Pull Node.js (~150 MB)
COPY package*.json .               # Copy deps list
RUN npm ci                         # Install ALL deps from package-lock.json
COPY frontend-vue/ .               # Copy source
RUN npm run build                  # Build for production

# Stage 2: Serve
FROM nginx:alpine                  # Pull Nginx (~40 MB)
COPY --from=builder /app/dist .    # Copy built files
```

**Installed automatically (via npm ci):**
- ✅ pdfjs-dist (PDF rendering)
- ✅ vue (framework)
- ✅ vuetify (UI components)
- ✅ pinia (state management)
- ✅ axios (HTTP client)
- ✅ vite (build tool)
- ... (all from package-lock.json)

**Total time:** 2-3 minutes  
**Total size:** Stage 1 (~200 MB) → Stage 2 (~50 MB final)

---

## Why Docker is Better

### ❌ Manual Installation (What you DON'T need to do):

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create Python virtual environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # Can fail due to missing system deps!

# Install Node.js dependencies
cd frontend-vue
npm install pdfjs-dist  # Can fail due to node version mismatch!
npm run build

# Configure database
sudo -u postgres psql
CREATE DATABASE requirements_db;
...
```

**Problems:**
- ❌ Version conflicts (Python 3.9 vs 3.11)
- ❌ Missing system dependencies (gcc, build-essential)
- ❌ Platform-specific issues (Windows vs Linux)
- ❌ "Works on my machine" syndrome

---

### ✅ Docker (What you DO):

```bash
docker-compose up -d --build
```

**Benefits:**
- ✅ All dependencies bundled in image
- ✅ Same environment everywhere (dev = prod)
- ✅ Isolated from host system
- ✅ One command to rule them all

---

## Deployment Checklist

### Before Running

- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] `.env` file created with API keys
- [ ] 10 GB free disk space

### Run

```bash
docker-compose up -d --build
```

### Verify

```bash
# Check all containers running
docker-compose ps

# Expected:
# - requirements-extractor-db       Up (healthy)
# - requirements-extractor-api      Up (healthy)
# - requirements-extractor-frontend Up
```

### Access

```
http://localhost:8080  # Frontend UI
http://localhost:8000/docs  # API docs
```

---

## First Time Setup (Detailed)

### Step 1: Install Docker

**Windows:**
```powershell
# Download Docker Desktop
# https://www.docker.com/products/docker-desktop/

# Install and restart computer
```

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

---

### Step 2: Clone Repository

```bash
git clone <repository_url>
cd test2
```

---

### Step 3: Configure

```bash
# Copy example env
cp .env.example .env

# Edit with your API keys
nano .env
```

**Minimum .env:**
```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

---

### Step 4: Build & Start

```bash
# Build all images (first time: 5-10 min)
docker-compose build

# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

---

### Step 5: Test

```bash
# Open browser
http://localhost:8080

# Upload a PDF
# Wait for processing
# Download results
```

---

## FAQ

### Q: Do I need to install PostgreSQL on my computer?
**A:** No! It runs in Docker container.

### Q: Do I need to run `pip install`?
**A:** No! All Python dependencies installed in container during build.

### Q: Do I need to run `npm install pdfjs-dist`?
**A:** No! All Node dependencies installed in container during build.

### Q: What if I change code?
**A:** Rebuild container:
```bash
docker-compose up -d --build api     # If backend changed
docker-compose up -d --build frontend # If frontend changed
```

### Q: How do I update dependencies?
**A:** 
1. Edit `requirements.txt` or `package.json`
2. Rebuild: `docker-compose build`
3. Restart: `docker-compose up -d`

### Q: How do I stop everything?
**A:**
```bash
docker-compose down  # Stop and remove containers
docker-compose down -v  # Also remove data (WARNING!)
```

---

## Production Deployment

### 1. On VPS/Cloud Server

```bash
# SSH to server
ssh user@your-server.com

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone repo
git clone <your-repo>
cd test2

# Setup
cp .env.example .env
nano .env  # Add API keys

# Deploy
docker-compose up -d --build

# Access via server IP
http://your-server-ip:8080
```

### 2. Add Domain & HTTPS

```bash
# Install Caddy (automatic HTTPS)
docker-compose -f docker-compose.prod.yml up -d
```

**Access:**
```
https://your-domain.com
```

---

## Summary

**What you need:**
- ✅ Docker
- ✅ `.env` file with API key

**What you DON'T need:**
- ❌ PostgreSQL installed
- ❌ Python virtual environment
- ❌ Node.js installed
- ❌ npm install commands

**One command:**
```bash
docker-compose up -d --build
```

**Result:** Full system running! 🚀
