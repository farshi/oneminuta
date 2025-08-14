# OneMinuta Chatbot Testing Guide

Comprehensive testing framework for the OneMinuta smart chatbot system, focusing on natural language processing accuracy and real-world user interactions.

## Testing Overview

The testing system validates:
- **Natural Language Processing** - Accuracy of extracting structured data from user messages
- **User Profile Detection** - Correct identification of user types and intents
- **Requirements Collection** - Proper extraction of property search criteria
- **Language Detection** - English/Russian language identification
- **End-to-End Conversations** - Complete conversation flows with real users

## Quick Start

### 1. Basic Structure Tests (No API Required)
```bash
# Test imports and basic functionality
python test_chatbot_structure.py

# Test language detection
python run_nlp_tests.py
```

### 2. NLP Extraction Tests (Requires OpenAI API)
```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-proj-your-key-here"

# Run comprehensive NLP accuracy tests
python run_nlp_tests.py

# Run specific test categories
python tests/chatbot/test_nlp_extraction.py --test-type profile
python tests/chatbot/test_nlp_extraction.py --test-type requirements
python tests/chatbot/test_nlp_extraction.py --test-type language
```

### 3. Telegram Bot Testing (Requires Bot Setup)
```bash
# Set required environment variables
export TELEGRAM_API_ID="your_api_id"
export TELEGRAM_API_HASH="your_api_hash"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export OPENAI_API_KEY="your_openai_key"

# Start Telegram bot for testing with @rezztelegram
python start_telegram_chatbot_test.py
```

## Test Categories

### 1. Language Detection Tests ✅
Tests automatic detection of English vs Russian languages.

**Test Coverage:**
- Pure English messages
- Pure Russian messages  
- Mixed language messages
- Edge cases (numbers, empty strings)

**Current Results:** 90.9% accuracy (10/11 tests passed)

**Example Test Cases:**
```python
"Hello, I'm looking for property" → "en" ✅
"Привет, ищу квартиру" → "ru" ✅
"Hello привет" → Should be "en" but detected "ru" ❌
```

### 2. User Profile Detection Tests
Tests identification of user types and intents from initial messages.

**Categories Tested:**
- **User Types**: buyer, seller, agent, investor
- **Intents**: search, sell, invest, browse
- **Languages**: English, Russian
- **Edge Cases**: Vague messages, numbers

**Test Examples:**
```python
# English Buyer
"Hi, I'm looking for a condo in Phuket"
Expected: {user_type: "buyer", intent: "search", language: "en"}

# Russian Seller  
"Хочу продать свою квартиру"
Expected: {user_type: "seller", intent: "sell", language: "ru"}

# Agent
"I'm a real estate agent, need access to properties"
Expected: {user_type: "agent", intent: "browse", language: "en"}
```

### 3. Requirements Extraction Tests
Tests extraction of structured property requirements from natural language.

**Fields Tested:**
- **Property Type**: condo, villa, house, townhouse, apartment
- **Location**: Specific areas, cities, regions
- **Transaction Type**: rent, sale, both
- **Budget**: min/max price ranges with currency
- **Features**: bedrooms, bathrooms, furnished status
- **Special Requirements**: Custom features

**Complex Test Examples:**
```python
# Comprehensive English
"Need unfurnished 2-bed 2-bath condo for rent in Kata, budget 20k-35k THB monthly"
Expected: {
    property_type: "condo",
    location_preference: "Kata", 
    rent_or_sale: "rent",
    budget_min: 20000,
    budget_max: 35000,
    bedrooms: 2,
    bathrooms: 2,
    furnished: false
}

# Russian with currency
"Ищу квартиру в аренду в Бангкоке, 1 спальня, до 25000 батов"
Expected: {
    property_type: "apartment",
    location_preference: "Бангкоке",
    rent_or_sale: "rent", 
    budget_max: 25000,
    bedrooms: 1
}
```

### 4. End-to-End Conversation Tests
Tests complete conversation flows from greeting to property matching.

**Test Scenarios:**
- **English Buyer Journey**: Condo search in Phuket
- **Russian Investor Journey**: Villa investment search
- **Seller Journey**: House listing process
- **Agent Journey**: Platform access and features

## Telegram Bot Testing

### Setup Requirements

1. **Create Telegram Bot**:
   - Message @BotFather on Telegram
   - Create new bot with `/newbot`
   - Get bot token

2. **Get Telegram API Credentials**:
   - Visit https://my.telegram.org
   - Create application
   - Get API ID and hash

3. **Environment Variables**:
   ```bash
   export TELEGRAM_API_ID="12345678"
   export TELEGRAM_API_HASH="abcdef1234567890abcdef1234567890"
   export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
   export OPENAI_API_KEY="sk-proj-your-key-here"
   ```

### Testing with @rezztelegram

1. **Start Test Bot**:
   ```bash
   python start_telegram_chatbot_test.py
   ```

2. **Bot Commands for Testing**:
   - `/start` - Begin testing session
   - `/reset` - Reset conversation state
   - `/stats` - View session statistics
   - `/test` - Run automated test scenarios

3. **Test Conversations**:
   ```
   @rezztelegram: Hi, I'm looking for a condo in Phuket
   Bot: Welcome! I'd love to help you find the perfect condo in Phuket...
   
   @rezztelegram: My budget is 30,000 THB per month
   Bot: Perfect! So you're looking for a condo for rent in Phuket...
   
   @rezztelegram: 2 bedrooms, furnished would be great
   Bot: Excellent! Let me search for furnished 2-bedroom condos...
   ```

### Test Logging

All interactions are logged for analysis:
- **Session Logs**: `storage/chatbot/test_logs/test_session_YYYY-MM-DD.ndjson`
- **Bridge Logs**: `storage/chatbot/telegram_bridge.log`
- **Test Results**: `storage/chatbot/test_results/`

**Log Entry Example**:
```json
{
  "timestamp": "2025-08-14T10:30:00Z",
  "user_id": "@rezztelegram", 
  "event_type": "chatbot_interaction",
  "data": {
    "user_message": "I need a 2-bedroom condo",
    "bot_reply": "Great! What's your budget range?",
    "stage": "inquiry-collection",
    "confidence": 0.85,
    "data_collected": {"bedrooms": 2, "property_type": "condo"}
  }
}
```

## Test Results Analysis

### Success Criteria

**Language Detection**: ≥90% accuracy
- Current: 90.9% ✅

**Profile Detection**: ≥80% accuracy
- Tests user type, intent, and language identification
- Requires OpenAI API for full testing

**Requirements Extraction**: ≥70% accuracy  
- Tests extraction of structured data from natural language
- Most critical for user experience

**End-to-End Conversations**: ≥85% completion rate
- Users should successfully complete property search
- Measured through Telegram bot testing

### Improving Test Results

**For Language Detection**:
- Tune Cyrillic character threshold (currently 30%)
- Add more sophisticated language detection libraries
- Handle mixed-language messages better

**For Profile/Requirements Extraction**:
- Refine OpenAI prompts for better accuracy
- Add more training examples
- Implement confidence thresholds
- Add fallback mechanisms

**For Conversation Flow**:
- Monitor real user interactions
- Identify common failure points
- Improve error handling and recovery

## Automated Testing

### Continuous Integration
```bash
# Add to CI pipeline
python test_chatbot_structure.py  # Always run
python run_nlp_tests.py           # If OPENAI_API_KEY available
```

### Performance Benchmarks
- Language detection: <10ms
- Profile detection: <3s (with OpenAI API)
- Requirements extraction: <3s (with OpenAI API)
- Property search integration: <100ms

### Monitoring Alerts
Set up alerts for:
- NLP accuracy dropping below thresholds
- API response time increases
- User conversation abandonment rates
- Error rates in production

## Troubleshooting

### Common Issues

**"Import Error" when running tests**:
```bash
pip install openai telethon
```

**"No OpenAI API key" warnings**:
```bash
export OPENAI_API_KEY="your-key-here"
```

**Telegram bot not responding**:
- Check bot token is correct
- Verify API credentials
- Ensure bot is not already running elsewhere

**Low NLP accuracy scores**:
- Check OpenAI API quota and limits
- Verify prompts are not hitting token limits
- Consider using different model (gpt-4 vs gpt-3.5-turbo)

### Debug Mode

Enable verbose logging:
```bash
export CHATBOT_DEBUG=true
python start_telegram_chatbot_test.py
```

Shows:
- Detailed API requests/responses
- Stage transition decisions
- Confidence scores
- Extracted data structures

## Production Readiness

### Quality Gates

Before production deployment:
- [ ] Language detection ≥90% accuracy
- [ ] Profile detection ≥80% accuracy  
- [ ] Requirements extraction ≥70% accuracy
- [ ] End-to-end conversations ≥85% completion
- [ ] Error handling covers all edge cases
- [ ] Performance meets benchmarks
- [ ] Security review completed

### Monitoring Setup

In production, monitor:
- Conversation completion rates
- User satisfaction scores
- NLP extraction accuracy
- API response times
- Error rates by stage
- Language distribution
- User type distribution

This comprehensive testing framework ensures the OneMinuta chatbot provides reliable, accurate, and user-friendly property search assistance.