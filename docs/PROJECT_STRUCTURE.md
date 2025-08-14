# OneMinuta Project Structure

Clean and organized file structure for easy navigation and maintenance.

## 📁 Root Directory (Clean & Essential)

```
├── run_bot.py                    # 🚀 Main Telegram bot launcher
├── oneminuta_cli.py              # 🖥️ CLI interface  
├── oneminuta                     # 🔧 CLI wrapper script (executable)
├── setup.py                      # 📦 Package setup
├── README.md                     # 📖 Main documentation
├── requirements.txt              # 📦 Python dependencies
└── pyproject.toml                # 📦 Modern Python packaging
```

## 📁 Core Directories

### `/services/` - Core Business Logic
```
├── core/                        # 🏗️ Core models and schemas
├── chatbot/                     # 🤖 AI chatbot system (86.7% accuracy)
├── analytics/                   # 📊 Client behavior analysis
├── collector/                   # 🔍 Property data collection
└── api/                         # 🌐 API endpoints
```

### `/scripts/` - Utilities & Tools
```
├── telegram/                    # 📱 Telegram bot scripts
│   ├── run_telegram_bot_channels.py  # Channel integration bot
│   ├── run_telegram_bot.py           # Basic bot
│   └── get_channel_id.py             # Utility tools
├── analytics/                   # 📈 Analytics scripts  
├── install-hooks.sh             # ⚙️ Git hooks installer
└── run_tests.sh                 # 🧪 Test runner
```

### `/docs/` - Documentation
```
├── telegram/                    # 📱 Telegram bot docs
│   ├── README_BOT.md
│   └── TELEGRAM_COMMANDS.md
├── testing/                     # 🧪 Testing documentation
│   └── TEST_RESULTS.md
├── CHATBOT.md                   # 🤖 Chatbot documentation
├── GIT_HOOKS.md                 # 🔒 Git hooks guide
└── [other technical docs]
```

### `/tests/` - Test Suite
```
├── chatbot/                     # 🤖 Chatbot tests (86.7% accuracy)
├── integration/                 # 🔗 Integration tests
├── unit/                        # ⚙️ Unit tests
├── fixtures/                    # 📋 Test data & fixtures
│   ├── geo/                     # Sample geo data
│   ├── users/                   # Mock user profiles  
│   └── chatbot_sessions/        # Test chat sessions
└── run_all_tests.py             # 🧪 Test runner
```

### `/storage/` - Production Data (Clean)
```
├── analytics/                   # 📊 Real client analytics
├── chatbot/                     # 🤖 Live chat sessions
├── geo/                         # 🗺️ Production geo index
├── users/                       # 👥 Real user data
└── config/                      # ⚙️ Runtime configuration
```

## 🧹 What Was Cleaned Up

### ❌ Before (Messy):
- `README_BOT.md`, `TELEGRAM_COMMANDS.md`, `TEST_RESULTS.md` in root
- `install-hooks.sh`, `run_tests.sh` in root
- `*.session` files scattered everywhere
- Analytics scripts mixed with telegram scripts
- `specs/schemas/models.py` - orphaned schema file
- `test_storage/` mixed with production storage
- Unused service folders (`indexer/`, `notifier/`, `parser/`)

### ✅ After (Organized):
- 📁 All docs in `/docs/` with subcategories
- 📁 All scripts in `/scripts/` by purpose
- 📁 Session files in proper storage locations
- 📁 Core models in `/services/core/`
- 📁 Test data in `/tests/fixtures/`
- 📁 Clean production `/storage/`
- 📁 Only active services maintained

## 🚀 Quick Commands

```bash
# Run bot
python3 run_bot.py

# Install git hooks  
./scripts/install-hooks.sh

# Run tests
./scripts/run_tests.sh

# Get channel ID
python3 scripts/telegram/get_channel_id.py
```

## 🎯 Benefits

- ✅ **Clean root** - Only essential files visible
- ✅ **Logical grouping** - Related files together
- ✅ **Easy navigation** - Clear folder structure
- ✅ **Maintainable** - New files have obvious homes
- ✅ **Professional** - Production-ready organization