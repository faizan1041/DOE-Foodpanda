# DOE Foodpanda Agent

Automated lunch ordering assistant for Foodpanda Pakistan. Searches restaurants, scores them based on your history, sends daily suggestions at lunch time, and lets you chat in natural language to find food.

Built on the DOE (Department of Efficiency) architecture: LLMs handle conversation, deterministic scripts handle everything else.

## How It Works

```
User (chat UI)
     |
     v
Claude Code CLI (claude -p)     <-- understands intent, picks action
     |
     v
Deterministic Python tools      <-- search, score, log, blacklist
     |
     v
Foodpanda API + SQLite           <-- data in, data out
```

**Three layers, each does one thing:**

| Layer | LLM? | What it does |
|-------|------|-------------|
| Chat | Yes (`claude -p`, haiku) | Understands "kuch acha khaana chahiye", typos, Urdu, natural language |
| Execution | No | Scrapes Foodpanda, scores restaurants, logs orders, manages blacklist |
| Scheduler | No | Runs at 12:30 PM PKT, scores 50 restaurants, picks top 5, sends desktop notification |

No API keys needed. The chat uses your existing Claude Code subscription via the CLI.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure claude CLI is available
claude --version

# Start the server
./start_foodpanda.sh
```

Open **http://localhost:8422** and start chatting.

## What You Can Say

The chat understands natural language -- no rigid commands:

- "pizza in F-7"
- "kuch spicy chahiye"
- "Check if Howdy is available"
- "show me chinese near gulberg"
- "I ordered chicken biryani and raita"
- "that place was terrible, never suggest it again"
- "what did I order last week?"

## Daily Lunch Flow

1. **Server starts** -- immediately searches Foodpanda and scores restaurants
2. **12:30 PM PKT** -- scheduled search runs again, sends a desktop notification with top 5 picks
3. **User opens chat** -- sees today's picks, taps to view menu or order
4. **After ordering** -- tells the agent what they got, logged for future scoring

### Fully Automatic -- No Interaction Needed

The entire lunch flow runs hands-free once the server is up:

1. **12:25 PM** -- Cron job runs `start_cron.sh`, which starts the server if it's not already running (does nothing if it is)
2. **12:30 PM** -- APScheduler inside the server triggers `run_daily_lunch_search()`:
   - Scrapes 50 restaurants from Foodpanda API for your default location
   - Filters out blacklisted and low-rated places
   - Scores and ranks using your order history (variety, recency, deals)
   - Saves top 5 to SQLite
   - **Sends a desktop notification** with the picks via `notify-send`
3. **You see the notification**, click it or open `http://localhost:8422` -- your picks are already there waiting

You don't need to open the chat, type anything, or even be at your computer before 12:30. The notification pops up on its own.

### Cron Setup

Already configured (`crontab -l`):
```
25 12 * * 1-5 /home/sarah/Desktop/Sarah/DOE-Foodpanda/start_cron.sh
```

On a new machine:
```bash
crontab -e
# Add:
25 12 * * 1-5 /path/to/DOE-Foodpanda/start_cron.sh
```

`start_cron.sh` is idempotent -- checks the PID file, only starts the server if it's not already running. It also exports `DISPLAY` and `DBUS_SESSION_BUS_ADDRESS` so desktop notifications work from cron.

### Scoring (0-100)

| Factor | Points |
|--------|--------|
| Base rating | 0-40 (rating/5 * 40) |
| Haven't ordered there in 4+ days | +20 |
| Cuisine variety (not in last 2 days) | +15 |
| Never ordered before | +10 |
| Ordered yesterday | -30 |
| Active deal | +10 |
| Fast delivery (<=30 min) | +5 |

The system learns from your orders and avoids suggesting the same places repeatedly.

## Project Structure

```
DOE-Foodpanda/
  execution/
    foodpanda_agent.py      # Chat agent (claude -p + deterministic tools)
    foodpanda_browser.py    # Foodpanda API client
    foodpanda_server.py     # FastAPI server (port 8422)
    chat_html.py            # Interactive chat UI
    lunch_db.py             # SQLite database layer
    lunch_scheduler.py      # Scoring algorithm + scheduled search
  directives/
    foodpanda_agent.md      # Agent SOP
    daily_lunch_assistant.md # Daily flow SOP
  start_foodpanda.sh        # Start script
  start_cron.sh             # Cron-safe launcher
  requirements.txt
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat UI |
| `/api/chat` | POST | Send message `{session_id, message}` |
| `/api/suggestions/today` | GET | Today's scored suggestions |
| `/api/history?days=30` | GET | Order history |
| `/api/blacklist` | GET/POST | View or add to blacklist |
| `/api/config` | GET/POST | User config (default location, etc.) |
| `/api/trigger-lunch-search` | POST | Manually trigger a new search |

## Requirements

- Python 3.10+
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- Linux with `notify-send` for desktop notifications (optional)
