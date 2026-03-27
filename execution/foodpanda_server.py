"""
Foodpanda Chat Server - FastAPI server with dark chatbot UI.

Provides:
- Chat interface for food discovery in Pakistan
- Session-based FoodpandaAgent management
- Restaurant cards and menu rendering
- Runs on port 8422
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from foodpanda_agent import FoodpandaAgent
import lunch_db
from lunch_scheduler import run_daily_lunch_search
from chat_html import get_chat_html


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}
SESSION_TIMEOUT = 30 * 60  # 30 minutes


def cleanup_stale_sessions():
    """Remove sessions that haven't been used in 30 minutes."""
    now = time.time()
    stale = [
        sid for sid, s in sessions.items()
        if now - s["last_used"] > SESSION_TIMEOUT
    ]
    for sid in stale:
        sessions.pop(sid, None)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize default config if not set
    if not lunch_db.get_config("default_location"):
        lunch_db.save_config("default_location", "I-10 Islamabad")

    # Schedule daily lunch search at 12:30 PM PKT (Asia/Karachi = UTC+5)
    scheduler.add_job(
        run_daily_lunch_search,
        CronTrigger(hour=12, minute=30, timezone="Asia/Karachi"),
        id="daily_lunch_search",
        name="Daily lunch restaurant search",
        replace_existing=True,
    )
    scheduler.start()
    print("[scheduler] Daily lunch search scheduled for 12:30 PM PKT")

    # Trigger lunch search immediately on startup
    print("[scheduler] Running lunch search on startup...")
    try:
        await run_daily_lunch_search()
        print("[scheduler] Startup lunch search complete")
    except Exception as e:
        print(f"[scheduler] Startup lunch search failed: {e}")

    yield

    scheduler.shutdown(wait=False)
    sessions.clear()


app = FastAPI(title="Foodpanda Bot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    session_id: str
    message: str = ""


class ResetRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat(req: ChatMessage):
    """Send a message to the agent and get responses."""
    cleanup_stale_sessions()

    sid = req.session_id
    if sid not in sessions:
        sessions[sid] = {
            "agent": FoodpandaAgent(),
            "last_used": time.time(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    session = sessions[sid]
    session["last_used"] = time.time()
    agent: FoodpandaAgent = session["agent"]

    try:
        responses = await agent.handle_message(req.message)
    except Exception as e:
        responses = [{"type": "text", "content": f"Something went wrong: {str(e)}"}]

    return JSONResponse({"responses": responses})


@app.post("/api/chat/reset")
async def reset_session(req: ResetRequest):
    """Reset a chat session."""
    sessions.pop(req.session_id, None)
    return JSONResponse({"status": "ok"})


@app.get("/api/geocode")
async def reverse_geocode(lat: float, lng: float):
    """Reverse geocode lat/lng to a readable address using OpenStreetMap Nominatim (free, no API key)."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1, "zoom": 16, "accept-language": "en"},
                headers={"User-Agent": "DOE-FoodpandaAgent/1.0", "Accept-Language": "en"},
                timeout=10,
            )
            data = resp.json()
            address = data.get("address", {})

            # Build a clean location string
            parts = []
            # Suburb/neighbourhood
            for key in ["suburb", "neighbourhood", "quarter", "residential"]:
                if address.get(key):
                    parts.append(address[key])
                    break
            # City
            for key in ["city", "town", "city_district"]:
                if address.get(key):
                    parts.append(address[key])
                    break

            location = ", ".join(parts) if parts else data.get("display_name", "").split(",")[0]
            return JSONResponse({"location": location, "full_address": data.get("display_name", "")})
    except Exception as e:
        return JSONResponse({"location": None, "error": str(e)}, status_code=500)


class ConfigRequest(BaseModel):
    key: str
    value: str


class BlacklistRequest(BaseModel):
    restaurant_name: str
    restaurant_code: str = ""
    reason: str = ""


@app.get("/api/suggestions/today")
async def get_today_suggestions():
    """Get today's pre-computed lunch suggestions."""
    suggestions = lunch_db.get_today_suggestions()
    return JSONResponse({"suggestions": suggestions or [], "date": datetime.now(timezone.utc).date().isoformat()})


@app.get("/api/history")
async def get_order_history(days: int = 30):
    """Get recent order history."""
    orders = lunch_db.get_recent_orders(days=days)
    return JSONResponse({"orders": orders})


@app.post("/api/config")
async def save_config(req: ConfigRequest):
    """Save a user config value."""
    lunch_db.save_config(req.key, req.value)
    return JSONResponse({"status": "ok", "key": req.key, "value": req.value})


@app.get("/api/config")
async def get_config():
    """Get all user config."""
    config = lunch_db.get_all_config()
    return JSONResponse({"config": config})


@app.post("/api/blacklist")
async def add_to_blacklist(req: BlacklistRequest):
    """Blacklist a restaurant."""
    lunch_db.blacklist_restaurant(req.restaurant_name, req.restaurant_code, req.reason)
    return JSONResponse({"status": "ok", "blacklisted": req.restaurant_name})


@app.get("/api/blacklist")
async def get_blacklist():
    """Get all blacklisted restaurants."""
    blacklist = lunch_db.get_blacklist()
    return JSONResponse({"blacklist": blacklist})


@app.post("/api/trigger-lunch-search")
async def trigger_lunch_search():
    """Manually trigger the daily lunch search (for testing)."""
    results = await run_daily_lunch_search()
    return JSONResponse({"status": "ok", "suggestions": results})


@app.get("/api/sessions")
async def list_sessions():
    """List active sessions."""
    cleanup_stale_sessions()
    result = []
    for sid, s in sessions.items():
        result.append({
            "session_id": sid,
            "created_at": s["created_at"],
            "last_used": datetime.fromtimestamp(s["last_used"], tz=timezone.utc).isoformat(),
        })
    return JSONResponse({"sessions": result})


# ---------------------------------------------------------------------------
# Chat UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return get_chat_html()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8422)

