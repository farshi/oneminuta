# OneMinuta Tests

Organized test suite for the OneMinuta property marketplace system.

## Test Structure

```
tests/
├── README.md                      # This file
├── run_all_tests.py              # Main test runner
├── setup_chatbot_testing.py      # Setup script for testing environment
│
├── chatbot/                      # Chatbot-specific tests
│   ├── test_chatbot_structure.py # Structure and import tests
│   ├── test_chatbot_mock.py      # Mock conversation flow tests
│   ├── test_chatbot.py           # Full chatbot integration test
│   ├── run_nlp_tests.py          # NLP extraction accuracy tests
│   └── test_nlp_extraction.py    # Detailed NLP test cases
│
├── integration/                  # Integration tests
│   └── start_telegram_chatbot_test.py  # Telegram bot integration
│
└── unit/                        # Unit tests
    ├── analytics/               # Analytics module tests
    ├── collector/              # Property collector tests
    └── geo-spherical/          # Geo-sharding tests
```

## Quick Start

### Run All Tests
```bash
cd tests
python run_all_tests.py --category all
```

### Run Quick Tests (No API Required)
```bash
python run_all_tests.py --category quick
```

### Run Specific Category
```bash
python run_all_tests.py --category chatbot
python run_all_tests.py --category unit
python run_all_tests.py --category integration
```

## Test Categories

### 1. Chatbot Tests (`tests/chatbot/`)

#### Structure Test
Tests imports, initialization, and basic structure.
```bash
python chatbot/test_chatbot_structure.py
```

#### Mock Test
Tests conversation flow without external APIs.
```bash
python chatbot/test_chatbot_mock.py
```

#### NLP Extraction Test
Tests natural language processing accuracy with OpenAI API.
```bash
python chatbot/run_nlp_tests.py
```
**Requires**: `OPENAI_API_KEY` in .env file

#### Full Chatbot Test
End-to-end chatbot conversation test.
```bash
python chatbot/test_chatbot.py
```
**Requires**: `OPENAI_API_KEY` in .env file

### 2. Integration Tests (`tests/integration/`)

#### Telegram Bot Test
Tests chatbot integration with Telegram for real user testing.
```bash
python integration/start_telegram_chatbot_test.py
```
**Requires**: 
- `TELEGRAM_API_ID` in .env file
- `TELEGRAM_API_HASH` in .env file
- `TELEGRAM_BOT_TOKEN` in .env file
- `OPENAI_API_KEY` in .env file

### 3. Unit Tests (`tests/unit/`)

Run all unit tests with pytest:
```bash
pytest unit/ -v
```

## Environment Setup

1. **Install dependencies:**
   ```bash
   pip install openai telethon pytest python-dotenv
   ```

2. **Configure .env file:**
   ```env
   # Required for chatbot tests
   OPENAI_API_KEY=your_openai_key
   LLM_MODEL=gpt-4o-mini
   
   # Required for Telegram integration
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   
   # Storage configuration
   STORAGE_PATH=./storage
   ```

3. **Run setup script:**
   ```bash
   python setup_chatbot_testing.py
   ```

## Test Results

### Current Test Status

| Test Category | Tests | Pass Rate | Status |
|--------------|-------|-----------|---------|
| Structure | 4 | 100% | ✅ Passing |
| Language Detection | 11 | 90.9% | ✅ Passing |
| NLP Extraction | 30 | 86.7% | ✅ Passing |
| Mock Conversation | 4 | 100% | ✅ Passing |
| Unit Tests | Various | TBD | 🔄 In Progress |

### Performance Benchmarks

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Language Detection | <10ms | <1ms | ✅ Excellent |
| Session Operations | <50ms | <10ms | ✅ Excellent |
| Property Search | <100ms | 3.7ms | ✅ Excellent |
| NLP Extraction | <3s | ~2s | ✅ Good |

## Test Output

Test results are saved to:
- NLP test results: `storage/chatbot/test_results/`
- Session logs: `storage/chatbot/sessions/`
- Telegram test logs: `storage/chatbot/test_logs/`

## Continuous Integration

Add to your CI pipeline:
```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    python tests/run_all_tests.py --category quick
    
- name: Run Full Tests
  if: github.event_name == 'push'
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    python tests/run_all_tests.py --category all
```

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the project root
cd /path/to/oneminuta
python tests/run_all_tests.py
```

### API Key Issues
```bash
# Check if .env is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:20] if os.getenv('OPENAI_API_KEY') else 'Not found')"
```

### Telegram Bot Not Responding
1. Check bot token is correct
2. Verify API credentials
3. Ensure bot is not already running

## Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Import project modules using:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   ```
4. Add test to appropriate category in `run_all_tests.py`