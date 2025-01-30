from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

class WeatherCondition(Enum):
    CALM = "Calm"  # 0-3 Beaufort
    MODERATE = "Moderate"  # 4-5 Beaufort
    ROUGH = "Rough"  # 6-7 Beaufort
    SEVERE = "Severe"  # 8+ Beaufort

class VesselStatus(Enum):
    EN_ROUTE = "En Route"
    APPROACHING = "Approaching"
    LOADING = "Loading"
    UNLOADING = "Unloading"
    DOCKED = "Docked"

class PortCongestion(Enum):
    NONE = "No Congestion"
    LOW = "Low Congestion"
    MEDIUM = "Medium Congestion"
    HIGH = "High Congestion"
    CRITICAL = "Critical Congestion"

@dataclass
class WeatherForecast:
    location: Tuple[float, float]  # lat, lon
    timestamp: datetime
    condition: WeatherCondition
    wind_speed: float  # knots
    wave_height: float  # meters
    visibility: float  # nautical miles

@dataclass
class VoyageData:
    voyage_id: str
    start_date: datetime
    end_date: datetime
    origin: str
    destination: str
    intermediate_stops: List[str]
    distance: float  # in nautical miles
    fuel_consumption: float  # in tons
    cargo_load: float  # percentage
    weather_conditions: List[WeatherCondition]
    port_waiting_times: Dict[str, timedelta]
    total_cost: float
    average_speed: float
    route_efficiency: float  # actual/optimal ratio
    actual_arrival_time: datetime = None