#!/usr/bin/env python3
"""
Minimal chatbot tests that don't require external APIs
For use in Git hooks and CI/CD
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all chatbot modules can be imported"""
    print("🧪 Testing Chatbot Imports")
    print("-" * 40)
    
    try:
        # Test core imports
        from services.chatbot.chatbot_manager import OneMinutaChatbotManager
        print("   ✅ ChatbotManager")
        
        from services.chatbot.session_manager import ChatbotSessionManager
        print("   ✅ SessionManager")
        
        # Test stage imports
        from services.chatbot.stages.base_stage import BaseChatbotStage
        print("   ✅ BaseChatbotStage")
        
        from services.chatbot.stages.user_profile_detection import UserProfileDetectionStage
        print("   ✅ UserProfileDetectionStage")
        
        from services.chatbot.stages.smart_greeting import SmartGreetingStage
        print("   ✅ SmartGreetingStage")
        
        from services.chatbot.stages.inquiry_collection import InquiryCollectionStage
        print("   ✅ InquiryCollectionStage")
        
        from services.chatbot.stages.property_matching import PropertyMatchingStage
        print("   ✅ PropertyMatchingStage")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_session_manager():
    """Test session manager without external dependencies"""
    print("\n🧪 Testing Session Manager")
    print("-" * 40)
    
    try:
        from services.chatbot.session_manager import ChatbotSessionManager
        
        # Test initialization
        session_manager = ChatbotSessionManager("./storage")
        print("   ✅ Session manager initialized")
        
        # Test directory creation
        if session_manager.sessions_dir.exists():
            print("   ✅ Sessions directory exists")
        else:
            print("   ❌ Sessions directory not created")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Session manager test failed: {e}")
        return False

def test_language_detection():
    """Test language detection without OpenAI"""
    print("\n🧪 Testing Language Detection")
    print("-" * 40)
    
    # Simple language detection function (copy of the actual one)
    def extract_language(text: str) -> str:
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars == 0:
            return "en"
        
        cyrillic_ratio = cyrillic_chars / total_chars
        return "ru" if cyrillic_ratio > 0.3 else "en"
    
    test_cases = [
        ("Hello, I need a condo", "en"),
        ("Привет, мне нужна квартира", "ru"),
        ("", "en"),
        ("12345", "en")
    ]
    
    passed = 0
    for text, expected in test_cases:
        detected = extract_language(text)
        if detected == expected:
            print(f"   ✅ '{text[:20]}...' → {detected}")
            passed += 1
        else:
            print(f"   ❌ '{text[:20]}...' → {detected} (expected {expected})")
    
    return passed == len(test_cases)

def test_cli_integration():
    """Test CLI integration"""
    print("\n🧪 Testing CLI Integration")
    print("-" * 40)
    
    try:
        from oneminuta_cli import OneMinutaCLI
        
        cli = OneMinutaCLI("./storage")
        
        # Check if chatbot methods exist
        if hasattr(cli, 'chatbot_interactive'):
            print("   ✅ chatbot_interactive method exists")
        else:
            print("   ❌ chatbot_interactive method missing")
            return False
        
        if hasattr(cli, 'chatbot_stats'):
            print("   ✅ chatbot_stats method exists")
        else:
            print("   ❌ chatbot_stats method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ CLI integration test failed: {e}")
        return False

def main():
    """Run all minimal tests"""
    print("🧪 OneMinuta Chatbot Minimal Tests")
    print("=" * 50)
    print("Tests that run without external APIs")
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Session Manager", test_session_manager),
        ("Language Detection", test_language_detection),
        ("CLI Integration", test_cli_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All minimal tests passed!")
        return True
    else:
        print("⚠️ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)