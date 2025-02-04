import sys
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import STORMGLASS_API_KEY
from src.utils.weather_api import WeatherAPI
from .types import (
    WeatherCondition, VesselStatus, PortCongestion,
    WeatherForecast, VoyageData
)

class VesselStatus(Enum):
    EN_ROUTE = "En Route"
    APPROACHING = "Approaching"
    LOADING = "Loading"
    UNLOADING = "Unloading"
    DOCKED = "Docked"


class WeatherCondition(Enum):
    CALM = "Calm"  # 0-3 Beaufort
    MODERATE = "Moderate"  # 4-5 Beaufort
    ROUGH = "Rough"  # 6-7 Beaufort
    SEVERE = "Severe"  # 8+ Beaufort


class PortCongestion(Enum):
    NONE = "No Congestion"
    LOW = "Low Congestion"
    MEDIUM = "Medium Congestion"
    HIGH = "High Congestion"
    CRITICAL = "Critical Congestion"


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
    actual_arrival_time: Optional[datetime] = None

@dataclass
class WeatherForecast:
    location: Tuple[float, float]  # lat, lon
    timestamp: datetime
    condition: WeatherCondition
    wind_speed: float  # knots
    wave_height: float  # meters
    visibility: float  # nautical miles


class EngineStatus:
    def __init__(self):
        self.rpm = 0.0
        self.load = 0.0  # percentage
        self.fuel_pressure = 0.0  # bar
        self.temperature = 0.0  # Celsius
        self.readings_history: List[Dict] = []  # για trend analysis

    def add_reading(self, reading: Dict):
        """Add a new reading to history"""
        self.readings_history.append({
            'timestamp': datetime.now(),
            **reading
        })
        if len(self.readings_history) > 100:  # Keep only last 100 readings
            self.readings_history.pop(0)


class BaseVessel:
    STATUS_COLORS = {
        VesselStatus.EN_ROUTE: "blue",
        VesselStatus.APPROACHING: "green",
        VesselStatus.LOADING: "orange",
        VesselStatus.UNLOADING: "purple",
        VesselStatus.DOCKED: "red"
    }

    WEATHER_IMPACT = {
        WeatherCondition.CALM: 1.0,
        WeatherCondition.MODERATE: 1.15,
        WeatherCondition.ROUGH: 1.3,
        WeatherCondition.SEVERE: 1.5
    }

    def __init__(self, name: str, lat: float, lon: float, destination: str,
                 eta: datetime, cargo_status: str, fuel_level: float):
        # Basic vessel info
        self.name = name
        self.position = (lat, lon)
        self.destination = destination
        self.original_eta = eta
        self.current_eta = eta
        self.cargo_status = cargo_status
        self.fuel_level = fuel_level
        self.status = self._determine_status()

        # Route and Weather
        self.route: List[Tuple[float, float]] = []
        self.weather_forecasts: List[WeatherForecast] = []
        self.current_weather = WeatherCondition.CALM

        # Tracking and History
        self.track_history: List[Tuple[float, float]] = []
        self.speed_history: List[float] = []
        self.heading = 0.0

        # Port status monitoring
        self.port_status = {
            'congestion_level': PortCongestion.NONE,
            'available_berths': 0,
            'queue_position': None,
            'estimated_waiting_time': timedelta(minutes=0)
        }

        # Performance metrics
        self.speed = 12.0  # Default speed in knots
        self.max_speed = 20.0
        self.load_percentage = 70.0
        self.hull_efficiency = 95.0
        self.distance_traveled = 0.0

        # New attributes for real-time metrics
        self.optimal_speed = 12.0  # Default optimal speed
        self.current_consumption = 0.0  # Current fuel consumption
        self.baseline_consumption = 0.0  # Baseline fuel consumption
        self.eta_deviation = 0  # Hours of deviation from original ETA

        # Engine monitoring
        self.engine = EngineStatus()
        self.normal_parameters = {
            'rpm_range': (70, 90),
            'load_range': (60, 85),
            'pressure_range': (7.5, 8.5),
            'temp_range': (75, 85)
        }

        # Delays and costs
        self.current_delay = timedelta(minutes=0)
        self.delay_history: List[Dict] = []
        self.total_delay_cost = 0.0

        # Historical data
        self.historical_consumption = []
        self.historical_speeds = []
        self._initialize_historical_data()

        # Voyage historical data
        self.voyage_history: List[VoyageData] = []
        self.fuel_cost_per_ton = 750.0  # USD per ton
        self.port_costs = {
            "Piraeus": {"docking": 1000, "daily_rate": 500},
            "Santorini": {"docking": 800, "daily_rate": 400},
            "Heraklion": {"docking": 900, "daily_rate": 450}
        }

    def calculate_optimal_speed(self) -> float:
        """Calculate optimal speed based on conditions"""
        base_optimal = 12.0
        weather_factor = self.WEATHER_IMPACT[self.current_weather]
        cargo_factor = 1.0 - (self.load_percentage - 70) / 100 * 0.2

        optimal_speed = base_optimal * weather_factor * cargo_factor
        return round(optimal_speed, 1)

    def update_consumption_metrics(self):
        """Update current and baseline consumption"""
        self.current_consumption = self._calculate_consumption_per_mile()
        self.baseline_consumption = 30.0 / (self.optimal_speed * 24)  # Basic calculation

    def update_eta_deviation(self):
        """Calculate deviation from original ETA in hours"""
        if self.current_eta and self.original_eta:
            deviation = self.current_eta - self.original_eta
            self.eta_deviation = round(deviation.total_seconds() / 3600, 1)

    def update_metrics(self):
        """Update all real-time vessel metrics"""
        self.optimal_speed = self.calculate_optimal_speed()
        self.update_consumption_metrics()
        self.update_eta_deviation()

    def add_voyage(self, voyage: VoyageData) -> None:
        """Add a new voyage to vessel's history"""
        self.voyage_history.append(voyage)

    def get_voyage_history(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[VoyageData]:
        """Get voyage history within date range"""
        if not (start_date and end_date):
            return self.voyage_history

        return [
            voyage for voyage in self.voyage_history
            if start_date <= voyage.start_date <= end_date
        ]

    def calculate_voyage_costs(self, voyage: VoyageData) -> Dict[str, float]:
        """Calculate detailed costs for a specific voyage"""
        # Fuel costs
        fuel_cost = voyage.fuel_consumption * self.fuel_cost_per_ton

        # Port costs and port delay costs
        port_costs = 0.0
        port_delay_costs = 0.0

        for port in [voyage.origin] + voyage.intermediate_stops + [voyage.destination]:
            if port in self.port_costs:
                port_data = self.port_costs[port]
                waiting_time = voyage.port_waiting_times.get(port, timedelta(0))
                days_waiting = waiting_time.total_seconds() / (24 * 3600)

                port_costs += port_data["docking"]
                port_costs += port_data["daily_rate"] * days_waiting
                port_delay_costs += waiting_time.total_seconds() / 3600 * 500  # $500 per hour

        # Schedule deviation costs (if voyage was delayed overall)
        schedule_deviation_costs = 0.0
        if voyage.actual_arrival_time and voyage.actual_arrival_time > voyage.end_date:
            total_delay = (voyage.actual_arrival_time - voyage.end_date).total_seconds() / 3600
            schedule_deviation_costs = total_delay * 750  # Higher rate for overall delay

        total_cost = fuel_cost + port_costs + port_delay_costs + schedule_deviation_costs

        return {
            "fuel_cost": fuel_cost,
            "port_costs": port_costs,
            "port_delay_costs": port_delay_costs,
            "schedule_deviation_costs": schedule_deviation_costs,
            "total_cost": total_cost,
            "cost_per_mile": total_cost / voyage.distance
        }

    def get_efficiency_metrics_by_voyage(self, voyage: VoyageData) -> Dict[str, float]:
        """Get detailed efficiency metrics for a specific voyage"""
        costs = self.calculate_voyage_costs(voyage)

        return {
            "fuel_consumption_per_mile": voyage.fuel_consumption / voyage.distance,
            "cost_per_mile": costs["cost_per_mile"],
            "route_efficiency": voyage.route_efficiency,
            "average_speed": voyage.average_speed,
            "cargo_load": voyage.cargo_load,
            "total_cost": costs["total_cost"]
        }
    pass

    def __init__(self, name: str, lat: float, lon: float, destination: str,
                 eta: datetime, cargo_status: str, fuel_level: float):
        # Basic vessel info
        self.name = name
        self.position = (lat, lon)
        self.destination = destination
        self.original_eta = eta
        self.current_eta = eta
        self.cargo_status = cargo_status
        self.fuel_level = fuel_level
        self.status = self._determine_status()

        # Route and Weather
        self.route: List[Tuple[float, float]] = []
        self.weather_forecasts: List[WeatherForecast] = []
        self.current_weather = WeatherCondition.CALM

        # Tracking and History
        self.track_history: List[Tuple[float, float]] = []  # Added track_history
        self.speed_history: List[float] = []  # Added speed_history
        self.heading = 0.0  # Added heading for vessel direction

        # Port status monitoring
        self.port_status = {
            'congestion_level': PortCongestion.NONE,
            'available_berths': 0,
            'queue_position': None,
            'estimated_waiting_time': timedelta(minutes=0)
        }

        # Performance metrics
        self.speed = 12.0  # Default speed in knots
        self.max_speed = 20.0
        self.load_percentage = 70.0
        self.hull_efficiency = 95.0
        self.distance_traveled = 0.0

        # Engine monitoring
        self.engine = EngineStatus()
        self.normal_parameters = {
            'rpm_range': (70, 90),
            'load_range': (60, 85),
            'pressure_range': (7.5, 8.5),
            'temp_range': (75, 85)
        }

        # Delays and costs
        self.current_delay = timedelta(minutes=0)
        self.delay_history: List[Dict] = []
        self.total_delay_cost = 0.0

        # Historical data
        self.historical_consumption = []
        self.historical_speeds = []
        self._initialize_historical_data()

        # Voyage historical data
        self.voyage_history: List[VoyageData] = []
        self.fuel_cost_per_ton = 750.0  # USD per ton
        self.port_costs = {
            "Piraeus": {"docking": 1000, "daily_rate": 500},
            "Santorini": {"docking": 800, "daily_rate": 400},
            "Heraklion": {"docking": 900, "daily_rate": 450}
        }

    def update_port_status(self, congestion_level: PortCongestion,
                           available_berths: int, queue_position: int = None) -> None:
        """Update port status and calculate delays"""
        self.port_status['congestion_level'] = congestion_level
        self.port_status['available_berths'] = available_berths
        self.port_status['queue_position'] = queue_position

        # Calculate estimated waiting time based on congestion
        waiting_times = {
            PortCongestion.NONE: 0,
            PortCongestion.LOW: 30,
            PortCongestion.MEDIUM: 60,
            PortCongestion.HIGH: 120,
            PortCongestion.CRITICAL: 240
        }

        base_waiting_time = waiting_times[congestion_level]
        if queue_position:
            base_waiting_time *= queue_position

        self.port_status['estimated_waiting_time'] = timedelta(minutes=base_waiting_time)

        # Add delay if there's congestion
        if congestion_level != PortCongestion.NONE:
            self.add_delay(
                duration=self.port_status['estimated_waiting_time'],
                reason=f"Port Congestion: {congestion_level.value}",
                cost=self._calculate_waiting_cost(self.port_status['estimated_waiting_time'])
            )

    def _calculate_waiting_cost(self, waiting_time: timedelta) -> float:
        """Calculate cost of waiting based on vessel type and duration"""
        hourly_cost = 500  # Base hourly cost in USD
        hours = waiting_time.total_seconds() / 3600
        return hourly_cost * hours

    def get_weather_summary(self) -> Dict:
        """Get simplified weather summary"""
        if not self.weather_forecasts:
            return {
                'current': self.current_weather.value,
                'next_hours': None,
                'destination': None,
                'alerts': []
            }

        # Get only relevant forecasts
        time_to_arrival = (self.current_eta - datetime.now()).total_seconds() / 3600
        relevant_forecasts = [f for f in self.weather_forecasts
                              if (f.timestamp - datetime.now()).total_seconds() / 3600 <= time_to_arrival]

        # Get conditions for next few hours
        next_hours = relevant_forecasts[:3] if len(relevant_forecasts) > 3 else relevant_forecasts

        # Get conditions near destination (last hour)
        destination_forecast = relevant_forecasts[-1] if relevant_forecasts else None

        # Check for severe weather alerts
        alerts = []
        for forecast in relevant_forecasts:
            if forecast.condition in [WeatherCondition.ROUGH, WeatherCondition.SEVERE]:
                alerts.append({
                    'time': forecast.timestamp,
                    'condition': forecast.condition.value,
                    'wind_speed': forecast.wind_speed,
                    'wave_height': forecast.wave_height
                })

        return {
            'current': self.current_weather.value,
            'next_hours': [
                {
                    'time': f.timestamp.strftime('%H:%M'),
                    'condition': f.condition.value
                } for f in next_hours
            ],
            'destination': {
                'time': destination_forecast.timestamp.strftime('%H:%M'),
                'condition': destination_forecast.condition.value
            } if destination_forecast else None,
            'alerts': alerts
        }

    def _initialize_historical_data(self):
        """Initialize historical data with realistic values"""
        base_consumption_per_mile = 30.0 / (12.0 * 24)  # Base efficiency at 12 knots
        for _ in range(10):
            self.historical_speeds.append(12.0)
            self.historical_consumption.append(base_consumption_per_mile * 12.0 * 24)

    def update_engine_status(self, rpm: float, load: float,
                             pressure: float, temp: float) -> None:
        """Update engine parameters and store in history"""
        print(
            f"Updating engine status for {self.name}: rpm={rpm}, load={load}, pressure={pressure}, temp={temp}")  # Προσωρινό logging
        self.engine.rpm = rpm
        self.engine.load = load
        self.engine.fuel_pressure = pressure
        self.engine.temperature = temp

        self.engine.add_reading({
            'rpm': rpm,
            'load': load,
            'pressure': pressure,
            'temp': temp
        })

    def _determine_status(self) -> VesselStatus:
        """Determine vessel status based on cargo status and ETA"""
        if self.cargo_status == "Loading":
            return VesselStatus.LOADING
        elif self.cargo_status == "Unloading":
            return VesselStatus.UNLOADING
        elif self.cargo_status == "En Route":
            time_to_arrival = (self.current_eta - datetime.now()).total_seconds() / 3600
            if time_to_arrival <= 24:
                return VesselStatus.APPROACHING
            return VesselStatus.EN_ROUTE
        return VesselStatus.DOCKED

    def get_marker_color(self) -> str:
        """Get color for map marker based on status"""
        return self.STATUS_COLORS[self.status]

    def is_delayed(self) -> bool:
        """Check if vessel is delayed"""
        return datetime.now() > self.current_eta

    def calculate_weather_delay(self) -> timedelta:
        """Calculate potential delay based on weather forecasts"""
        total_delay = timedelta(minutes=0)

        for forecast in self.weather_forecasts:
            if forecast.condition == WeatherCondition.ROUGH:
                total_delay += timedelta(minutes=30)
            elif forecast.condition == WeatherCondition.SEVERE:
                total_delay += timedelta(minutes=60)

        return total_delay

    def add_delay(self, duration: timedelta, reason: str, cost: float):
        """Add a new delay event"""
        self.current_delay += duration
        self.delay_history.append({
            'timestamp': datetime.now(),
            'duration': duration,
            'reason': reason,
            'cost': cost,
            'weather': self.current_weather
        })
        self.total_delay_cost += cost
        self.current_eta = self.original_eta + self.current_delay

    def check_engine_parameters(self) -> Dict[str, any]:
        """Check all engine parameters for anomalies"""
        alerts = []

        # RPM Check
        if not (self.normal_parameters['rpm_range'][0] <= self.engine.rpm <=
                self.normal_parameters['rpm_range'][1]):
            alerts.append({
                'parameter': 'RPM',
                'value': self.engine.rpm,
                'normal_range': self.normal_parameters['rpm_range'],
                'severity': 'high' if abs(self.engine.rpm -
                                          sum(self.normal_parameters['rpm_range']) / 2) > 15 else 'medium'
            })

        # Load Check
        if not (self.normal_parameters['load_range'][0] <= self.engine.load <=
                self.normal_parameters['load_range'][1]):
            alerts.append({
                'parameter': 'Engine Load',
                'value': self.engine.load,
                'normal_range': self.normal_parameters['load_range'],
                'severity': 'high' if self.engine.load > 90 else 'medium'
            })

        # Pressure Check
        if not (self.normal_parameters['pressure_range'][0] <= self.engine.fuel_pressure <=
                self.normal_parameters['pressure_range'][1]):
            alerts.append({
                'parameter': 'Fuel Pressure',
                'value': self.engine.fuel_pressure,
                'normal_range': self.normal_parameters['pressure_range'],
                'severity': 'high'
            })

        # Temperature Check
        if not (self.normal_parameters['temp_range'][0] <= self.engine.temperature <=
                self.normal_parameters['temp_range'][1]):
            alerts.append({
                'parameter': 'Temperature',
                'value': self.engine.temperature,
                'normal_range': self.normal_parameters['temp_range'],
                'severity': 'high' if self.engine.temperature >
                                      self.normal_parameters['temp_range'][1] + 10 else 'medium'
            })

        return {
            'has_alerts': len(alerts) > 0,
            'alerts': alerts,
            'current_values': {
                'rpm': self.engine.rpm,
                'load': self.engine.load,
                'pressure': self.engine.fuel_pressure,
                'temperature': self.engine.temperature
            }
        }

    def get_efficiency_metrics(self) -> Dict[str, float]:
        """Get comprehensive efficiency metrics"""
        return {
            "current_consumption_per_mile": self._calculate_consumption_per_mile(),
            "average_consumption_per_mile": self._get_average_efficiency(),
            "speed": self.speed,
            "hull_efficiency": self.hull_efficiency,
            "weather_impact": self.WEATHER_IMPACT[self.current_weather],
            "load_percentage": self.load_percentage
        }

    def _calculate_consumption_per_mile(self) -> float:
        """Calculate current fuel consumption per nautical mile"""
        if self.speed == 0:
            return 0
        daily_consumption = self._calculate_daily_consumption()
        return daily_consumption / (self.speed * 24)

    def _calculate_daily_consumption(self) -> float:
        """Calculate daily fuel consumption in tons"""
        speed_factor = (self.speed / 12.0) ** 3  # Cubic relationship with speed
        weather_factor = self.WEATHER_IMPACT[self.current_weather]
        load_factor = 1 + (self.load_percentage - 70) / 100 * 0.2
        hull_factor = 100 / self.hull_efficiency

        return 30.0 * speed_factor * weather_factor * load_factor * hull_factor

    def _get_average_efficiency(self) -> float:
        """Calculate average historical consumption per mile"""
        if not self.historical_consumption or not self.historical_speeds:
            return 0.0
        efficiencies = [cons / (speed * 24) for cons, speed
                        in zip(self.historical_consumption, self.historical_speeds)]
        return sum(efficiencies) / len(efficiencies)

    def get_status_info(self) -> Dict:
        """Get comprehensive vessel status including delays and weather"""
        weather_delay = self.calculate_weather_delay()
        total_delay = self.current_delay + weather_delay

        return {
            "status": self.status.value,
            "position": self.position,
            "destination": self.destination,
            "original_eta": self.original_eta,
            "current_eta": self.current_eta,
            "current_delay": self.current_delay,
            "weather_delay": weather_delay,
            "total_delay": total_delay,
            "total_delay_cost": self.total_delay_cost,
            "current_weather": self.current_weather.value,
            "weather_forecasts": [
                {
                    "location": f.location,
                    "condition": f.condition.value,
                    "wind_speed": f.wind_speed,
                    "wave_height": f.wave_height,
                    "visibility": f.visibility
                } for f in self.weather_forecasts
            ],
            "fuel_level": self.fuel_level,
            "speed": self.speed,
            "engine_status": self.check_engine_parameters()
        }

    def is_on_time(self) -> bool:
        """
        Check if the voyage was completed on time.
        """
        if self.actual_arrival_time:
            return self.actual_arrival_time <= self.end_date  # it is on-time if end <= actual

        # if there is not actual arrival time, shipping hasn't ended yet
        return False

    def calculate_on_time_statistics(self) -> Dict[str, int]:
        """Calculate the number of voyages completed on time and delayed."""
        on_time_count = 0
        delayed_count = 0

        for voyage in self.voyage_history:
            if voyage.actual_arrival_time and voyage.actual_arrival_time <= voyage.end_date:
                on_time_count += 1
            else:
                delayed_count += 1

        return {
            "on_time": on_time_count,
            "delayed": delayed_count
        }

    def update_weather_conditions(self, weather_data: Dict):
        """Update vessel's weather conditions"""
        self.current_weather_data = weather_data

        # Update vessel speed based on weather
        if weather_data.get('wave_height', 0) > 3:
            self.speed *= 0.8  # Reduce speed in rough seas

        # Update fuel consumption based on weather
        wind_speed = weather_data.get('wind_speed', 0)
        if wind_speed > 20:
            self.fuel_consumption *= 1.2  # Increase fuel consumption in strong winds

            def update_weather_data(self):
                """Update vessel weather data from API"""
                weather_api = WeatherAPI(STORMGLASS_API_KEY)
                weather_data = weather_api.get_vessel_weather_data(
                    self.position[0],
                    self.position[1]
                )

                self.current_weather = weather_data['current_weather']
                self.weather_forecasts = weather_data['weather_forecasts']

                # Update vessel parameters based on weather
                self.update_weather_conditions({
                    'wave_height': weather_data['wave_height'],
                    'wind_speed': weather_data['wind_speed']
                })

class Vessel(BaseVessel, ABC):
    def __init__(self, name: str, lat: float, lon: float, destination: str,
                 eta: datetime, cargo_status: str, fuel_level: float):
        super().__init__(name, lat, lon, destination, eta, cargo_status, fuel_level)

    @abstractmethod
    def calculate_specific_consumption(self) -> float:
        """Calculate vessel-type specific fuel consumption"""
        pass

    @abstractmethod
    def get_vessel_specific_info(self) -> Dict[str, any]:
        """Get vessel-type specific information"""
        pass

class TankerVessel(Vessel):
    def __init__(self, name: str, lat: float, lon: float, destination: str,
                 eta: datetime, cargo_status: str, fuel_level: float,
                 tank_type: str, cargo_capacity: float):
        super().__init__(name, lat, lon, destination, eta, cargo_status, fuel_level)
        self.tank_type = tank_type
        self.cargo_capacity = cargo_capacity
        self.tank_cleaning_status = "clean"
        self.cargo_temperature = None
        self.heating_required = False

    def calculate_specific_consumption(self) -> float:
        base_consumption = self._calculate_daily_consumption()
        if self.heating_required:
            base_consumption *= 1.15
        return base_consumption

    def get_vessel_specific_info(self) -> Dict[str, any]:
        return {
            "tank_type": self.tank_type,
            "cargo_capacity": self.cargo_capacity,
            "tank_cleaning_status": self.tank_cleaning_status,
            "cargo_temperature": self.cargo_temperature,
            "heating_required": self.heating_required
        }

class BulkCarrierVessel(Vessel):
    def __init__(self, name: str, lat: float, lon: float, destination: str,
                 eta: datetime, cargo_status: str, fuel_level: float,
                 hold_count: int, hatch_type: str):
        super().__init__(name, lat, lon, destination, eta, cargo_status, fuel_level)
        self.hold_count = hold_count
        self.hatch_type = hatch_type
        self.ballast_condition = "normal"
        self.hold_cleaning_status = ["clean"] * hold_count

    def calculate_specific_consumption(self) -> float:
        base_consumption = self._calculate_daily_consumption()
        if self.ballast_condition == "heavy":
            base_consumption *= 1.1
        return base_consumption

    def get_vessel_specific_info(self) -> Dict[str, any]:
        return {
            "hold_count": self.hold_count,
            "hatch_type": self.hatch_type,
            "ballast_condition": self.ballast_condition,
            "hold_cleaning_status": self.hold_cleaning_status
        }
