from pydantic import BaseModel, Field, HttpUrl
from typing import List


class Source(BaseModel):
    name: str = Field(..., description="The name of the source")
    url: HttpUrl = Field(..., description="The link of the source")


class LlmLatency(BaseModel):
    planner: int = Field(..., ge=0, description="Planner LLM latency in ms")
    response: int = Field(..., ge=0, description="Response LLM latency in ms")
    total: int = Field(..., ge=0, description="Total LLM latency in ms")


class ByStepLatency(BaseModel):
    retrieve: int = Field(..., ge=0,
                          description="Retrieval step latency in ms")
    llm: LlmLatency = Field(..., description="LLM latency breakdown")


class Latency(BaseModel):
    total: int = Field(..., ge=0, description="Total latency in ms")
    by_step: ByStepLatency = Field(..., description="Latency by step")


class TokenUsage(BaseModel):
    input: int = Field(..., ge=0, description="Input tokens count")
    output: int = Field(..., ge=0, description="Output tokens count")


class ResponseOutput(BaseModel):
    answer: str = Field(..., description="Grounded answer text")
    sources: List[Source] = Field(
        default_factory=list,
        description="Only the sources actually used in the answer"
    )


class Tokens(BaseModel):
    planner: TokenUsage = Field(..., description="Planner token usage")
    response: TokenUsage = Field(..., description="Response token usage")
    total: TokenUsage = Field(..., description="Total token usage")


class GraphOutput(BaseModel):
    answer: str = Field(..., description="The answer text")
    reasoning: str = Field(
        ..., description="Planner reasoning explaining tool selection")
    sources: List[Source] = Field(...,
                                  description="List of sources used by the response node")
    latency_ms: Latency = Field(..., description="Latency information")
    tokens: Tokens = Field(..., description="Token usage information")
