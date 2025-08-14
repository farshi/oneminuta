#!/usr/bin/env python3
"""
Test chatbot structure without API calls
"""

import sys
from pathlib import Path

# Add project to path (tests/chatbot -> project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_chatbot_structure():
    """Test chatbot structure and imports"""
    
    print("🧪 Testing OneMinuta Chatbot Structure")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from services.chatbot.chatbot_manager import OneMinutaChatbotManager
        from services.chatbot.session_manager import ChatbotSessionManager
        from services.chatbot.stages import (
            UserProfileDetectionStage,
            SmartGreetingStage,
            InquiryCollectionStage,
            PropertyMatchingStage
        )
        print("   ✅ All imports successful")
        
        # Test session manager without API key
        print("\n2. Testing session manager...")
        storage_path = "./storage"
        session_manager = ChatbotSessionManager(storage_path)
        print(f"   ✅ Session manager initialized: {session_manager.sessions_dir}")
        
        # Test stages initialization
        print("\n3. Testing stage initialization...")
        fake_key = "test_key"
        stages = {
            'user-profile-detection': UserProfileDetectionStage(fake_key),
            'smart-greeting': SmartGreetingStage(fake_key),
            'inquiry-collection': InquiryCollectionStage(fake_key),
            'property-matching': PropertyMatchingStage(storage_path, fake_key)
        }
        
        for stage_name, stage in stages.items():
            print(f"   ✅ {stage_name}: {stage.get_stage_name()}")
        
        print("\n4. Testing CLI integration...")
        from oneminuta_cli import OneMinutaCLI
        cli = OneMinutaCLI(storage_path)
        
        # Check if chatbot methods exist
        assert hasattr(cli, 'chatbot_interactive'), "Missing chatbot_interactive method"
        assert hasattr(cli, 'chatbot_stats'), "Missing chatbot_stats method"
        print("   ✅ CLI methods available")
        
        print("\n✅ All structural tests passed!")
        print("\nℹ️  To test full functionality:")
        print("   1. Set OPENAI_API_KEY environment variable")
        print("   2. Run: python oneminuta_cli.py chat")
        print("   3. Or run: python test_chatbot.py")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chatbot_structure()
    sys.exit(0 if success else 1)