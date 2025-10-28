# 🌐 OAuth Browser Authentication & Security Guide

Complete guide for accessing and securing your MCP Memory Service with OAuth 2.1 authentication.

> **📚 Quick Navigation:**
>
> - [🚀 Quick Start](#quick-start-recommended) - Get started in 3 steps
> - [🔒 Security Configuration](#security-configuration) - Lock down your server (Production)
> - [🔑 Authentication Methods](#authentication-methods) - All available options
> - [🛠️ Troubleshooting](#troubleshooting) - Common issues and solutions
> - [📚 Advanced Usage](#advanced-usage) - API integration and customization
> - [⚙️ Technical Implementation](#technical-implementation) - How it works

> **✅ FIXED (Oct 28, 2025):**
>
> 1. OAuth login pages now accessible at root URLs (`/oauth-login.html` and `/oauth-callback.html`)
> 2. SSE authentication works automatically - token passed as query parameter since EventSource cannot set custom headers
> 3. SSE test page (`/static/sse_test.html`) updated with authentication support
> 4. Both dashboard and test page support ModHeader extension for Authorization header injection
> 5. **All UI API calls now authenticated** - Fixed missing authentication in:
>    - Management endpoints: `/api/manage/tags/stats`, `/api/manage/bulk-delete`, `/api/manage/cleanup-duplicates`
>    - Analytics endpoints: `/api/analytics/overview`, `/api/analytics/memory-growth`, `/api/analytics/tag-usage`, `/api/analytics/memory-types`
>    - Memory endpoints: `/api/memories` (pagination)
>    - Document uploads: `/api/documents/upload`, `/api/documents/batch-upload`
> 6. **OAuth disabled mode works correctly** - When `MCP_OAUTH_ENABLED=false`, SSE and all endpoints work without authentication

## 🎯 What Was Created

Three new files have been added to enable OAuth browser authentication:

1. **`/oauth-login.html`** - OAuth login page with auto-registration
2. **`/oauth-callback.html`** - OAuth callback handler
3. **Enhanced `app.js`** - Automatic authentication for all API calls

---

## 🚀 Quick Start (Recommended)

### **Option 1: One-Click Auto Login** ⭐ (Easiest)

1. **Open the login page** in your browser:

   ```
   http://192.168.1.30:8000/oauth-login.html
   ```

2. **Click "Auto Register & Login"**

   - Automatically registers a new OAuth client
   - Gets authorization code
   - Exchanges for access token
   - Redirects to dashboard

3. **You're in!** The dashboard will now work with authentication.

**That's it!** Your token is saved in localStorage and will be used automatically for all API requests.

---

## 🔧 Alternative Methods

### **Option 2: Manual OAuth Flow** (Advanced)

1. Open `http://192.168.1.30:8000/oauth-login.html`
2. Click "Manual OAuth Flow (Advanced)"
3. Register a client with:
   - **Client Name**: Any name (e.g., "My Browser Client")
   - **Redirect URI**: `http://localhost:3000/callback` (or any local URL)
4. Click "Get Authorization Code"
5. Copy the `code` parameter from the redirect URL
6. Paste it and click "Exchange for Access Token"
7. Click "Open Dashboard"

### **Option 3: API Key Authentication** (Legacy)

If you have an API key configured in `.env`:

1. Open `http://192.168.1.30:8000/oauth-login.html`
2. Click "API Key Authentication"
3. Enter your API key from `.env` file (`MCP_API_KEY`)
4. Click "Login with API Key"

---

## 🔐 How It Works

### **Authentication Flow**

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ 1. Visit /oauth-login.html
       ▼
┌─────────────────────┐
│  OAuth Login Page   │
│  - Auto Register    │
│  - Manual Flow      │
│  - API Key          │
└──────┬──────────────┘
       │
       │ 2. Register OAuth Client
       ▼
┌─────────────────────┐
│  OAuth Server       │
│  /oauth/register    │
│  Returns:           │
│  - client_id        │
│  - client_secret    │
└──────┬──────────────┘
       │
       │ 3. Get Authorization Code
       ▼
┌─────────────────────┐
│  OAuth Server       │
│  /oauth/authorize   │
│  Returns:           │
│  - code             │
└──────┬──────────────┘
       │
       │ 4. Exchange for Token
       ▼
┌─────────────────────┐
│  OAuth Server       │
│  /oauth/token       │
│  Returns:           │
│  - access_token     │
│  - expires_in       │
└──────┬──────────────┘
       │
       │ 5. Store token in localStorage
       ▼
┌─────────────────────┐
│   Dashboard         │
│   All API calls     │
│   automatically     │
│   include token     │
└─────────────────────┘
```

### **Token Storage**

Tokens are stored in two places:

1. **`localStorage.mcp_oauth_data`** - Persistent storage (survives browser restart)

   ```javascript
   {
     clientId: "mcp_...",
     clientSecret: "secret_...",
     redirectUri: "http://...",
     accessToken: "eyJ...",
     expiresIn: 3600,
     tokenType: "Bearer"
   }
   ```

2. **`sessionStorage.mcp_access_token`** - Quick access (current session only)
   ```
   "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

### **Automatic Authentication**

The dashboard (`app.js`) has been enhanced to:

✅ **Automatically include tokens** in all API requests
✅ **Detect 401 errors** and redirect to login
✅ **Support both OAuth and API key** authentication
✅ **Persist login state** across browser sessions

---

## 📊 Dashboard Features with Authentication

Once authenticated, you get full access to:

- 💾 **Memory Management** - Create, read, update, delete memories
- 🔍 **Advanced Search** - Semantic, tag-based, and time-based queries
- 📄 **Document Ingestion** - Upload and parse PDF, DOCX, TXT files
- 📊 **Analytics** - View memory statistics and trends
- 🏷️ **Tag Management** - Organize memories with tags
- 📡 **Real-time Updates** - Server-Sent Events for live updates

---

## 🔍 Testing Your Authentication

### **Quick Health Check**

```bash
# Get your token from the browser console
token = sessionStorage.getItem('mcp_access_token')

# Test the token
fetch('/api/health/detailed', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json()).then(console.log)
```

### **Expected Response**

```json
{
  "status": "healthy",
  "version": "8.9.0",
  "storage": {
    "backend": "hybrid",
    "total_memories": 42
  }
}
```

---

## 🛠️ Troubleshooting

### **Problem: "Authorization required" error**

**Solution:**

1. Clear your browser cache and localStorage
2. Visit `/oauth-login.html` again
3. Click "Auto Register & Login"

```javascript
// Clear saved data in browser console
localStorage.removeItem("mcp_oauth_data");
sessionStorage.removeItem("mcp_access_token");
location.reload();
```

### **Problem: Token expired**

**Solution:** Tokens expire after 60 minutes (default). Just re-login:

1. Visit `/oauth-login.html`
2. If you have saved credentials, click "Open Dashboard" (auto-refresh)
3. Otherwise, click "Auto Register & Login"

### **Problem: OAuth registration fails**

**Solution:** Ensure OAuth is enabled in your `.env`:

```bash
MCP_OAUTH_ENABLED=true
```

Restart the service:

```bash
uv run memory server
```

### **Problem: Redirect URI mismatch**

**Solution:** The auto-flow uses `${window.location.origin}/oauth-callback.html` as the redirect URI. If you're accessing from a different domain/port, the callback might not match.

**Fix:**

- Use the same URL consistently (e.g., always use `http://192.168.1.30:8000`)
- Or use the manual flow and specify your exact redirect URI

### **SSE Authentication (Now Working Automatically!)**

**How It Works:**

The dashboard now **automatically includes your authentication token** in SSE connections!

**Technical Implementation:**

1. After login, token is saved in `sessionStorage`
2. Dashboard reads token and passes it as query parameter: `/api/events?token=YOUR_TOKEN`
3. Server validates token from either query parameter OR Authorization header
4. SSE connects with full authentication ✅

**Why Query Parameters?**
The browser's `EventSource` API doesn't support custom headers. Passing the token as a query parameter solves this limitation while maintaining security.

**Alternative: ModHeader Extension**
If you prefer using Authorization headers:

1. Install [ModHeader](https://modheader.com/) browser extension
2. Add header: `Authorization` = `Bearer YOUR_TOKEN`
3. SSE will use header authentication instead

**Both methods work!** The app automatically handles whichever method you use.

### **SSE Test Page**

The SSE test page (`/static/sse_test.html`) also supports authentication:

1. **Auto-load token**: Opens with token pre-filled from storage if you've logged in
2. **Manual entry**: Paste your API key or OAuth token in the input field
3. **Click "Load from Storage"**: Loads token from sessionStorage/localStorage
4. **Connect**: SSE and all API calls will use authentication automatically

**Features:**

- Real-time event monitoring with authentication
- Test memory operations (store, search, delete) with auth
- Works with both OAuth tokens and API keys
- Compatible with ModHeader extension

---

## 🔒 Security Notes

### **Token Security**

✅ **Tokens are stored in localStorage** - Persistent but accessible only to your domain
✅ **HTTPS recommended** - Use `MCP_HTTPS_ENABLED=true` for production
✅ **Token expiration** - Tokens expire after 60 minutes (configurable)
✅ **Client secrets** - Stored securely in localStorage (not visible in code)

### **Best Practices**

1. **Use HTTPS in production** - Enable with `MCP_HTTPS_ENABLED=true`
2. **Rotate API keys** - Change `MCP_API_KEY` regularly
3. **Clear tokens on logout** - Click "Logout" button to remove all saved data
4. **Don't share tokens** - Never copy tokens to public places

---

## 🎨 Customization

### **Change Token Expiration**

Edit `.env`:

```bash
# Default: 60 minutes
MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES=120
```

### **Disable OAuth (Use API Key Only)**

Edit `.env`:

```bash
MCP_OAUTH_ENABLED=false
MCP_API_KEY=your-api-key-here
```

Then use "API Key Authentication" option in the login page.

### **Allow Anonymous Access** (Not Recommended)

Edit `.env`:

```bash
MCP_ALLOW_ANONYMOUS_ACCESS=true
```

Then you can access the dashboard directly without authentication.

---

## 📚 Advanced Usage

### **Using Tokens Programmatically**

```javascript
// Get token
const token = sessionStorage.getItem("mcp_access_token");

// Make authenticated API calls
async function callAPI(endpoint, method = "GET", data = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  const response = await fetch(`/api${endpoint}`, options);
  return response.json();
}

// Examples
await callAPI("/memories"); // Get all memories
await callAPI("/search", "POST", { query: "test", n_results: 5 }); // Search
await callAPI("/memories", "POST", { content: "New memory", tags: ["test"] }); // Create
```

### **Refresh Token on Expiry**

```javascript
// Check if token is expired
function isTokenExpired() {
  const savedData = localStorage.getItem("mcp_oauth_data");
  if (!savedData) return true;

  const oauthData = JSON.parse(savedData);
  // Implement expiry check based on your needs
  return false;
}

// Auto-refresh if needed
if (isTokenExpired()) {
  window.location.href = "/oauth-login.html";
}
```

---

## 📖 API Endpoints Reference

All API endpoints automatically work with OAuth tokens:

### **Memory Management**

- `POST /api/memories` - Store new memory
- `GET /api/memories` - List all memories
- `GET /api/memories/{hash}` - Get specific memory
- `DELETE /api/memories/{hash}` - Delete memory

### **Search**

- `POST /api/search` - Semantic search
- `POST /api/search/by-tag` - Tag-based search
- `POST /api/search/by-time` - Time-based search

### **Health & Status**

- `GET /api/health` - Quick health check
- `GET /api/health/detailed` - Detailed health info

---

## 🎉 Success!

You now have a fully functional OAuth 2.1 authentication system for your MCP Memory Service dashboard!

**Next Steps:**

1. Open `http://192.168.1.30:8000/oauth-login.html`
2. Click "Auto Register & Login"
3. Enjoy the dashboard! 🎊

**Need Help?**

- Check the browser console for error messages
- Review server logs: `journalctl -u mcp-memory-service -f`
- Test token validity: `/api/health/detailed`

---

---

## 🔒 Security Configuration

### Understanding OAuth Security Levels

By default, OAuth allows **anyone** to register a client and authenticate. This is convenient for development but risky for production.

**New in v8.9.0+:** Granular security controls to disable OAuth registration and authorization.

### Security Levels

#### 🔓 Level 1: Fully Open (Default - Development)

**Configuration:**

```bash
MCP_OAUTH_ENABLED=true
MCP_OAUTH_ALLOW_CLIENT_REGISTRATION=true
MCP_OAUTH_ALLOW_AUTHORIZATION=true
```

**Available Methods:** All 3 options (Auto, Manual, API Key)  
**Security:** Anyone can register and authenticate  
**Use Case:** Development, testing

---

#### 🔐 Level 2: API Key Only (Recommended - Production)

**Configuration:**

```bash
MCP_OAUTH_ENABLED=true
MCP_OAUTH_ALLOW_CLIENT_REGISTRATION=false
MCP_OAUTH_ALLOW_AUTHORIZATION=false
MCP_API_KEY=mcp-your-secure-api-key
```

**Available Methods:** API Key only  
**Security:** Only users with API key can access  
**Use Case:** Production, controlled access

**Generate secure API key:**

```bash
python -c "import secrets; print(f'mcp-{secrets.token_hex(32)}')"
```

---

#### 🔒 Level 3: OAuth Fully Disabled

**Configuration:**

```bash
MCP_OAUTH_ENABLED=false
MCP_API_KEY=mcp-your-secure-api-key
```

**Available Methods:** API Key only  
**Security:** OAuth infrastructure completely disabled  
**Use Case:** Maximum security environments

---

### How Security Controls Work

#### Backend Enforcement

When you disable OAuth features, the **endpoints are NOT loaded** into FastAPI:

```python
# When OAUTH_ALLOW_CLIENT_REGISTRATION=false
# /oauth/register → Returns 404 (not loaded)

# When OAUTH_ALLOW_AUTHORIZATION=false
# /oauth/authorize → Returns 404 (not loaded)
# /oauth/token → Returns 404 (not loaded)
```

**Security Guarantee:** Even if someone knows the OAuth API, they cannot use disabled endpoints.

#### Frontend Adaptation

The login page automatically:

- ✅ Hides disabled authentication options
- ✅ Shows "🔒 Secure Mode" message
- ✅ Highlights recommended method

---

### Locking Down Your Server (Step-by-Step)

#### Step 1: Edit `.env` file

```bash
# Keep OAuth infrastructure (for existing components)
MCP_OAUTH_ENABLED=true

# Disable OAuth registration and authorization
MCP_OAUTH_ALLOW_CLIENT_REGISTRATION=false
MCP_OAUTH_ALLOW_AUTHORIZATION=false

# Set your API key (only way to authenticate)
MCP_API_KEY=mcp-7239472398472394243972398

# Disable anonymous access
MCP_ALLOW_ANONYMOUS_ACCESS=false
```

#### Step 2: Restart the service

```bash
sudo systemctl restart mcp-memory-service

# Or if running directly:
uv run memory server
```

#### Step 3: Verify security

**Check server logs:**

```bash
journalctl -u mcp-memory-service -n 30 | grep -i oauth
```

**You should see:**

```
OAuth client registration allowed: False
OAuth authorization flow allowed: False
OAuth client registration endpoint DISABLED (security)
OAuth authorization endpoint DISABLED (security)
```

**Test login page:**

Visit: `http://192.168.1.30:8000/oauth-login.html`

**You'll see:**

```
🔒 Secure Mode
OAuth registration is disabled. Use your API key to authenticate.

[🔑 API Key Authentication (Recommended)]
```

✅ Option 1 (Auto Register) - **HIDDEN**  
✅ Option 2 (Manual Flow) - **HIDDEN**  
✅ Option 3 (API Key) - **VISIBLE**

---

### Security Verification Tests

#### Test 1: OAuth Registration Disabled

```bash
curl -X POST http://192.168.1.30:8000/oauth/register \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Test", "redirect_uris": ["http://localhost:3000"]}'
```

**Expected:** `{"detail":"Not Found"}` (404) ✅

#### Test 2: OAuth Authorization Disabled

```bash
curl "http://192.168.1.30:8000/oauth/authorize?response_type=code&client_id=test"
```

**Expected:** `{"detail":"Not Found"}` (404) ✅

#### Test 3: API Key Works

```bash
curl http://192.168.1.30:8000/api/health/detailed \
  -H "Authorization: Bearer YOUR-API-KEY-HERE"
```

**Expected:** Success response with health data ✅

---

### Configuration Reference

#### Environment Variables

| Variable                                | Default | Description                |
| --------------------------------------- | ------- | -------------------------- |
| `MCP_OAUTH_ENABLED`                     | `true`  | Master OAuth switch        |
| `MCP_OAUTH_ALLOW_CLIENT_REGISTRATION`   | `true`  | Allow new OAuth clients    |
| `MCP_OAUTH_ALLOW_AUTHORIZATION`         | `true`  | Allow OAuth auth flow      |
| `MCP_API_KEY`                           | None    | API key for authentication |
| `MCP_ALLOW_ANONYMOUS_ACCESS`            | `false` | Allow no authentication    |
| `MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`    | Token validity (minutes)   |

#### Production Setup Template

```bash
# ============================================
# Production Security Configuration
# ============================================

# OAuth Security
MCP_OAUTH_ENABLED=true
MCP_OAUTH_ALLOW_CLIENT_REGISTRATION=false
MCP_OAUTH_ALLOW_AUTHORIZATION=false

# API Key (generate with: python -c "import secrets; print(f'mcp-{secrets.token_hex(32)}')")
MCP_API_KEY=mcp-your-secure-key-here

# Security
MCP_ALLOW_ANONYMOUS_ACCESS=false

# HTTPS (highly recommended)
MCP_HTTPS_ENABLED=true
MCP_HTTPS_CERT_FILE=/path/to/fullchain.pem
MCP_HTTPS_KEY_FILE=/path/to/privkey.pem

# OAuth Issuer (for production)
MCP_OAUTH_ISSUER=https://api.yourdomain.com

# Token Expiration
MCP_OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

### Re-Enable OAuth (If Needed)

To re-enable all authentication methods:

```bash
# .env
MCP_OAUTH_ALLOW_CLIENT_REGISTRATION=true
MCP_OAUTH_ALLOW_AUTHORIZATION=true

# Restart
sudo systemctl restart mcp-memory-service
```

---

## Authentication Methods

### Available Options

The login page (`/oauth-login.html`) offers up to 3 authentication methods, depending on your security configuration.

---

---

## ⚙️ Technical Implementation

### What Was Implemented (v8.9.0+)

#### New Configuration Options

Two new environment variables provide granular security control:

```python
# src/mcp_memory_service/config.py
OAUTH_ALLOW_CLIENT_REGISTRATION = safe_get_bool_env('MCP_OAUTH_ALLOW_CLIENT_REGISTRATION', True)
OAUTH_ALLOW_AUTHORIZATION = safe_get_bool_env('MCP_OAUTH_ALLOW_AUTHORIZATION', True)
```

#### Backend Router Control

OAuth endpoints are conditionally loaded based on configuration:

```python
# src/mcp_memory_service/web/app.py
if OAUTH_ALLOW_CLIENT_REGISTRATION:
    app.include_router(oauth_registration_router)  # /oauth/register
else:
    logger.info("OAuth client registration endpoint DISABLED (security)")

if OAUTH_ALLOW_AUTHORIZATION:
    app.include_router(oauth_authorization_router)  # /oauth/authorize, /oauth/token
else:
    logger.info("OAuth authorization endpoint DISABLED (security)")
```

**Security Guarantee:** Disabled endpoints are NOT loaded - they return `404`, not `401` or `403`.

#### Authentication Configuration API

New endpoint tells frontend which authentication methods are available:

**Endpoint:** `GET /api/auth/config`

**Response:**

```json
{
  "available_methods": [
    {
      "id": "api_key",
      "name": "API Key Authentication",
      "description": "Login with pre-configured API key",
      "enabled": true,
      "recommended": true
    }
  ],
  "oauth_enabled": true,
  "api_key_enabled": true,
  "anonymous_access_allowed": false
}
```

#### Frontend Dynamic UI

Login page (`/oauth-login.html`) automatically:

- Calls `/api/auth/config` on load
- Hides disabled authentication options
- Updates UI messages based on server configuration
- Highlights recommended authentication method

### Files Modified

1. **`src/mcp_memory_service/config.py`**

   - Added `OAUTH_ALLOW_CLIENT_REGISTRATION`
   - Added `OAUTH_ALLOW_AUTHORIZATION`
   - Added logging for security settings

2. **`src/mcp_memory_service/web/app.py`**

   - Conditional OAuth router loading
   - Security-aware endpoint registration

3. **`src/mcp_memory_service/web/static/oauth-login.html`**
   - Dynamic authentication method detection
   - Adaptive UI based on server configuration

### Files Created

- **`src/mcp_memory_service/web/api/auth_config.py`** - Configuration endpoint

### Architecture

**Before (v8.9.0):**

```
FastAPI App
├── /oauth/register (always loaded)
├── /oauth/authorize (always loaded)
├── /oauth/token (always loaded)
└── API Key Auth (always available)

→ Anyone can register OAuth clients
→ Anyone can authenticate via OAuth
```

**After (v8.9.0+ with security config):**

```
FastAPI App
├── /oauth/register (NOT LOADED - returns 404)
├── /oauth/authorize (NOT LOADED - returns 404)
├── /oauth/token (NOT LOADED - returns 404)
├── /api/auth/config (NEW - tells UI what's available)
└── API Key Auth (only authentication method)

→ Only users with API key can authenticate
→ OAuth endpoints truly disabled (not just protected)
→ Frontend adapts automatically
```

---

**Built with ❤️ for MCP Memory Service v8.9.0+**

_Secure by default, flexible when needed_

---

**Version:** 8.9.0+  
**Last Updated:** October 28, 2025  
**Security Features:** OAuth granular controls, backend endpoint disabling, dynamic frontend adaptation
