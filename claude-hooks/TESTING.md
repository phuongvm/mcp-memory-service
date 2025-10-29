# Manual Testing Guide for Claude Code Memory Hooks

This guide shows you how to manually test the memory hooks before using them in Claude Code.

## Quick Test Methods

### Method 1: Direct Execution (Built-in Test Mode)

Both hooks have built-in test support when run directly:

#### Test Session Start Hook

```powershell
cd C:\Users\phuong\.claude\hooks
node core\session-start.js
```

This will:

- Detect your current project
- Try to connect to the memory service
- Show what memories would be injected
- Display the formatted context that would be sent to Claude

#### Test Session End Hook

```powershell
cd C:\Users\phuong\.claude\hooks
node core\session-end.js
```

This will:

- Use mock conversation data
- Analyze the session
- Show what would be stored
- Test the consolidation process

### Method 2: Test from Project Directory

To test with a real project context, navigate to your project directory first:

```powershell
# Navigate to your actual project
cd o:\workspaces\mcp-memory-service

# Then run the hook
node C:\Users\phuong\.claude\hooks\core\session-start.js
```

This will detect the actual project (mcp-memory-service) and fetch relevant memories for it.

### Method 3: Using Test Scripts

#### Integration Tests

```powershell
cd C:\Users\phuong\.claude\hooks
node tests\integration-test.js
```

Runs 14 comprehensive tests including:

- Project detection
- Memory scoring
- Configuration loading
- Hook structure validation
- Memory service connectivity

#### Natural Memory Triggers Tests

```powershell
cd C:\Users\phuong\.claude\hooks
node test-natural-triggers.js
```

Tests the mid-conversation hook with pattern detection.

### Method 4: Test with Specific Configuration

You can test with different endpoints or configurations:

```powershell
# Set environment variables before running
$env:MCP_MEMORY_ENDPOINT="https://memory.ptdev.vip"
$env:MCP_API_KEY="your-api-key"
node core\session-start.js
```

### Method 5: Test Memory Connection Only

Test if the memory service is reachable:

```powershell
node -e "const https = require('https'); const url = new URL('https://memory.ptdev.vip/api/health'); const options = { hostname: url.hostname, port: 443, path: url.pathname, method: 'GET', timeout: 5000, rejectUnauthorized: false }; const req = https.request(options, (res) => { console.log('Status:', res.statusCode); res.on('data', (d) => process.stdout.write(d)); }); req.on('error', (e) => console.error('Error:', e.message)); req.end();"
```

## Expected Outputs

### Successful Session Start Test

- ✅ Project detected
- ✅ Storage backend identified
- ✅ Memory queries executed
- ✅ Formatted context displayed (if memories found)

### Successful Session End Test

- ✅ Session analysis completed
- ✅ Topics and decisions extracted
- ✅ Memory stored successfully with hash

## Troubleshooting

### "No active connection available"

- Check your `config.json` endpoint: `https://memory.ptdev.vip`
- Verify the memory service is running
- Check network connectivity
- Confirm API key is correct

### "Failed to connect"

- Verify the endpoint URL is correct
- Check if firewall is blocking HTTPS (port 443)
- Ensure the memory service is accessible

### "No relevant memories found"

- This is normal if your memory database is empty
- The hook still works, just no memories to inject
- Start storing memories by using Claude Code sessions

## Testing in Real Claude Code Sessions

Once manual tests pass, the hooks will automatically:

- **Session Start**: Inject memories when Claude Code starts
- **Session End**: Store session outcomes automatically
- **Mid-Conversation**: Trigger memory injection during conversations (if enabled)

No additional setup needed - just start using Claude Code!
