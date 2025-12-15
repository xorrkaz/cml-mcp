# Docker Deployment

The cml-mcp server is available as a Docker container for easy deployment. This guide covers building, running, and deploying the container.

## Quick Start

```bash
# Pull the image
docker pull ghcr.io/xorrkaz/cml-mcp:latest

# Run with environment variables
docker run --rm -it \
  -e CML_URL=https://cml.example.com \
  -e CML_USERNAME=admin \
  -e CML_PASSWORD=secret \
  ghcr.io/xorrkaz/cml-mcp:latest
```

---

## Docker Compose

The project includes a `docker-compose.yml` with multiple profiles for different use cases.

### Profiles

| Profile | Description | Transport |
|---------|-------------|-----------|
| `http` | Production HTTP server | SSE over HTTP |
| `stdio` | Interactive stdio mode | stdio |
| `dev` | Development with hot reload | SSE over HTTP |

### Environment File

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Configure the required settings:

```ini
# Required Settings
CML_URL=https://cml.example.com
CML_USERNAME=admin
CML_PASSWORD=your-secure-password

# Optional Settings
CML_VERIFY_SSL=true
CML_MCP_TRANSPORT=sse
CML_MCP_BIND=0.0.0.0
CML_MCP_PORT=8080
DEBUG=false
```

### Running with Docker Compose

```bash
# HTTP mode (recommended for production)
docker compose --profile http up -d

# Check logs
docker compose --profile http logs -f

# Stop
docker compose --profile http down
```

---

## Justfile Commands

The project includes convenient Just commands for Docker operations:

```bash
# Build container
just docker-build

# Run with HTTP transport
just docker-up

# View logs
just docker-logs

# Stop and remove
just docker-down

# Full cleanup (includes volumes)
just docker-clean
```

!!! tip "Project Isolation"
    All Docker Compose commands use `-p cml-mcp` for project scoping, preventing conflicts with other projects.

---

## Transport Modes

### HTTP Mode (Production)

HTTP mode runs as a stateless HTTP server, ideal for multi-user access.

```yaml
services:
  cml-mcp-http:
    profiles: ["http"]
    build: .
    environment:
      - CML_MCP_TRANSPORT=sse
      - CML_MCP_BIND=0.0.0.0
      - CML_MCP_PORT=8080
    ports:
      - "8080:8080"
```

!!! warning "Authentication"
    In HTTP mode, credentials must be provided per-request via HTTP headers. The container's `CML_USERNAME`/`CML_PASSWORD` are ignored.

### stdio Mode (Single User)

stdio mode is for direct connection to an AI client.

```yaml
services:
  cml-mcp-stdio:
    profiles: ["stdio"]
    build: .
    environment:
      - CML_MCP_TRANSPORT=stdio
    stdin_open: true
    tty: true
```

---

## Building the Image

### Local Build

```bash
docker build -t cml-mcp:local .
```

### Multi-Platform Build

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/xorrkaz/cml-mcp:latest \
  --push .
```

### Dockerfile Details

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies with uv
RUN pip install uv
COPY pyproject.toml .
RUN uv sync --no-cache

# Copy application
COPY src/ ./src/

# Entrypoint script handles transport selection
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
```

---

## Health Checks

The HTTP mode exposes health endpoints:

```bash
# Simple health check
curl http://localhost:8080/health

# Full status
curl http://localhost:8080/sse
```

Docker Compose can use these for health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

---

## Production Deployment

### With Traefik (HTTPS)

```yaml
services:
  cml-mcp:
    image: ghcr.io/xorrkaz/cml-mcp:latest
    environment:
      - CML_URL=${CML_URL}
      - CML_MCP_TRANSPORT=sse
      - CML_MCP_BIND=0.0.0.0
      - CML_MCP_PORT=8080
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cml-mcp.rule=Host(`mcp.example.com`)"
      - "traefik.http.routers.cml-mcp.tls=true"
      - "traefik.http.routers.cml-mcp.tls.certresolver=letsencrypt"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

### With Nginx Reverse Proxy

```nginx
upstream cml-mcp {
    server localhost:8080;
}

server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate /etc/ssl/certs/mcp.crt;
    ssl_certificate_key /etc/ssl/private/mcp.key;

    location / {
        proxy_pass http://cml-mcp;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;

        # SSE support
        proxy_set_header X-Accel-Buffering no;
    }
}
```

---

## Resource Limits

Configure container resources for production:

```yaml
services:
  cml-mcp:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
```

---

## Logging

Configure JSON logging for production:

```yaml
services:
  cml-mcp:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Or use an external logging driver:

```yaml
services:
  cml-mcp:
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logserver:514"
        tag: "cml-mcp"
```

---

## Troubleshooting

### Container Won't Start

1. Check environment variables:
   ```bash
   docker compose config
   ```

2. View startup logs:
   ```bash
   docker compose logs cml-mcp-http
   ```

3. Verify CML connectivity:
   ```bash
   docker run --rm -it \
     -e CML_URL=https://cml.example.com \
     ghcr.io/xorrkaz/cml-mcp:latest \
     curl -k ${CML_URL}/api/v0/system/information
   ```

### SSL Certificate Issues

If your CML server uses self-signed certificates:

```bash
# Disable SSL verification (development only!)
docker run --rm -it \
  -e CML_URL=https://cml.example.com \
  -e CML_VERIFY_SSL=false \
  ghcr.io/xorrkaz/cml-mcp:latest
```

!!! danger "Security Warning"
    Disabling SSL verification exposes credentials to man-in-the-middle attacks. Only use for local development.

### Connection Refused

Ensure the container can reach the CML server:

```bash
# Test connectivity from container
docker run --rm -it \
  --entrypoint /bin/sh \
  ghcr.io/xorrkaz/cml-mcp:latest \
  -c "curl -v https://cml.example.com"
```
