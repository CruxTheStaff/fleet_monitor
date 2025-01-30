from src.utils.weather_api import WeatherAPI


def test_weather_api():
    # Create WeatherAPI instance
    weather_api = WeatherAPI()

    # Test coordinates (Πειραιάς)
    lat = 37.9838
    lon = 23.7275

    try:
        # Get weather data
        weather_data = weather_api.get_vessel_weather_data(lat, lon)

        # Print results
        print("Weather Data Retrieved:")
        print(f"Current Weather: {weather_data['current_weather']}")
        print(f"Wave Height: {weather_data['wave_height']} meters")
        print(f"Wind Speed: {weather_data['wind_speed']} knots")
        print("\nForecasts:")
        for forecast in weather_data['weather_forecasts'][:3]:  # Show first 3 forecasts
            print(f"Time: {forecast.timestamp}")
            print(f"Condition: {forecast.condition}")
            print(f"Wave Height: {forecast.wave_height}")
            print(f"Wind Speed: {forecast.wind_speed}")
            print("---")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    test_weather_api()

