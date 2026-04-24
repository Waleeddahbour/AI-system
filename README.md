# AI Assessment Agentic QA Service

A small production-minded **Agentic QA** service built for the take-home assessment.

The service:

- decides whether a question should be answered directly or with tools
- executes the minimal tool set needed
- returns a grounded structured response
- tracks latency and token usage
- persists chat history with cache + database fallback

## What it does

The system accepts a user question and returns a structured JSON response:

```json
{
  "answer": "string",
  "reasoning": "string",
  "sources": [
    {
      "name": "string",
      "url": "string"
    }
  ],
  "latency_ms": {
    "total": 123,
    "by_step": {
      "retrieve": 45,
      "llm": {
        "planner": 20,
        "response": 58,
        "total": 78
      }
    }
  },
  "tokens": {
    "planner": {
      "input": 0,
      "output": 0
    },
    "response": {
      "input": 0,
      "output": 0
    },
    "total": {
      "input": 0,
      "output": 0
    }
  }
}
```

## Core features

- **Explicit planner / agent loop in application code**
- **Tool registry** with clear schemas and handlers
- **Two tools**
  - `web_search` DuckDuckGo
  - `weather` a dummy tool

- **Structured planner output**
- **Structured final response**
- **FastAPI API**
- **History cache + DB fallback**
- **SQLAlchemy models**
- **Alembic migrations**
- **Dockerized setup**
- **Basic tests**

## Architecture

The application uses a small single-agent flow.

### 1. Preparation

- validates input
- loads recent history from in-memory cache
- falls back to the database if cache misses
- initializes state

### 2. Planner

The planner decides whether tools are needed.

It returns structured output with:

- `need_tool`
- `tool_calls`
- `direct_answer`
- `reasoning`

This allows the system to:

- skip tool execution when no tools are needed for generic queries like hello, how are you, etc.
- skip the second LLM call when a direct answer is enough

### 3. Tool execution

If tools are needed:

- tool calls are validated
- tool handlers are executed from the registry
- results are collected and cached where appropriate

### 4. Response generation

If tools were used:

- the response node generates a grounded final answer
- only tool-derived sources are included

If tools were not used:

- the planner’s direct answer is returned immediately

## Tools

### `web_search`

Used for:

- factual lookup
- citation-requiring questions
- verification
- real-world entities
- follow-up questions that need grounding

### `weather`

Used for:

- weather
- temperature
- forecast-style questions

## Project structure

```text
AI-Assessment/
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── ai/
│   │   ├── nodes/
│   │   │   ├── planner_node.py
│   │   │   ├── preparation_node.py
│   │   │   ├── response_node.py
│   │   │   └── tool_node.py
│   │   ├── schemas/
│   │   │   ├── graph_schema.py
│   │   │   └── tools_schema.py
│   │   ├── tools/
│   │   │   └── tools.py
│   │   ├── agent.py
│   │   ├── handleDB.py
│   │   ├── history_cache.py
│   │   ├── prompt.py
│   │   └── state.py
│   ├── config/
│   │   ├── db.py
│   │   └── logging.py
│   ├── models/
│   │   ├── accountModels.py
│   │   ├── chatModels.py
│   │   └── userModels.py
│   ├── routes/
│   │   └── chatRoute.py
│   ├── tests/
│   │   ├── test_planner.py
│   │   ├── test_response.py
│   │   ├── test_routes.py
│   │   └── test_tools.py
│   └── seed_superadmin.py
├── .env.example
├── alembic.ini
├── chat_with_agent.py
├── docker-compose.yaml
├── Dockerfile
├── main.py
├── pyproject.toml
└── uv.lock
```

## Environment variables

Create a `.env` file from `.env.example`.

Example:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
DB_URI=postgresql+psycopg://postgres:postgres@postgres:5432/postgres

SUPERADMIN_USERNAME=superadmin
SUPERADMIN_EMAIL=superadmin@example.com
SUPERADMIN_PASSWORD=supersecret
```

## Running locally

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn main:app --reload
```

**Note**: Postgres must be running.

## Running with Docker

Build the image:

```bash
docker compose build
```

Start containers:

```bash
docker compose up -d
```

Apply migrations:

```bash
docker compose exec app alembic upgrade head
```

Seed initial data:

```bash
docker compose exec app python -m app.seed_superadmin
```

Or simply using `chat_with_agent.py` after the setup:

```bash
# In docker:
 docker compose exec app python manual_test_agent.py

 # In project root:
 .venv\Scripts\activate
 python manual_test_agent.py
```

## API

### Health check

```http
GET /health
```

### Root

```http
GET /
```

### Chat

```http
POST /chat
```

Request body:

```json
{
  "question": "What is the weather in Dubai?",
  "account_id": 1,
  "user_id": 1
}
```

Example response:

```json
{
  "answer": "I used the weather tool. The weather in Dubai is sunny with a temperature of 34°C.",
  "reasoning": "The question is about weather in a specific city, so the weather tool was needed.",
  "sources": [
    {
      "name": "Dummy Weather Tool",
      "url": "https://example.com/dummy-weather"
    }
  ],
  "latency_ms": {
    "total": 214,
    "by_step": {
      "retrieve": 41,
      "llm": {
        "planner": 57,
        "response": 116,
        "total": 173
      }
    }
  },
  "tokens": {
    "planner": {
      "input": 612,
      "output": 44
    },
    "response": {
      "input": 215,
      "output": 44
    },
    "total": {
      "input": 827,
      "output": 88
    }
  }
}
```

## Running pytests

```bash
uv run tests
```

## Design decisions

### Why an explicit planner + tool registry?

The assessment asked for the **core agent loop (planner + tool registry)** to be visible in application code.
Because of that, the planner, tool routing, validation, and response synthesis are implemented explicitly instead of being fully hidden inside a framework abstraction.

### Why structured schemas?

Pydantic models are used for:

- planner output
- tool input/output
- final response

This keeps the system predictable, validated, and easier to debug.

### Why keep planner and response separate?

This keeps responsibilities clear:

- the planner decides whether tools are needed
- the tool node executes validated calls
- the response node turns tool results into grounded output

It also allows direct-answer questions to skip tool execution and skip the second LLM call.

### Why cache history?

Recent chat history is cached in memory to reduce repeated DB reads.
If the cache misses, the system falls back to the database and rehydrates the cache.

## Tradeoffs

This is intentionally a small prototype.

### Simplifications

- single rolling history per `(account_id, user_id)`
- in-memory cache instead of Redis
- minimal tool set
- lightweight observability
- no auth layer

### What I would improve next

- Redis-backed cache
- per-conversation/session model
- stronger retry / circuit-breaker behavior for tools
- streaming responses
- richer tracing / dashboards
- broader evaluation coverage
- stricter source-quality controls for web search

## Notes for reviewer

Docker run flow is:

```bash
docker compose build
docker compose up -d
docker compose exec app alembic upgrade head
docker compose exec app python -m app.seed_superadmin
```

Then call:

```http
POST http://localhost:3000/chat
```

with a body like:

```json
{
  "question": "What is the weather in Dubai?",
  "account_id": 1,
  "user_id": 1
}
```
