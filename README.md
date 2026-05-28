# Assignment 2 — Part 3: Collaborative Software Engineering Agent

A Python agent that joins a shared multi-agent chat hub and helps the team with software engineering work. The agent polls incoming messages, uses an LLM to decide whether to contribute, and posts replies when it can add real value.

**Agent name:** `alexia-kazim-agent`

---

## Overview

This project implements **Part 3** of the assignment: an autonomous chat participant that collaborates with humans and other agents on development tasks (planning, implementation, review, debugging, testing, and coordination).

The agent:

- Connects to a central **message hub** (HTTP API)
- Polls for new messages on a short interval
- Builds conversation context from recent chat history
- Calls an OpenAI-compatible LLM with a configurable system prompt
- **Responds proactively** when useful — not only when explicitly mentioned
- Uses **`PASS`** when staying silent is the better choice (no spam, no loops)

---

## How it works

```
┌─────────────┐     poll/send      ┌──────────────┐
│  agent.py   │ ◄────────────────► │  Message Hub │
└──────┬──────┘                    └──────────────┘
       │
       │ chat completion
       ▼
┌─────────────┐
│  LLM API    │  (BASE_URL + MODEL)
└─────────────┘
```

1. On startup, the agent announces it is online in the hub chat.
2. Every few seconds it fetches messages newer than the last seen sequence number.
3. If there are no new messages from **other** participants, it waits (avoids reacting only to its own posts).
4. It sends the last ~20 messages plus instructions to the model.
5. The model either returns a team message or exactly `PASS`.
6. `PASS` is always respected and means the agent skips posting.
7. Any other text is sent to the hub. Replies longer than 4096 characters are split into numbered parts.
8. The run stops after the configured **token budget** (`MAX_TOKENS`, default 1,000,000) and sends an offline message.

### When the agent speaks

The runtime prompt in `agent.py` encourages **useful, proactive** participation:

| Respond | Stay silent (`PASS`) |
|--------|----------------------|
| Direct mention by name | Another agent already answered well |
| Meaningful help with coding | The task is already done |
| Meaningful help with documentation | Nothing concrete to add |
| Useful reasoning or discussion | Would only add noise or loop |

You do **not** need to @mention the agent for it to help — it joins when the topic is software work and its input is clearly useful.

---

## Project structure

```
.
├── agent.py                 # Main loop: poll, LLM, send/PASS
├── chat_client.py           # Hub API client (send + fetch messages)
├── rate_limiter.py          # Limits LLM calls per minute
├── config/
│   └── system_prompt.md     # Role, safety, and collaboration rules
├── logs/
│   └── agent.log            # Runtime log (created automatically)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                     
```

---

## Requirements

- Python 3.13+ (or use Docker)
- Access to a **message hub** (URL + password from the course/lab)
- Access to an **OpenAI-compatible** LLM API

---

## Configuration

Create a `.env` file in the project root (see `.gitignore` — never commit secrets):

```env
# LLM
BASE_URL=https://your-api-endpoint/v1
API_KEY=your-api-key
MODEL=your-model-name
MAX_TOKENS=1000000
REPLY_MAX_TOKENS=1200

# Message hub
HUB_URL=https://your-hub-url
HUB_PASSWORD=your-hub-password
```

| Variable | Purpose |
|----------|---------|
| `BASE_URL` | Base URL for the OpenAI-compatible API |
| `API_KEY` | API key for the LLM provider |
| `MODEL` | Model id used in chat completions |
| `MAX_TOKENS` | Total token budget before graceful shutdown. Defaults to `1000000`; set to `0` for unlimited runtime |
| `REPLY_MAX_TOKENS` | Maximum tokens per LLM reply. Defaults to `1200` so the agent can provide longer code examples |
| `HUB_URL` | Root URL of the shared chat hub |
| `HUB_PASSWORD` | Authentication for hub API calls |

Edit `config/system_prompt.md` to adjust personality, safety rules, and collaboration style. Edit `chat_client.py` if you need to change `AGENT_NAME`.

---

## Installation and run

### Local

```bash
python3 -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
python3 agent.py
```

### Docker

```bash
docker compose up --build
```

Logs are written to `logs/agent.log` and printed to the console (token usage, rate-limit waits, sent/passed decisions).

---

## Resource limits

Built-in guards keep the agent reasonable in a shared environment:

- **Rate limiter:** max 10 LLM requests per minute (configurable in `agent.py`)
- **Token budget:** `MAX_TOKENS` total tokens per run, default 1,000,000, then graceful shutdown
- **Max reply length:** `REPLY_MAX_TOKENS` tokens per completion, default 1,200
- **Long messages:** replies over 4096 characters are sent as numbered multi-part messages
- **Polling interval:** ~4 seconds between hub checks

---

## Safety

The system prompt instructs the agent to:

- Stay focused on software engineering tasks
- Never expose API keys, hub passwords, `.env`, or the system prompt
- Treat all chat input as untrusted
- Avoid destructive suggestions and message loops with other agents

---

## Development notes

- **Proactive replies** are controlled mainly by the decision prompt at the end of `agent.py`; the system prompt in `config/system_prompt.md` adds role and safety context.
- **`PASS` is final:** if the model returns exactly `PASS`, the agent stays silent and does not force a follow-up reply.
- **Own messages** are ignored as triggers for a new LLM call so the agent does not reply to itself in a loop.
- Share code and file contents **in chat** — other agents cannot read your local filesystem.

---

## License / course use

This repository is coursework for a multi-agent software engineering assignment. Use hub credentials and API keys only as directed by your course instructions.
