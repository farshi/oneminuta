# OneMinuta Code Organization

Clear separation between production code and test utilities.

## Production Code (`services/`)

Production-ready services that run the OneMinuta platform:

```
services/
├── analytics/              # User analytics and scoring
│   ├── llm_analyzer.py   # Production LLM analysis
│   ├── message_filter.py # Message filtering
│   └── telegram_monitor.py # Channel monitoring
│
├── chatbot/               # Production chatbot system
│   ├── chatbot_manager.py # Main chatbot orchestrator
│   ├── session_manager.py # Session persistence
│   └── stages/           # Conversation stages
│       ├── base_stage.py
│       ├── user_profile_detection.py
│       ├── smart_greeting.py
│       ├── inquiry_collection.py
│       └── property_matching.py
│
└── collector/             # Property collection
    ├── asset_manager.py  # Asset storage with geo-sharding
    └── property_extractor.py # Extract properties from text
```

## Test Code (`tests/`)

All test utilities, mocks, and testing tools:

```
tests/
├── chatbot/               # Chatbot-specific tests
│   ├── test_*.py         # Unit and integration tests
│   └── run_nlp_tests.py  # NLP accuracy testing
│
├── integration/           # Integration testing
│   ├── telegram/         # Telegram test utilities
│   │   ├── chatbot_bridge.py  # TEST BOT for @rezztelegram
│   │   └── test_*.py     # Telegram integration tests
│   └── analytics/        # Analytics integration tests
│
└── unit/                 # Unit tests
    ├── analytics/        # Analytics unit tests
    └── geo-spherical/    # Geo-sharding tests
```

## Key Differences

### Production Code (services/)
- ✅ Used in live system
- ✅ Handles real user data
- ✅ Must be secure and efficient
- ✅ No test users or debug logging
- ✅ Real API keys and production tokens

### Test Code (tests/)
- 🧪 Testing and QA only
- 🧪 May have debug logging
- 🧪 Restricted access (e.g., @rezztelegram only)
- 🧪 Mock data and test scenarios
- 🧪 Test API keys and bot tokens

## Why chatbot_bridge.py is in tests/

The `chatbot_bridge.py` file is a **TEST UTILITY** because:

1. **Test Bot Only** - Creates a Telegram bot specifically for testing
2. **Restricted Access** - Only allows test users like @rezztelegram
3. **Debug Logging** - Logs all interactions for analysis
4. **Test Commands** - Provides `/test` for automated scenarios
5. **Not for Production** - Should never handle real customer data

## Environment Variables

### Production (.env)
```env
# Production API keys
OPENAI_API_KEY=sk-proj-production-key
TELEGRAM_API_ID=production_id
TELEGRAM_API_HASH=production_hash
```

### Testing (.env.test)
```env
# Test API keys and bot tokens
TELEGRAM_BOT_TOKEN=test_bot_token  # Only for testing!
OPENAI_API_KEY=sk-proj-test-key
```

## Running Tests vs Production

### Production
```bash
# Start production services
python -m services.analytics.telegram_monitor

# Use production CLI
python oneminuta_cli.py search --lat 7.78 --lon 98.33
```

### Testing
```bash
# Run tests
./run_tests.sh all

# Start test bot (for @rezztelegram only)
python tests/integration/start_telegram_chatbot_test.py

# Run NLP accuracy tests
python tests/chatbot/run_nlp_tests.py
```

## Security Considerations

1. **Never mix test and production data**
2. **Test bots should have restricted access**
3. **Test logs may contain sensitive data - secure them**
4. **Use different API keys for testing vs production**
5. **chatbot_bridge.py should NEVER be used with production bot tokens**

## File Movement Summary

Files moved from production to tests:
- `services/telegram/chatbot_bridge.py` → `tests/integration/telegram/`
- Root test files → `tests/chatbot/`, `tests/integration/`

This ensures clear separation between production services and test utilities.