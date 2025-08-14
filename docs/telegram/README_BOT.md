# OneMinuta Telegram Bot

OneMinuta AI property search assistant for Telegram with channel integration.

## Quick Start

```bash
# Run the bot
python3 run_bot.py
```

## Features

- 🤖 **AI-powered conversations** - 86.7% NLP accuracy
- 🏠 **Property search** - Condos, villas, apartments
- 🌐 **Multi-language** - English & Russian
- 📢 **Channel integration** - Auto-greet new channel members
- 📊 **Analytics** - Track user conversations and leads

## Bot Commands

- `/start` - Start conversation
- `/join` - Test channel join experience (demo)
- `/reset` - Reset conversation
- `/stats` - View your activity  
- `/channels` - Partner channels info
- `/help` - Full help

## Configuration

Bot reads from `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4o-mini
STORAGE_PATH=./storage
```

## Channel Integration

The bot automatically welcomes new members who join partner channels:

1. Add @OneMinutaBot as admin to your channel
2. Configure channel in `scripts/telegram/run_telegram_bot_channels.py`
3. New members get personalized welcome DMs

### Current Channels
- @oneminuta_property (ID: -1002875386834)

## File Structure

```
├── run_bot.py                          # Main launcher
├── scripts/telegram/
│   ├── run_telegram_bot_channels.py    # Channel integration bot
│   ├── run_telegram_bot.py             # Basic bot
│   └── get_channel_id.py               # Utility to get channel IDs
├── services/chatbot/                   # Core chatbot logic
└── tests/integration/telegram/         # Test utilities
```

## Testing

Test channel join experience without real users:
```bash
# In Telegram, message @OneMinutaBot:
/start
/join
```

This simulates the exact experience new channel members receive.