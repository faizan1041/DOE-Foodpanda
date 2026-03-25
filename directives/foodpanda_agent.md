# Directive: Foodpanda Ordering Agent

## Goal
Conversational chatbot that helps users find food on Foodpanda Pakistan. Asks for preferences (cuisine, party size, location), scrapes Foodpanda via headless browser, ranks restaurants by rating, and presents the best options with prices and deals.

## Inputs
- **Cuisine preference**: What the user is in the mood for (desi, chinese, pizza, etc.)
- **Party size**: Number of people ordering
- **Delivery area**: User's location in Pakistan (e.g. F-7 Islamabad, Gulberg Lahore)

## Conversation Flow

### Step 1: Greeting
Bot asks what the user is in the mood for.

### Step 2: Cuisine
User says cuisine type. Bot maps it to a Foodpanda category:
- "desi" / "pakistani" / "karahi" / "nihari" / "paratha" → Desi
- "chinese" / "asian" → Chinese
- "pizza" / "italian" → Pizza/Italian
- "burger" / "fast food" → Fast Food
- "biryani" → Biryani
- "bbq" / "tikka" / "seekh" / "grill" → BBQ
- "dessert" / "sweet" / "mithai" / "ice cream" → Desserts

### Step 3: Party Size
Bot asks how many people. Accepts numbers or words ("five" = 5).

### Step 4: Location
Bot asks delivery area. User provides area + city.

### Step 5: Search
Bot opens Foodpanda in headless browser:
1. Navigate to foodpanda.pk
2. Set delivery location (via address input or URL parameter)
3. Search for cuisine type
4. Scroll and scrape restaurant listings
5. Extract: name, rating, delivery time, delivery fee, cuisine tags, deal badges, URL

### Step 6: Rank & Present
- Filter out restaurants with rating < 3.0
- Score: (rating × 20) + deal bonus (15 points) - unknown rating penalty
- Sort by score descending
- Show top 8 as clickable cards with rating, delivery time, and deal info
- For groups of 4+, suggest looking for family/deal combos

### Step 7: Menu (optional)
User picks a restaurant number. Bot scrapes the menu:
- Item names, prices, descriptions
- Calculates estimated cost per person for the group
- Provides direct Foodpanda link to order

### Step 8: Order
User says "order" → bot provides the direct Foodpanda URL.

## Execution Scripts
- `execution/foodpanda_server.py` - FastAPI chat UI server (port 8422)
- `execution/foodpanda_agent.py` - Conversation state machine, ranking, orchestration
- `execution/foodpanda_browser.py` - Playwright automation for foodpanda.pk

## Start Command
```bash
./start_foodpanda.sh
```
Then open http://localhost:8422

## Environment Variables
```
FOODPANDA_PORT=8422  # optional, default 8422
```

## Edge Cases & Learnings
- **Location not found**: Foodpanda may not cover all areas. Bot suggests trying a different area.
- **No restaurants**: Cuisine might not be available in that area. Bot prompts to try different cuisine.
- **Menu scraping fails**: Restaurant pages vary in layout. Bot provides direct URL as fallback.
- **Headless browser**: Runs without visible window. Uses `domcontentloaded` wait (not `networkidle`) to avoid timeouts.
- **Session cleanup**: Idle sessions (30+ minutes) are automatically cleaned up.

## Output
- Conversational chat interface with food recommendations
- Restaurant cards with ratings, delivery times, deals
- Menu items with prices
- Direct Foodpanda order links
- Estimated cost per person for group orders
