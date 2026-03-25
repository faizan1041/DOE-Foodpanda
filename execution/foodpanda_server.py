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

from foodpanda_agent import FoodpandaAgent


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
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


def get_chat_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Foodpanda Bot</title>
<style>
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

:root {
    --bg: #f5f5f5;
    --surface: #ffffff;
    --surface-alt: #e8e8e8;
    --border: #d1d5db;
    --text: #1a1a1a;
    --text-subtle: #6b7280;
    --text-muted: #9ca3af;
    --accent: #d70f64;
    --green: #d70f64;
    --green-bright: #e81b72;
    --green-text: #d70f64;
    --radius: 16px;
    --header-h: 60px;
    --input-h: 68px;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
}

html, body {
    height: 100%;
    overflow: hidden;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ---- Header ---- */
.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--header-h);
    display: flex;
    align-items: center;
    padding: 0 20px;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    z-index: 100;
}

.header-icon {
    font-size: 24px;
    margin-right: 12px;
    display: flex;
    align-items: center;
}

.header-info {
    flex: 1;
    min-width: 0;
}

.header-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 8px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green-bright);
    display: inline-block;
    box-shadow: 0 0 6px rgba(46, 160, 67, 0.4);
}

.header-subtitle {
    font-size: 12px;
    color: var(--text-subtle);
    margin-top: 1px;
}

.header-actions {
    display: flex;
    gap: 8px;
}

.btn-icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-subtle);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    transition: all 0.15s ease;
}

.btn-icon:hover {
    background: var(--surface-alt);
    color: var(--text);
    border-color: #484f58;
}

/* ---- Chat area ---- */
.chat-area {
    position: fixed;
    top: var(--header-h);
    left: 0;
    right: 0;
    bottom: var(--input-h);
    overflow-y: auto;
    overflow-x: hidden;
    padding: 20px 16px;
    scroll-behavior: smooth;
}

.chat-area::-webkit-scrollbar {
    width: 6px;
}
.chat-area::-webkit-scrollbar-track {
    background: transparent;
}
.chat-area::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
}

.chat-container {
    max-width: 720px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

/* ---- Messages ---- */
.msg-row {
    display: flex;
    flex-direction: column;
    animation: msgIn 0.3s ease-out both;
}

@keyframes msgIn {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.msg-row.bot {
    align-items: flex-start;
}

.msg-row.user {
    align-items: flex-end;
}

.msg-bubble {
    max-width: 80%;
    padding: 10px 14px;
    font-size: 15px;
    line-height: 1.5;
    word-wrap: break-word;
    overflow-wrap: break-word;
}

.msg-row.bot .msg-bubble {
    background: var(--surface-alt);
    border-radius: 4px var(--radius) var(--radius) var(--radius);
    color: var(--text);
}

.msg-row.user .msg-bubble {
    background: var(--green);
    border-radius: var(--radius) 4px var(--radius) var(--radius);
    color: #fff;
}

.msg-bubble strong {
    font-weight: 600;
}

.msg-time {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
    padding: 0 4px;
}

/* ---- Restaurant cards ---- */
.restaurant-list {
    max-width: 80%;
    display: flex;
    flex-direction: column;
    gap: 8px;
    animation: msgIn 0.3s ease-out both;
}

.restaurant-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}

.restaurant-card:hover {
    border-color: var(--accent);
    background: #fff0f5;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.restaurant-card:active {
    transform: translateY(0);
}

.restaurant-rank {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--surface-alt);
    color: var(--accent);
    font-weight: 700;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.restaurant-info {
    flex: 1;
    min-width: 0;
}

.restaurant-name {
    font-weight: 600;
    font-size: 15px;
    color: var(--text);
    margin-bottom: 4px;
}

.restaurant-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    color: var(--text-subtle);
    margin-bottom: 6px;
    flex-wrap: wrap;
}

.restaurant-rating {
    color: #f0b232;
}

.restaurant-deal {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    background: rgba(215, 15, 100, 0.1);
    color: var(--green-text);
    font-size: 12px;
    font-weight: 500;
}

.restaurant-cuisines {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}

.cuisine-tag {
    padding: 2px 8px;
    border-radius: 6px;
    background: var(--surface-alt);
    color: var(--text-subtle);
    font-size: 12px;
}

/* ---- Menu items ---- */
.menu-card {
    max-width: 80%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    animation: msgIn 0.3s ease-out both;
}

.menu-item {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    gap: 16px;
}

.menu-item:last-child {
    border-bottom: none;
}

.menu-item-info {
    flex: 1;
    min-width: 0;
}

.menu-item-name {
    font-weight: 600;
    font-size: 14px;
    color: var(--text);
}

.menu-item-desc {
    font-size: 13px;
    color: var(--text-subtle);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 400px;
}

.menu-item-price {
    font-weight: 600;
    font-size: 14px;
    color: var(--green-text);
    white-space: nowrap;
    flex-shrink: 0;
}

/* ---- Typing indicator ---- */
.typing-row {
    display: flex;
    align-items: flex-start;
    animation: msgIn 0.25s ease-out both;
}

.typing-bubble {
    background: var(--surface-alt);
    border-radius: 4px var(--radius) var(--radius) var(--radius);
    padding: 12px 18px;
    display: flex;
    gap: 5px;
    align-items: center;
}

.typing-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-subtle);
    animation: bounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0.32s; }

@keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
}

/* ---- Input bar ---- */
.input-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--input-h);
    background: var(--surface);
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 16px;
    z-index: 100;
}

.input-container {
    max-width: 720px;
    margin: 0 auto;
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
}

.input-field {
    flex: 1;
    height: 42px;
    padding: 0 16px;
    border-radius: 21px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font-size: 15px;
    font-family: var(--font);
    outline: none;
    transition: border-color 0.2s ease;
}

.input-field::placeholder {
    color: var(--text-muted);
}

.input-field:focus {
    border-color: var(--accent);
}

.input-field:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.send-btn {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: none;
    background: var(--green);
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
    background: var(--green-bright);
    transform: scale(1.05);
}

.send-btn:active:not(:disabled) {
    transform: scale(0.95);
}

.send-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.send-btn svg {
    width: 18px;
    height: 18px;
    fill: currentColor;
}

.loc-btn {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--accent);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    flex-shrink: 0;
}
.loc-btn:hover {
    background: var(--border);
    transform: scale(1.05);
}
.loc-btn:active {
    transform: scale(0.95);
}
.loc-btn.loading {
    animation: pulse 1s ease-in-out infinite;
    pointer-events: none;
    opacity: 0.6;
}
@keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}

/* ---- Responsive ---- */
@media (max-width: 600px) {
    .msg-bubble,
    .restaurant-list,
    .menu-card {
        max-width: 90%;
    }

    .chat-area {
        padding: 16px 12px;
    }

    .menu-item-desc {
        max-width: 200px;
    }
}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="header-icon">🍕</div>
    <div class="header-info">
        <div class="header-title">
            Foodpanda Bot
            <span class="status-dot"></span>
        </div>
        <div class="header-subtitle">Your AI food finder for Pakistan</div>
    </div>
    <div class="header-actions">
        <button class="btn-icon" onclick="resetChat()" title="New chat">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M1.5 1h13l.5.5v10l-.5.5H7.7l-3.1 2.8L4 14V12H1.5l-.5-.5v-10l.5-.5zm1 1v9h2.5l.5.5v1.8l2.3-2.1.2-.2h6V2h-12z"/></svg>
        </button>
    </div>
</div>

<!-- Chat area -->
<div class="chat-area" id="chatArea">
    <div class="chat-container" id="chatContainer"></div>
</div>

<!-- Input bar -->
<div class="input-bar">
    <div class="input-container">
        <button class="loc-btn" id="locBtn" onclick="useMyLocation()" title="Use my location" style="display:none;">
            <svg viewBox="0 0 24 24" width="20" height="20"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill="currentColor"/></svg>
        </button>
        <input
            type="text"
            class="input-field"
            id="msgInput"
            placeholder="Type your message..."
            autocomplete="off"
        />
        <button class="send-btn" id="sendBtn" onclick="sendMessage()">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
    </div>
</div>

<script>
// ---- State ----
const SESSION_ID = crypto.randomUUID();
let isWaiting = false;

const chatContainer = document.getElementById('chatContainer');
const chatArea = document.getElementById('chatArea');
const msgInput = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');

// ---- Helpers ----
function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function formatText(text) {
    // Bold: **text**
    let out = escapeHtml(text);
    out = out.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
    // Newlines
    out = out.replace(/\\n/g, '<br>');
    return out;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    });
}

function setInputEnabled(enabled) {
    isWaiting = !enabled;
    msgInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
    if (enabled) msgInput.focus();
}

// ---- Render messages ----

function addUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'msg-row user';
    row.innerHTML = `
        <div class="msg-bubble">${escapeHtml(text)}</div>
        <div class="msg-time">${formatTime()}</div>
    `;
    chatContainer.appendChild(row);
    scrollToBottom();
}

function addBotText(text) {
    const row = document.createElement('div');
    row.className = 'msg-row bot';
    row.innerHTML = `
        <div class="msg-bubble">${formatText(text)}</div>
        <div class="msg-time">${formatTime()}</div>
    `;
    chatContainer.appendChild(row);
    scrollToBottom();
}

function addRestaurantCards(restaurants) {
    const list = document.createElement('div');
    list.className = 'restaurant-list';

    restaurants.forEach((r, i) => {
        const rank = r.rank || (i + 1);
        const card = document.createElement('div');
        card.className = 'restaurant-card';
        card.onclick = () => sendAutoMessage(String(rank));

        let metaHtml = '';
        if (r.rating) metaHtml += `<span class="restaurant-rating">⭐ ${escapeHtml(String(r.rating))}</span>`;
        if (r.delivery_time) metaHtml += `<span>${escapeHtml(r.delivery_time)}</span>`;

        let dealHtml = '';
        if (r.deal) dealHtml = `<span class="restaurant-deal">${escapeHtml(r.deal)}</span>`;

        let cuisinesHtml = '';
        if (r.cuisines && r.cuisines.length) {
            cuisinesHtml = '<div class="restaurant-cuisines">' +
                r.cuisines.map(c => `<span class="cuisine-tag">${escapeHtml(c)}</span>`).join('') +
                '</div>';
        }

        card.innerHTML = `
            <div class="restaurant-rank">${rank}</div>
            <div class="restaurant-info">
                <div class="restaurant-name">${escapeHtml(r.name || '')}</div>
                <div class="restaurant-meta">${metaHtml} ${dealHtml}</div>
                ${cuisinesHtml}
            </div>
        `;
        list.appendChild(card);
    });

    const timeEl = document.createElement('div');
    timeEl.className = 'msg-time';
    timeEl.textContent = formatTime();

    const wrapper = document.createElement('div');
    wrapper.className = 'msg-row bot';
    wrapper.appendChild(list);
    wrapper.appendChild(timeEl);
    chatContainer.appendChild(wrapper);
    scrollToBottom();
}

function addMenuItems(items) {
    const card = document.createElement('div');
    card.className = 'menu-card';

    items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'menu-item';
        row.innerHTML = `
            <div class="menu-item-info">
                <div class="menu-item-name">${escapeHtml(item.name || '')}</div>
                ${item.description ? `<div class="menu-item-desc">${escapeHtml(item.description)}</div>` : ''}
            </div>
            <div class="menu-item-price">${escapeHtml(item.price || '')}</div>
        `;
        card.appendChild(row);
    });

    const timeEl = document.createElement('div');
    timeEl.className = 'msg-time';
    timeEl.textContent = formatTime();

    const wrapper = document.createElement('div');
    wrapper.className = 'msg-row bot';
    wrapper.appendChild(card);
    wrapper.appendChild(timeEl);
    chatContainer.appendChild(wrapper);
    scrollToBottom();
}

// ---- Typing indicator ----

let typingEl = null;

function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'typing-row';
    typingEl.innerHTML = `
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatContainer.appendChild(typingEl);
    scrollToBottom();
}

function hideTyping() {
    if (typingEl) {
        typingEl.remove();
        typingEl = null;
    }
}

// ---- API ----

async function postChat(message) {
    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: SESSION_ID, message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
}

// ---- Render responses sequentially with delay ----

async function renderResponses(responses) {
    for (let i = 0; i < responses.length; i++) {
        if (i > 0) await new Promise(r => setTimeout(r, 300));
        const resp = responses[i];
        switch (resp.type) {
            case 'text':
                addBotText(resp.content);
                break;
            case 'restaurants':
                addRestaurantCards(resp.content);
                break;
            case 'menu':
                addMenuItems(resp.content);
                break;
            default:
                addBotText(typeof resp.content === 'string' ? resp.content : JSON.stringify(resp.content));
        }
    }
}

// ---- Geolocation ----

const locBtn = document.getElementById('locBtn');

function checkShowLocationButton(responses) {
    // Show the location button if the bot just asked for delivery area
    const hasLocationAsk = responses.some(r =>
        r.type === 'text' && (r.content.includes('delivery area') || r.content.includes('delivery location'))
    );
    locBtn.style.display = hasLocationAsk ? 'flex' : 'none';
}

async function useMyLocation() {
    if (!navigator.geolocation) {
        addBotText("Your browser doesn't support geolocation. Please type your area manually.");
        return;
    }

    locBtn.classList.add('loading');

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;
            try {
                const res = await fetch(`/api/geocode?lat=${latitude}&lng=${longitude}`);
                const data = await res.json();
                const location = data.location;

                locBtn.classList.remove('loading');
                locBtn.style.display = 'none';

                if (location) {
                    // Auto-send the detected location as a message
                    await sendAutoMessage(location);
                } else {
                    addBotText("Couldn't determine your area from GPS. Please type it manually.");
                    setInputEnabled(true);
                }
            } catch (err) {
                locBtn.classList.remove('loading');
                addBotText("Couldn't look up your location. Please type your area manually.");
                console.error(err);
            }
        },
        (error) => {
            locBtn.classList.remove('loading');
            if (error.code === error.PERMISSION_DENIED) {
                addBotText("Location access denied. No worries - just type your area instead!");
            } else {
                addBotText("Couldn't get your location. Please type your area manually.");
            }
            console.error('Geolocation error:', error);
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

// ---- Send message ----

async function sendMessage() {
    if (isWaiting) return;
    const text = msgInput.value.trim();
    if (!text) return;

    msgInput.value = '';
    addUserMessage(text);
    setInputEnabled(false);
    showTyping();

    try {
        const data = await postChat(text);
        hideTyping();
        const responses = data.responses || [];
        await renderResponses(responses);
        checkShowLocationButton(responses);
    } catch (err) {
        hideTyping();
        addBotText('Sorry, something went wrong. Please try again.');
        console.error(err);
    }

    setInputEnabled(true);
}

async function sendAutoMessage(text) {
    if (isWaiting) return;

    addUserMessage(text);
    setInputEnabled(false);
    showTyping();
    locBtn.style.display = 'none';

    try {
        const data = await postChat(text);
        hideTyping();
        const responses = data.responses || [];
        await renderResponses(responses);
        checkShowLocationButton(responses);
    } catch (err) {
        hideTyping();
        addBotText('Sorry, something went wrong. Please try again.');
        console.error(err);
    }

    setInputEnabled(true);
}

async function resetChat() {
    try {
        await fetch('/api/chat/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID }),
        });
    } catch (_) {}
    chatContainer.innerHTML = '';
    initChat();
}

// ---- Init ----

async function initChat() {
    setInputEnabled(false);
    locBtn.style.display = 'none';
    showTyping();

    try {
        const data = await postChat('');
        hideTyping();
        const responses = data.responses || [];
        await renderResponses(responses);
        checkShowLocationButton(responses);
    } catch (err) {
        hideTyping();
        addBotText('Welcome! I\\'m having trouble connecting. Please refresh the page.');
        console.error(err);
    }

    setInputEnabled(true);
}

// Keyboard
msgInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Boot
initChat();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8422)
