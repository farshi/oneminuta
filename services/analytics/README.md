# OneMinuta Telegram Analytics

Real-time analysis of Telegram property channels to identify hot clients.

## 📁 Project Structure

```
oneminuta/
├── services/analytics/     # Core analytics modules
│   ├── telegram_monitor.py # Telegram channel monitoring
│   ├── client_analyzer.py  # Client scoring & analysis
│   ├── llm_analyzer.py     # AI-powered analysis
│   ├── session_manager.py  # Session management
│   └── config.py           # Configuration
│
├── scripts/                # Utility scripts
│   ├── analyze_channels_only.py
│   ├── authenticate_telegram_once.py
│   ├── debug_channel_messages.py
│   └── debug_telegram.py
│
├── tests/                  # Test files
│   ├── test_channel_access.py
│   ├── test_realtime_monitor.py
│   └── test_final_analysis.py
│
├── examples/               # Demo & example scripts
│   ├── demo_analytics_results.py
│   └── demo_telegram_monitoring.py
│
├── docs/                   # Documentation
│   ├── PRODUCTION_SETUP.md
│   ├── TELEGRAM_SETUP.md
│   └── CLI_SPEC.md
│
├── storage/               # Data storage
│   ├── analytics/         # Analysis results
│   └── config/            # Runtime configs
│
├── sessions/              # Telegram session files
│
└── .env                  # Environment variables
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy and edit .env file
cp .env.example .env
# Add your Telegram API credentials
```

### 2. Authenticate (One Time Only)

```bash
python scripts/authenticate_telegram_once.py
```

This creates a persistent session - you only need to do this once!

### 3. Analyze Channels

```bash
# Analyze last 3 days (default)
python scripts/analyze_channels_only.py

# Analyze last 7 days
python scripts/analyze_channels_only.py --days-back 7
```

## 🔧 Main Commands

| Command | Description |
|---------|-------------|
| `python scripts/authenticate_telegram_once.py` | One-time Telegram authentication |
| `python scripts/analyze_channels_only.py` | Analyze channels for hot clients |
| `python oneminuta_cli.py` | Main CLI interface |
| `python tests/test_channel_access.py` | Test channel access |
| `python scripts/debug_channel_messages.py` | Debug message filtering |

## 📊 Features

- **AI-Powered Analysis**: Uses GPT to analyze client intent
- **Smart Filtering**: Filters out owner/promotional messages
- **Hotness Scoring**: Scores clients from 0-100
- **Multi-language**: Supports English and Russian
- **Real-time Monitoring**: Optional real-time message monitoring

## 🔥 Client Scoring

- **🔥 Burning (86-100)**: Urgent buyers, ready to act
- **⚡ Hot (61-85)**: Active searchers, high intent
- **🟡 Warm (31-60)**: Interested but not urgent
- **❄️ Cold (0-30)**: Passive browsers

## 📝 Configuration

Edit `services/analytics/config.py` or use environment variables:

```env
# Telegram API (required)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# OpenAI API (required)
OPENAI_API_KEY=your_openai_key

# Optional
LLM_MODEL=gpt-4o-mini
HOT_CLIENT_THRESHOLD=70.0
```

## 🛠️ Development

### Run Tests
```bash
python tests/test_channel_access.py
python tests/test_final_analysis.py
```

### Debug Messages
```bash
python scripts/debug_channel_messages.py
```

### Check Session
```bash
ls -la sessions/
```

## 📚 Documentation

- [Production Setup](docs/PRODUCTION_SETUP.md) - Deploy to production
- [Telegram Setup](docs/TELEGRAM_SETUP.md) - Telegram API setup
- [CLI Specification](docs/CLI_SPEC.md) - CLI command reference

## ⚠️ Important Notes

1. **Session Files**: Keep `sessions/` folder secure - contains auth keys
2. **Rate Limits**: Telegram has rate limits - avoid excessive requests
3. **Privacy**: Only analyzes public channels or channels you're member of
4. **Filtering**: Automatically filters out channel owner posts

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Database is locked" | Use `analyze_channels_only.py` instead of real-time monitor |
| "Not authorized" | Run `python scripts/authenticate_telegram_once.py` |
| "No messages found" | Check channel names in config, try longer time period |
| Multiple auth prompts | Use single session via authenticate_telegram_once.py |

## 📌 Configured Channels

Currently monitoring:
- @phuketgidsell
- @phuketgid
- @sabay_property

To change channels, edit `services/analytics/config.py`