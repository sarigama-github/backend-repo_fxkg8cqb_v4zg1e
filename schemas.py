"""
Database Schemas for RAKB (Rental Agency platform for cars and renters in Morocco)

Each Pydantic model represents a MongoDB collection (collection name = lowercase class name).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date


class User(BaseModel):
    """
    Users of the platform: owners, renters, admins
    Collection: "user"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    role: str = Field("renter", description="user role: renter | owner | admin")
    city: Optional[str] = Field(None, description="Base city (e.g., Casablanca)")
    is_verified: bool = Field(False, description="KYC/identity verified")


class Car(BaseModel):
    """
    Car details managed by owners
    Collection: "car"
    """
    owner_id: str = Field(..., description="Reference to user (owner)")
    make: str = Field(..., description="Brand (e.g., Dacia, Peugeot)")
    model: str = Field(..., description="Model name")
    year: int = Field(..., ge=1980, le=2100, description="Year of manufacture")
    transmission: str = Field(..., description="manual | automatic")
    fuel: str = Field(..., description="gasoline | diesel | hybrid | electric")
    seats: int = Field(..., ge=2, le=9, description="Number of seats")
    features: List[str] = Field(default_factory=list, description="Feature tags (AC, GPS, etc.)")
    photos: List[str] = Field(default_factory=list, description="Image URLs")


class Listing(BaseModel):
    """
    A rentable listing that ties a car to a location and price window
    Collection: "listing"
    """
    car_id: str = Field(..., description="Reference to car")
    owner_id: str = Field(..., description="Owner user id")
    city: str = Field(..., description="City of pickup (e.g., Marrakech)")
    daily_price: float = Field(..., ge=0, description="Price per day in MAD")
    description: Optional[str] = Field(None, description="Listing description")
    available_from: Optional[date] = Field(None, description="Availability start date")
    available_to: Optional[date] = Field(None, description="Availability end date")


class Booking(BaseModel):
    """
    A renter's reservation for a listing
    Collection: "booking"
    """
    listing_id: str = Field(..., description="Listing reference")
    renter_id: str = Field(..., description="Renter user id")
    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")
    total_price: float = Field(..., ge=0, description="Computed total price in MAD")
    status: str = Field("pending", description="pending | confirmed | cancelled | completed")


class Review(BaseModel):
    """
    Reviews left by renters for listings/owners
    Collection: "review"
    """
    listing_id: str = Field(...)
    renter_id: str = Field(...)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
