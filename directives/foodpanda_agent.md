# Directive: Foodpanda Ordering Agent

## Goal
Food ordering assistant for Foodpanda Pakistan with a clean separation between intelligence and execution.

**Philosophy:** This is a DOE (Department of Efficiency) agent. The architecture separates concerns:
- **Repetitive execution** (searching, scoring, scheduling, logging, blacklisting) = deterministic Python scripts. No LLM needed.
- **User interaction** (understanding intent, presenting results, having a conversation) = Claude Code CLI (`claude -p`). Uses existing subscription, zero API keys.
- **Automated daily flow** (12:30 PM suggestions, scoring, notifications) = fully deterministic, runs on a cron with zero LLM involvement.

## How It Works

### Chat Layer (Claude Code CLI)
The chat UI calls `claude -p` (subprocess) to understand natural language. Uses the existing Claude Code subscription -- no API keys. Users can say anything:
- "Check if Ginyaki is available" -- Claude understands the intent, searches
- "Something spicy near F-7" -- Claude maps this to a search
- "I ordered chicken biryani and raita" -- Claude logs the order
- "That place was terrible, don't show it again" -- Claude blacklists it

Claude responds with JSON action blocks that the server executes deterministically. The LLM never scrapes or writes to the database directly.

### Tools (called by Claude)
- `search_restaurants(location, cuisine?)` -- scrape Foodpanda API, rank results
- `load_menu(restaurant_number)` -- scrape menu for a restaurant
- `open_restaurant(restaurant_number)` -- open in browser for checkout
- `log_order(restaurant_name, items, cuisine?)` -- save to SQLite
- `blacklist_restaurant(restaurant_name, reason?)` -- block forever
- `get_today_suggestions()` -- return pre-computed daily picks
- `get_order_history(days?)` -- return recent orders
- `get_blacklist()` -- return blocked restaurants

### Flow
1. User opens chat -- sees today's suggestions or a greeting
2. User says what they want in natural language
3. Claude understands intent, calls the right tools
4. Tools do the work (deterministic), return results
5. Claude presents results naturally to the user
6. After ordering, Claude asks what they got and logs it

## Execution Scripts
- `execution/foodpanda_server.py` - FastAPI server (port 8422), runs lunch search on startup
- `execution/foodpanda_agent.py` - Claude Code CLI for chat understanding, deterministic tool execution
- `execution/foodpanda_browser.py` - Playwright automation for foodpanda.pk
- `execution/lunch_db.py` - SQLite persistence (orders, blacklist, config, suggestions)
- `execution/lunch_scheduler.py` - Scoring algorithm and scheduled search

## Start Command
```bash
./start_foodpanda.sh
```
Then open http://localhost:8422

## Environment Variables
```
FOODPANDA_PORT=8422  # optional, default 8422
```

No API keys needed. Chat uses `claude -p` (Claude Code CLI) which uses the existing subscription.

## Daily Lunch Assistant
See `directives/daily_lunch_assistant.md` for full details.

- Automatic restaurant search at 12:30 PM PKT via APScheduler
- Also runs immediately on server startup
- Smart scoring: ratings + variety + recency + deals
- Desktop notifications via `notify-send`
- Order history tracking in SQLite
- Restaurant blacklisting

## Edge Cases & Learnings
- **Location not found**: Foodpanda may not cover all areas. Agent suggests trying a different area.
- **No restaurants**: Cuisine might not be available. Agent prompts to try different cuisine.
- **Menu scraping fails**: Restaurant pages vary. Agent provides direct URL as fallback.
- **Session cleanup**: Idle sessions (30+ minutes) auto-cleaned.
- **Server not running at 12:30**: Use `POST /api/trigger-lunch-search` to manually trigger.
- **DHA ambiguity**: "DHA" alone won't resolve -- user must specify "DHA Lahore" or "DHA Karachi".
- **Claude Code CLI not found**: Ensure `claude` is in PATH. Install via `npm install -g @anthropic-ai/claude-code`.
- **Unrecognized input**: Claude handles it conversationally -- no rigid pattern matching.

## Output
- Command-driven chat interface with food search
- Restaurant cards with ratings, delivery times, deals
- Menu items with prices
- Direct Foodpanda order links
- Daily lunch suggestions with smart scoring
- Desktop notifications at lunch time
