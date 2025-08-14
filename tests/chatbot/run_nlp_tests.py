#!/usr/bin/env python3
"""
Quick runner for NLP extraction accuracy tests
Loads configuration from .env file
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def main():
    print("🧪 OneMinuta NLP Extraction Tests")
    print("=" * 50)
    
    # Check if OpenAI API key is available (from .env)
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print("✅ OpenAI API key loaded from .env - running full tests")
        use_api = True
    else:
        print("⚠️ No OpenAI API key in .env - running structural tests only")
        use_api = False
    
    try:
        from tests.chatbot.test_nlp_extraction import NLPExtractionTester
        
        # Initialize tester
        tester = NLPExtractionTester(openai_key if use_api else "test_key")
        
        if use_api:
            # Run full test suite
            print("\n🚀 Running comprehensive NLP tests...")
            results = await tester.run_all_tests()
            
            # Save results
            tester.save_test_results(results)
            
            # Show recommendation
            success_rate = results['overall_summary']['overall_success_rate']
            if success_rate >= 80:
                print("\n🎉 READY FOR PRODUCTION - NLP accuracy is excellent!")
            elif success_rate >= 70:
                print("\n✅ READY FOR TESTING - NLP accuracy is good")
            else:
                print("\n⚠️ NEEDS IMPROVEMENT - Consider tuning prompts or adding more training data")
        
        else:
            # Run language detection only (doesn't require API)
            print("\n🧪 Running language detection tests...")
            lang_results = await tester.test_language_detection()
            
            print(f"\n📊 Language Detection: {lang_results['success_rate']:.1f}% accuracy")
            if lang_results['success_rate'] >= 90:
                print("✅ Language detection is working well")
            else:
                print("⚠️ Language detection may need improvement")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)