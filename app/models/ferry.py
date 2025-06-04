"""
Ferry and booking models for the Maritime Reservation System.
Handles ferry operators, routes, bookings, and related entities.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Date, ARRAY, JSON, DECIMAL, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from app.db.session import Base


class BookingStatus(str, Enum):
    """Booking status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"
    PARTIAL = "partial"


class FerryOperator(Base):
    """Ferry operator model with API integration settings."""
    
    __tablename__ = "ferry_operators"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # CTN, GNV, CORS, etc.
    name = Column(String(200), nullable=False)
    display_name = Column(JSON, nullable=True)  # Multilingual display names
    description = Column(JSON, nullable=True)  # Multilingual descriptions
    
    # Branding and contact
    logo_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    headquarters_address = Column(JSON, nullable=True)
    
    # API integration settings
    api_endpoint = Column(String(500), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    api_authentication_type = Column(String(50), nullable=True)
    api_rate_limit = Column(Integer, nullable=True)
    api_timeout_seconds = Column(Integer, default=30, nullable=False)
    
    # Business terms
    booking_terms_url = Column(JSON, nullable=True)  # Multilingual terms URLs
    cancellation_policy = Column(JSON, nullable=True)
    refund_policy = Column(JSON, nullable=True)
    commission_rate = Column(DECIMAL(5, 4), nullable=True)
    currency = Column(String(3), nullable=True)
    
    # Status and synchronization
    is_active = Column(Boolean, default=True, nullable=False)
    integration_status = Column(String(20), default="pending", nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    routes = relationship("Route", back_populates="operator", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="operator")
    
    def __repr__(self) -> str:
        return f"<FerryOperator(id={self.id}, code={self.code}, name={self.name})>"


class Port(Base):
    """Port model with geographical and facility information."""
    
    __tablename__ = "ports"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # IATA or custom codes
    name = Column(String(200), nullable=False)
    display_name = Column(JSON, nullable=True)  # Multilingual port names
    
    # Location information
    city = Column(String(100), nullable=False)
    country = Column(String(3), nullable=False, index=True)  # ISO 3166-1 alpha-3
    region = Column(String(100), nullable=True)
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Facilities and services
    facilities = Column(JSON, nullable=True)  # parking, restaurants, wifi, etc.
    accessibility_features = Column(JSON, nullable=True)
    contact_info = Column(JSON, nullable=True)
    address = Column(JSON, nullable=True)
    transportation_links = Column(JSON, nullable=True)  # bus, train, airport connections
    
    # Media
    port_image_urls = Column(ARRAY(Text), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    departure_routes = relationship("Route", foreign_keys="Route.departure_port_id", back_populates="departure_port")
    arrival_routes = relationship("Route", foreign_keys="Route.arrival_port_id", back_populates="arrival_port")
    
    def __repr__(self) -> str:
        return f"<Port(id={self.id}, code={self.code}, name={self.name}, city={self.city})>"


class Route(Base):
    """Ferry route model with scheduling and operational information."""
    
    __tablename__ = "routes"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("ferry_operators.id"), nullable=False, index=True)
    route_code = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    
    # Route endpoints
    departure_port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False, index=True)
    arrival_port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False, index=True)
    
    # Route characteristics
    distance_nautical_miles = Column(Integer, nullable=True)
    typical_duration_minutes = Column(Integer, nullable=True)
    route_type = Column(String(20), nullable=True)  # regular, seasonal, charter
    
    # Seasonal operation
    seasonal_start_date = Column(Date, nullable=True)
    seasonal_end_date = Column(Date, nullable=True)
    operating_days = Column(ARRAY(Integer), nullable=True)  # 0=Sunday, 1=Monday, etc.
    
    # Descriptions and amenities
    route_description = Column(JSON, nullable=True)  # Multilingual descriptions
    amenities = Column(JSON, nullable=True)  # onboard facilities
    vessel_types = Column(ARRAY(String(50)), nullable=True)
    
    # Capacity information
    passenger_capacity_min = Column(Integer, nullable=True)
    passenger_capacity_max = Column(Integer, nullable=True)
    vehicle_capacity_min = Column(Integer, nullable=True)
    vehicle_capacity_max = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    operator = relationship("FerryOperator", back_populates="routes")
    departure_port = relationship("Port", foreign_keys=[departure_port_id], back_populates="departure_routes")
    arrival_port = relationship("Port", foreign_keys=[arrival_port_id], back_populates="arrival_routes")
    bookings = relationship("Booking", back_populates="route")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("departure_port_id != arrival_port_id", name="check_different_ports"),
    )
    
    def __repr__(self) -> str:
        return f"<Route(id={self.id}, code={self.route_code}, name={self.name})>"


class Booking(Base):
    """Main booking model with comprehensive reservation information."""
    
    __tablename__ = "bookings"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_reference = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # Nullable for guest bookings
    
    # Booking relationships
    operator_id = Column(UUID(as_uuid=True), ForeignKey("ferry_operators.id"), nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=False, index=True)
    operator_booking_reference = Column(String(100), nullable=True)
    
    # Status tracking
    booking_status = Column(String(20), default=BookingStatus.PENDING, nullable=False, index=True)
    payment_status = Column(String(20), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Travel details
    departure_date = Column(Date, nullable=False, index=True)
    departure_time = Column(String(8), nullable=False)  # HH:MM:SS format
    arrival_date = Column(Date, nullable=False)
    arrival_time = Column(String(8), nullable=False)
    
    # Passenger and vehicle counts
    passenger_count = Column(Integer, nullable=False)
    vehicle_count = Column(Integer, default=0, nullable=False)
    
    # Financial information
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    commission_amount = Column(DECIMAL(10, 2), nullable=True)
    booking_fee = Column(DECIMAL(10, 2), nullable=True)
    taxes_amount = Column(DECIMAL(10, 2), nullable=True)
    discount_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    final_amount = Column(DECIMAL(10, 2), nullable=False)
    
    # Booking metadata
    booking_source = Column(String(50), nullable=True)  # web, mobile, api, agent
    special_requests = Column(Text, nullable=True)
    booking_notes = Column(Text, nullable=True)
    
    # Cancellation information
    cancellation_reason = Column(Text, nullable=True)
    cancellation_fee = Column(DECIMAL(10, 2), nullable=True)
    refund_amount = Column(DECIMAL(10, 2), nullable=True)
    
    # Important timestamps
    expires_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Standard timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    operator = relationship("FerryOperator", back_populates="bookings")
    route = relationship("Route", back_populates="bookings")
    passengers = relationship("BookingPassenger", back_populates="booking", cascade="all, delete-orphan")
    vehicles = relationship("BookingVehicle", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("PaymentTransaction", back_populates="booking", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("passenger_count > 0", name="check_positive_passengers"),
        CheckConstraint("vehicle_count >= 0", name="check_non_negative_vehicles"),
        CheckConstraint("total_amount >= 0", name="check_non_negative_amount"),
        CheckConstraint("final_amount >= 0", name="check_non_negative_final_amount"),
    )
    
    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, reference={self.booking_reference}, status={self.booking_status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if booking is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_confirmed(self) -> bool:
        """Check if booking is confirmed."""
        return self.booking_status == BookingStatus.CONFIRMED
    
    @property
    def is_paid(self) -> bool:
        """Check if booking is fully paid."""
        return self.payment_status == PaymentStatus.PAID


class BookingPassenger(Base):
    """Passenger information for bookings."""
    
    __tablename__ = "booking_passengers"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True)
    
    # Passenger classification
    passenger_type = Column(String(20), nullable=False)  # adult, child, infant, senior
    
    # Personal information
    title = Column(String(10), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(3), nullable=True)
    
    # Travel documents
    passport_number = Column(String(50), nullable=True)
    passport_expiry = Column(Date, nullable=True)
    
    # Special requirements
    special_assistance = Column(Boolean, default=False, nullable=False)
    assistance_details = Column(Text, nullable=True)
    dietary_requirements = Column(ARRAY(Text), nullable=True)
    
    # Seating and accommodation
    seat_preference = Column(String(50), nullable=True)
    cabin_assignment = Column(String(20), nullable=True)
    deck_level = Column(Integer, nullable=True)
    
    # Pricing
    passenger_fare = Column(DECIMAL(10, 2), nullable=True)
    taxes_amount = Column(DECIMAL(10, 2), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="passengers")
    
    def __repr__(self) -> str:
        return f"<BookingPassenger(id={self.id}, name={self.first_name} {self.last_name}, type={self.passenger_type})>"


class BookingVehicle(Base):
    """Vehicle information for bookings."""
    
    __tablename__ = "booking_vehicles"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True)
    
    # Vehicle classification
    vehicle_type = Column(String(50), nullable=False)  # car, motorcycle, camper, truck
    
    # Vehicle details
    make = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    license_plate = Column(String(20), nullable=True)
    
    # Dimensions
    length_meters = Column(DECIMAL(4, 2), nullable=True)
    width_meters = Column(DECIMAL(4, 2), nullable=True)
    height_meters = Column(DECIMAL(4, 2), nullable=True)
    weight_kg = Column(Integer, nullable=True)
    fuel_type = Column(String(20), nullable=True)
    
    # Driver information
    driver_name = Column(String(200), nullable=True)
    driver_license_number = Column(String(50), nullable=True)
    
    # Pricing and insurance
    vehicle_fare = Column(DECIMAL(10, 2), nullable=True)
    insurance_required = Column(Boolean, default=False, nullable=False)
    insurance_amount = Column(DECIMAL(10, 2), nullable=True)
    
    # Deck assignment
    deck_assignment = Column(String(20), nullable=True)
    parking_space = Column(String(20), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="vehicles")
    
    def __repr__(self) -> str:
        return f"<BookingVehicle(id={self.id}, type={self.vehicle_type}, license={self.license_plate})>"


class PaymentTransaction(Base):
    """Payment transaction model with comprehensive tracking."""
    
    __tablename__ = "payment_transactions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True)
    transaction_reference = Column(String(100), unique=True, nullable=False, index=True)
    
    # Payment gateway information
    payment_gateway = Column(String(50), nullable=False)  # stripe, paypal, bank_transfer
    gateway_transaction_id = Column(String(200), nullable=True)
    payment_method = Column(String(50), nullable=True)  # credit_card, debit_card, paypal, bank_transfer
    
    # Card information (if applicable)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(20), nullable=True)
    
    # Financial details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    exchange_rate = Column(DECIMAL(10, 6), nullable=True)
    amount_in_base_currency = Column(DECIMAL(10, 2), nullable=True)
    
    # Transaction details
    transaction_type = Column(String(20), nullable=False)  # payment, refund, chargeback
    transaction_status = Column(String(20), nullable=False)  # pending, completed, failed, cancelled
    failure_reason = Column(Text, nullable=True)
    
    # Fees and costs
    gateway_fee = Column(DECIMAL(10, 2), nullable=True)
    processing_fee = Column(DECIMAL(10, 2), nullable=True)
    
    # Fraud and risk assessment
    fraud_score = Column(DECIMAL(3, 2), nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    
    # Customer information
    customer_ip = Column(INET, nullable=True)
    customer_location = Column(JSON, nullable=True)
    billing_address = Column(JSON, nullable=True)
    
    # Additional metadata
    payment_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="payments")
    
    def __repr__(self) -> str:
        return f"<PaymentTransaction(id={self.id}, reference={self.transaction_reference}, status={self.transaction_status})>"

