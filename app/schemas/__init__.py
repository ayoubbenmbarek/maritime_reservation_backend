"""
Pydantic schemas for the Maritime Reservation System.
Handles request/response validation and serialization.
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
import uuid


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        orm_mode = True
        use_enum_values = True
        validate_assignment = True
        allow_population_by_field_name = True


# Enums
class BookingStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"
    PARTIAL = "partial"


class PassengerTypeEnum(str, Enum):
    ADULT = "adult"
    CHILD = "child"
    INFANT = "infant"
    SENIOR = "senior"


class VehicleTypeEnum(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    CAMPER = "camper"
    TRUCK = "truck"
    BUS = "bus"


# User schemas
class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=3)
    preferred_language: str = Field("en", max_length=5)
    preferred_currency: str = Field("EUR", max_length=3)


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=100)
    username: Optional[str] = Field(None, max_length=100)
    terms_accepted: bool = True
    privacy_policy_accepted: bool = True
    marketing_consent: bool = False
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for user updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=3)
    preferred_language: Optional[str] = Field(None, max_length=5)
    preferred_currency: Optional[str] = Field(None, max_length=3)


class UserResponse(UserBase):
    """Schema for user responses."""
    id: uuid.UUID
    username: Optional[str] = None
    email_verified: bool
    phone_verified: bool
    account_status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int


class UserProfileBase(BaseSchema):
    """Base user profile schema."""
    title: Optional[str] = Field(None, max_length=10)
    middle_name: Optional[str] = Field(None, max_length=100)
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    passport_country: Optional[str] = Field(None, max_length=3)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relationship: Optional[str] = Field(None, max_length=50)
    dietary_restrictions: Optional[List[str]] = None
    accessibility_requirements: Optional[List[str]] = None
    bio: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=200)
    company_vat_number: Optional[str] = Field(None, max_length=50)


class UserProfileUpdate(UserProfileBase):
    """Schema for user profile updates."""
    travel_preferences: Optional[Dict[str, Any]] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None


class UserProfileResponse(UserProfileBase):
    """Schema for user profile responses."""
    user_id: uuid.UUID
    loyalty_points: int
    loyalty_tier: str
    referral_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Authentication schemas
class Token(BaseSchema):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseSchema):
    """Token data schema."""
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None


class LoginRequest(BaseSchema):
    """Login request schema."""
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""
    refresh_token: str


# Ferry operator schemas
class FerryOperatorBase(BaseSchema):
    """Base ferry operator schema."""
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=200)
    display_name: Optional[Dict[str, str]] = None
    description: Optional[Dict[str, str]] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)


class FerryOperatorCreate(FerryOperatorBase):
    """Schema for ferry operator creation."""
    api_endpoint: Optional[str] = Field(None, max_length=500)
    api_authentication_type: Optional[str] = Field(None, max_length=50)
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    currency: Optional[str] = Field(None, max_length=3)


class FerryOperatorResponse(FerryOperatorBase):
    """Schema for ferry operator responses."""
    id: uuid.UUID
    is_active: bool
    integration_status: str
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Port schemas
class PortBase(BaseSchema):
    """Base port schema."""
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=200)
    display_name: Optional[Dict[str, str]] = None
    city: str = Field(..., max_length=100)
    country: str = Field(..., max_length=3)
    region: Optional[str] = Field(None, max_length=100)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    timezone: Optional[str] = Field(None, max_length=50)


class PortCreate(PortBase):
    """Schema for port creation."""
    facilities: Optional[Dict[str, Any]] = None
    accessibility_features: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None
    address: Optional[Dict[str, Any]] = None
    transportation_links: Optional[Dict[str, Any]] = None


class PortResponse(PortBase):
    """Schema for port responses."""
    id: uuid.UUID
    facilities: Optional[Dict[str, Any]] = None
    accessibility_features: Optional[Dict[str, Any]] = None
    port_image_urls: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Route schemas
class RouteBase(BaseSchema):
    """Base route schema."""
    route_code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    distance_nautical_miles: Optional[int] = Field(None, ge=0)
    typical_duration_minutes: Optional[int] = Field(None, ge=0)
    route_type: Optional[str] = Field(None, max_length=20)


class RouteCreate(RouteBase):
    """Schema for route creation."""
    operator_id: uuid.UUID
    departure_port_id: uuid.UUID
    arrival_port_id: uuid.UUID
    seasonal_start_date: Optional[date] = None
    seasonal_end_date: Optional[date] = None
    operating_days: Optional[List[int]] = Field(None, min_items=0, max_items=7)
    route_description: Optional[Dict[str, str]] = None
    amenities: Optional[Dict[str, Any]] = None
    vessel_types: Optional[List[str]] = None
    passenger_capacity_min: Optional[int] = Field(None, ge=0)
    passenger_capacity_max: Optional[int] = Field(None, ge=0)
    vehicle_capacity_min: Optional[int] = Field(None, ge=0)
    vehicle_capacity_max: Optional[int] = Field(None, ge=0)


class RouteResponse(RouteBase):
    """Schema for route responses."""
    id: uuid.UUID
    operator: FerryOperatorResponse
    departure_port: PortResponse
    arrival_port: PortResponse
    amenities: Optional[Dict[str, Any]] = None
    vessel_types: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Booking schemas
class BookingPassengerBase(BaseSchema):
    """Base booking passenger schema."""
    passenger_type: PassengerTypeEnum
    title: Optional[str] = Field(None, max_length=10)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=3)
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    special_assistance: bool = False
    assistance_details: Optional[str] = None
    dietary_requirements: Optional[List[str]] = None
    seat_preference: Optional[str] = Field(None, max_length=50)


class BookingPassengerCreate(BookingPassengerBase):
    """Schema for booking passenger creation."""
    pass


class BookingPassengerResponse(BookingPassengerBase):
    """Schema for booking passenger responses."""
    id: uuid.UUID
    cabin_assignment: Optional[str] = None
    deck_level: Optional[int] = None
    passenger_fare: Optional[Decimal] = None
    taxes_amount: Optional[Decimal] = None
    created_at: datetime


class BookingVehicleBase(BaseSchema):
    """Base booking vehicle schema."""
    vehicle_type: VehicleTypeEnum
    make: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    license_plate: Optional[str] = Field(None, max_length=20)
    length_meters: Optional[Decimal] = Field(None, ge=0, le=50)
    width_meters: Optional[Decimal] = Field(None, ge=0, le=10)
    height_meters: Optional[Decimal] = Field(None, ge=0, le=10)
    weight_kg: Optional[int] = Field(None, ge=0)
    fuel_type: Optional[str] = Field(None, max_length=20)
    driver_name: Optional[str] = Field(None, max_length=200)
    driver_license_number: Optional[str] = Field(None, max_length=50)


class BookingVehicleCreate(BookingVehicleBase):
    """Schema for booking vehicle creation."""
    insurance_required: bool = False


class BookingVehicleResponse(BookingVehicleBase):
    """Schema for booking vehicle responses."""
    id: uuid.UUID
    vehicle_fare: Optional[Decimal] = None
    insurance_required: bool
    insurance_amount: Optional[Decimal] = None
    deck_assignment: Optional[str] = None
    parking_space: Optional[str] = None
    created_at: datetime


class BookingBase(BaseSchema):
    """Base booking schema."""
    route_id: uuid.UUID
    departure_date: date
    departure_time: str = Field(..., regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$")
    passenger_count: int = Field(..., ge=1, le=20)
    vehicle_count: int = Field(0, ge=0, le=5)
    special_requests: Optional[str] = None


class BookingCreate(BookingBase):
    """Schema for booking creation."""
    passengers: List[BookingPassengerCreate]
    vehicles: Optional[List[BookingVehicleCreate]] = None
    
    @validator("passengers")
    def validate_passengers(cls, v, values):
        if len(v) != values.get("passenger_count", 0):
            raise ValueError("Number of passengers must match passenger_count")
        return v
    
    @validator("vehicles")
    def validate_vehicles(cls, v, values):
        if v and len(v) != values.get("vehicle_count", 0):
            raise ValueError("Number of vehicles must match vehicle_count")
        return v


class BookingUpdate(BaseSchema):
    """Schema for booking updates."""
    special_requests: Optional[str] = None
    booking_notes: Optional[str] = None


class BookingResponse(BookingBase):
    """Schema for booking responses."""
    id: uuid.UUID
    booking_reference: str
    operator: FerryOperatorResponse
    route: RouteResponse
    booking_status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    arrival_date: date
    arrival_time: str
    total_amount: Decimal
    currency: str
    commission_amount: Optional[Decimal] = None
    booking_fee: Optional[Decimal] = None
    taxes_amount: Optional[Decimal] = None
    discount_amount: Decimal
    final_amount: Decimal
    booking_source: Optional[str] = None
    passengers: List[BookingPassengerResponse]
    vehicles: List[BookingVehicleResponse]
    expires_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Search schemas
class RouteSearchRequest(BaseSchema):
    """Schema for route search requests."""
    departure_port_code: str = Field(..., max_length=10)
    arrival_port_code: str = Field(..., max_length=10)
    departure_date: date
    return_date: Optional[date] = None
    passenger_count: int = Field(..., ge=1, le=20)
    vehicle_count: int = Field(0, ge=0, le=5)
    passenger_types: Optional[Dict[PassengerTypeEnum, int]] = None
    vehicle_types: Optional[Dict[VehicleTypeEnum, int]] = None
    preferred_operators: Optional[List[str]] = None
    max_price: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("EUR", max_length=3)
    
    @validator("departure_date")
    def validate_departure_date(cls, v):
        if v < date.today():
            raise ValueError("Departure date cannot be in the past")
        return v
    
    @validator("return_date")
    def validate_return_date(cls, v, values):
        if v and v <= values.get("departure_date"):
            raise ValueError("Return date must be after departure date")
        return v


class RouteSearchResult(BaseSchema):
    """Schema for route search results."""
    route: RouteResponse
    available_departures: List[Dict[str, Any]]
    pricing: Dict[str, Any]
    availability: Dict[str, Any]


class RouteSearchResponse(BaseSchema):
    """Schema for route search responses."""
    results: List[RouteSearchResult]
    total_results: int
    search_params: RouteSearchRequest
    search_timestamp: datetime


# Payment schemas
class PaymentMethodBase(BaseSchema):
    """Base payment method schema."""
    payment_gateway: str = Field(..., max_length=50)
    payment_method: str = Field(..., max_length=50)


class PaymentRequest(PaymentMethodBase):
    """Schema for payment requests."""
    booking_id: uuid.UUID
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(..., max_length=3)
    payment_metadata: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None


class PaymentResponse(BaseSchema):
    """Schema for payment responses."""
    id: uuid.UUID
    transaction_reference: str
    booking_id: uuid.UUID
    payment_gateway: str
    gateway_transaction_id: Optional[str] = None
    amount: Decimal
    currency: str
    transaction_status: str
    processed_at: Optional[datetime] = None
    created_at: datetime


# Generic response schemas
class MessageResponse(BaseSchema):
    """Generic message response schema."""
    message: str
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseSchema):
    """Error response schema."""
    error: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseSchema):
    """Paginated response schema."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool


# Health check schema
class HealthCheckResponse(BaseSchema):
    """Health check response schema."""
    status: str
    service: str
    version: str
    environment: str
    timestamp: float
    checks: Optional[Dict[str, bool]] = None

