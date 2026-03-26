# Directive: Daily Lunch Assistant

## Goal
Proactive daily lunch assistant that automatically searches for restaurants at 12:30 PM PKT, scores them based on ratings, order history, and variety, sends a desktop notification with top picks, and tracks what the user orders to improve future suggestions.

## Daily Flow

### 12:30 PM - Automated Search
1. APScheduler triggers `run_daily_lunch_search()` in `execution/lunch_scheduler.py`
2. Reads default location from SQLite (`user_config` table)
3. Searches Foodpanda API for restaurants (no cuisine filter, broad pool of 50)
4. Filters: rating >= 3.5, not blacklisted
5. Scores restaurants using the variety-aware algorithm (see Scoring below)
6. Saves top 5 to `daily_suggestions` table
7. Sends desktop notification via `notify-send`

### 12:30-1:00 PM - User Interaction
1. User opens http://localhost:8422
2. Chat detects today's suggestions exist → shows them as greeting instead of generic welcome
3. User picks a restaurant, browses menu, orders on Foodpanda
4. Agent auto-asks "What did you end up ordering?"
5. Order is logged to `order_history` table

### Bad Experience
- User says "blacklist X" or "never suggest X again"
- Agent writes to `restaurant_blacklist` table
- Restaurant is permanently excluded from future suggestions

## Scoring Algorithm (0-100)

| Component | Points | Logic |
|-----------|--------|-------|
| Base rating | 0-40 | `(rating / 5.0) * 40` |
| Variety (restaurant) | +20 | Not ordered in last 4 days |
| Variety (cuisine) | +15 | Cuisine not ordered in last 2 days |
| Novelty | +10 | Never ordered before |
| Recency penalty | -30 to 0 | -30 yesterday, -20 two days ago, -10 three days ago |
| Deal bonus | +10 | Active deal/discount |
| Delivery speed | +2 to +5 | ≤30 min: +5, ≤45 min: +2 |

## Execution Scripts
- `execution/lunch_db.py` - SQLite persistence (order history, blacklist, config, suggestions)
- `execution/lunch_scheduler.py` - Scoring algorithm and scheduled search logic
- `execution/foodpanda_server.py` - APScheduler integration, new API endpoints
- `execution/foodpanda_agent.py` - New actions: `log_order`, `blacklist_restaurant`, `show_today_suggestions`

## API Endpoints
- `GET /api/suggestions/today` - Today's suggestions
- `GET /api/history?days=30` - Order history
- `POST /api/config` - Save config (`{"key": "...", "value": "..."}`)
- `GET /api/config` - Get all config
- `POST /api/blacklist` - Blacklist a restaurant
- `GET /api/blacklist` - Get blacklist
- `POST /api/trigger-lunch-search` - Manual trigger (testing)

## Database
SQLite at `execution/lunch_history.db` with tables:
- `user_config` - Key/value store for preferences
- `order_history` - What was ordered, when, from where
- `restaurant_blacklist` - Never-suggest-again list
- `daily_suggestions` - Daily scored suggestion sets

## Edge Cases
- **Server not running at 12:30**: Suggestions won't fire. User can manually trigger via `/api/trigger-lunch-search`
- **No restaurants found**: Notification tells user to search manually via chat
- **All restaurants blacklisted**: Very unlikely, but scoring will return empty → fallback notification
- **First day (no history)**: All restaurants get max variety bonus, sorted purely by rating + deals
