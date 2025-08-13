# Production Setup for Telegram Monitoring

## Understanding Telegram Sessions

Telegram uses **session files** to maintain authentication:
- A `.session` file is created after first authentication
- Contains encrypted auth keys and server configuration  
- **Reusable** - authenticate once, use forever (until revoked)
- **One session per app** - multiple session names = multiple auth requests

## Problem You're Facing

You keep getting auth requests because:
1. Different scripts use different session names
2. Session files get locked when multiple scripts run
3. No centralized session management

## Production Solution

### Step 1: One-Time Authentication

Run this ONCE to create your production session:

```bash
python authenticate_telegram_once.py
```

This will:
- Create a persistent session in `./sessions/oneminuta_prod.session`
- Ask for your phone number and verification code ONCE
- Save the session for all future use

### Step 2: Use Session Manager in Scripts

All scripts should use the session manager to avoid re-authentication:

```python
from services.analytics.session_manager import get_session_manager

# Get shared session manager
manager = get_session_manager()
client = await manager.get_client()

# Use client for operations
# ...

# Cleanup
await manager.disconnect()
```

### Step 3: Production Deployment

For production, you should:

1. **Authenticate locally first**:
   ```bash
   python authenticate_telegram_once.py
   ```

2. **Copy session to production server**:
   ```bash
   scp sessions/oneminuta_prod.session user@server:/app/sessions/
   ```

3. **Set permissions**:
   ```bash
   chmod 600 sessions/oneminuta_prod.session
   ```

4. **Use environment variables** for credentials:
   ```env
   TELEGRAM_API_ID=26818131
   TELEGRAM_API_HASH=85b2edabf016108450eb958ac80fa2d7
   ```

5. **Run with single session**:
   - All scripts use same session file
   - No re-authentication needed
   - No database locks

## Best Practices

### DO:
✅ Use one consistent session name  
✅ Authenticate once locally, copy to production  
✅ Keep session file secure (chmod 600)  
✅ Use session manager for all operations  
✅ Handle disconnections gracefully  

### DON'T:
❌ Create new session names for each script  
❌ Share session files publicly  
❌ Run multiple scripts with same session simultaneously  
❌ Delete session files unless necessary  

## Troubleshooting

### "Database is locked" error
**Cause**: Multiple scripts using same session file  
**Fix**: Use session manager with proper locking or run scripts sequentially

### "Not authorized" error
**Cause**: Session expired or revoked  
**Fix**: Re-run `python authenticate_telegram_once.py`

### "Session file corrupted"
**Cause**: Interrupted during write operation  
**Fix**: Delete session file and re-authenticate

## Docker/Container Setup

For containerized deployments:

```dockerfile
# Dockerfile
FROM python:3.9

# Create sessions directory
RUN mkdir -p /app/sessions

# Copy pre-authenticated session
COPY sessions/oneminuta_prod.session /app/sessions/

# Set permissions
RUN chmod 600 /app/sessions/oneminuta_prod.session

# Your app code
COPY . /app
WORKDIR /app

CMD ["python", "analyze_channels_only.py"]
```

## Security Notes

1. **Session files are sensitive** - contain auth keys
2. **Never commit to git** - add to .gitignore:
   ```
   *.session
   sessions/
   ```
3. **Rotate periodically** - revoke old sessions in Telegram settings
4. **Use read-only access** when possible - Telegram client API can read public channels without special permissions

## Summary

The key is to:
1. Authenticate ONCE with `authenticate_telegram_once.py`
2. Use the same session file for all scripts
3. Never create multiple session names
4. Copy session to production (don't re-auth on prod)