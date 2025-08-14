#!/usr/bin/env python3
"""
Setup script for OneMinuta Chatbot Testing

Helps configure environment and dependencies for comprehensive chatbot testing.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = {
        'openai': 'pip install openai>=1.0.0',
        'telethon': 'pip install telethon',
        'pytest': 'pip install pytest'
    }
    
    missing = []
    
    for package, install_cmd in required_packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - Run: {install_cmd}")
            missing.append(install_cmd)
    
    if missing:
        print(f"\n💡 Install missing packages:")
        for cmd in missing:
            print(f"  {cmd}")
        return False
    
    return True

def check_environment():
    """Check environment variables"""
    print("\n🔧 Checking environment variables...")
    
    optional_vars = {
        'OPENAI_API_KEY': 'Required for full NLP testing',
        'TELEGRAM_API_ID': 'Required for Telegram bot testing', 
        'TELEGRAM_API_HASH': 'Required for Telegram bot testing',
        'TELEGRAM_BOT_TOKEN': 'Required for Telegram bot testing'
    }
    
    found = {}
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}")
            found[var] = True
        else:
            print(f"  ⚠️ {var} - {description}")
            found[var] = False
    
    return found

def create_test_structure():
    """Create testing directory structure"""
    print("\n📁 Creating test directory structure...")
    
    test_dirs = [
        "storage/chatbot/sessions",
        "storage/chatbot/test_logs",
        "storage/chatbot/test_results",
        "tests/chatbot"
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {dir_path}")

def suggest_next_steps(env_status):
    """Suggest next steps based on current setup"""
    print("\n🎯 Recommended Next Steps:")
    
    # Always available tests
    print("\n1. 📊 Basic Structure Tests (No API required):")
    print("   python test_chatbot_structure.py")
    print("   python run_nlp_tests.py")
    
    # NLP tests with API
    if env_status.get('OPENAI_API_KEY'):
        print("\n2. 🧠 Full NLP Accuracy Tests:")
        print("   python tests/chatbot/test_nlp_extraction.py --save-results")
        print("   python run_nlp_tests.py")
    else:
        print("\n2. 🧠 NLP Tests (Set OPENAI_API_KEY first):")
        print("   export OPENAI_API_KEY='sk-proj-your-key-here'")
        print("   python run_nlp_tests.py")
    
    # Telegram bot testing
    telegram_ready = all(env_status.get(var, False) for var in 
                        ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY'])
    
    if telegram_ready:
        print("\n3. 🤖 Telegram Bot Testing with @rezztelegram:")
        print("   python start_telegram_chatbot_test.py")
        print("   # Then send /start to the bot from @rezztelegram")
    else:
        print("\n3. 🤖 Telegram Bot Testing (Set environment variables first):")
        missing_vars = [var for var, status in env_status.items() if not status]
        for var in missing_vars:
            print(f"   export {var}='your_value_here'")
        print("   python start_telegram_chatbot_test.py")

def show_testing_examples():
    """Show example testing commands"""
    print("\n📚 Testing Examples:")
    print("""
# Quick health check
python test_chatbot_structure.py

# Language detection accuracy
python run_nlp_tests.py

# Comprehensive NLP testing (with API)
export OPENAI_API_KEY="sk-proj-..."
python tests/chatbot/test_nlp_extraction.py --test-type all --save-results

# Interactive chatbot testing  
python oneminuta_cli.py chat

# Telegram bot testing (with @rezztelegram)
export TELEGRAM_API_ID="12345"
export TELEGRAM_API_HASH="abcd..."  
export TELEGRAM_BOT_TOKEN="123:ABC..."
export OPENAI_API_KEY="sk-proj-..."
python start_telegram_chatbot_test.py
""")

def main():
    print("🚀 OneMinuta Chatbot Testing Setup")
    print("=" * 50)
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check environment  
    env_status = check_environment()
    
    # Create test structure
    create_test_structure()
    
    print("\n" + "=" * 50)
    
    if deps_ok:
        print("✅ Setup completed successfully!")
        suggest_next_steps(env_status)
        show_testing_examples()
        
        print("\n📖 For detailed testing guide, see: docs/TESTING.md")
        
        return True
    else:
        print("❌ Setup incomplete - install missing dependencies first")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)