# Telegram Integration Tests

This directory contains test utilities for testing OneMinuta with real Telegram interactions.

## chatbot_bridge.py

**Purpose**: A TEST UTILITY that creates a Telegram bot for testing the OneMinuta chatbot with real users.

### What it does:

1. **Creates a Test Bot** - Sets up a Telegram bot specifically for testing purposes
2. **Restricts Access** - Only allows authorized users (like @rezztelegram) to interact
3. **Bridges to Chatbot** - Connects Telegram messages to OneMinuta's chatbot system
4. **Logs Interactions** - Records all test conversations for analysis
5. **Provides Test Commands**:
   - `/start` - Begin a test conversation
   - `/reset` - Reset the conversation state
   - `/stats` - View session statistics
   - `/test` - Run automated test scenarios

### Why it's in tests folder:

- ✅ **Test-only functionality** - Not part of production system
- ✅ **Authorized users only** - Restricted to test users like @rezztelegram
- ✅ **Logging for analysis** - Saves test logs for debugging
- ✅ **Manual testing tool** - Used for quality assurance, not production

### How to use:

1. **Set up environment variables in .env:**
   ```env
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   OPENAI_API_KEY=your_openai_key
   ```

2. **Run the test bridge:**
   ```bash
   python tests/integration/start_telegram_chatbot_test.py
   ```

3. **Test with Telegram:**
   - Open Telegram
   - Message the bot as @rezztelegram
   - Send `/start` to begin testing
   - Have a conversation to test the chatbot
   - Check logs in `storage/chatbot/test_logs/`

### Test Logging:

All interactions are logged to:
- `storage/chatbot/test_logs/test_session_YYYY-MM-DD.ndjson`
- `storage/chatbot/telegram_bridge.log`

Each log entry contains:
- User message
- Bot response
- Conversation stage
- Confidence scores
- Extracted data
- Timestamps

### Security:

- Only authorized users can interact (default: @rezztelegram)
- Test bot token should never be used in production
- Logs may contain sensitive test data - keep secure

## Other Test Files:

- `test_channel_access.py` - Tests accessing Telegram channels
- `test_realtime_monitor.py` - Tests real-time message monitoring
- `test_telegram_channels.py` - Tests channel listing and access

All these files are TEST UTILITIES and should not be used in production.