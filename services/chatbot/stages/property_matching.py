"""
Property Matching Stage

Final stage that searches for properties matching user requirements
and presents results in a conversational format.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_stage import BaseChatbotStage


class PropertyMatchingStage(BaseChatbotStage):
    """Match user requirements with available properties and present results"""
    
    def __init__(self, storage_path: str, openai_api_key: str):
        super().__init__(openai_api_key)
        self.storage_path = Path(storage_path)
        
        # Add libs to path for property search
        libs_path = Path(__file__).parent.parent.parent.parent / "libs" / "geo-spherical"
        if str(libs_path) not in sys.path:
            sys.path.insert(0, str(libs_path))
    
    def get_stage_name(self) -> str:
        return "property-matching"
    
    async def process(self, user_id: str, message: str, session: Dict, context: Dict = None) -> Dict:
        """Process message and match properties to user requirements"""
        
        # Get user requirements from session
        collected_data = session.get('collected_data', {})
        requirements = collected_data.get('requirements', {})
        profile = collected_data.get('profile', {})
        language = profile.get('language_preference', 'en')
        
        if not requirements:
            return {
                'reply': self._get_response_template(language, "error"),
                'data_collected': {},
                'confidence': 0.2,
                'user_message': message
            }
        
        # Search for matching properties
        matching_properties = await self._search_properties(requirements)
        
        if not matching_properties:
            # No properties found
            response = await self._generate_no_results_response(requirements, language)
            return {
                'reply': response,
                'properties_found': [],
                'session_complete': True,
                'confidence': 0.8,
                'user_message': message
            }
        
        # Generate personalized property presentation
        presentation = await self._generate_property_presentation(matching_properties, requirements, language)
        
        return {
            'reply': presentation,
            'properties_found': matching_properties,
            'session_complete': True,
            'data_collected': {'search_results': {
                'count': len(matching_properties),
                'search_criteria': requirements
            }},
            'confidence': 0.9,
            'user_message': message
        }
    
    async def _search_properties(self, requirements: Dict) -> List[Dict]:
        """Search for properties matching user requirements"""
        
        try:
            # Use existing CLI search functionality
            sys.path.insert(0, str(self.storage_path.parent))
            from oneminuta_cli import OneMinutaCLI
            
            cli = OneMinutaCLI(str(self.storage_path))
            
            # Convert requirements to search parameters
            search_params = self._convert_requirements_to_search_params(requirements)
            
            if not search_params:
                return []
            
            # Perform search using CLI
            results = cli.search(**search_params)
            
            # Return up to 5 best matches
            return results[:5] if results else []
            
        except Exception as e:
            self.logger.error(f"Error searching properties: {e}")
            return []
    
    def _convert_requirements_to_search_params(self, requirements: Dict) -> Dict:
        """Convert user requirements to OneMinutaCLI search parameters"""
        
        search_params = {}
        
        # Handle location preference
        location = requirements.get('location_preference', '').lower()
        
        # Map common location names to coordinates
        location_mapping = {
            'phuket': {'lat': 7.8804, 'lon': 98.3923},
            'rawai': {'lat': 7.77965, 'lon': 98.32532},
            'kata': {'lat': 7.8167, 'lon': 98.3500},
            'patong': {'lat': 7.8980, 'lon': 98.2940},
            'bangkok': {'lat': 13.7563, 'lon': 100.5018}
        }
        
        # Find matching location
        for loc_name, coords in location_mapping.items():
            if loc_name in location:
                search_params.update(coords)
                break
        
        # If no specific location found, use default Phuket coordinates
        if 'lat' not in search_params:
            search_params.update(location_mapping['phuket'])
        
        # Set search radius based on specificity
        search_params['radius_m'] = 10000  # 10km default
        
        # Handle rent or sale
        rent_or_sale = requirements.get('rent_or_sale', '').lower()
        if rent_or_sale == 'rent':
            search_params['rent'] = True
        elif rent_or_sale == 'sale':
            search_params['sale'] = True
        
        # Handle budget
        if 'budget_min' in requirements:
            search_params['min_price'] = requirements['budget_min']
        if 'budget_max' in requirements:
            search_params['max_price'] = requirements['budget_max']
        
        # Handle property features
        if 'bedrooms' in requirements:
            search_params['bedrooms'] = requirements['bedrooms']
        if 'bathrooms' in requirements:
            search_params['bathrooms'] = requirements['bathrooms']
        
        # Handle property type
        property_type = requirements.get('property_type')
        if property_type:
            search_params['asset_type'] = property_type
        
        # Set reasonable limit
        search_params['limit'] = 10
        search_params['json_output'] = True
        
        return search_params
    
    async def _generate_property_presentation(self, properties: List[Dict], requirements: Dict, language: str) -> str:
        """Generate personalized presentation of matching properties"""
        
        system_prompt = f"""You are OneMinuta's property expert presenting search results to a client. 

Create an engaging presentation of the properties found that:
1. Starts with enthusiasm about the results
2. Highlights how the properties match their requirements
3. Presents each property with key details
4. Uses a conversational, expert tone
5. Language: {language} ({'English' if language == 'en' else 'Russian'})
6. Include property IDs for reference
7. End with next steps offer

User requirements: {json.dumps(requirements, indent=2)}

Properties found: {json.dumps(properties, indent=2)}

Format as a natural conversation, not a rigid list.
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.8,
            max_tokens=800
        )
        
        if response:
            return response
        
        # Fallback presentation
        return self._generate_fallback_presentation(properties, requirements, language)
    
    def _generate_fallback_presentation(self, properties: List[Dict], requirements: Dict, language: str) -> str:
        """Generate fallback presentation if LLM fails"""
        
        intro = {
            "en": f"Excellent! I found {len(properties)} properties that match your requirements:",
            "ru": f"Отлично! Я нашел {len(properties)} объектов недвижимости, соответствующих вашим требованиям:"
        }
        
        outro = {
            "en": "\nWould you like more details about any of these properties? I can provide additional information or help you schedule viewings.",
            "ru": "\nХотели бы вы получить больше деталей о любом из этих объектов? Я могу предоставить дополнительную информацию или помочь запланировать просмотры."
        }
        
        lang_intro = intro.get(language, intro["en"])
        lang_outro = outro.get(language, outro["en"])
        
        result = [lang_intro, ""]
        
        for i, prop in enumerate(properties, 1):
            # Format property details
            prop_type = prop.get('type', 'property').title()
            area = prop.get('location', {}).get('area', 'Unknown')
            distance = prop.get('distance_m', 0)
            price = prop.get('price', {})
            
            price_text = ""
            if price.get('value'):
                if prop.get('for_rent_or_sale') == 'rent':
                    price_text = f"Rent: {price['value']:,} {price.get('currency', 'THB')}/month"
                else:
                    price_text = f"Sale: {price['value']:,} {price.get('currency', 'THB')}"
            
            details = []
            if prop.get('bedrooms'):
                details.append(f"{prop['bedrooms']} bed")
            if prop.get('bathrooms'):
                details.append(f"{prop['bathrooms']} bath")
            if prop.get('area_sqm'):
                details.append(f"{prop['area_sqm']} sqm")
            
            detail_text = ", ".join(details) if details else ""
            
            prop_text = f"{i}. {prop_type} in {area} ({distance}m away)"
            if price_text:
                prop_text += f"\n   {price_text}"
            if detail_text:
                prop_text += f"\n   {detail_text}"
            prop_text += f"\n   ID: {prop.get('id', 'Unknown')}"
            
            result.append(prop_text)
        
        result.append(lang_outro)
        
        return "\n".join(result)
    
    async def _generate_no_results_response(self, requirements: Dict, language: str) -> str:
        """Generate response when no properties match requirements"""
        
        system_prompt = f"""Generate a helpful response when no properties match the user's requirements.

User requirements: {json.dumps(requirements, indent=2)}
Language: {language} ({'English' if language == 'en' else 'Russian'})

Generate a response that:
1. Acknowledges their specific requirements
2. Explains why no matches were found (be helpful, not disappointing)
3. Suggests alternatives (expanding criteria, different areas, etc.)
4. Offers to help adjust their search
5. Keep it encouraging and solution-focused
6. 3-4 sentences maximum
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.7,
            max_tokens=300
        )
        
        if response:
            return response
        
        # Fallback no results response
        fallbacks = {
            "en": "I couldn't find properties matching your exact criteria right now. Would you like me to expand the search area or adjust the budget range? I'm confident we can find great options with small modifications to your requirements.",
            "ru": "Я не смог найти недвижимость, точно соответствующую вашим критериям. Хотели бы вы расширить область поиска или скорректировать бюджетный диапазон? Я уверен, что мы найдем отличные варианты с небольшими изменениями ваших требований."
        }
        
        return fallbacks.get(language, fallbacks["en"])