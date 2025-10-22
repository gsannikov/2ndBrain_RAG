# Deployment Guide

**Production-ready deployment instructions for 2ndBrain_RAG**

---

## Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed
- 4GB RAM minimum
- For HTTPS: SSL certificate and key

### Deploy with Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/gsannikov/2ndBrain_RAG.git
cd 2ndBrain_RAG

# 2. Create data directory
mkdir -p data

# 3. (Optional) Set up SSL certificates
mkdir -p ssl
# Copy your cert.pem and key.pem to ssl/

# 4. Start services
docker-compose up -d

# 5. Pull Ollama model
docker exec 2ndbrain-ollama ollama pull llama3

# 6. Verify
curl http://localhost:8000/status
# Or visit https://localhost if SSL is configured
```

Services will be available:
- RAG API: `http://localhost:8000`
- Ollama: `http://localhost:11434`
- Nginx (HTTPS): `https://localhost`

---

## Docker Deployment

### Dockerfile Overview

Multi-stage build optimizes image size:
- **Stage 1**: Build dependencies, install packages
- **Stage 2**: Runtime-only, smaller footprint (~500MB)

### Key Features

✅ Health checks on all services
✅ Auto-restart on failure
✅ Volume mounting for data persistence
✅ Network isolation between services
✅ Ollama GPU support (optional)

### Customization

#### Use Different LLM Model

```bash
# Set environment variable
export OLLAMA_MODEL=mistral

docker-compose up -d
docker exec 2ndbrain-ollama ollama pull mistral
```

#### Enable API Key

```bash
export RAG_API_KEY="your-secret-key"
docker-compose up -d

# Test with API key
curl -H "X-API-Key: your-secret-key" http://localhost:8000/status
```

#### Adjust Rate Limiting

```bash
# In docker-compose.yml environment:
- RATE_LIMIT_ENABLED=true
- RATE_LIMIT_PER_MINUTE=100  # Default: 60
```

#### Scale Ollama (GPU Support)

Add to `docker-compose.yml`:
```yaml
ollama:
  ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

---

## HTTPS/TLS Setup

### With Self-Signed Certificate

```bash
# Generate certificate (valid 365 days)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=localhost"

# Start with Docker Compose (nginx will handle HTTPS)
docker-compose up -d
```

### With Production Certificate

```bash
# Copy your certificate files
cp /path/to/cert.pem ssl/cert.pem
cp /path/to/key.pem ssl/key.pem

# Update nginx.conf if using different domain
# Modify: server_name yourdomain.com;

docker-compose up -d
```

### Certificate Renewal (Let's Encrypt)

```bash
# Using Certbot in container
docker run --rm -it \
  -v /path/to/ssl:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certify \
    -d yourdomain.com \
    --standalone

# Copy renewed certificates to ssl/
```

---

## Kubernetes Deployment

### Create Deployment Files

**k8s/deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rag-server
  template:
    metadata:
      labels:
        app: rag-server
    spec:
      containers:
      - name: rag
        image: 2ndbrain-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_HOST
          value: http://ollama:11434
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /status
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

**k8s/service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-service
spec:
  selector:
    app: rag-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Deploy to Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods -l app=rag-server
kubectl get service rag-service
```

---

## Manual Deployment (Linux/macOS)

### System Requirements
- Python 3.8+
- Ollama installed and running
- 2GB RAM minimum

### Installation

```bash
# 1. Clone repository
git clone https://github.com/gsannikov/2ndBrain_RAG.git
cd 2ndBrain_RAG

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Ollama (separate terminal)
ollama serve

# 5. Start RAG server
python -m uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000

# 6. (Optional) Set up systemd service
sudo cp rag.service /etc/systemd/system/
sudo systemctl enable rag
sudo systemctl start rag
```

### Systemd Service File

**rag.service**
```ini
[Unit]
Description=2ndBrain RAG Server
After=network.target ollama.service

[Service]
Type=simple
User=rag_user
WorkingDirectory=/home/rag_user/2ndBrain_RAG
Environment="RAG_FOLDER=/home/rag_user/2ndBrain_RAG"
Environment="OLLAMA_HOST=http://localhost:11434"
ExecStart=/home/rag_user/2ndBrain_RAG/venv/bin/python -m uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Setup with Supervisor

```ini
# /etc/supervisor/conf.d/rag.conf
[program:rag]
command=/home/rag_user/2ndBrain_RAG/venv/bin/python -m uvicorn rag_mcp_server:app --host 0.0.0.0 --port 8000
directory=/home/rag_user/2ndBrain_RAG
autostart=true
autorestart=true
stderr_logfile=/var/log/rag.err.log
stdout_logfile=/var/log/rag.out.log
environment=PATH="/home/rag_user/2ndBrain_RAG/venv/bin",OLLAMA_HOST="http://localhost:11434"
```

---

## Reverse Proxy Setup

### Nginx Configuration (HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    location / {
        limit_req zone=api burst=20;
        # ... rest of config
    }
}
```

### Apache Configuration

```apache
<VirtualHost *:443>
    ServerName yourdomain.com
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/yourdomain.com/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    <Location />
        Order allow,deny
        Allow from all
    </Location>
</VirtualHost>
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check API status
curl http://localhost:8000/status

# Check cache performance
curl http://localhost:8000/cache-stats

# Check logs (Docker)
docker-compose logs -f rag_server

# Check logs (systemd)
journalctl -u rag -f
```

### Database Maintenance

```bash
# Rebuild index
curl -X POST http://localhost:8000/ingest?full_rebuild=true

# Check Ollama
curl http://localhost:11434/api/tags
```

### Performance Tuning

| Parameter | Default | Description |
|-----------|---------|-------------|
| RATE_LIMIT_PER_MINUTE | 60 | API requests/min |
| RATE_LIMIT_ENABLED | true | Enable rate limiting |
| RAG_API_KEY | (none) | Optional API key |

### Log Monitoring

```bash
# View logs in real-time
tail -f /var/log/rag.out.log

# Search for errors
grep ERROR /var/log/rag.out.log

# Count requests by type
grep "Search query" /var/log/rag.out.log | wc -l
```

---

## Backup & Recovery

### Backup ChromaDB

```bash
# Backup vector database
tar -czf rag-backup-$(date +%Y%m%d).tar.gz data/.chroma

# Store in S3/GCS
aws s3 cp rag-backup-*.tar.gz s3://my-bucket/backups/
```

### Restore from Backup

```bash
# Extract backup
tar -xzf rag-backup-20231022.tar.gz

# Restart server
docker-compose restart rag_server
```

---

## Security Hardening

### Enable API Key

```bash
export RAG_API_KEY="complex-random-key-here"
docker-compose up -d

# All requests must include: X-API-Key header
curl -H "X-API-Key: $RAG_API_KEY" http://localhost:8000/status
```

### Configure Firewall

```bash
# Allow only specific IPs
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw enable
```

### Use HTTPS Only

```bash
# In nginx.conf or reverse proxy
return 301 https://$server_name$request_uri;
```

### Update Security Headers

Already configured in `nginx.conf`:
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process or use different port
docker-compose down
```

### Ollama Connection Failed

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify in docker-compose
docker ps | grep ollama

# Restart
docker-compose restart ollama
```

### Out of Memory

```bash
# Reduce model size
export OLLAMA_MODEL=phi  # Smaller model

# Reduce cache size
docker-compose down
docker system prune -a
docker-compose up -d
```

### SSL Certificate Issues

```bash
# Test certificate
openssl x509 -in ssl/cert.pem -text -noout

# Verify key matches cert
openssl x509 -noout -modulus -in ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in ssl/key.pem | openssl md5
```

---

## Scaling

### Horizontal Scaling (Load Balancing)

```yaml
# Multiple RAG instances with shared database
services:
  rag_1:
    ...
  rag_2:
    ...
  rag_3:
    ...

  load_balancer:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./lb.conf:/etc/nginx/nginx.conf
```

### Vertical Scaling

```bash
# Increase resources in docker-compose
rag_server:
  ...
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
```

---

## Cost Optimization

- Use lightweight embedding model: `all-MiniLM-L6-v2`
- Use fast Ollama model: `phi`, `mistral` (not llama3-70b)
- Enable query caching (reduce redundant searches)
- Use spot instances (cloud deployments)
- Implement data deduplication

---

## Production Checklist

- [ ] SSL/TLS configured
- [ ] API key enabled
- [ ] Rate limiting configured
- [ ] Backups automated
- [ ] Monitoring active
- [ ] Health checks working
- [ ] Logs aggregated
- [ ] Resource limits set
- [ ] Firewall rules applied
- [ ] Database backups tested

---

**For support and issues**, visit: https://github.com/gsannikov/2ndBrain_RAG/issues

