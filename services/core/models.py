"""
Data models and schemas for OneMinuta platform
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class AssetType(str, Enum):
    # Property types (v1 - supported)
    CONDO = "condo"
    VILLA = "villa"
    HOUSE = "house"
    LAND = "land"
    TOWNHOUSE = "townhouse"
    SHOPHOUSE = "shophouse"
    
    # Future asset types (v2+ - not yet supported)
    VEHICLE_CAR = "vehicle_car"
    VEHICLE_BIKE = "vehicle_bike"
    TIME_SLOT = "time_slot"
    TICKET = "ticket"
    SERVICE = "service"
    
    OTHER = "other"


class RentOrSale(str, Enum):
    RENT = "rent"
    SALE = "sale"
    BOTH = "both"


class PropertyStatus(str, Enum):
    AVAILABLE = "available"
    LEASED = "leased"
    SOLD = "sold"
    PENDING = "pending"
    REMOVED = "removed"


class EventType(str, Enum):
    CREATED = "created"
    PRICE_UPDATED = "price_updated"
    STATUS_UPDATED = "status_updated"
    FOR_RENT_OR_SALE_UPDATED = "for_rent_or_sale_updated"
    DESCRIPTION_CHANGED = "description_changed"
    PHOTO_ADDED = "photo_added"
    RELOCATED = "relocated"


class Price(BaseModel):
    value: float
    currency: str = "THB"
    period: Optional[str] = None  # "month", "year", None for sale


class Location(BaseModel):
    city: str
    area: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    country: str = "TH"
    
    @validator('lat')
    def validate_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('lon')
    def validate_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class SpheriCode(BaseModel):
    code: str
    bits_per_axis: int = 16
    prefix_len: int


class Media(BaseModel):
    telegram_file_ids: List[str] = []
    cloud_urls: List[str] = []
    local_paths: List[str] = []


class PropertyMeta(BaseModel):
    """Immutable metadata stored in meta.json - v1 Property only"""
    id: str
    owner_user_id: str
    asset_type: AssetType  # v1: only property types
    location: Location
    created_at: datetime
    source_channel: Optional[str] = None
    source_message_id: Optional[int] = None
    
    @validator('asset_type')
    def validate_asset_type_v1(cls, v):
        # v1 restriction: only property types
        supported_v1 = ['condo', 'villa', 'house', 'land', 'townhouse', 'shophouse', 'other']
        if v not in supported_v1:
            raise ValueError(f'Asset type {v} not supported in v1. Only properties are supported.')
        return v


class PropertyState(BaseModel):
    """Mutable state stored in state.json"""
    for_rent_or_sale: RentOrSale
    price: Price
    status: PropertyStatus
    last_updated: datetime
    spheri: SpheriCode
    media: Media
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    furnished: Optional[bool] = None
    parking: Optional[int] = None
    
    @validator('bedrooms', 'bathrooms', 'parking', 'floor', 'total_floors')
    def validate_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be positive')
        return v


class Event(BaseModel):
    """Event stored in events.ndjson"""
    ts: datetime
    type: EventType
    data: Dict[str, Any]
    actor: Optional[str] = None  # service that created event


class UserFilter(BaseModel):
    """User search preferences"""
    user_id: str
    areas: List[str]
    asset_types: List[AssetType]
    rent_or_sale: RentOrSale
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    radius_m: float = 5000
    notification_frequency: str = "daily"  # "immediate", "daily", "weekly"
    active: bool = True
    created_at: datetime
    updated_at: datetime


class SearchQuery(BaseModel):
    """API search query"""
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_m: float = 5000
    asset_type: Optional[AssetType] = None
    rent_or_sale: Optional[RentOrSale] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    area: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PropertyIndex(BaseModel):
    """Index stored in geo folders"""
    cell: str
    count: int
    by_status: Dict[PropertyStatus, int]
    by_asset_type: Dict[AssetType, int]
    properties: List[str]  # format: "@agent:property_id"
    children: List[str]  # child cell codes
    last_indexed: datetime


class UserProfile(BaseModel):
    """User profile stored in profile.json"""
    user_id: str
    handle: str  # @username
    public: bool = False
    created_at: datetime
    verified: bool = False


class UserPreferences(BaseModel):
    """User preferences stored in preferences.json"""
    language: str = "en"
    notify_hours_local: List[int] = [9, 21]  # Local hours for notifications
    radius_default_m: float = 3000
    timezone: str = "Asia/Bangkok"
    
    @validator('notify_hours_local')
    def validate_hours(cls, v):
        if not all(0 <= h <= 23 for h in v):
            raise ValueError('Hours must be between 0 and 23')
        return v


class Wish(BaseModel):
    """Single wish/request in wishlist"""
    kind: str  # "rent_my_asset", "buy", "find"
    asset_id: Optional[str] = None  # For "rent_my_asset"
    asset_type: Optional[AssetType] = None
    area_alias: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    created_at: datetime


class TimeSlot(BaseModel):
    """Available time slot"""
    from_time: datetime
    to_time: datetime
    available: bool = True
    asset_id: Optional[str] = None  # If linked to property viewing


class UserAvailability(BaseModel):
    """User availability stored in availability.json"""
    timezone: str = "Asia/Bangkok"
    slots: List[TimeSlot] = []


class UserIndex(BaseModel):
    """Index stored in user folders"""
    user_id: str
    total_properties: int
    active_properties: int
    by_status: Dict[PropertyStatus, int]
    by_asset_type: Dict[AssetType, int]
    last_updated: datetime