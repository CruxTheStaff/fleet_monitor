import requests
import random
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from functools import lru_cache  # Πρόσθεσε αυτό για το @lru_cache

from src.models.vessel import (
    Vessel, WeatherCondition, PortCongestion, VoyageData, WeatherForecast  # Πρόσθεσε το WeatherForecast
)
from src.utils.data_manager import DataManager
from src.models.vessel import TankerVessel, BulkCarrierVessel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fleet_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API related errors"""
    pass


class MarineTrafficAPI:
    def __init__(self, api_key: str = "test_key", cache_duration: int = 300):
        self.api_key = api_key
        self.base_url = "https://services.marinetraffic.com/api/exportvessel/v:5/"
        self.cache_duration = cache_duration
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Add DataManager
        self.data_manager = DataManager()

        # Weather simulation parameters
        self.weather_patterns = self._initialize_weather_patterns()

        # Port congestion simulation
        self.port_congestion = self._initialize_port_congestion()

    @staticmethod
    def _initialize_weather_patterns() -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Initialize realistic weather patterns for different regions"""
        return {
            "Aegean": {
                "summer": {
                    "probability": {
                        WeatherCondition.CALM: 0.6,
                        WeatherCondition.MODERATE: 0.3,
                        WeatherCondition.ROUGH: 0.08,
                        WeatherCondition.SEVERE: 0.02
                    },
                    "wind_speed_range": (5, 25),
                    "wave_height_range": (0.5, 2.5)
                },
                "winter": {
                    "probability": {
                        WeatherCondition.CALM: 0.3,
                        WeatherCondition.MODERATE: 0.4,
                        WeatherCondition.ROUGH: 0.2,
                        WeatherCondition.SEVERE: 0.1
                    },
                    "wind_speed_range": (10, 40),
                    "wave_height_range": (1.0, 4.0)
                }
            }
        }

    @staticmethod
    def _initialize_port_congestion() -> Dict[str, Dict[str, Any]]:
        """Initialize port congestion data"""
        return {
            "Piraeus": {
                "total_berths": 10,
                "current_occupancy": 7,
                "queue": 2,
                "congestion_level": PortCongestion.MEDIUM
            },
            "Santorini": {
                "total_berths": 4,
                "current_occupancy": 2,
                "queue": 0,
                "congestion_level": PortCongestion.LOW
            },
            "Heraklion": {
                "total_berths": 6,
                "current_occupancy": 5,
                "queue": 3,
                "congestion_level": PortCongestion.HIGH
            }
        }

    def update_port_congestion(self, port: str) -> dict[str, Any] | None:
        """Simulate changes in port congestion"""
        if port not in self.port_congestion:
            return None

        port_data = self.port_congestion[port]

        # Simulate random changes
        port_data['current_occupancy'] = min(
            port_data['total_berths'],
            max(0, port_data['current_occupancy'] + random.randint(-1, 1))
        )
        port_data['queue'] = max(0, port_data['queue'] + random.randint(-1, 1))

        # Update congestion level
        occupancy_rate = port_data['current_occupancy'] / port_data['total_berths']
        if occupancy_rate > 0.9 and port_data['queue'] > 2:
            port_data['congestion_level'] = PortCongestion.CRITICAL
        elif occupancy_rate > 0.8 or port_data['queue'] > 2:
            port_data['congestion_level'] = PortCongestion.HIGH
        elif occupancy_rate > 0.6 or port_data['queue'] > 0:
            port_data['congestion_level'] = PortCongestion.MEDIUM
        elif occupancy_rate > 0.4:
            port_data['congestion_level'] = PortCongestion.LOW
        else:
            port_data['congestion_level'] = PortCongestion.NONE

        return port_data

    @lru_cache(maxsize=128)
    def get_vessel_positions(self) -> List[Dict[str, Any]]:
        """Get vessel positions from API with caching"""
        cache_file = self.cache_dir / f"vessel_positions_{datetime.now().strftime('%Y%m%d_%H')}.json"

        if cache_file.exists() and self._is_cache_valid(cache_file):
            logger.info("Using cached vessel positions")
            cached_data = self._load_from_cache(cache_file)
            if cached_data:
                return cached_data

        try:
            params = {
                "api_key": self.api_key,
                "timespan": 60,
                "protocol": "jsono"
            }

            logger.info("Fetching vessel positions from API")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                data = [data]
            self._save_to_cache(cache_file, data)
            return data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise APIError(f"Failed to fetch vessel positions: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise APIError("Invalid API response format")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def get_sample_data(self) -> List[Vessel]:
        """Get enhanced test data with more realistic variations"""
        vessels = []
        logger.info("Creating test vessels from sample data")

        # Απευθείας χρήση του SAMPLE_DATA
        for data in self.SAMPLE_DATA:
            try:
                vessel = self._create_vessel(data)
                if vessel:
                    # Αρχικοποίηση tracking data
                    vessel.track_history = [vessel.position]
                    vessel.speed_history = [vessel.speed]
                    vessel.heading = 0.0

                    # Δημιουργία αρχικού ιστορικού κίνησης
                    for _ in range(5):  # Δημιουργία 5 αρχικών σημείων
                        self.update_vessel_position(vessel)

                    # Ενημέρωση port status
                    port_status = self.update_port_congestion(vessel.destination)
                    if port_status:
                        vessel.update_port_status(
                            congestion_level=port_status['congestion_level'],
                            available_berths=port_status['total_berths'] - port_status['current_occupancy'],
                            queue_position=port_status['queue']
                        )

                    vessels.append(vessel)
                    self._simulate_realistic_conditions(vessel)
            except Exception as e:
                logger.error(f"Error creating vessel from sample data: {str(e)}")
                continue

        logger.info(f"Successfully created {len(vessels)} test vessels")
        return vessels

    def update_vessel_position(self, vessel: Vessel) -> None:
        """Update vessel position and track history"""
        try:
            # Simulate vessel movement
            current_lat, current_lon = vessel.position

            # Calculate new position with realistic movement
            movement_factor = vessel.speed / vessel.max_speed
            lat_change = random.uniform(-0.01, 0.01) * movement_factor
            lon_change = random.uniform(-0.01, 0.01) * movement_factor

            new_lat = current_lat + lat_change
            new_lon = current_lon + lon_change
            new_position = (new_lat, new_lon)

            # Update vessel position
            vessel.position = new_position

            # Update track history (keep last 100 positions)
            vessel.track_history.append(new_position)
            if len(vessel.track_history) > 100:
                vessel.track_history.pop(0)

            # Update speed with realistic variations
            speed_variation = random.uniform(-1, 1)
            new_speed = min(max(vessel.speed + speed_variation, 0), vessel.max_speed)
            vessel.speed = new_speed

            # Update speed history (keep last 100 readings)
            vessel.speed_history.append(new_speed)
            if len(vessel.speed_history) > 100:
                vessel.speed_history.pop(0)

            # Calculate heading based on last two positions
            if len(vessel.track_history) >= 2:
                vessel.heading = self._calculate_heading(
                    vessel.track_history[-2],
                    vessel.track_history[-1]
                )

            logger.debug(f"Updated position for vessel {vessel.name}: {new_position}")

        except Exception as e:
            logger.error(f"Error updating vessel position: {str(e)}")

    def _calculate_heading(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate heading angle between two positions"""
        import math

        lat1, lon1 = pos1
        lat2, lon2 = pos2

        # Convert to radians
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)

        d_lon = lon2 - lon1

        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)

        heading = math.atan2(y, x)

        # Convert to degrees and normalize
        heading_degrees = math.degrees(heading)
        normalized_heading = (heading_degrees + 360) % 360

        return normalized_heading

    @staticmethod
    def _save_to_cache(cache_file: Path, data: List[Dict[str, Any]]) -> None:
        """Save data to cache file"""
        try:
            with cache_file.open('w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache is still valid"""
        return (datetime.now().timestamp() - cache_file.stat().st_mtime) < self.cache_duration

    @staticmethod
    def _load_from_cache(cache_file: Path) -> Optional[List[Dict[str, Any]]]:
        """Load data from cache file"""
        try:
            with cache_file.open('r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"Failed to load cache: {str(e)}")
            return None

    def _create_vessel(self, data: dict) -> Optional[Vessel]:
        """Create a single vessel with error handling"""
        try:
            print(f"\nCreating vessel: {data['name']}")  # Debug print
            print(f"Vessel type: {data.get('vessel_type', 'unknown')}")  # Debug print

            # Create appropriate vessel type based on vessel_type
            if data["vessel_type"] == "tanker":
                vessel = TankerVessel(
                    name=data["name"],
                    lat=data["lat"],
                    lon=data["lon"],
                    destination=data["destination"],
                    eta=datetime.strptime(data["eta"], "%Y-%m-%d"),
                    cargo_status=data["cargo_status"],
                    fuel_level=data["fuel_level"],
                    tank_type=data["tank_type"],
                    cargo_capacity=data["cargo_capacity"]
                )
            elif data["vessel_type"] == "bulk_carrier":
                vessel = BulkCarrierVessel(
                    name=data["name"],
                    lat=data["lat"],
                    lon=data["lon"],
                    destination=data["destination"],
                    eta=datetime.strptime(data["eta"], "%Y-%m-%d"),
                    cargo_status=data["cargo_status"],
                    fuel_level=data["fuel_level"],
                    hold_count=data["hold_count"],
                    hatch_type=data["hatch_type"]
                )
            else:
                raise ValueError(f"Unknown vessel type: {data.get('vessel_type')}")

            print(f"Vessel created, setting properties...")  # Debug print
            # Set additional properties
            self._set_vessel_properties(vessel, data)

            print(f"Properties set, checking engine values:")  # Debug print
            print(f"RPM: {vessel.engine.rpm}")
            print(f"Load: {vessel.engine.load}")
            print(f"Pressure: {vessel.engine.fuel_pressure}")
            print(f"Temperature: {vessel.engine.temperature}")

            # Simulate historical data
            self._simulate_historical_readings(vessel)

            # Add voyage history
            self._add_voyage_history(vessel)

            return vessel

        except Exception as e:
            print(f"Error in create_vessel: {str(e)}")  # Debug print
            logger.error(f"Failed to create vessel {data.get('name', 'unknown')}: {str(e)}")
            return None

    def _add_voyage_history(self, vessel: Vessel) -> None:
        """Add sample voyage history to vessel"""
        if vessel.name in self.SAMPLE_VOYAGES:
            for voyage_data in self.SAMPLE_VOYAGES[vessel.name]:
                voyage = VoyageData(
                    voyage_id=voyage_data["voyage_id"],
                    start_date=voyage_data["start_date"],
                    end_date=voyage_data["end_date"],
                    origin=voyage_data["origin"],
                    destination=voyage_data["destination"],
                    intermediate_stops=voyage_data["intermediate_stops"],
                    distance=voyage_data["distance"],
                    fuel_consumption=voyage_data["fuel_consumption"],
                    cargo_load=voyage_data["cargo_load"],
                    weather_conditions=voyage_data["weather_conditions"],
                    port_waiting_times=voyage_data["port_waiting_times"],
                    total_cost=voyage_data["total_cost"],
                    average_speed=voyage_data["average_speed"],
                    route_efficiency=voyage_data["route_efficiency"]
                )
                vessel.add_voyage(voyage)

    @staticmethod
    def _set_vessel_properties(vessel: Vessel, data: dict) -> None:
        """Set vessel properties with validation"""
        try:
            print(f"Setting properties for vessel {vessel.name}")  # Προσωρινό logging
            vessel.speed = min(max(0, data["speed"]), vessel.max_speed)
            vessel.current_weather = WeatherCondition[data["weather"]]
            vessel.load_percentage = min(max(0, data["load_percentage"]), 100)
            vessel.hull_efficiency = min(max(0, data["hull_efficiency"]), 100)
            vessel.distance_traveled = max(0, data["distance_traveled"])

            print(f"Engine data for {vessel.name}: {data['engine']}")  # Προσωρινό logging
            vessel.update_engine_status(
                rpm=data["engine"]["rpm"],
                load=data["engine"]["load"],
                pressure=data["engine"]["fuel_pressure"],
                temp=data["engine"]["temperature"]
            )
        except Exception as e:
            print(f"Error setting vessel properties: {str(e)}")  # Προσωρινό logging
            logger.error(f"Error setting vessel properties: {str(e)}")
            raise

    @staticmethod
    def _simulate_historical_readings(vessel: Vessel) -> None:
        """Simulate realistic historical engine readings"""
        try:
            base_rpm = vessel.engine.rpm
            base_load = vessel.engine.load
            base_pressure = vessel.engine.fuel_pressure
            base_temp = vessel.engine.temperature

            for _ in range(20):
                time_factor = random.uniform(0.8, 1.2)

                rpm = base_rpm * time_factor + random.gauss(0, 2)
                load = base_load * time_factor + random.gauss(0, 1.5)
                pressure = base_pressure + random.gauss(0, 0.1)
                temp = base_temp + random.gauss(0, 1)

                rpm = min(max(60, rpm), 100)
                load = min(max(50, load), 95)
                pressure = min(max(7.0, pressure), 9.0)
                temp = min(max(70, temp), 90)

                vessel.update_engine_status(rpm, load, pressure, temp)

        except Exception as e:
            logger.error(f"Error simulating historical readings: {str(e)}")
            raise

    def _simulate_realistic_conditions(self, vessel: Vessel) -> None:
        """Simulate realistic weather and operational conditions"""
        try:
            current_month = datetime.now().month
            season = "summer" if 4 <= current_month <= 9 else "winter"
            pattern = self.weather_patterns["Aegean"][season]

            weather_conditions: List[WeatherForecast] = []
            for hour in range(24):
                condition = random.choices(
                    list(pattern["probability"].keys()),
                    list(pattern["probability"].values())
                )[0]

                wind_speed = random.uniform(*pattern["wind_speed_range"])
                wave_height = random.uniform(*pattern["wave_height_range"])

                forecast = WeatherForecast(
                    location=vessel.position,
                    timestamp=datetime.now() + timedelta(hours=hour),
                    condition=condition,
                    wind_speed=wind_speed,
                    wave_height=wave_height,
                    visibility=random.uniform(5, 15)
                )
                weather_conditions.append(forecast)

            vessel.weather_forecasts = weather_conditions

        except Exception as e:
            logger.error(f"Error simulating conditions: {str(e)}")
            raise

    def save_current_state(self, vessels: List[Vessel]) -> None:
        """Save current state of all vessels"""
        vessels_data = []
        voyages_data = []

        for vessel in vessels:
            # Prepare vessel data
            vessel_data = {
                "name": vessel.name,
                "position": vessel.position,
                "destination": vessel.destination,
                "status": vessel.status.value,
                "fuel_level": vessel.fuel_level,
                "current_weather": vessel.current_weather.name,
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")  # Format datetime
            }
            vessels_data.append(vessel_data)

            # Prepare voyage data
            for voyage in vessel.voyage_history:
                voyage_data = {
                    "vessel_name": vessel.name,
                    "voyage_id": voyage.voyage_id,
                    "start_date": voyage.start_date.strftime("%Y-%m-%dT%H:%M:%S"),  # Format datetime
                    "end_date": voyage.end_date.strftime("%Y-%m-%dT%H:%M:%S"),  # Format datetime
                    "origin": voyage.origin,
                    "destination": voyage.destination,
                    "distance": voyage.distance,
                    "fuel_consumption": voyage.fuel_consumption,
                    "total_cost": voyage.total_cost,
                    "weather_conditions": [w.name for w in voyage.weather_conditions],
                    "port_waiting_times": {
                        port: f"{time.total_seconds() / 3600:.1f} hours"
                        for port, time in voyage.port_waiting_times.items()
                    }
                }
                voyages_data.append(voyage_data)

        # Save to JSON files
        self.data_manager.save_vessels(vessels_data)
        self.data_manager.save_voyages(voyages_data)

    def load_saved_state(self) -> Optional[tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        """Load saved state from JSON files"""
        try:
            vessels_data = self.data_manager.load_vessels()
            voyages_data = self.data_manager.load_voyages()

            if not vessels_data:
                logger.warning("No saved vessel data found, using sample data")
                return None

            return (vessels_data, voyages_data)  # Return as tuple
        except Exception as e:
            logger.error(f"Error loading saved state: {str(e)}")
            return None

    def initialize_vessel_tracking(self, vessel: Vessel) -> None:
        """Initialize tracking data for a new vessel"""
        # Initialize with current position
        vessel.track_history = [vessel.position]
        vessel.speed_history = [vessel.speed]
        vessel.heading = 0.0  # Initial heading

        # Create some initial history
        for _ in range(5):  # Add 5 initial points
            self.update_vessel_position(vessel)

    def _create_vessel_from_saved_state(
            self,
            vessel_data: Dict[str, Any],
            voyages_data: List[Dict[str, Any]]
    ) -> Optional[Vessel]:
        """Create vessel object from saved state data"""
        try:
            # Create basic vessel
            vessel = Vessel(
                name=vessel_data["name"],
                lat=vessel_data["position"][0],
                lon=vessel_data["position"][1],
                destination=vessel_data["destination"],
                eta=datetime.now() + timedelta(hours=24),
                cargo_status=vessel_data["status"],
                fuel_level=vessel_data["fuel_level"]
            )

            # Set weather condition
            try:
                vessel.current_weather = WeatherCondition[vessel_data["current_weather"].upper()]
            except KeyError:
                vessel.current_weather = WeatherCondition.CALM

            # Add voyage history
            vessel_voyages = [v for v in voyages_data if v["vessel_name"] == vessel.name]
            for voyage_data in vessel_voyages:
                try:
                    # Parse dates with type checking
                    if isinstance(voyage_data["start_date"], str):
                        start_date = datetime.strptime(voyage_data["start_date"], "%Y-%m-%dT%H:%M:%S")
                    else:
                        start_date = voyage_data["start_date"]  # Assuming it's already a datetime object

                    if isinstance(voyage_data["end_date"], str):
                        end_date = datetime.strptime(voyage_data["end_date"], "%Y-%m-%dT%H:%M:%S")
                    else:
                        end_date = voyage_data["end_date"]  # Assuming it's already a datetime object

                    # Convert weather conditions
                    weather_conditions = [
                        WeatherCondition[w.upper()]
                        for w in voyage_data["weather_conditions"]
                    ]

                    voyage = VoyageData(
                        voyage_id=voyage_data["voyage_id"],
                        start_date=start_date,
                        end_date=end_date,
                        origin=voyage_data["origin"],
                        destination=voyage_data["destination"],
                        intermediate_stops=[],
                        distance=float(voyage_data["distance"]),
                        fuel_consumption=float(voyage_data["fuel_consumption"]),
                        cargo_load=75.0,
                        weather_conditions=weather_conditions,
                        port_waiting_times={
                            port: timedelta(hours=float(time.split()[0]))
                            for port, time in voyage_data["port_waiting_times"].items()
                        },
                        total_cost=float(voyage_data["total_cost"]),
                        average_speed=12.0,
                        route_efficiency=0.9
                    )
                    vessel.add_voyage(voyage)
                except Exception as e:
                    logger.warning(f"Error loading voyage data: {str(e)}")
                    continue

            return vessel

        except Exception as e:
            logger.error(f"Error creating vessel from saved state: {str(e)}")
            return None

    # Test data
    SAMPLE_DATA = [
        {
            "name": "OLYMPIC CHAMPION",
            "vessel_type": "tanker",  # Προσθήκη τύπου πλοίου
            "tank_type": "crude_oil",  # Ειδικά πεδία για tanker
            "cargo_capacity": 120000.0,
            "tank_cleaning_status": "clean",
            "cargo_temperature": 25.0,
            "heating_required": True,
            "lat": 37.9838,
            "lon": 23.7275,
            "destination": "Piraeus",
            "eta": "2024-01-01",
            "cargo_status": "Loading",
            "fuel_level": 85,
            "speed": 15.0,
            "weather": "MODERATE",
            "load_percentage": 75.0,
            "hull_efficiency": 92.0,
            "distance_traveled": 150.0,
            "engine": {
                "rpm": 85,
                "load": 78,
                "fuel_pressure": 8.2,
                "temperature": 82
            }
        },
        {
            "name": "BLUE STAR DELOS",
            "vessel_type": "bulk_carrier",  # Προσθήκη τύπου πλοίου
            "hold_count": 7,  # Ειδικά πεδία για bulk carrier
            "hatch_type": "folding",
            "ballast_condition": "normal",
            "hold_cleaning_status": ["clean"] * 7,
            "lat": 38.1234,
            "lon": 23.8765,
            "destination": "Santorini",
            "eta": (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d"),
            "cargo_status": "En Route",
            "fuel_level": 65,
            "speed": 18.0,
            "weather": "CALM",
            "load_percentage": 85.0,
            "hull_efficiency": 95.0,
            "distance_traveled": 220.0,
            "engine": {
                "rpm": 92,
                "load": 88,
                "fuel_pressure": 8.5,
                "temperature": 84
            }
        },
        {
            "name": "SUPERFAST XI",
            "vessel_type": "bulk_carrier",  # Προσθήκη τύπου πλοίου
            "hold_count": 5,  # Ειδικά πεδία για bulk carrier
            "hatch_type": "standard",
            "ballast_condition": "heavy",
            "hold_cleaning_status": ["clean"] * 5,
            "lat": 37.8765,
            "lon": 23.9876,
            "destination": "Heraklion",
            "eta": (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d"),
            "cargo_status": "En Route",
            "fuel_level": 25,
            "speed": 12.0,
            "weather": "ROUGH",
            "load_percentage": 90.0,
            "hull_efficiency": 88.0,
            "distance_traveled": 180.0,
            "engine": {
                "rpm": 75,
                "load": 82,
                "fuel_pressure": 7.8,
                "temperature": 86
            }
        }
    ]

    SAMPLE_VOYAGES = {
        "OLYMPIC CHAMPION": [  # Tanker voyages
            {
                "voyage_id": "OC001",
                "start_date": datetime.now() - timedelta(days=30),
                "end_date": datetime.now() - timedelta(days=29),
                "origin": "Piraeus",
                "destination": "Heraklion",
                "intermediate_stops": [],
                "distance": 180.0,
                "fuel_consumption": 28.5,
                "cargo_load": 85.0,
                # Tanker-specific data
                "cargo_type": "crude_oil",
                "cargo_temperature_log": [38.5, 38.2, 38.7, 38.4],  # Temperature readings
                "heating_hours": 12,
                "tank_washing_required": False,
                "cargo_pressure": 2.8,  # bar
                "inert_gas_system_status": "operational",
                # Common data
                "weather_conditions": [WeatherCondition.CALM, WeatherCondition.MODERATE],
                "port_waiting_times": {
                    "Heraklion": timedelta(hours=2)
                },
                "total_cost": 25000.0,
                "average_speed": 15.5,
                "route_efficiency": 0.92
            }
        ],
        "BLUE STAR DELOS": [  # Bulk carrier voyages
            {
                "voyage_id": "BSD001",
                "start_date": datetime.now() - timedelta(days=25),
                "end_date": datetime.now() - timedelta(days=24),
                "origin": "Piraeus",
                "destination": "Santorini",
                "intermediate_stops": [],
                "distance": 160.0,
                "fuel_consumption": 25.0,
                "cargo_load": 75.0,
                # Bulk carrier-specific data
                "cargo_type": "grain",
                "hold_utilization": [80, 75, 85, 70, 78, 82, 76],  # Percentage per hold
                "ballast_conditions": ["normal", "normal", "heavy"],  # Changes during voyage
                "hold_cleaning_status": ["clean"] * 7,
                "hatch_inspections": ["passed"] * 7,
                # Common data
                "weather_conditions": [WeatherCondition.CALM],
                "port_waiting_times": {
                    "Santorini": timedelta(hours=1)
                },
                "total_cost": 22000.0,
                "average_speed": 16.0,
                "route_efficiency": 0.95
            }
        ],
        "SUPERFAST XI": [  # Bulk carrier voyages
            {
                "voyage_id": "SF001",
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() - timedelta(days=19),
                "origin": "Piraeus",
                "destination": "Heraklion",
                "intermediate_stops": [],
                "distance": 180.0,
                "fuel_consumption": 30.0,
                "cargo_load": 95.0,
                # Bulk carrier-specific data
                "cargo_type": "coal",
                "hold_utilization": [92, 95, 90, 93, 94],  # Percentage per hold
                "ballast_conditions": ["heavy", "heavy", "normal"],  # Changes during voyage
                "hold_cleaning_status": ["clean"] * 5,
                "hatch_inspections": ["passed"] * 5,
                "dust_suppression_active": True,
                # Common data
                "weather_conditions": [WeatherCondition.ROUGH],
                "port_waiting_times": {
                    "Heraklion": timedelta(hours=4)
                },
                "total_cost": 27000.0,
                "average_speed": 13.5,
                "route_efficiency": 0.85
            }
        ]
    }


