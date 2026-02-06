"""
OpenWeatherMap API tool for fetching weather data.
"""

import logging
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import ToolResult, ToolType, WeatherData
from .base import BaseTool

logger = logging.getLogger(__name__)


class WeatherTool(BaseTool):
    """Tool for fetching weather data from OpenWeatherMap API."""
    
    name = "Weather"
    tool_type = ToolType.WEATHER
    description = "Get current weather information for a city"
    
    def __init__(self):
        self.base_url = settings.openweathermap_api_base
        self.api_key = settings.openweathermap_api_key
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make a request to OpenWeatherMap API."""
        params["appid"] = self.api_key
        
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def execute(
        self,
        city: str,
        country_code: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """
        Get current weather for a city.
        
        Args:
            city: City name
            country_code: Optional ISO country code (e.g., US, UK, JP)
            
        Returns:
            ToolResult with weather data
        """
        try:
            query = city
            if country_code:
                query = f"{city},{country_code}"
            
            params = {
                "q": query,
                "units": "metric"
            }
            
            logger.info(f"Fetching weather for: {query}")
            data = await self._make_request("/weather", params)
            
            main = data.get("main", {})
            weather_info = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            sys_info = data.get("sys", {})
            
            temp_celsius = main.get("temp", 0)
            temp_fahrenheit = (temp_celsius * 9/5) + 32
            
            weather_data = WeatherData(
                city=data.get("name", city),
                country=sys_info.get("country", ""),
                temperature_celsius=round(temp_celsius, 1),
                temperature_fahrenheit=round(temp_fahrenheit, 1),
                feels_like_celsius=round(main.get("feels_like", 0), 1),
                humidity=main.get("humidity", 0),
                description=weather_info.get("description", "").capitalize(),
                wind_speed_mps=wind.get("speed", 0),
                visibility_km=round(data.get("visibility", 0) / 1000, 1)
            )
            
            return self._create_result(
                success=True,
                data=weather_data.model_dump()
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Weather API error: {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = f"City not found: {city}"
            elif e.response.status_code == 401:
                error_msg = "Invalid API key"
            logger.error(error_msg)
            return self._create_result(success=False, error=error_msg)
            
        except Exception as e:
            logger.error(f"Weather tool error: {e}")
            return self._create_result(success=False, error=str(e))
    
    async def get_forecast(
        self,
        city: str,
        country_code: Optional[str] = None,
        days: int = 5
    ) -> ToolResult:
        """
        Get weather forecast for a city.
        
        Args:
            city: City name
            country_code: Optional ISO country code
            days: Number of days (1-5)
            
        Returns:
            ToolResult with forecast data
        """
        try:
            query = city
            if country_code:
                query = f"{city},{country_code}"
            
            params = {
                "q": query,
                "units": "metric",
                "cnt": min(days * 8, 40)
            }
            
            data = await self._make_request("/forecast", params)
            
            forecasts = []
            for item in data.get("list", []):
                forecast = {
                    "datetime": item.get("dt_txt"),
                    "temperature_celsius": item.get("main", {}).get("temp"),
                    "description": item.get("weather", [{}])[0].get("description", "")
                }
                forecasts.append(forecast)
            
            return self._create_result(
                success=True,
                data={
                    "city": data.get("city", {}).get("name", city),
                    "forecasts": forecasts
                }
            )
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return self._create_result(success=False, error=str(e))
