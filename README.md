# Event Propagator Service

[![CI](https://github.com/alfon96/cybercare-propagator/actions/workflows/ci.yml/badge.svg)](https://github.com/alfon96/cybercare-propagator/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)
![Poetry](https://img.shields.io/badge/deps-poetry-60A5FA?logo=poetry)
![License](https://img.shields.io/badge/license-MIT-green)
![Async](https://img.shields.io/badge/stack-aiohttp%20%7C%20asyncio-ff69b4)

Async event propagator that periodically sends events to an HTTP endpoint (consumer service).

## Prerequisites

Choose one of the following:

- **Poetry**: Python 3.11+, [Poetry 1.8.4](https://python-poetry.org/docs/#installation)
- **Docker**: [Docker](https://docs.docker.com/get-docker/)

## Configuration

This service needs the following environment variables:

| Variable                | Required | Description                                                |
| ----------------------- | -------- | ---------------------------------------------------------- |
| `PERIOD_IN_SECONDS`     | Yes      | Interval between event sends (positive integer)            |
| `HTTP_POST_ENDPOINT`    | Yes      | Consumer endpoint URL (e.g., `http://httpbin.org/post`)    |
| `PAYLOAD_FILE_PATH`     | Yes      | Path to JSON file with event payloads                      |
| `HEALTH_CHECK_ENDPOINT` | No       | Optional consumer health endpoint to probe before starting |

**Payload file format**: JSON array of objects

```json
[
  { "event_type": "user_joined", "event_payload": "Alice" },
  { "event_type": "message", "event_payload": "hello" }
]
```

### Standalone Run Note

> `httpbin.org/post` is used only so the propagator can run **without the consumer service**.  
> It acts as a fake receiver but is a public demo service and may return `503`.  
> In real setups, set `HTTP_POST_ENDPOINT` to the endpoint exposed by [cybercare-consumer](https://github.com/alfon96/cybercare-consumer).

## Getting Started

### Poetry

```bash
git clone https://github.com/alfon96/cybercare-propagator.git
cd cybercare-propagator

# Create a `.env` file in the repo root:
cat > .env << 'EOF'
PERIOD_IN_SECONDS=2
HTTP_POST_ENDPOINT=http://httpbin.org/post
PAYLOAD_FILE_PATH=./payloads.json
EOF

# Create `payloads.json` in the repo root:
cat > payloads.json << 'EOF'
[
  {"event_type":"user_joined","event_payload":"Alice"},
  {"event_type":"message","event_payload":"hello"}
]
EOF
make install
make run
```

### Docker

```bash
git clone https://github.com/alfon96/cybercare-propagator.git
cd cybercare-propagator

cat > payloads.json << 'EOF'
[
  {"event_type":"user_joined","event_payload":"Alice"},
  {"event_type":"message","event_payload":"hello"}
]
EOF

docker build -t event-propagator .
docker run -e PERIOD_IN_SECONDS=2 \
  -e HTTP_POST_ENDPOINT="http://httpbin.org/post" \
  -e PAYLOAD_FILE_PATH="/app/payloads.json" \
  -v $(pwd)/payloads.json:/app/payloads.json \
  event-propagator
```

### DockerHub

```bash
cat > payloads.json << 'EOF'
[
  {"event_type":"user_joined","event_payload":"Alice"},
  {"event_type":"message","event_payload":"hello"}
]
EOF

docker run -e PERIOD_IN_SECONDS=2 \
  -e HTTP_POST_ENDPOINT="http://httpbin.org/post" \
  -e PAYLOAD_FILE_PATH="/app/payloads.json" \
  -v $(pwd)/payloads.json:/app/payloads.json \
  alfo96/af-propagator:latest
```

If using PostgreSQL, install `psql` instead (comes with PostgreSQL).

### How to interpret the metrics

Imagine the period is set to **2 seconds** and you see logs like:

```text
05/12/25 19:38:22 [INFO] ... HTTP metrics: jitter=  0.1 ms | status=200 | ...
05/12/25 19:38:28 [INFO] ... HTTP metrics: jitter=  1.2 ms | status=200 | ...
```

- **jitter** shows how far the send time drifted from the ideal 2-second tick  
  (the closer to 0, the more on time).
- The **timestamp** is **not** when the request was sent, it’s when the **response** arrived.

The service logs on **response** (status + metrics) instead of logging “request fired”, because it lets the user see the response status code.

## Development

### Commands

```bash
make help         # Show all available commands
make install      # Install dependencies with dev tools
make run          # Start the service
make test         # Run pytest
make coverage     # Run tests with coverage report
make lint         # Check code with ruff
make typecheck    # Run mypy type checking
make format       # Auto-format code (isort, black, ruff)
make deps         # Check for dependency issues
make docs         # Generate documentation
make check        # Run all checks: format, lint, typecheck, deps, coverage
```

### CI/CD

Tests and code quality checks run automatically on every commit. Docker images are built and pushed to [alfo96/af-propagator](https://hub.docker.com/r/alfo96/af-propagator) on merge to main.

## Full Stack Setup

> **Recommended**: For a fast setup of the complete stack (Consumer + Propagator + PostgreSQL with Docker Compose), visit the [cybercare-stack](https://github.com/alfon96/cybercare-stack) repository.
>
> The sections below cover running this service individually.

## Features

- **Async scheduling**: Maintains precise intervals with jitter compensation
- **Health checks**: Optional pre-flight check before starting propagation
- **Graceful shutdown**: SIGTERM handling for container orchestration
- **Metrics**: Tracks jitter, failure rate, and request status
- **Retry logic**: Exponential backoff on transient errors

## Architecture

Hexagonal architecture with clear separation: core scheduling logic → adapters (HTTP, config, metrics, signals). Fully tested with pytest.
