"""
Ferry Operator Integration Service
Handles integration with multiple ferry operators through various patterns.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import json

from app.core.config import settings
from app.models.ferry import FerryOperator, Route, Port
from app.schemas import RouteSearchRequest, RouteSearchResult


class IntegrationType(str, Enum):
    """Integration type enumeration."""
    DIRECT = "direct"
    AGGREGATOR = "aggregator"
    HYBRID = "hybrid"


class OperatorStatus(str, Enum):
    """Operator integration status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class SearchRequest:
    """Standardized search request format."""
    departure_port: str
    arrival_port: str
    departure_date: date
    return_date: Optional[date]
    passengers: int
    vehicles: int
    passenger_types: Dict[str, int]
    vehicle_types: Dict[str, int]


@dataclass
class SearchResponse:
    """Standardized search response format."""
    operator_code: str
    route_id: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    available_seats: int
    available_vehicles: int
    base_price: Decimal
    currency: str
    booking_reference: Optional[str]
    amenities: List[str]
    vessel_name: str


class BaseFerryOperatorAdapter:
    """Base adapter class for ferry operator integrations."""
    
    def __init__(self, operator: FerryOperator, session: aiohttp.ClientSession):
        self.operator = operator
        self.session = session
        self.logger = logging.getLogger(f"ferry_adapter.{operator.code}")
        
    async def search_routes(self, request: SearchRequest) -> List[SearchResponse]:
        """Search for available routes."""
        raise NotImplementedError
        
    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new booking."""
        raise NotImplementedError
        
    async def get_booking_status(self, booking_reference: str) -> Dict[str, Any]:
        """Get booking status."""
        raise NotImplementedError
        
    async def cancel_booking(self, booking_reference: str) -> Dict[str, Any]:
        """Cancel a booking."""
        raise NotImplementedError
        
    async def health_check(self) -> bool:
        """Check if the operator API is healthy."""
        raise NotImplementedError


class LykoAggregatorAdapter(BaseFerryOperatorAdapter):
    """Adapter for Lyko aggregator platform."""
    
    def __init__(self, operator: FerryOperator, session: aiohttp.ClientSession):
        super().__init__(operator, session)
        self.base_url = "https://api.lyko.tech/v1"
        self.api_key = operator.api_key_encrypted  # Should be decrypted
        
    async def search_routes(self, request: SearchRequest) -> List[SearchResponse]:
        """Search routes through Lyko aggregator."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "departure_port": request.departure_port,
                "arrival_port": request.arrival_port,
                "departure_date": request.departure_date.isoformat(),
                "return_date": request.return_date.isoformat() if request.return_date else None,
                "passengers": request.passengers,
                "vehicles": request.vehicles,
                "passenger_types": request.passenger_types,
                "vehicle_types": request.vehicle_types,
                "operators": [self.operator.code]
            }
            
            async with self.session.post(
                f"{self.base_url}/search",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_search_response(data)
                else:
                    self.logger.error(f"Search failed: {response.status} - {await response.text()}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Search error: {e}", exc_info=True)
            return []
    
    def _parse_search_response(self, data: Dict[str, Any]) -> List[SearchResponse]:
        """Parse Lyko search response into standardized format."""
        results = []
        
        for item in data.get("results", []):
            try:
                result = SearchResponse(
                    operator_code=item.get("operator_code", self.operator.code),
                    route_id=item.get("route_id"),
                    departure_time=item.get("departure_time"),
                    arrival_time=item.get("arrival_time"),
                    duration_minutes=item.get("duration_minutes", 0),
                    available_seats=item.get("available_seats", 0),
                    available_vehicles=item.get("available_vehicles", 0),
                    base_price=Decimal(str(item.get("price", 0))),
                    currency=item.get("currency", "EUR"),
                    booking_reference=item.get("booking_reference"),
                    amenities=item.get("amenities", []),
                    vessel_name=item.get("vessel_name", "")
                )
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {e}")
                continue
                
        return results
    
    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create booking through Lyko aggregator."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                f"{self.base_url}/bookings",
                headers=headers,
                json=booking_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    error_text = await response.text()
                    self.logger.error(f"Booking creation failed: {response.status} - {error_text}")
                    return {"error": f"Booking failed: {error_text}"}
                    
        except Exception as e:
            self.logger.error(f"Booking creation error: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """Check Lyko API health."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with self.session.get(
                f"{self.base_url}/health",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


class CTNDirectAdapter(BaseFerryOperatorAdapter):
    """Direct adapter for CTN ferry operator."""
    
    def __init__(self, operator: FerryOperator, session: aiohttp.ClientSession):
        super().__init__(operator, session)
        self.base_url = operator.api_endpoint or "https://api.ctn.com.tn/v1"
        self.api_key = operator.api_key_encrypted  # Should be decrypted
        
    async def search_routes(self, request: SearchRequest) -> List[SearchResponse]:
        """Search routes directly with CTN."""
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": request.departure_port,
                "to": request.arrival_port,
                "date": request.departure_date.isoformat(),
                "passengers": request.passengers,
                "vehicles": request.vehicles
            }
            
            async with self.session.post(
                f"{self.base_url}/search",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_ctn_response(data)
                else:
                    self.logger.error(f"CTN search failed: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"CTN search error: {e}", exc_info=True)
            return []
    
    def _parse_ctn_response(self, data: Dict[str, Any]) -> List[SearchResponse]:
        """Parse CTN-specific response format."""
        results = []
        
        for sailing in data.get("sailings", []):
            try:
                result = SearchResponse(
                    operator_code="CTN",
                    route_id=sailing.get("route_id"),
                    departure_time=sailing.get("departure"),
                    arrival_time=sailing.get("arrival"),
                    duration_minutes=sailing.get("duration"),
                    available_seats=sailing.get("seats_available"),
                    available_vehicles=sailing.get("vehicles_available"),
                    base_price=Decimal(str(sailing.get("fare", 0))),
                    currency=sailing.get("currency", "TND"),
                    booking_reference=None,
                    amenities=sailing.get("services", []),
                    vessel_name=sailing.get("vessel")
                )
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to parse CTN result: {e}")
                continue
                
        return results
    
    async def health_check(self) -> bool:
        """Check CTN API health."""
        try:
            headers = {"X-API-Key": self.api_key}
            
            async with self.session.get(
                f"{self.base_url}/status",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"CTN health check failed: {e}")
            return False


class FerryOperatorIntegrationService:
    """Main service for managing ferry operator integrations."""
    
    def __init__(self):
        self.adapters: Dict[str, BaseFerryOperatorAdapter] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("ferry_integration")
        
    async def initialize(self, operators: List[FerryOperator]):
        """Initialize the integration service with operators."""
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=20),
            timeout=aiohttp.ClientTimeout(total=60)
        )
        
        for operator in operators:
            if not operator.is_active:
                continue
                
            try:
                adapter = self._create_adapter(operator)
                self.adapters[operator.code] = adapter
                self.logger.info(f"Initialized adapter for {operator.code}")
            except Exception as e:
                self.logger.error(f"Failed to initialize {operator.code}: {e}")
    
    def _create_adapter(self, operator: FerryOperator) -> BaseFerryOperatorAdapter:
        """Create appropriate adapter based on operator configuration."""
        if operator.integration_status == "lyko":
            return LykoAggregatorAdapter(operator, self.session)
        elif operator.code == "CTN" and operator.api_endpoint:
            return CTNDirectAdapter(operator, self.session)
        else:
            # Default to Lyko aggregator
            return LykoAggregatorAdapter(operator, self.session)
    
    async def search_all_operators(self, request: SearchRequest) -> List[SearchResponse]:
        """Search across all active operators."""
        tasks = []
        
        for operator_code, adapter in self.adapters.items():
            task = asyncio.create_task(
                self._safe_search(adapter, request),
                name=f"search_{operator_code}"
            )
            tasks.append(task)
        
        if not tasks:
            return []
        
        # Wait for all searches to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out errors
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Search task failed: {result}")
        
        # Sort by price and departure time
        all_results.sort(key=lambda x: (x.base_price, x.departure_time))
        
        return all_results
    
    async def _safe_search(self, adapter: BaseFerryOperatorAdapter, request: SearchRequest) -> List[SearchResponse]:
        """Safely execute search with error handling."""
        try:
            return await adapter.search_routes(request)
        except Exception as e:
            self.logger.error(f"Search failed for {adapter.operator.code}: {e}")
            return []
    
    async def create_booking(self, operator_code: str, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create booking with specific operator."""
        adapter = self.adapters.get(operator_code)
        if not adapter:
            return {"error": f"Operator {operator_code} not available"}
        
        try:
            return await adapter.create_booking(booking_data)
        except Exception as e:
            self.logger.error(f"Booking creation failed for {operator_code}: {e}")
            return {"error": str(e)}
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all operator integrations."""
        tasks = []
        
        for operator_code, adapter in self.adapters.items():
            task = asyncio.create_task(
                adapter.health_check(),
                name=f"health_{operator_code}"
            )
            tasks.append((operator_code, task))
        
        results = {}
        for operator_code, task in tasks:
            try:
                results[operator_code] = await task
            except Exception as e:
                self.logger.error(f"Health check failed for {operator_code}: {e}")
                results[operator_code] = False
        
        return results
    
    async def close(self):
        """Close the integration service and cleanup resources."""
        if self.session:
            await self.session.close()
        
        self.adapters.clear()
        self.logger.info("Ferry integration service closed")


# Global service instance
ferry_integration_service = FerryOperatorIntegrationService()

