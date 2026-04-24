from ..schemas.tools_schema import (
    WeatherInput,
    WeatherOutput,
    WebSearchInput,
    WebSearchOutput,
    SearchSource,
)


async def web_search_tool(args: WebSearchInput) -> WebSearchOutput:
    return WebSearchOutput(results=results[:5])


async def weather_tool(args: WeatherInput) -> WeatherOutput:
    return WeatherOutput(city=args.city,
                         temp_c=weather['temp_c'],
                         condition=weather['condition'],
                         source_name='Dummy Weather Tool',
                         source_url='https://example.com/dummy-weather')
