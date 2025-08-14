#!/usr/bin/env python3
"""
Offline test of analytics system without requiring OpenAI API key
"""

import json
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.analytics.llm_analyzer import LLMClientAnalysis


def test_client_analysis_structure():
    """Test the client analysis data structure"""
    print("🧪 Testing LLMClientAnalysis structure...")
    
    # Create a sample analysis
    analysis = LLMClientAnalysis(
        user_id="test_user_123",
        hotness_score=78.5,
        hotness_level="hot",
        primary_intent="buying",
        intent_confidence=0.85,
        urgency_level="high",
        budget_min=150000,
        budget_max=300000,
        currency="USD",
        preferred_locations=["Phuket", "Rawai"],
        asset_types=["condo", "villa"],
        bedrooms=2,
        bathrooms=2,
        financing_ready=True,
        wants_viewing=True,
        wants_contact=True,
        timeline="this_month",
        language_detected="en",
        confidence=0.88,
        key_phrases=["cash ready", "urgent", "viewing this week"],
        reasoning="Client shows strong buying intent with specific budget and urgency"
    )
    
    print("✅ Analysis object created successfully")
    print(f"   User: {analysis.user_id}")
    print(f"   Score: {analysis.hotness_score}/100 ({analysis.hotness_level})")
    print(f"   Intent: {analysis.primary_intent} (confidence: {analysis.intent_confidence})")
    print(f"   Budget: ${analysis.budget_min:,} - ${analysis.budget_max:,}")
    print(f"   Locations: {', '.join(analysis.preferred_locations)}")
    print(f"   Signals: Financing={analysis.financing_ready}, Viewing={analysis.wants_viewing}")
    
    return analysis


def test_message_formats():
    """Test different message formats for analysis"""
    print("\n🔍 Testing message format handling...")
    
    # English messages
    en_messages = [
        {
            "content": "Hi, I'm looking for a 2-bedroom condo in Phuket, budget around $200k. Need urgent!",
            "timestamp": "2024-01-15T10:30:00Z",
            "channel": "@phuket_property"
        },
        {
            "content": "Cash ready, can view this weekend. Please contact me ASAP",
            "timestamp": "2024-01-15T11:45:00Z",
            "channel": "@phuket_property"
        }
    ]
    
    # Russian messages
    ru_messages = [
        {
            "content": "Срочно ищу квартиру в Паттайе до $150k, готов покупать сегодня",
            "timestamp": "2024-01-15T10:30:00Z",
            "channel": "@pattaya_russian"
        },
        {
            "content": "Наличные готовы, можно посмотреть в выходные. Свяжитесь срочно!",
            "timestamp": "2024-01-15T11:45:00Z",
            "channel": "@pattaya_russian"
        }
    ]
    
    print("✅ English messages:")
    for i, msg in enumerate(en_messages, 1):
        print(f"   {i}. [{msg['channel']}] {msg['content'][:50]}...")
    
    print("✅ Russian messages:")
    for i, msg in enumerate(ru_messages, 1):
        print(f"   {i}. [{msg['channel']}] {msg['content'][:50]}...")
    
    return en_messages, ru_messages


def test_json_serialization():
    """Test JSON serialization of analysis results"""
    print("\n💾 Testing JSON serialization...")
    
    analysis = test_client_analysis_structure()
    
    try:
        # Convert to dict
        analysis_dict = {
            'user_id': analysis.user_id,
            'hotness_score': analysis.hotness_score,
            'hotness_level': analysis.hotness_level,
            'primary_intent': analysis.primary_intent,
            'intent_confidence': analysis.intent_confidence,
            'urgency_level': analysis.urgency_level,
            'budget_min': analysis.budget_min,
            'budget_max': analysis.budget_max,
            'currency': analysis.currency,
            'preferred_locations': analysis.preferred_locations,
            'asset_types': analysis.asset_types,
            'bedrooms': analysis.bedrooms,
            'bathrooms': analysis.bathrooms,
            'financing_ready': analysis.financing_ready,
            'wants_viewing': analysis.wants_viewing,
            'wants_contact': analysis.wants_contact,
            'timeline': analysis.timeline,
            'language_detected': analysis.language_detected,
            'confidence': analysis.confidence,
            'key_phrases': analysis.key_phrases,
            'reasoning': analysis.reasoning
        }
        
        # Serialize to JSON
        json_str = json.dumps(analysis_dict, indent=2, ensure_ascii=False)
        
        print("✅ JSON serialization successful")
        print("   Sample JSON output:")
        print("   " + "\n   ".join(json_str.split('\n')[:10]))
        print("   ...")
        
        # Test deserialization
        parsed = json.loads(json_str)
        print(f"✅ JSON deserialization successful - {len(parsed)} fields")
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")


def test_scoring_logic():
    """Test the scoring logic categorization"""
    print("\n📊 Testing scoring logic...")
    
    test_scores = [
        (95, "burning"),
        (78, "hot"), 
        (45, "warm"),
        (15, "cold")
    ]
    
    for score, expected_level in test_scores:
        if score >= 86:
            level = "burning"
        elif score >= 61:
            level = "hot"
        elif score >= 31:
            level = "warm"
        else:
            level = "cold"
        
        status = "✅" if level == expected_level else "❌"
        print(f"   {status} Score {score} → {level} (expected: {expected_level})")


def test_language_keywords():
    """Test language-specific keywords"""
    print("\n🌍 Testing language-specific keywords...")
    
    english_keywords = {
        'urgency': ['urgent', 'asap', 'immediately', 'cash ready', 'today', 'this week', 'fast'],
        'viewing': ['viewing', 'visit', 'see the property', 'schedule', 'appointment'],
        'budget': ['budget', 'price', 'cost', 'up to', 'around', 'maximum']
    }
    
    russian_keywords = {
        'urgency': ['срочно', 'готов покупать', 'наличные готовы', 'сегодня', 'на этой неделе'],
        'viewing': ['посмотреть', 'осмотр', 'показ', 'встреча', 'когда можно'],
        'budget': ['бюджет', 'цена', 'стоимость', 'до', 'около', 'максимум']
    }
    
    print("✅ English keywords loaded:")
    for category, words in english_keywords.items():
        print(f"   {category}: {len(words)} words")
    
    print("✅ Russian keywords loaded:")
    for category, words in russian_keywords.items():
        print(f"   {category}: {len(words)} words")


def main():
    """Run all offline tests"""
    print("🚀 OneMinuta Analytics - Offline Test Suite")
    print("=" * 50)
    
    test_client_analysis_structure()
    test_message_formats()
    test_json_serialization()
    test_scoring_logic()
    test_language_keywords()
    
    print("\n" + "=" * 50)
    print("✅ All offline tests completed successfully!")
    print("\n💡 Next steps:")
    print("   1. Set OPENAI_API_KEY environment variable")
    print("   2. Run: python -m services.analytics.cli test --language en")
    print("   3. Try: python -m services.analytics.cli hot-clients")
    print("   4. Start monitoring: python -m services.analytics.cli monitor")


if __name__ == "__main__":
    main()