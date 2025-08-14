"""
Property Listing Extractor
Identifies and extracts property information from Telegram messages
"""

import re
import logging
from typing import List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from services.core.models import AssetType, RentOrSale


@dataclass
class ExtractedProperty:
    """Extracted property data from Telegram message"""

    # Source information
    channel: str
    message_id: int
    sender_id: str
    message_text: str
    message_date: datetime

    # Property details
    asset_type: Optional[AssetType] = None
    rent_or_sale: Optional[RentOrSale] = None
    price: Optional[float] = None
    currency: str = "THB"

    # Property specifications
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqm: Optional[float] = None
    floor: Optional[int] = None

    # Location
    location_text: Optional[str] = None
    extracted_locations: List[str] = None

    # Features
    features: List[str] = None

    # Contact information
    contact_info: List[str] = None

    # Media
    has_photos: bool = False
    photo_count: int = 0

    # Confidence
    extraction_confidence: float = 0.0

    def __post_init__(self):
        if self.extracted_locations is None:
            self.extracted_locations = []
        if self.features is None:
            self.features = []
        if self.contact_info is None:
            self.contact_info = []


class PropertyExtractor:
    """Extracts property listings from Telegram messages"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Property type patterns
        self.property_types = {
            AssetType.CONDO: [
                "condo",
                "condominium",
                "apartment",
                "apt",
                "unit",
                "квартира",
                "кондо",
                "кондоминиум",
                "апартамент",
            ],
            AssetType.HOUSE: [
                "house",
                "villa",
                "townhouse",
                "home",
                "residence",
                "дом",
                "вилла",
                "таунхаус",
                "резиденция",
            ],
            AssetType.LAND: [
                "land",
                "plot",
                "lot",
                "rai",
                "ngan",
                "wah",
                "земля",
                "участок",
                "рай",
                "нган",
            ],
        }

        # Sale/Rent patterns
        self.transaction_types = {
            RentOrSale.SALE: [
                "for sale",
                "sale",
                "buy",
                "purchase",
                "own",
                "ownership",
                "продажа",
                "продается",
                "купить",
                "покупка",
                "собственность",
            ],
            RentOrSale.RENT: [
                "for rent",
                "rent",
                "rental",
                "lease",
                "monthly",
                "аренда",
                "сдается",
                "снять",
                "арендовать",
                "месячно",
            ],
        }

        # Price patterns (more comprehensive)
        self.price_patterns = [
            # Thai Baht
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:baht|bahts|฿|thb)",
            r"฿\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:บาท|ล้านบาท)",
            # USD
            r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:usd|dollars?)",
            # Millions/thousands
            r"(\d+(?:\.\d+)?)\s*(?:million|mil|m)\s*(?:baht|bahts|฿|thb|\$)",
            r"(\d+(?:\.\d+)?)\s*(?:thousand|k)\s*(?:baht|bahts|฿|thb|\$)",
            # Russian Rubles
            r"(\d+(?:\s?\d{3})*(?:\.\d+)?)\s*(?:руб|рублей|₽)",
            r"(\d+(?:\.\d+)?)\s*(?:млн|миллион)\s*(?:руб|рублей)",
            # General price indicators
            r"(?:price|цена):\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:per month|в месяц)",
        ]

        # Room patterns
        self.room_patterns = [
            r"(\d+)\s*(?:bed|bedroom|br|спальн)",
            r"(\d+)\s*(?:bath|bathroom|ванн)",
            r"(\d+)\s*(?:floor|этаж)",
        ]

        # Size patterns
        self.size_patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:sqm|sq\.?m|square\s*meter|кв\.?м)",
            r"(\d+(?:\.\d+)?)\s*(?:m2|м2)",
            r"size:\s*(\d+(?:\.\d+)?)",
        ]

        # Location patterns (Thailand focused)
        self.location_keywords = [
            # Bangkok areas
            "bangkok",
            "sukhumvit",
            "silom",
            "sathorn",
            "phrom phong",
            "thonglor",
            "ekkamai",
            "asoke",
            "chitlom",
            "siam",
            "ratchada",
            "huai khwang",
            # Phuket areas
            "phuket",
            "patong",
            "kata",
            "karon",
            "rawai",
            "nai harn",
            "bang tao",
            "surin",
            "kamala",
            "mai khao",
            "chalong",
            "phuket town",
            # Pattaya areas
            "pattaya",
            "jomtien",
            "na jomtien",
            "wong amat",
            "central pattaya",
            "north pattaya",
            "south pattaya",
            # Other popular areas
            "hua hin",
            "koh samui",
            "chiang mai",
            "chiang rai",
            "krabi",
            # Russian translations
            "бангкок",
            "пхукет",
            "патонг",
            "пхукета",
            "паттайя",
            "хуа хин",
        ]

        # Feature keywords
        self.feature_keywords = {
            "pool": ["pool", "swimming", "бассейн"],
            "gym": ["gym", "fitness", "спортзал", "фитнес"],
            "parking": ["parking", "garage", "car park", "парковка", "гараж"],
            "furnished": ["furnished", "furniture", "меблированный", "мебель"],
            "balcony": ["balcony", "terrace", "балкон", "терраса"],
            "view": ["sea view", "ocean view", "city view", "вид на море", "вид на город"],
            "security": ["security", "24h", "24/7", "guard", "охрана", "безопасность"],
            "elevator": ["elevator", "lift", "лифт"],
            "wifi": ["wifi", "internet", "wi-fi", "интернет"],
            "aircon": ["air con", "aircon", "a/c", "кондиционер"],
        }

        # Contact patterns
        self.contact_patterns = [
            r"(?:contact|call|phone|tel|line|whatsapp):\s*([+]?\d[\d\s\-\(\)]{7,})",
            r"([+]?\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4})",
            r"@\w+",  # Telegram handles
            r"line:\s*(\w+)",
            r"(?:контакт|звонить|телефон):\s*([+]?\d[\d\s\-\(\)]{7,})",
        ]

    def is_property_listing(self, message_text: str) -> bool:
        """
        Determine if a message is a property listing
        More sophisticated than the analytics filter
        """
        text_lower = message_text.lower()

        # Must have at least one property type
        has_property_type = any(
            prop_word in text_lower
            for prop_types in self.property_types.values()
            for prop_word in prop_types
        )

        # Must have transaction type (sale/rent)
        has_transaction = any(
            trans_word in text_lower
            for trans_types in self.transaction_types.values()
            for trans_word in trans_types
        )

        # Should have price or location
        has_price = any(re.search(pattern, text_lower) for pattern in self.price_patterns)
        has_location = any(loc in text_lower for loc in self.location_keywords)

        # Should have rooms or size
        has_rooms = any(re.search(pattern, text_lower) for pattern in self.room_patterns)
        has_size = any(re.search(pattern, text_lower) for pattern in self.size_patterns)

        # Calculate confidence
        score = 0
        if has_property_type:
            score += 25
        if has_transaction:
            score += 25
        if has_price:
            score += 20
        if has_location:
            score += 15
        if has_rooms:
            score += 10
        if has_size:
            score += 5

        # Must have minimum score to be considered listing
        return score >= 40

    def extract_property_details(
        self,
        message_text: str,
        channel: str,
        message_id: int,
        sender_id: str,
        message_date: datetime,
    ) -> Optional[ExtractedProperty]:
        """Extract property details from a message"""

        # First check if it's a property listing
        if not self.is_property_listing(message_text):
            return None

        extracted = ExtractedProperty(
            channel=channel,
            message_id=message_id,
            sender_id=sender_id,
            message_text=message_text,
            message_date=message_date,
        )

        text_lower = message_text.lower()

        # Extract property type
        extracted.asset_type = self._extract_property_type(text_lower)

        # Extract transaction type
        extracted.rent_or_sale = self._extract_transaction_type(text_lower)

        # Extract price
        extracted.price, extracted.currency = self._extract_price(text_lower)

        # Extract rooms and size
        extracted.bedrooms = self._extract_rooms(text_lower, "bed")
        extracted.bathrooms = self._extract_rooms(text_lower, "bath")
        extracted.floor = self._extract_rooms(text_lower, "floor")
        extracted.size_sqm = self._extract_size(text_lower)

        # Extract location
        extracted.extracted_locations = self._extract_locations(text_lower)
        if extracted.extracted_locations:
            extracted.location_text = ", ".join(extracted.extracted_locations[:3])

        # Extract features
        extracted.features = self._extract_features(text_lower)

        # Extract contact info
        extracted.contact_info = self._extract_contacts(message_text)

        # Calculate extraction confidence
        extracted.extraction_confidence = self._calculate_confidence(extracted)

        return extracted

    def _extract_property_type(self, text_lower: str) -> Optional[AssetType]:
        """Extract property type from text"""
        for prop_type, keywords in self.property_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return prop_type
        return None

    def _extract_transaction_type(self, text_lower: str) -> Optional[RentOrSale]:
        """Extract transaction type (sale/rent) from text"""
        for trans_type, keywords in self.transaction_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return trans_type
        return None

    def _extract_price(self, text_lower: str) -> Tuple[Optional[float], str]:
        """Extract price and currency from text"""
        for pattern in self.price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    price_str = match.group(1).replace(",", "").replace(" ", "")
                    price = float(price_str)

                    # Detect currency and normalize
                    if any(curr in match.group(0) for curr in ["$", "usd", "dollar"]):
                        return price, "USD"
                    elif any(curr in match.group(0) for curr in ["руб", "₽"]):
                        return price, "RUB"
                    else:
                        # Default to THB
                        return price, "THB"

                except ValueError:
                    continue

        return None, "THB"

    def _extract_rooms(self, text_lower: str, room_type: str) -> Optional[int]:
        """Extract number of rooms (bedrooms, bathrooms, floors)"""
        patterns = {
            "bed": r"(\d+)\s*(?:bed|bedroom|br|спальн)",
            "bath": r"(\d+)\s*(?:bath|bathroom|ванн)",
            "floor": r"(\d+)\s*(?:floor|этаж)",
        }

        pattern = patterns.get(room_type)
        if pattern:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None

    def _extract_size(self, text_lower: str) -> Optional[float]:
        """Extract property size in square meters"""
        for pattern in self.size_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_locations(self, text_lower: str) -> List[str]:
        """Extract location keywords from text"""
        found_locations = []
        for location in self.location_keywords:
            if location in text_lower:
                found_locations.append(location.title())
        return found_locations

    def _extract_features(self, text_lower: str) -> List[str]:
        """Extract property features from text"""
        found_features = []
        for feature, keywords in self.feature_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_features.append(feature)
        return found_features

    def _extract_contacts(self, message_text: str) -> List[str]:
        """Extract contact information from text"""
        contacts = []
        for pattern in self.contact_patterns:
            matches = re.findall(pattern, message_text)
            contacts.extend(matches)
        return contacts

    def _calculate_confidence(self, extracted: ExtractedProperty) -> float:
        """Calculate extraction confidence score (0-100)"""
        score = 0.0

        # Base score for having property type and transaction
        if extracted.asset_type:
            score += 20
        if extracted.rent_or_sale:
            score += 20

        # Price information
        if extracted.price:
            score += 15

        # Location information
        if extracted.extracted_locations:
            score += 10

        # Property specifications
        if extracted.bedrooms:
            score += 8
        if extracted.bathrooms:
            score += 7
        if extracted.size_sqm:
            score += 10

        # Features and contact
        if extracted.features:
            score += 5
        if extracted.contact_info:
            score += 5

        return min(100.0, score)
