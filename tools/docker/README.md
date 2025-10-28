# Docker Setup for MCP Memory Service

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [What's New](#-whats-new-v890)
- [Configuration](#-configuration)
- [Authentication Setup](#-authentication-setup)
- [Testing](#-testing)
- [Deployment Scenarios](#-deployment-scenarios)
- [Migration Guide](#-migration-guide)
- [Feature Highlights](#-feature-highlights-v890)
- [Configuration Reference](#-configuration-reference)
- [HTTP Mode Endpoints](#-http-mode-endpoints)
- [Troubleshooting](#-troubleshooting)
- [Image Variants](#-image-variants)
- [Security Best Practices](#-security-best-practices)

## ⚡ TL;DR (Quick Setup)

```bash
# 1. Build image
cd /path/to/mcp-memory-service
docker build -f tools/docker/Dockerfile.slim -t mcp-memory-service:latest .

# 2. Configure (copy .env and set your API key)
cp .env.example .env
# Edit .env: Set MCP_API_KEY=your-secure-key

# 3. Run
docker compose up -d

# 4. Test
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/api/health
```

## 🚀 Quick Start

### Step 1: Build the Image

Build the Docker image with authentication support:

```bash
# Navigate to the project root
cd /path/to/mcp-memory-service

# Build the slim image (recommended - includes OAuth support)
docker build -f tools/docker/Dockerfile.slim \
  -t mcp-memory-service:latest \
  -t mcp-memory-service:v8.9.0 .

# Or build the full image (includes all dependencies)
docker build -f tools/docker/Dockerfile \
  -t mcp-memory-service:full .
```

### Step 2: Configure Environment

Copy and configure your `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
# See "Environment Configuration" section below
```

### Step 3: Run the Container

Choose your mode:

#### HTTP API Mode (default - with authentication)
```bash
docker compose up -d
```

#### MCP Protocol Mode (stdio)
```bash
docker compose -f docker-compose.mcp.yml up -d
```

## 📝 What's New (v8.9.0)

### ✅ New Features
- **OAuth 2.1 Authentication** with JWT token support (RS256)
- **Cryptography Package** for secure RSA key generation
- **python-jose** for JWT token handling
- **API Key Authentication** as alternative to OAuth
- **Fixed Line Endings** for cross-platform compatibility

### 🎯 Previous Improvements (v5.0.4)
- **PYTHONPATH** correctly set to `/app/src`
- **run_server.py** properly copied for HTTP mode
- **Embedding models** pre-downloaded during build
- **2 clear modes** instead of 4 confusing variants
- **Unified entrypoint** that auto-detects mode

## 🔧 Configuration

### Environment Variables

#### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_MODE` | Operation mode: `mcp` or `http` | `http` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HTTP_PORT` | Host port for HTTP mode | `8000` |
| `MCP_HTTP_PORT` | Container internal port | `8000` |
| `MCP_HTTP_HOST` | Bind address | `0.0.0.0` |

#### Storage Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_MEMORY_STORAGE_BACKEND` | Backend: `sqlite_vec`, `cloudflare`, `hybrid` | `sqlite_vec` |
| `MCP_MEMORY_SQLITE_PATH` | SQLite database path | `/app/data/sqlite_vec.db` |
| `MCP_MEMORY_BACKUPS_PATH` | Backups directory | `/app/data/backups` |
| `MCP_MEMORY_USE_ONNX` | Use ONNX embeddings (CPU-only) | `1` |

#### Authentication (OAuth 2.1)

| Variable | Description | Required |
|----------|-------------|----------|
| `MCP_OAUTH_ENABLED` | Enable OAuth authentication | No (default: `false`) |
| `MCP_OAUTH_PRIVATE_KEY` | RSA private key for JWT signing | Yes if OAuth enabled |
| `MCP_OAUTH_PUBLIC_KEY` | RSA public key for JWT verification | Yes if OAuth enabled |
| `MCP_OAUTH_ISSUER` | OAuth issuer URL | Yes if OAuth enabled |
| `MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry (minutes) | No (default: `60`) |
| `MCP_API_KEY` | API key for Bearer token auth | Recommended |

#### Cloudflare Configuration (Optional)

| Variable | Description | Required |
|----------|-------------|----------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token | If using Cloudflare backend |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID | If using Cloudflare backend |
| `CLOUDFLARE_D1_DATABASE_ID` | D1 database ID | If using Cloudflare backend |
| `CLOUDFLARE_VECTORIZE_INDEX` | Vectorize index name | If using Cloudflare backend |

### Volume Mounts

All data is stored in a single `./data` directory:
- SQLite database: `./data/sqlite_vec.db`
- Backups: `./data/backups/`
- ONNX models cache: `/root/.cache/mcp_memory/onnx_models/`

## 🔐 Authentication Setup

### Option 1: API Key Authentication (Simpler)

1. Generate a secure API key:
```bash
# On Linux/Mac
openssl rand -hex 32

# On Windows PowerShell
$bytes = New-Object byte[] 32; `
(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); `
[Convert]::ToBase64String($bytes)
```

2. Add to `.env`:
```bash
MCP_API_KEY=your-generated-api-key-here
MCP_OAUTH_ENABLED=false
```

3. Use the API key:
```bash
curl -H "Authorization: Bearer your-api-key-here" \
     http://localhost:8000/api/memories
```

### Option 2: OAuth 2.1 with JWT (More Secure)

1. Generate RSA key pair:
```bash
docker run --rm --entrypoint="" mcp-memory-service:latest python -c "
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

print('MCP_OAUTH_PRIVATE_KEY=\"' + private_pem + '\"')
print('MCP_OAUTH_PUBLIC_KEY=\"' + public_pem + '\"')
"
```

2. Add to `.env`:
```bash
MCP_OAUTH_ENABLED=true
MCP_OAUTH_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...your private key...
-----END PRIVATE KEY-----"

MCP_OAUTH_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
...your public key...
-----END PUBLIC KEY-----"

MCP_OAUTH_ISSUER=http://localhost:8000
MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

3. Obtain and use JWT tokens via OAuth flow

### Disable Authentication (Development Only)

**⚠️ NOT RECOMMENDED FOR PRODUCTION**

```bash
MCP_OAUTH_ENABLED=false
# Remove or leave MCP_API_KEY empty
```

## 🧪 Testing

### Test Authentication

```bash
# Test without authentication (should fail)
curl http://localhost:8000/api/memories

# Test with API key (should succeed)
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/api/memories

# Test health endpoint (public, no auth required)
curl http://localhost:8000/api/health
```

### Run Test Script

```bash
./test-docker-modes.sh
```

## 🔄 Deployment Scenarios

### Scenario 1: Local Development (Build from Source)
```bash
cd mcp-memory-service/tools/docker
cp env.template .env
# Edit .env with basic settings
docker compose -f docker-compose.slim.yml up -d
```

### Scenario 2: Production with Pre-built Image
```bash
cd mcp-memory-service/tools/docker
cp env.template .env

# Set your registry image
echo "MEMORY_IMAGE=your-registry/mcp-memory:v8.9.0" >> .env

# Configure authentication
echo "MCP_API_KEY=$(openssl rand -hex 32)" >> .env

docker compose -f docker-compose.slim.yml up -d
```

### Scenario 3: Production with OAuth
```bash
# Generate RSA keys
docker run --rm --entrypoint="" mcp-memory-service:latest python -c "
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

print('===PRIVATE_KEY===')
print(private_pem)
print('===PUBLIC_KEY===')
print(public_pem)
"

# Add to .env:
# MCP_OAUTH_ENABLED=true
# MCP_OAUTH_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
# MCP_OAUTH_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."

docker compose -f docker-compose.slim.yml up -d
```

### Scenario 4: Cloudflare Backend
```bash
# Configure Cloudflare credentials in .env
MCP_MEMORY_STORAGE_BACKEND=cloudflare
CLOUDFLARE_API_TOKEN=your-token
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_D1_DATABASE_ID=your-database-id
CLOUDFLARE_VECTORIZE_INDEX=mcp-memory-index
CLOUDFLARE_R2_BUCKET=mcp-memory-content

docker compose -f docker-compose.slim.yml up -d
```

## 🔄 Migration Guide

### From v5.0.4 to v8.9.0

**No breaking changes!** All existing configurations continue to work.

#### What's New (Optional Features)
1. **Authentication** - Add `MCP_API_KEY` or enable OAuth
2. **Cloudflare Backend** - Set backend to `cloudflare` or `hybrid`
3. **mDNS Discovery** - Automatic service advertisement
4. **Pre-built Images** - Use `MEMORY_IMAGE` environment variable

#### Gradual Adoption Path

**Step 1: Continue as-is** (No changes needed)
```bash
# Your existing setup works without modification
docker compose -f docker-compose.slim.yml up -d
```

**Step 2: Add API Key** (Simple authentication)
```bash
# Add one line to .env
MCP_API_KEY=$(openssl rand -hex 32)
```

**Step 3: Enable OAuth** (When ready for enhanced security)
```bash
# Generate keys and update .env
MCP_OAUTH_ENABLED=true
MCP_OAUTH_PRIVATE_KEY="..."
MCP_OAUTH_PUBLIC_KEY="..."
```

**Step 4: Switch Backend** (Optional - Cloudflare/Hybrid)
```bash
# Update .env
MCP_MEMORY_STORAGE_BACKEND=cloudflare
# Add Cloudflare credentials
```

### From docker-compose.yml to docker-compose.slim.yml

The slim variant is recommended for most deployments:

**Differences:**
- ✅ **Dockerfile.slim**: Uses ONNX (CPU-only, ~2GB vs ~6GB)
- ✅ **Better defaults**: All config has sensible defaults
- ✅ **More options**: OAuth, Cloudflare, mDNS support
- ✅ **Same features**: All core functionality identical

**Migration:**
```bash
# Replace your docker-compose command
docker compose -f docker-compose.yml up -d      # Old
docker compose -f docker-compose.slim.yml up -d # New (recommended)
```

## 📚 Related Documentation

- HTTP/SSE API overview: docs/IMPLEMENTATION_PLAN_HTTP_SSE.md
- SQLite-vec backend guide: docs/sqlite-vec-backend.md
- Remote configuration and environment: docs/remote-configuration-wiki-section.md
- Architecture and components: docs/architecture.md
- OAuth setup guide: docs/oauth-setup.md

These docs explain how the HTTP endpoints, SSE, and SQLite-vec storage work, and how to configure the service via environment variables (used by this Docker setup via .env).

## 📊 HTTP Mode Endpoints

When running in HTTP mode:
- **Dashboard**: http://localhost:8000/
- **API Docs**: http://localhost:8000/api/docs (Swagger UI)
- **Health Check**: http://localhost:8000/api/health (No auth required)
- **Memories API**: http://localhost:8000/api/memories (Auth required)
- **OAuth Discovery**: http://localhost:8000/.well-known/oauth-authorization-server

## 🆕 Feature Highlights (v8.9.0)

### Authentication & Security
- **OAuth 2.1 Support**: Industry-standard JWT tokens with RS256 signing
- **API Key Auth**: Simpler Bearer token authentication
- **Flexible Security**: Choose no auth, API key, or full OAuth
- **HTTPS Ready**: SSL certificate support built-in

### Backend Options
- **SQLite-vec**: Fast local storage (default)
- **Cloudflare**: D1 + Vectorize + R2 cloud storage
- **Hybrid**: Best of both - local speed, cloud persistence

### Deployment Features
- **Pre-built Images**: Use registry images or build from source
- **mDNS Discovery**: Automatic service advertisement
- **Health Checks**: Built-in readiness probing
- **Multi-container**: Custom network support

### Configuration
- **40+ Environment Variables**: Comprehensive control
- **Sensible Defaults**: Works out-of-box
- **env.template**: Complete configuration guide
- **Backward Compatible**: No breaking changes

## 📦 Configuration Reference

### New in v8.9.0

**Authentication:**
- `MCP_OAUTH_ENABLED` - Enable OAuth 2.1
- `MCP_OAUTH_PRIVATE_KEY` - RSA private key for JWT signing
- `MCP_OAUTH_PUBLIC_KEY` - RSA public key for verification
- `MCP_OAUTH_ISSUER` - OAuth issuer URL

**Cloudflare Backend:**
- `CLOUDFLARE_API_TOKEN` - API authentication
- `CLOUDFLARE_ACCOUNT_ID` - Account identifier
- `CLOUDFLARE_D1_DATABASE_ID` - D1 database
- `CLOUDFLARE_VECTORIZE_INDEX` - Vector search index
- `CLOUDFLARE_R2_BUCKET` - Object storage bucket

**Service Discovery:**
- `MCP_MDNS_ENABLED` - Enable mDNS advertisement
- `MCP_MDNS_SERVICE_NAME` - Service name for discovery

**Hybrid Backend:**
- `MCP_HYBRID_SYNC_INTERVAL` - Sync frequency (seconds)
- `MCP_HYBRID_BATCH_SIZE` - Batch operation size
- `MCP_HYBRID_SYNC_ON_STARTUP` - Initial sync behavior

**Image Management:**
- `MEMORY_IMAGE` - Use pre-built image instead of building

See `env.template` for complete list with descriptions.

## 🔄 Migration from Old Setup

### From Legacy Docker Files

If you were using the old Docker files:

| Old File | New Alternative | Status |
|----------|-----------------|--------|
| `docker-compose.standalone.yml` | `docker-compose.slim.yml` | ✅ Enhanced |
| `docker-compose.uv.yml` | Built-in to Dockerfile.slim | ✅ Included |
| `docker-compose.pythonpath.yml` | Fixed in Dockerfile.slim | ✅ Fixed |

See [DEPRECATED.md](./DEPRECATED.md) for details.

## 🐛 Troubleshooting

### Container exits immediately

Check the logs:
```bash
docker logs memory-service --tail 50
```

Common causes:
- **OAuth configuration error**: Missing RSA keys or invalid configuration
  - Solution: Check OAuth environment variables in `.env`
  - Or disable OAuth: `MCP_OAUTH_ENABLED=false`

- **Line ending issues**: CRLF vs LF in entrypoint scripts
  - Solution: Rebuild image with `--no-cache`

- **Missing dependencies**: python-jose, cryptography
  - Solution: Use the latest Dockerfile.slim (v8.9.0+)

### Cannot connect to HTTP endpoints

Verify setup:
```bash
# Check if container is running
docker ps -a --filter "name=memory-service"

# Check port mapping
docker port memory-service

# Test health endpoint (no auth)
curl http://localhost:8000/api/health
```

If health check fails:
- Verify `HTTP_PORT` in `.env` matches your docker-compose port mapping
- Check firewall rules
- Ensure no other service is using port 8000

### Authentication errors

**Error**: `{"error":"authorization_required"}`
- ✅ This is CORRECT behavior - authentication is working
- Solution: Add `Authorization: Bearer <your-api-key>` header

**Error**: `"Invalid OAuth configuration: JWT configuration error"`
- Check OAuth keys are properly formatted in `.env`
- Ensure no extra spaces or line breaks in RSA keys
- Verify `cryptography` and `python-jose` packages are installed

**Error**: `"No JWT signing key available"`
- Set either `MCP_OAUTH_PRIVATE_KEY` + `MCP_OAUTH_PUBLIC_KEY` (RS256)
- Or set `MCP_OAUTH_SECRET_KEY` (HS256)
- Or disable OAuth: `MCP_OAUTH_ENABLED=false`

### Embedding model errors

Models are pre-downloaded during build, but may download at runtime if cache is missing:
```bash
# Check if models are cached
docker exec memory-service ls -la /root/.cache/mcp_memory/onnx_models/

# Force rebuild with fresh models
docker-compose down
docker build --no-cache -f tools/docker/Dockerfile.slim -t mcp-memory-service:latest .
docker-compose up -d
```

### Permission issues

If you see permission errors:
```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) ./data

# Or run with specific user
docker-compose run --user $(id -u):$(id -g) memory-service
```

### Performance issues

- Increase Docker memory allocation (4GB+ recommended)
- Use ONNX embeddings (CPU-only, lighter): `MCP_MEMORY_USE_ONNX=1`
- Monitor resource usage: `docker stats memory-service`

## 📦 Image Variants

### Dockerfile.slim (Recommended)
- **Size**: ~2GB
- **Includes**: ONNX embeddings, OAuth support, cryptography
- **Best for**: Production, CPU-only environments
- **Dependencies**: 71 packages including `cryptography`, `python-jose`

### Dockerfile (Full)
- **Size**: ~6GB+
- **Includes**: PyTorch, all ML dependencies
- **Best for**: GPU environments, advanced ML features
- **Dependencies**: Full ML stack

## 🔒 Security Best Practices

1. **Always use authentication in production**
   - Set strong API keys (32+ characters)
   - Use RS256 OAuth for better security
   - Never commit `.env` to git

2. **Use HTTPS in production**
   ```bash
   MCP_HTTPS_ENABLED=true
   MCP_HTTPS_PORT=8443
   MCP_SSL_CERT_FILE=/path/to/cert.pem
   MCP_SSL_KEY_FILE=/path/to/key.pem
   ```

3. **Rotate keys regularly**
   - Generate new API keys monthly
   - Regenerate OAuth keys quarterly
   - Update `.env` and restart container

4. **Use environment-specific configurations**
   - Development: `.env.development`
   - Production: `.env.production`
   - Never use development keys in production

## 🙏 Credits

Special thanks to:
- **Joe Esposito** for identifying and helping fix the Docker setup issues!
- All contributors who helped improve authentication and security features
