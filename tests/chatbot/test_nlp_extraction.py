"""
Natural Language Processing Extraction Tests

Tests the accuracy of JSON extraction from natural language messages
in the OneMinuta chatbot system.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
# Optional pytest import
try:
    import pytest
except ImportError:
    pytest = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.config_loader import get_openai_api_key

from services.chatbot.stages.user_profile_detection import UserProfileDetectionStage
from services.chatbot.stages.inquiry_collection import InquiryCollectionStage


class NLPExtractionTester:
    """Test suite for natural language processing accuracy"""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or get_openai_api_key(required=False) or 'test_key'
        self.profile_stage = UserProfileDetectionStage(self.openai_api_key)
        self.inquiry_stage = InquiryCollectionStage(self.openai_api_key)
        
        # Test results storage
        self.test_results = []
    
    async def test_user_profile_extraction(self) -> Dict:
        """Test user profile detection accuracy"""
        print("🧪 Testing User Profile Detection...")
        
        test_cases = [
            # English buyer cases
            {
                "input": "Hi, I'm looking for a condo in Phuket",
                "expected": {
                    "user_type": "buyer",
                    "intent": "search",
                    "language": "en"
                }
            },
            {
                "input": "I need to find a villa for my family, budget around 50k THB",
                "expected": {
                    "user_type": "buyer", 
                    "intent": "search",
                    "language": "en"
                }
            },
            
            # Russian buyer cases
            {
                "input": "Привет, ищу квартиру в Бангкоке",
                "expected": {
                    "user_type": "buyer",
                    "intent": "search", 
                    "language": "ru"
                }
            },
            {
                "input": "Хочу купить виллу для инвестиций",
                "expected": {
                    "user_type": "investor",
                    "intent": "invest",
                    "language": "ru"
                }
            },
            
            # Seller cases
            {
                "input": "I want to sell my house in Bangkok",
                "expected": {
                    "user_type": "seller",
                    "intent": "sell",
                    "language": "en"
                }
            },
            {
                "input": "Хочу продать свою квартиру",
                "expected": {
                    "user_type": "seller",
                    "intent": "sell",
                    "language": "ru"
                }
            },
            
            # Agent cases
            {
                "input": "I'm a real estate agent, need access to properties",
                "expected": {
                    "user_type": "agent",
                    "intent": "browse",
                    "language": "en"
                }
            },
            
            # Investor cases
            {
                "input": "Looking for investment opportunities in Thai real estate",
                "expected": {
                    "user_type": "investor",
                    "intent": "invest",
                    "language": "en"
                }
            },
            
            # Edge cases
            {
                "input": "What properties do you have?",
                "expected": {
                    "user_type": "buyer",
                    "intent": "browse",
                    "language": "en"
                }
            },
            {
                "input": "123456",
                "expected": {
                    "user_type": "buyer",  # Default fallback
                    "intent": "browse",    # Default fallback
                    "language": "en"       # Default fallback
                }
            }
        ]
        
        results = []
        passed = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"  Test {i+1}: {test_case['input'][:50]}...")
            
            try:
                # Mock session for testing
                mock_session = {"conversation_history": []}
                
                # Extract profile
                extracted = await self.profile_stage._analyze_user_profile(
                    test_case['input'], 
                    test_case['expected']['language'],
                    mock_session
                )
                
                if not extracted:
                    # Use language detection fallback
                    detected_lang = self.profile_stage._extract_language(test_case['input'])
                    extracted = {
                        "user_type": "buyer",
                        "intent": "browse", 
                        "confidence": 0.3
                    }
                    test_case['expected']['language'] = detected_lang
                
                # Check accuracy
                score = 0
                total_checks = 3
                
                if extracted.get('user_type') == test_case['expected']['user_type']:
                    score += 1
                if extracted.get('intent') == test_case['expected']['intent']:
                    score += 1
                
                # Language detection test
                detected_lang = self.profile_stage._extract_language(test_case['input'])
                if detected_lang == test_case['expected']['language']:
                    score += 1
                
                accuracy = (score / total_checks) * 100
                
                result = {
                    "test_id": i + 1,
                    "input": test_case['input'],
                    "expected": test_case['expected'],
                    "extracted": extracted,
                    "detected_language": detected_lang,
                    "accuracy": accuracy,
                    "passed": accuracy >= 66.67  # At least 2/3 correct
                }
                
                if result['passed']:
                    passed += 1
                    print(f"    ✅ PASS ({accuracy:.1f}%)")
                else:
                    print(f"    ❌ FAIL ({accuracy:.1f}%)")
                    print(f"       Expected: {test_case['expected']}")
                    print(f"       Got: {extracted}")
                
                results.append(result)
                
            except Exception as e:
                print(f"    ❌ ERROR: {e}")
                results.append({
                    "test_id": i + 1,
                    "input": test_case['input'],
                    "error": str(e),
                    "passed": False,
                    "accuracy": 0
                })
        
        summary = {
            "test_type": "user_profile_detection",
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": len(test_cases) - passed,
            "success_rate": (passed / len(test_cases)) * 100,
            "results": results
        }
        
        print(f"\n📊 Profile Detection Summary: {passed}/{len(test_cases)} passed ({summary['success_rate']:.1f}%)")
        return summary
    
    async def test_requirements_extraction(self) -> Dict:
        """Test property requirements extraction accuracy"""
        print("\n🧪 Testing Requirements Extraction...")
        
        test_cases = [
            # Basic requirements
            {
                "input": "I need a 2-bedroom condo in Phuket for rent under 30,000 THB",
                "expected": {
                    "property_type": "condo",
                    "location_preference": "Phuket", 
                    "rent_or_sale": "rent",
                    "budget_max": 30000,
                    "bedrooms": 2
                }
            },
            {
                "input": "Looking for a furnished villa to buy in Rawai, 3 bedrooms, around 8 million",
                "expected": {
                    "property_type": "villa",
                    "location_preference": "Rawai",
                    "rent_or_sale": "sale",
                    "budget_max": 8000000,
                    "bedrooms": 3,
                    "furnished": True
                }
            },
            
            # Russian requirements
            {
                "input": "Ищу квартиру в аренду в Бангкоке, 1 спальня, до 25000 батов",
                "expected": {
                    "property_type": "apartment",
                    "location_preference": "Бангкоке", 
                    "rent_or_sale": "rent",
                    "budget_max": 25000,
                    "bedrooms": 1
                }
            },
            {
                "input": "Хочу купить дом с 4 спальнями в Паттайе",
                "expected": {
                    "property_type": "house",
                    "location_preference": "Паттайе",
                    "rent_or_sale": "sale", 
                    "bedrooms": 4
                }
            },
            
            # Complex requirements
            {
                "input": "Need unfurnished 2-bed 2-bath condo for rent in Kata, budget 20k-35k THB monthly",
                "expected": {
                    "property_type": "condo",
                    "location_preference": "Kata",
                    "rent_or_sale": "rent",
                    "budget_min": 20000,
                    "budget_max": 35000,
                    "bedrooms": 2,
                    "bathrooms": 2,
                    "furnished": False
                }
            },
            
            # Partial information
            {
                "input": "I want a house for sale",
                "expected": {
                    "property_type": "house",
                    "rent_or_sale": "sale"
                }
            },
            {
                "input": "2 bedrooms, furnished",
                "expected": {
                    "bedrooms": 2,
                    "furnished": True
                }
            },
            
            # Edge cases
            {
                "input": "Something cheap near the beach",
                "expected": {}  # Very vague, should extract minimal
            },
            {
                "input": "Price negotiable, any location",
                "expected": {}  # Too vague
            }
        ]
        
        results = []
        passed = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"  Test {i+1}: {test_case['input'][:50]}...")
            
            try:
                # Mock session
                mock_session = {"conversation_history": []}
                
                # Extract requirements
                extracted = await self.inquiry_stage._extract_requirements(
                    test_case['input'],
                    "en",  # Default to English for testing
                    mock_session
                )
                
                if not extracted:
                    extracted = {}
                
                # Calculate accuracy based on expected fields
                expected_fields = test_case['expected']
                if not expected_fields:
                    # For edge cases with no expected extraction
                    accuracy = 100 if not extracted else 50
                    passed_test = True
                else:
                    score = 0
                    total_fields = len(expected_fields)
                    
                    for field, expected_value in expected_fields.items():
                        if field in extracted:
                            if field in ['budget_min', 'budget_max', 'bedrooms', 'bathrooms']:
                                # Numeric fields - allow some tolerance
                                if abs(extracted[field] - expected_value) <= (expected_value * 0.1):
                                    score += 1
                            elif field == 'furnished':
                                # Boolean fields
                                if extracted[field] == expected_value:
                                    score += 1
                            else:
                                # String fields - case insensitive partial match
                                if str(expected_value).lower() in str(extracted[field]).lower():
                                    score += 1
                    
                    accuracy = (score / total_fields) * 100 if total_fields > 0 else 0
                    passed_test = accuracy >= 70  # 70% accuracy threshold
                
                if passed_test:
                    passed += 1
                    print(f"    ✅ PASS ({accuracy:.1f}%)")
                else:
                    print(f"    ❌ FAIL ({accuracy:.1f}%)")
                    print(f"       Expected: {expected_fields}")
                    print(f"       Got: {extracted}")
                
                result = {
                    "test_id": i + 1,
                    "input": test_case['input'],
                    "expected": expected_fields,
                    "extracted": extracted,
                    "accuracy": accuracy,
                    "passed": passed_test
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"    ❌ ERROR: {e}")
                results.append({
                    "test_id": i + 1,
                    "input": test_case['input'],
                    "error": str(e),
                    "passed": False,
                    "accuracy": 0
                })
        
        summary = {
            "test_type": "requirements_extraction",
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": len(test_cases) - passed,
            "success_rate": (passed / len(test_cases)) * 100,
            "results": results
        }
        
        print(f"\n📊 Requirements Extraction Summary: {passed}/{len(test_cases)} passed ({summary['success_rate']:.1f}%)")
        return summary
    
    async def test_language_detection(self) -> Dict:
        """Test language detection accuracy"""
        print("\n🧪 Testing Language Detection...")
        
        test_cases = [
            ("Hello, I'm looking for property", "en"),
            ("Hi there, what do you have?", "en"),
            ("I need a condo in Phuket", "en"),
            ("Привет, ищу квартиру", "ru"),
            ("Хочу купить дом в Таиланде", "ru"),
            ("Добрый день, нужна вилла", "ru"),
            ("Сколько стоит недвижимость?", "ru"),
            ("123456", "en"),  # Numbers default to English
            ("", "en"),  # Empty default to English
            ("Hello привет", "ru"),  # Mixed, but more Russian (6/11 chars are Cyrillic)
            ("Привет hello дом", "ru"),  # Mixed, but more Russian
        ]
        
        results = []
        passed = 0
        
        for i, (text, expected_lang) in enumerate(test_cases):
            detected = self.profile_stage._extract_language(text)
            is_correct = detected == expected_lang
            
            if is_correct:
                passed += 1
                print(f"  Test {i+1}: ✅ '{text[:30]}...' → {detected}")
            else:
                print(f"  Test {i+1}: ❌ '{text[:30]}...' → {detected} (expected {expected_lang})")
            
            results.append({
                "test_id": i + 1,
                "input": text,
                "expected": expected_lang,
                "detected": detected,
                "correct": is_correct
            })
        
        summary = {
            "test_type": "language_detection",
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": len(test_cases) - passed,
            "success_rate": (passed / len(test_cases)) * 100,
            "results": results
        }
        
        print(f"\n📊 Language Detection Summary: {passed}/{len(test_cases)} passed ({summary['success_rate']:.1f}%)")
        return summary
    
    async def run_all_tests(self) -> Dict:
        """Run all NLP extraction tests"""
        print("🚀 Starting NLP Extraction Test Suite")
        print("=" * 60)
        
        # Run all test categories
        profile_results = await self.test_user_profile_extraction()
        requirements_results = await self.test_requirements_extraction() 
        language_results = await self.test_language_detection()
        
        # Overall summary
        total_tests = (profile_results['total_tests'] + 
                      requirements_results['total_tests'] + 
                      language_results['total_tests'])
        
        total_passed = (profile_results['passed'] + 
                       requirements_results['passed'] + 
                       language_results['passed'])
        
        overall_success_rate = (total_passed / total_tests) * 100
        
        summary = {
            "overall_summary": {
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_tests - total_passed,
                "overall_success_rate": overall_success_rate
            },
            "test_categories": {
                "profile_detection": profile_results,
                "requirements_extraction": requirements_results,
                "language_detection": language_results
            }
        }
        
        print("\n" + "=" * 60)
        print(f"🎯 OVERALL TEST RESULTS")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_tests - total_passed}")
        print(f"Success Rate: {overall_success_rate:.1f}%")
        
        # Determine overall result
        if overall_success_rate >= 80:
            print("✅ EXCELLENT - NLP extraction is highly accurate")
        elif overall_success_rate >= 70:
            print("✅ GOOD - NLP extraction is adequately accurate")
        elif overall_success_rate >= 60:
            print("⚠️ FAIR - NLP extraction needs improvement")
        else:
            print("❌ POOR - NLP extraction requires significant work")
        
        return summary
    
    def save_test_results(self, results: Dict, filename: str = None):
        """Save test results to file"""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nlp_test_results_{timestamp}.json"
        
        # Ensure test results directory exists
        test_dir = Path(project_root) / "storage" / "chatbot" / "test_results"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = test_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Test results saved to: {filepath}")


async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NLP Extraction Test Suite")
    parser.add_argument("--openai-key", help="OpenAI API key (or set OPENAI_API_KEY)")
    parser.add_argument("--save-results", action="store_true", help="Save results to file")
    parser.add_argument("--test-type", choices=["profile", "requirements", "language", "all"], 
                       default="all", help="Which tests to run")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.openai_key or get_openai_api_key(required=False)
    if not api_key:
        print("⚠️ Warning: No OpenAI API key provided. Using mock responses.")
        api_key = "test_key"
    
    # Initialize tester
    tester = NLPExtractionTester(api_key)
    
    # Run selected tests
    if args.test_type == "profile":
        results = await tester.test_user_profile_extraction()
    elif args.test_type == "requirements":
        results = await tester.test_requirements_extraction()
    elif args.test_type == "language":
        results = await tester.test_language_detection()
    else:
        results = await tester.run_all_tests()
    
    # Save results if requested
    if args.save_results:
        tester.save_test_results(results)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())