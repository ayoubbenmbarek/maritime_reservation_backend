"""
Main API router for the Maritime Reservation System.
Includes all API endpoints and route organization.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, operators, ports, routes, bookings, search, payments

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(operators.router, prefix="/operators", tags=["Ferry Operators"])
api_router.include_router(ports.router, prefix="/ports", tags=["Ports"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routes"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])

