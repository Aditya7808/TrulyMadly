# AI Operations Assistant

A multi-agent AI system that accepts natural-language tasks, plans execution steps, calls real APIs, and returns structured answers. Built with LLM-powered reasoning and a Planner-Executor-Verifier architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER TASK (Natural Language)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PLANNER AGENT                          │
│  - Analyzes user intent                                     │
│  - Selects appropriate tools                                │
│  - Creates step-by-step execution plan (JSON)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      EXECUTOR AGENT                         │
│  - Iterates through plan steps                              │
│  - Calls tools (GitHub API, Weather API)                    │
│  - Handles retries on failure                               │
│  - Tracks execution status                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      VERIFIER AGENT                         │
│  - Validates completeness of results                        │
│  - Checks for missing/incorrect data                        │
│  - Formats final structured output                          │
│  - Calculates completeness score                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FINAL RESPONSE                           │
│  - Formatted human-readable output                          │
│  - Structured JSON data                                     │
│  - Execution metrics                                        │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
ai_ops_assistant/
├── agents/
│   ├── __init__.py
│   ├── base.py           # Base agent class
│   ├── planner.py        # Planner Agent - creates execution plans
│   ├── executor.py       # Executor Agent - runs tools
│   ├── verifier.py       # Verifier Agent - validates results
│   └── orchestrator.py   # Coordinates agent workflow
├── tools/
│   ├── __init__.py
│   ├── base.py           # Base tool class and registry
│   ├── github_tool.py    # GitHub API integration
│   └── weather_tool.py   # OpenWeatherMap API integration
├── llm/
│   ├── __init__.py
│   ├── client.py         # OpenAI LLM client
│   └── prompts.py        # Prompt templates for agents
├── main.py               # FastAPI backend
├── app.py                # Streamlit UI
├── config.py             # Configuration management
├── models.py             # Pydantic data models
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Integrated APIs

### 1. GitHub API

- **Endpoint**: `https://api.github.com/search/repositories`
- **Features**: Search repositories, get stars, forks, descriptions, language
- **Authentication**: Optional token for higher rate limits
- **Rate Limit**: 10 requests/minute (unauthenticated), 30 requests/minute (authenticated)

### 2. OpenWeatherMap API

- **Endpoint**: `https://api.openweathermap.org/data/2.5/weather`
- **Features**: Current weather, temperature, humidity, wind speed, conditions
- **Authentication**: Required API key (free tier available)
- **Rate Limit**: 1000 calls/day (free tier)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd TrulyMadly
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENWEATHERMAP_API_KEY=your-openweathermap-api-key-here

# Optional (increases GitHub rate limit)
GITHUB_TOKEN=your-github-token-here

# LLM Configuration (optional)
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.1
```

### 5. Get API Keys

**OpenAI API Key:**

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env` as `OPENAI_API_KEY`

**OpenWeatherMap API Key:**

1. Go to https://openweathermap.org/api
2. Sign up for free account
3. Get API key from dashboard
4. Add to `.env` as `OPENWEATHERMAP_API_KEY`

**GitHub Token (Optional):**

1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Add to `.env` as `GITHUB_TOKEN`

## Running the Project

### Option 1: Streamlit UI (Recommended)

```bash
streamlit run app.py
```

Opens interactive UI at `http://localhost:8501`

### Option 2: FastAPI Backend

```bash
uvicorn main:app --reload
```

API available at `http://localhost:8000`

- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Option 3: Direct API Call

```bash
curl -X POST "http://localhost:8000/task" \
  -H "Content-Type: application/json" \
  -d '{"task": "Find top Python AI repos and weather in Tokyo"}'
```

## Example Prompts to Test

### Basic Examples

1. **GitHub + Weather Combined:**

   ```
   Find top Python machine learning repositories and check the weather in San Francisco
   ```
2. **GitHub Only:**

   ```
   Search GitHub for FastAPI projects with many stars
   ```
3. **Weather Only:**

   ```
   What's the current weather in Tokyo, Japan?
   ```
4. **Multi-city Weather:**

   ```
   Get weather information for London
   ```
5. **Specific Tech Search:**

   ```
   Find popular React dashboard repositories on GitHub
   ```

### Advanced Examples

6. **Combined Query:**

   ```
   I need to find weather API libraries on GitHub and also check the current weather in New York
   ```
7. **Language-specific Search:**

   ```
   Search for trending JavaScript frameworks with over 1000 stars
   ```
8. **Weather + Related Repos:**

   ```
   What's the weather in Berlin and find weather visualization projects
   ```

## API Endpoints

### POST /task

Execute a task with simplified response.

**Request:**

```json
{
  "task": "Find Python AI repos and weather in NYC",
  "retry_on_failure": false
}
```

**Response:**

```json
{
  "success": true,
  "task": "Find Python AI repos and weather in NYC",
  "summary": "Found 5 GitHub repositories. Weather in New York: 15.2C",
  "formatted_response": "...",
  "total_time_ms": 2345.67,
  "plan_steps": 2,
  "completed_steps": 2,
  "completeness_score": 1.0
}
```

### POST /task/full

Execute a task with full detailed response including plan, all step results, and verification data.

### GET /health

Check service health and API configuration status.

## Key Features

### Multi-Agent Design

- **Planner Agent**: Uses LLM to convert natural language to structured JSON execution plan
- **Executor Agent**: Executes plan steps with retry logic and error handling
- **Verifier Agent**: Validates results and produces formatted output

### LLM Usage

- Structured JSON outputs using OpenAI's response format
- Separate prompts for each agent (no monolithic prompts)
- Fallback mechanisms when LLM fails

### Error Handling

- Automatic retries on API failures (3 attempts with exponential backoff)
- Graceful degradation with partial results
- Detailed error messages in responses

### Real-time UI

- Live progress tracking
- Agent-by-agent result visualization
- Expandable step details
- Task history

## Known Limitations / Tradeoffs

1. **Rate Limits**: GitHub API has strict rate limits without authentication (10 req/min). Use a token for better performance.
2. **LLM Dependency**: Requires OpenAI API key. If the LLM fails, fallback plans are less accurate.
3. **Weather API Free Tier**: Limited to 1000 calls/day on free OpenWeatherMap tier.
4. **Sequential Execution**: Steps are executed sequentially. Parallel execution could improve performance for independent steps.
5. **No Caching**: API responses are not cached. Repeated queries make new API calls.
6. **City Name Matching**: Weather tool requires reasonably accurate city names. Typos may cause failures.
7. **English Only**: Prompts and parsing optimized for English language queries.

## Future Improvements

With more time, the following enhancements could be added:

- [ ] Response caching with TTL
- [ ] Parallel tool execution for independent steps
- [ ] Cost tracking per request
- [ ] Additional tools (News API, Stock API, etc.)
- [ ] Conversation history and context
- [ ] User authentication
- [ ] Rate limit handling with queuing
- [ ] Comprehensive test suite

## Technology Stack

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: Streamlit
- **LLM**: OpenAI GPT-3.5/4
- **APIs**: GitHub REST API, OpenWeatherMap API
- **Data Validation**: Pydantic
- **HTTP Client**: httpx (async)
- **Retry Logic**: tenacity

## License

MIT License
