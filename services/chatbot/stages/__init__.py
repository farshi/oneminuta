"""
Chatbot Conversation Stages

Each stage handles a specific part of the conversation flow:
1. user-profile-detection: Determine user type and language
2. smart-greeting: Personalized greeting based on profile
3. inquiry-collection: Collect property requirements
4. property-matching: Find and present matching properties
"""

from .user_profile_detection import UserProfileDetectionStage
from .smart_greeting import SmartGreetingStage
from .inquiry_collection import InquiryCollectionStage
from .property_matching import PropertyMatchingStage

__all__ = [
    'UserProfileDetectionStage',
    'SmartGreetingStage', 
    'InquiryCollectionStage',
    'PropertyMatchingStage'
]