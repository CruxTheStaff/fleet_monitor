# src/utils/weather_api.py
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from src.utils.config import STORMGLASS_API_KEY
from ..models.types import WeatherCondition, WeatherForecast

class WeatherAPI:
    def __init__(self):
        self.api_key = STORMGLASS_API_KEY
        self.base_url = "https://api.stormglass.io/v2"
        self.logger = logging.getLogger(__name__)

    def get_vessel_weather_data(self, lat: float, lon: float, hours: int = 24) -> Dict:
        """Get weather data and forecasts for vessel"""
        try:
            endpoint = f"{self.base_url}/weather/point"
            params = {
                'lat': lat,
                'lng': lon,
                'params': ','.join([
                    'waveHeight',
                    'windSpeed',
                    'windDirection',
                    'visibility'  # Added visibility parameter
                ]),
                'hours': hours
            }
            headers = {'Authorization': self.api_key}

            response = requests.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return self._process_weather_data(data)

        except Exception as e:
            self.logger.error(f"Error fetching weather data: {str(e)}")
            return self._get_fallback_data()

    def _process_weather_data(self, data: Dict) -> Dict:
        """Process API data into vessel weather format"""
        if not data or 'hours' not in data:
            return self._get_fallback_data()

        current_hour = data['hours'][0]
        forecasts = []

        for hour in data['hours']:
            wave_height = hour.get('waveHeight', {}).get('noaa', 0)
            wind_speed = hour.get('windSpeed', {}).get('noaa', 0)
            visibility = hour.get('visibility', {}).get('noaa', 10)  # Default to 10 nm if not available

            # Determine weather condition
            condition = self._determine_condition(wave_height, wind_speed)

            # Create WeatherForecast object
            forecast = WeatherForecast(
                location=(data['meta']['lat'], data['meta']['lng']),  # Location from API response
                timestamp=datetime.fromisoformat(hour['time'].replace('Z', '+00:00')),
                condition=condition,
                wind_speed=wind_speed,
                wave_height=wave_height,
                visibility=visibility
            )
            forecasts.append(forecast)

        return {
            'current_weather': self._determine_condition(
                current_hour.get('waveHeight', {}).get('noaa', 0),
                current_hour.get('windSpeed', {}).get('noaa', 0)
            ),
            'weather_forecasts': forecasts,
            'wave_height': current_hour.get('waveHeight', {}).get('noaa', 0),
            'wind_speed': current_hour.get('windSpeed', {}).get('noaa', 0)
        }

    def _determine_condition(self, wave_height: float, wind_speed: float) -> WeatherCondition:
        """Determine weather condition based on wave height and wind speed"""
        if wave_height > 4 or wind_speed > 25:
            return WeatherCondition.SEVERE
        elif wave_height > 2 or wind_speed > 15:
            return WeatherCondition.ROUGH
        elif wave_height > 1 or wind_speed > 10:
            return WeatherCondition.MODERATE
        return WeatherCondition.CALM

    def _get_fallback_data(self) -> Dict:
        """Return fallback data when API fails"""
        current_time = datetime.now()
        fallback_forecast = WeatherForecast(
            location=(0.0, 0.0),  # Default coordinates
            timestamp=current_time,
            condition=WeatherCondition.CALM,
            wind_speed=0,
            wave_height=0,
            visibility=10  # Default visibility
        )

        return {
            'current_weather': WeatherCondition.CALM,
            'weather_forecasts': [fallback_forecast],
            'wave_height': 0,
            'wind_speed': 0
        }
