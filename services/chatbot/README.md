# OneMinuta Smart Chatbot

The OneMinuta Smart Chatbot provides intelligent, conversational property assistance through a multi-stage conversation system that guides users from initial inquiry to property matching.

## Features

- **Multi-Language Support**: English and Russian language detection and responses
- **Staged Conversations**: Four progressive stages for comprehensive requirement gathering
- **User Profiling**: Automatic detection of user type (buyer, seller, agent, investor)
- **Intelligent Requirements Collection**: Natural language processing of property preferences
- **Property Matching**: Integration with OneMinuta's geo-sharded property search system
- **Session Management**: Persistent conversation state with file-based storage

## Conversation Stages

### 1. User Profile Detection
- Analyzes initial message to determine user type and language
- Detects intent (search, sell, invest, browse) 
- Sets conversation tone and direction

### 2. Smart Greeting
- Provides personalized greeting based on detected profile
- Establishes rapport and sets expectations
- Transitions smoothly to requirements gathering

### 3. Inquiry Collection
- Systematically collects property requirements:
  - Property type (condo, villa, house, townhouse)
  - Location preferences
  - Budget range (rent or sale)
  - Bedroom/bathroom requirements
  - Special features (furnished, etc.)
- Asks intelligent follow-up questions
- Validates and structures collected data

### 4. Property Matching
- Searches OneMinuta's geo-sharded property database
- Presents matching properties in conversational format
- Provides property details and contact information
- Offers next steps (viewings, more details)

## Usage

### Command Line Interface

#### Interactive Chat Session
```bash
# Start interactive chatbot
oneminuta chat

# With specific OpenAI API key
oneminuta chat --openai-key sk-proj-...
```

#### Session Statistics
```bash
# View chatbot usage statistics
oneminuta chat-stats
```

#### Dedicated Chatbot CLI
```bash
# Interactive session
python services/chatbot/chatbot_cli.py chat

# Batch testing with scenarios
python services/chatbot/chatbot_cli.py test

# Session management
python services/chatbot/chatbot_cli.py stats
python services/chatbot/chatbot_cli.py cleanup --days 30
```

### Programmatic Usage

```python
import asyncio
from services.chatbot.chatbot_manager import OneMinutaChatbotManager

# Initialize chatbot
chatbot = OneMinutaChatbotManager(
    storage_path="./storage",
    openai_api_key="your-openai-key"
)

# Process user message
response = await chatbot.process_message(
    user_id="user_123",
    message="I'm looking for a condo in Phuket"
)

print(response['reply'])
print(f"Stage: {response['stage']}")
print(f"Properties found: {len(response.get('properties_found', []))}")
```

## Configuration

### Environment Variables
```bash
# Required for chatbot functionality
export OPENAI_API_KEY="sk-proj-your-key-here"

# Optional: Enable debug output
export CHATBOT_DEBUG=true
```

### Session Storage
- Sessions stored in: `storage/chatbot/sessions/`
- Format: `{user_id}.json`
- Automatic cleanup of inactive sessions (30+ days)
- Session archiving to `storage/chatbot/sessions/archived/`

## Example Conversations

### English Buyer
```
User: Hi, I'm looking for a condo in Phuket
Bot:  Welcome! I'd love to help you find the perfect condo in Phuket. To find you the best properties, I'd like to understand your preferences better. What's your budget range for the condo?

User: Around 30,000 THB per month for rent, 2 bedrooms
Bot:  Perfect! So you're looking for a 2-bedroom condo for rent in Phuket with a budget of 30,000 THB/month. Do you have any specific area preferences in Phuket, such as Rawai, Kata, or Patong?

User: Rawai would be great, preferably furnished
Bot:  Excellent! I now have all the information I need. Let me search for furnished 2-bedroom condos for rent in Rawai within your 30,000 THB budget - I think you'll be excited by what I find!

Bot:  Fantastic! I found 3 properties that match your requirements:

1. Modern Condo in Rawai (200m away)
   Rent: 28,000 THB/month
   2 bed, 1 bath, 65 sqm, furnished
   ID: user_456:prop_789
   
[Additional properties...]

Would you like more details about any of these properties?
```

### Russian Investor
```
User: Привет, ищу виллу для инвестиций
Bot:  Привет! Приятно встретить инвестора! Я помогу вам найти отличные инвестиционные возможности. Какой бюджетный диапазон вы рассматриваете для покупки виллы?

User: До 10 миллионов батов, предпочитаю Пхукет
Bot:  Отлично! Виллы в Пхукете до 10 миллионов батов - отличный выбор для инвестиций. Есть ли у вас предпочтения по количеству спален или особым характеристикам?

[Conversation continues...]
```

## Technical Architecture

### Components
- **ChatbotManager**: Main orchestrator for conversation flow
- **SessionManager**: Persistent session storage and management  
- **Stage Classes**: Individual conversation stage handlers
- **Property Integration**: Direct integration with OneMinutaCLI search

### Data Flow
1. User message → ChatbotManager
2. Load/create session → SessionManager
3. Process through current stage → StageHandler
4. Update session with results → SessionManager
5. Return structured response → User interface

### Error Handling
- Graceful degradation when OpenAI API unavailable
- Fallback responses for each stage
- Session recovery and cleanup
- Input validation and sanitization

## Performance

- **Session Loading**: < 10ms for file-based sessions
- **Stage Processing**: 1-3 seconds with OpenAI API calls
- **Property Search**: < 100ms using geo-sharded indexes
- **Memory Usage**: Minimal - sessions stored on disk

## Testing

### Unit Tests
```bash
# Test structure without API calls
python test_chatbot_structure.py

# Test with API (requires OPENAI_API_KEY)
python test_chatbot.py
```

### Integration Testing
```bash
# Batch conversation scenarios
python services/chatbot/chatbot_cli.py test
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Install OpenAI dependency
pip install openai>=1.0.0
```

**API Key Issues**
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API connectivity
python -c "import openai; print(openai.OpenAI().models.list().data[0].id)"
```

**Session Corruption**
```bash
# Clear specific user session
rm storage/chatbot/sessions/user_id.json

# Clear all sessions
rm storage/chatbot/sessions/*.json
```

### Debug Mode
```bash
export CHATBOT_DEBUG=true
python oneminuta_cli.py chat
```

Shows additional information:
- Stage transitions
- Data collection progress
- Confidence scores
- Property search results

## Roadmap

### Planned Features
- **Multi-modal Support**: Image and document analysis
- **Advanced Filtering**: Price alerts and saved searches
- **CRM Integration**: Lead scoring and follow-up
- **Analytics Dashboard**: Conversation flow analysis
- **Voice Interface**: Speech-to-text integration
- **Webhook Integration**: Real-time notifications

### Language Expansion
- Thai language support
- German language support
- Automatic language detection improvement

### Enhanced Matching
- ML-based property recommendations
- Market trend integration  
- Comparative market analysis
- Investment return calculations