from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, StrictBool, model_validator


class WebSearchInput(BaseModel):
    query: str = Field(..., min_length=3, description="Search query string")


class WeatherInput(BaseModel):
    city: str = Field(..., min_length=3,
                      description="City name for weather lookup")


class WebSearchToolCall(BaseModel):
    tool_name: Literal["web_search"] = Field(
        ..., description="Use web_search for factual or cited lookup"
    )
    arguments: WebSearchInput


class WeatherToolCall(BaseModel):
    tool_name: Literal["weather"] = Field(
        ..., description="Use weather for weather, temperature, or forecast lookup"
    )
    arguments: WeatherInput


ToolCall = Annotated[
    WebSearchToolCall | WeatherToolCall,
    Field(discriminator="tool_name"),
]


class PlannerOutput(BaseModel):
    need_tool: StrictBool
    tool_calls: list[ToolCall] = Field(default_factory=list)
    direct_answer: str | None = None
    reasoning: str = Field(...,
                           description="Why is this tool needed or why no tool is needed?")

    @model_validator(mode="after")
    def validate_shape(self):
        if self.need_tool:
            if not self.tool_calls:
                raise ValueError(
                    "tool_calls is required when need_tool is True")
            if self.direct_answer is not None:
                raise ValueError(
                    "direct_answer must be None when need_tool is True")
        else:
            if self.direct_answer is None or not self.direct_answer.strip():
                raise ValueError(
                    "direct_answer is required when need_tool is False")
            if self.tool_calls not in (None, []):
                raise ValueError(
                    "tool_calls must be empty or None when need_tool is False")
        return self


class SearchSource(BaseModel):
    name: str = Field(..., description="Source name")
    url: HttpUrl = Field(..., description="Source URL")
    snippet: str = Field(..., description="Snippet from the source")


class WebSearchOutput(BaseModel):
    results: list[SearchSource] = Field(...,
                                        description="List of search results")
    error: str | None = Field(
        default=None, description="Tool error message when search request failed.")


class WeatherOutput(BaseModel):
    city: str = Field(..., description="City name")
    temp_c: float = Field(..., description="Temperature in Celsius")
    condition: str = Field(..., description="Weather condition")
    source_name: str = Field(..., description="Weather data source name")
    source_url: HttpUrl = Field(..., description="Weather data source URL")
    error: str | None = Field(
        default=None, description="Tool error message when weather lookup failed.")
