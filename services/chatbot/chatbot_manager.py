"""
OneMinuta Smart Chatbot Manager

Orchestrates staged conversations with users to understand their requirements
and provide personalized property recommendations.
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .stages import (
    UserProfileDetectionStage,
    SmartGreetingStage, 
    InquiryCollectionStage,
    PropertyMatchingStage
)
from .session_manager import ChatbotSessionManager


class OneMinutaChatbotManager:
    """Main chatbot manager coordinating all conversation stages"""
    
    def __init__(self, storage_path: str, openai_api_key: str):
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)
        
        # Initialize session manager
        self.session_manager = ChatbotSessionManager(storage_path)
        
        # Initialize conversation stages
        self.stages = {
            'user-profile-detection': UserProfileDetectionStage(openai_api_key),
            'smart-greeting': SmartGreetingStage(openai_api_key),
            'inquiry-collection': InquiryCollectionStage(openai_api_key),
            'property-matching': PropertyMatchingStage(storage_path, openai_api_key)
        }
        
        self.logger.info("OneMinuta Chatbot Manager initialized")
    
    async def process_message(self, user_id: str, message: str, context: Dict = None) -> Dict:
        """
        Process incoming message through appropriate conversation stage
        
        Args:
            user_id: Unique identifier for the user
            message: User's message text
            context: Additional context (channel, message_id, etc.)
            
        Returns:
            Response dict with stage info and reply
        """
        try:
            # Get or create session
            session = await self.session_manager.get_session(user_id)
            
            # Determine current stage
            current_stage = session.get('current_stage', 'user-profile-detection')
            
            self.logger.info(f"Processing message from {user_id} in stage: {current_stage}")
            
            # Get stage handler
            stage_handler = self.stages[current_stage]
            
            # Process message through current stage
            stage_result = await stage_handler.process(user_id, message, session, context)
            
            # Update session with stage result
            updated_session = await self._update_session(session, stage_result)
            
            # Save updated session
            await self.session_manager.save_session(user_id, updated_session)
            
            # Prepare response
            response = {
                'user_id': user_id,
                'stage': current_stage,
                'next_stage': stage_result.get('next_stage'),
                'reply': stage_result.get('reply', ''),
                'data_collected': stage_result.get('data_collected', {}),
                'properties_found': stage_result.get('properties_found', []),
                'session_complete': stage_result.get('session_complete', False),
                'confidence': stage_result.get('confidence', 0.0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Generated response for {user_id}: stage={current_stage}, next={response['next_stage']}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message for {user_id}: {e}")
            return {
                'user_id': user_id,
                'stage': 'error',
                'reply': 'I apologize, but I encountered an error processing your message. Please try again.',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _update_session(self, session: Dict, stage_result: Dict) -> Dict:
        """Update session data with stage processing results"""
        
        # Update stage progression
        if stage_result.get('next_stage'):
            session['current_stage'] = stage_result['next_stage']
        
        # Update collected data
        if stage_result.get('data_collected'):
            if 'collected_data' not in session:
                session['collected_data'] = {}
            session['collected_data'].update(stage_result['data_collected'])
        
        # Update conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        session['conversation_history'].append({
            'stage': session.get('previous_stage', session.get('current_stage')),
            'user_message': stage_result.get('user_message', ''),
            'bot_reply': stage_result.get('reply', ''),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data_collected': stage_result.get('data_collected', {}),
            'confidence': stage_result.get('confidence', 0.0)
        })
        
        # Update session metadata
        session['last_active'] = datetime.now(timezone.utc).isoformat()
        session['message_count'] = session.get('message_count', 0) + 1
        
        # Mark as complete if final stage
        if stage_result.get('session_complete'):
            session['status'] = 'completed'
            session['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        return session
    
    async def get_user_requirements(self, user_id: str) -> Optional[Dict]:
        """Get collected user requirements from session"""
        try:
            session = await self.session_manager.get_session(user_id)
            return session.get('collected_data', {})
        except Exception as e:
            self.logger.error(f"Error getting requirements for {user_id}: {e}")
            return None
    
    async def reset_conversation(self, user_id: str) -> bool:
        """Reset conversation to beginning for user"""
        try:
            await self.session_manager.clear_session(user_id)
            self.logger.info(f"Reset conversation for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error resetting conversation for {user_id}: {e}")
            return False
    
    async def get_conversation_summary(self, user_id: str) -> Optional[Dict]:
        """Get summary of conversation progress"""
        try:
            session = await self.session_manager.get_session(user_id)
            
            return {
                'user_id': user_id,
                'current_stage': session.get('current_stage', 'user-profile-detection'),
                'status': session.get('status', 'active'),
                'message_count': session.get('message_count', 0),
                'data_completeness': self._calculate_data_completeness(session.get('collected_data', {})),
                'last_active': session.get('last_active'),
                'created_at': session.get('created_at'),
                'estimated_completion': self._estimate_completion_percentage(session)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation summary for {user_id}: {e}")
            return None
    
    async def generate_welcome_message(self, user_id: str, context: str) -> Optional[str]:
        """Generate personalized welcome message using AI"""
        try:
            # Use the profile detection stage to generate welcome message
            profile_stage = self.stages['user-profile-detection']
            
            messages = [
                {
                    "role": "system", 
                    "content": """You are OneMinuta, a friendly Thai property search assistant. 
                    Generate a warm, professional welcome message based on the context provided.
                    Keep it brief (max 3 sentences), personalized, and end with an engaging question about their property needs.
                    Be conversational and helpful."""
                },
                {
                    "role": "user",
                    "content": context
                }
            ]
            
            response = await profile_stage._call_openai(
                messages=messages,
                temperature=0.8,
                max_tokens=200
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating welcome message: {e}")
            return None
    
    def _calculate_data_completeness(self, collected_data: Dict) -> Dict:
        """Calculate how much required data has been collected"""
        required_fields = {
            'profile': ['user_type', 'language_preference'],
            'requirements': ['property_type', 'budget_range', 'location_preference'],
            'preferences': ['bedrooms', 'bathrooms', 'rent_or_sale']
        }
        
        completeness = {}
        
        for category, fields in required_fields.items():
            if category in collected_data:
                filled = sum(1 for field in fields if collected_data[category].get(field))
                completeness[category] = {
                    'filled': filled,
                    'total': len(fields),
                    'percentage': round((filled / len(fields)) * 100, 1)
                }
            else:
                completeness[category] = {
                    'filled': 0,
                    'total': len(fields), 
                    'percentage': 0.0
                }
        
        return completeness
    
    def _estimate_completion_percentage(self, session: Dict) -> float:
        """Estimate overall conversation completion percentage"""
        stage_weights = {
            'user-profile-detection': 20,
            'smart-greeting': 10,
            'inquiry-collection': 50,
            'property-matching': 20
        }
        
        current_stage = session.get('current_stage', 'user-profile-detection')
        
        # Base progress on current stage
        stages = list(stage_weights.keys())
        if current_stage in stages:
            stage_index = stages.index(current_stage)
            base_progress = sum(list(stage_weights.values())[:stage_index])
            
            # Add partial progress for current stage based on data collected
            data_completeness = self._calculate_data_completeness(session.get('collected_data', {}))
            avg_completeness = sum(cat['percentage'] for cat in data_completeness.values()) / len(data_completeness)
            current_stage_progress = (avg_completeness / 100) * stage_weights[current_stage]
            
            return min(base_progress + current_stage_progress, 100.0)
        
        return 0.0