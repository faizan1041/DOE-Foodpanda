"""
get_chat_html() - Returns the complete interactive Foodpanda chat UI as an HTML string.
Light theme, Foodpanda pink accent, mobile-first, no external dependencies.
"""


def get_chat_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Foodpanda Bot</title>
<style>
/* ============================================================
   RESET & TOKENS
   ============================================================ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --pink:       #d70f64;
  --pink-light: #f9e0ec;
  --pink-dim:   rgba(215, 15, 100, 0.12);
  --pink-hover: #b80d55;

  --bg:         #f4f4f6;
  --surface:    #ffffff;
  --surface-2:  #f0f0f3;
  --surface-3:  #e8e8ec;

  --border:     rgba(0,0,0,0.08);
  --border-md:  rgba(0,0,0,0.12);

  --text:       #111118;
  --text-2:     #555560;
  --text-3:     #888896;

  --green:      #17b26a;
  --yellow:     #f59e0b;
  --red:        #ef4444;

  --radius-sm:  8px;
  --radius:     14px;
  --radius-lg:  20px;
  --radius-xl:  28px;

  --header-h:   58px;
  --input-h:    70px;

  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI",
          Helvetica, Arial, sans-serif;

  --shadow-sm:  0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow:     0 4px 16px rgba(0,0,0,0.08), 0 1px 4px rgba(0,0,0,0.04);
  --shadow-lg:  0 8px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06);
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

/* ============================================================
   HEADER
   ============================================================ */
.header {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--header-h);
  display: flex;
  align-items: center;
  padding: 0 16px 0 18px;
  background: rgba(255,255,255,0.90);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border);
  z-index: 200;
  gap: 12px;
}

.header-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--pink);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(215,15,100,0.35);
}

.header-avatar svg {
  width: 20px;
  height: 20px;
  fill: #fff;
}

.header-info { flex: 1; min-width: 0; }

.header-title {
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.2px;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(23,178,106,0.22);
  animation: statusPulse 3s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(23,178,106,0.22); }
  50%       { box-shadow: 0 0 0 4px rgba(23,178,106,0.10); }
}

.header-sub {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 0px;
  letter-spacing: 0;
}

.header-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-md);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s, transform 0.1s;
  flex-shrink: 0;
}

.header-btn:hover  { background: var(--surface-3); color: var(--text); }
.header-btn:active { transform: scale(0.94); }

.header-btn svg { width: 16px; height: 16px; fill: currentColor; }

/* ============================================================
   CHAT AREA
   ============================================================ */
.chat-area {
  position: fixed;
  top: var(--header-h);
  left: 0; right: 0;
  bottom: var(--input-h);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 18px 16px 6px;
  scroll-behavior: smooth;
}

.chat-area::-webkit-scrollbar { width: 5px; }
.chat-area::-webkit-scrollbar-track { background: transparent; }
.chat-area::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 3px; }

.chat-container {
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* ============================================================
   MESSAGE ROWS
   ============================================================ */
.msg-row {
  display: flex;
  flex-direction: column;
  animation: fadeUp 0.28s cubic-bezier(0.16,1,0.3,1) both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.msg-row.bot  { align-items: flex-start; }
.msg-row.user { align-items: flex-end; }

.msg-row + .msg-row { margin-top: 4px; }
.msg-row.bot  + .msg-row.user,
.msg-row.user + .msg-row.bot  { margin-top: 10px; }

.msg-bubble {
  max-width: 78%;
  padding: 10px 14px;
  font-size: 15px;
  line-height: 1.55;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.msg-row.bot .msg-bubble {
  background: var(--surface);
  border-radius: 4px var(--radius) var(--radius) var(--radius);
  color: var(--text);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
}

.msg-row.user .msg-bubble {
  background: var(--pink);
  border-radius: var(--radius) 4px var(--radius) var(--radius);
  color: #fff;
  box-shadow: 0 2px 8px rgba(215,15,100,0.28);
}

.msg-bubble strong { font-weight: 650; }
.msg-bubble a { color: var(--pink); }
.msg-row.user .msg-bubble a { color: rgba(255,255,255,0.85); }

.msg-time {
  font-size: 11px;
  color: var(--text-3);
  margin-top: 3px;
  padding: 0 2px;
}

/* ============================================================
   QUICK ACTION CHIPS
   ============================================================ */
.quick-actions {
  animation: fadeUp 0.35s cubic-bezier(0.16,1,0.3,1) 0.15s both;
  margin-top: 10px;
  margin-bottom: 4px;
}

.chips-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 8px;
  padding-left: 2px;
}

.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-xl);
  border: 1.5px solid var(--border-md);
  background: var(--surface);
  color: var(--text);
  font-size: 13.5px;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.16s cubic-bezier(0.34,1.56,0.64,1);
  white-space: nowrap;
  user-select: none;
  box-shadow: var(--shadow-sm);
}

.chip:hover {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(215,15,100,0.28);
}

.chip:active { transform: scale(0.94) translateY(0); }

.chip.primary {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
  box-shadow: 0 2px 8px rgba(215,15,100,0.22);
}

.chip.primary:hover {
  background: var(--pink-hover);
  border-color: var(--pink-hover);
  box-shadow: 0 4px 14px rgba(215,15,100,0.35);
}

.chip-icon {
  font-size: 14px;
  line-height: 1;
}

/* Cuisine grid */
.cuisine-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
  margin-top: 10px;
  animation: fadeUp 0.28s cubic-bezier(0.16,1,0.3,1) both;
}

.cuisine-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 12px 8px;
  border-radius: var(--radius);
  border: 1.5px solid var(--border-md);
  background: var(--surface);
  color: var(--text);
  font-size: 12.5px;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.16s cubic-bezier(0.34,1.56,0.64,1);
  user-select: none;
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.cuisine-chip:hover {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(215,15,100,0.28);
}

.cuisine-chip:active { transform: scale(0.93) translateY(0); }
.cuisine-chip .ci { font-size: 22px; line-height: 1; }

/* Location chips */
.location-row {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 10px;
  animation: fadeUp 0.28s cubic-bezier(0.16,1,0.3,1) both;
}

.loc-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 13px;
  border-radius: var(--radius-xl);
  border: 1.5px solid var(--border-md);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.16s cubic-bezier(0.34,1.56,0.64,1);
  white-space: nowrap;
  user-select: none;
  box-shadow: var(--shadow-sm);
}

.loc-chip:hover {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(215,15,100,0.25);
}

.loc-chip:active { transform: scale(0.94) translateY(0); }

.loc-chip.gps {
  border-color: var(--pink);
  color: var(--pink);
  font-weight: 600;
}

.loc-chip.gps:hover { background: var(--pink); color: #fff; }

.loc-chip.gps.loading {
  animation: locPulse 1s ease-in-out infinite;
  pointer-events: none;
  opacity: 0.7;
}

@keyframes locPulse {
  0%, 100% { opacity: 0.7; }
  50%       { opacity: 1; }
}

/* ============================================================
   RESTAURANT CARDS
   ============================================================ */
.restaurant-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 520px;
  animation: fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both;
}

.r-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  position: relative;
}

.r-card:hover {
  border-color: rgba(215,15,100,0.25);
  box-shadow: var(--shadow);
  transform: translateY(-1px);
}

.r-card.removing {
  animation: cardOut 0.3s cubic-bezier(0.4,0,1,1) both;
}

@keyframes cardOut {
  from { opacity: 1; transform: translateX(0) scale(1); max-height: 200px; }
  to   { opacity: 0; transform: translateX(24px) scale(0.96); max-height: 0; padding: 0; margin: 0; }
}

.r-card-top {
  padding: 13px 14px 10px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* Score badge */
.score-badge {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1;
}

.score-badge.green  { background: rgba(23,178,106,0.12); color: #0d9457; }
.score-badge.yellow { background: rgba(245,158,11,0.12); color: #b45309; }
.score-badge.red    { background: rgba(239,68,68,0.12);  color: #b91c1c; }
.score-badge.rank   { background: var(--pink-dim); color: var(--pink); }

.score-badge .score-label {
  font-size: 8px;
  font-weight: 600;
  opacity: 0.75;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  margin-top: 1px;
}

.r-info { flex: 1; min-width: 0; }

.r-name {
  font-size: 14.5px;
  font-weight: 650;
  color: var(--text);
  margin-bottom: 4px;
  letter-spacing: -0.1px;
}

.r-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: var(--text-2);
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.r-rating { color: #d97706; font-weight: 600; }

.r-deal {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--pink-dim);
  color: var(--pink);
  font-size: 11.5px;
  font-weight: 600;
}

.r-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.r-tag {
  padding: 2px 8px;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--text-3);
  font-size: 11.5px;
}

/* Block button */
.r-block-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 1px solid var(--border-md);
  background: var(--surface);
  color: var(--text-3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  z-index: 2;
}

.r-block-btn:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: var(--red);
}

.r-block-btn:active { transform: scale(0.88); }
.r-block-btn svg { width: 13px; height: 13px; fill: currentColor; }

/* Action buttons */
.r-actions {
  display: flex;
  border-top: 1px solid var(--border);
}

.r-action-btn {
  flex: 1;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 550;
  font-family: var(--font);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.r-action-btn + .r-action-btn {
  border-left: 1px solid var(--border);
}

.r-action-btn:hover { background: var(--surface-2); color: var(--text); }
.r-action-btn:active { background: var(--surface-3); }

.r-action-btn.order {
  color: var(--pink);
  font-weight: 650;
}

.r-action-btn.order:hover {
  background: var(--pink-dim);
  color: var(--pink-hover);
}

.r-action-btn svg { width: 13px; height: 13px; fill: currentColor; }

/* ============================================================
   MENU CARDS
   ============================================================ */
.menu-wrap {
  width: 100%;
  max-width: 520px;
  animation: fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both;
}

.menu-category {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  margin-bottom: 8px;
}

.menu-cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  cursor: pointer;
  user-select: none;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}

.menu-cat-header:hover { background: var(--surface-3); }

.menu-cat-name {
  font-size: 13px;
  font-weight: 650;
  color: var(--text-2);
  letter-spacing: 0.1px;
}

.menu-cat-count {
  font-size: 11.5px;
  color: var(--text-3);
  display: flex;
  align-items: center;
  gap: 6px;
}

.menu-cat-chevron {
  width: 16px;
  height: 16px;
  fill: var(--text-3);
  transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1);
}

.menu-category.collapsed .menu-cat-chevron { transform: rotate(-90deg); }
.menu-category.collapsed .menu-items-body { display: none; }

.menu-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 11px 14px;
  gap: 14px;
  border-bottom: 1px solid var(--border);
  transition: background 0.12s;
}

.menu-item:last-child { border-bottom: none; }
.menu-item:hover { background: var(--surface-2); }

.menu-item-info { flex: 1; min-width: 0; }

.menu-item-name {
  font-size: 13.5px;
  font-weight: 580;
  color: var(--text);
  margin-bottom: 2px;
}

.menu-item-desc {
  font-size: 12px;
  color: var(--text-3);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

.menu-item-price {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--pink);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ============================================================
   ORDER LOGGER
   ============================================================ */
.order-logger {
  width: 100%;
  max-width: 520px;
  background: var(--surface);
  border: 1.5px solid rgba(215,15,100,0.2);
  border-radius: var(--radius);
  padding: 14px;
  box-shadow: 0 4px 20px rgba(215,15,100,0.08);
  animation: fadeUp 0.32s cubic-bezier(0.16,1,0.3,1) both;
}

.order-logger-title {
  font-size: 13px;
  font-weight: 650;
  color: var(--text-2);
  margin-bottom: 10px;
  letter-spacing: 0.1px;
}

.order-logger-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 11px;
  min-height: 0;
}

.order-item-chip {
  padding: 5px 11px;
  border-radius: var(--radius-xl);
  border: 1.5px solid var(--border-md);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}

.order-item-chip:hover {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
}

.order-item-chip.selected {
  background: var(--pink);
  border-color: var(--pink);
  color: #fff;
}

.order-logger-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.order-logger-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border-radius: var(--radius-xl);
  border: 1.5px solid var(--border-md);
  background: var(--surface-2);
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
  outline: none;
  transition: border-color 0.15s;
}

.order-logger-input:focus { border-color: var(--pink); }
.order-logger-input::placeholder { color: var(--text-3); }

.logger-btn {
  padding: 0 14px;
  height: 38px;
  border-radius: var(--radius-xl);
  border: none;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.15s;
}

.logger-btn.submit {
  background: var(--pink);
  color: #fff;
  box-shadow: 0 2px 8px rgba(215,15,100,0.25);
}

.logger-btn.submit:hover { background: var(--pink-hover); }

.logger-btn.skip {
  background: var(--surface-3);
  color: var(--text-2);
}

.logger-btn.skip:hover { background: var(--surface-3); color: var(--text); }

/* ============================================================
   HISTORY VIEW
   ============================================================ */
.history-wrap {
  width: 100%;
  max-width: 520px;
  animation: fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both;
}

.history-date-header {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 14px 0 7px 2px;
}

.history-date-header:first-child { margin-top: 0; }

.history-entry {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 13px;
  margin-bottom: 6px;
  box-shadow: var(--shadow-sm);
  display: flex;
  align-items: center;
  gap: 11px;
}

.history-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pink);
  flex-shrink: 0;
}

.history-entry-info { flex: 1; min-width: 0; }

.history-restaurant {
  font-size: 13.5px;
  font-weight: 620;
  color: var(--text);
}

.history-items {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 1px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ============================================================
   TYPING INDICATOR
   ============================================================ */
.typing-row {
  display: flex;
  align-items: flex-start;
  animation: fadeUp 0.22s ease-out both;
}

.typing-bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px var(--radius) var(--radius) var(--radius);
  padding: 11px 16px;
  display: flex;
  gap: 4px;
  align-items: center;
  box-shadow: var(--shadow-sm);
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
  animation: typeBounce 1.3s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.13s; }
.typing-dot:nth-child(3) { animation-delay: 0.26s; }

@keyframes typeBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30%            { transform: translateY(-5px); opacity: 1; }
}

/* ============================================================
   INPUT BAR
   ============================================================ */
.input-bar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: var(--input-h);
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  z-index: 200;
}

.input-inner {
  max-width: 680px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 9px;
}

.input-field {
  flex: 1;
  height: 44px;
  padding: 0 18px;
  border-radius: 22px;
  border: 1.5px solid var(--border-md);
  background: var(--surface-2);
  color: var(--text);
  font-size: 15px;
  font-family: var(--font);
  outline: none;
  transition: border-color 0.18s, background 0.18s;
}

.input-field::placeholder { color: var(--text-3); }
.input-field:focus { border-color: var(--pink); background: var(--surface); }
.input-field:disabled { opacity: 0.45; cursor: not-allowed; }

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--pink);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s cubic-bezier(0.34,1.56,0.64,1);
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(215,15,100,0.30);
}

.send-btn:hover:not(:disabled) {
  background: var(--pink-hover);
  transform: scale(1.07);
  box-shadow: 0 4px 14px rgba(215,15,100,0.38);
}

.send-btn:active:not(:disabled) { transform: scale(0.93); }
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; transform: none; }

.send-btn svg { width: 19px; height: 19px; fill: currentColor; }

/* ============================================================
   MISCELLANEOUS
   ============================================================ */
.spacer { height: 10px; }

.msg-row.bot .full-width-content {
  width: 100%;
  max-width: 520px;
}

@media (max-width: 580px) {
  .msg-bubble { max-width: 88%; }
  .restaurant-list,
  .menu-wrap,
  .history-wrap,
  .order-logger { max-width: 100%; }
  .cuisine-grid { grid-template-columns: repeat(3, 1fr); }
  .chat-area { padding: 14px 12px 6px; }
}

@media (max-width: 360px) {
  .cuisine-grid { grid-template-columns: repeat(2, 1fr); }
}

/* Divider for bot widget rows */
.widget-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  animation: fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both;
  margin-top: 4px;
}

.widget-row .msg-time {
  margin-top: 5px;
}
</style>
</head>
<body>

<!-- ============================================================
     HEADER
     ============================================================ -->
<header class="header">
  <div class="header-avatar">
    <!-- Foodpanda panda icon (simplified SVG) -->
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
    </svg>
  </div>
  <div class="header-info">
    <div class="header-title">
      Foodpanda Bot
      <span class="status-dot"></span>
    </div>
    <div class="header-sub">Pakistan lunch ordering</div>
  </div>
  <button class="header-btn" onclick="resetChat()" title="Start new session" aria-label="Reset chat">
    <!-- Refresh icon -->
    <svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
  </button>
</header>

<!-- ============================================================
     CHAT AREA
     ============================================================ -->
<main class="chat-area" id="chatArea" role="log" aria-live="polite" aria-label="Chat messages">
  <div class="chat-container" id="chatContainer"></div>
</main>

<!-- ============================================================
     INPUT BAR
     ============================================================ -->
<div class="input-bar" role="form" aria-label="Send a message">
  <div class="input-inner">
    <input
      type="text"
      class="input-field"
      id="msgInput"
      placeholder="Type a command or tap above..."
      autocomplete="off"
      autocorrect="off"
      spellcheck="false"
      aria-label="Message input"
    />
    <button class="send-btn" id="sendBtn" onclick="handleSend()" aria-label="Send message">
      <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
    </button>
  </div>
</div>

<script>
/* ============================================================
   STATE
   ============================================================ */
const SESSION_ID = crypto.randomUUID();
let isWaiting = false;
let lastMenuItems = [];           // cache for order logger chips
let lastMenuRestaurant = null;    // cache restaurant context
let orderLoggerActive = false;    // is the order logger shown?
let selectedOrderItems = new Set(); // tapped items in logger

const chatContainer = document.getElementById('chatContainer');
const chatArea      = document.getElementById('chatArea');
const msgInput      = document.getElementById('msgInput');
const sendBtn       = document.getElementById('sendBtn');

/* ============================================================
   UTILITIES
   ============================================================ */
function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// Simple markdown: **bold**, \n -> <br>
function renderText(text) {
  let out = esc(text);
  out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/\n/g, '<br>');
  return out;
}

function scrollBottom(smooth = true) {
  requestAnimationFrame(() => {
    chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
  });
}

function setInputEnabled(on) {
  isWaiting = !on;
  msgInput.disabled = !on;
  sendBtn.disabled  = !on;
  if (on) msgInput.focus();
}

/* ============================================================
   TYPING INDICATOR
   ============================================================ */
let typingEl = null;

function showTyping() {
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'typing-row';
  typingEl.setAttribute('aria-label', 'Bot is typing');
  typingEl.innerHTML = `
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatContainer.appendChild(typingEl);
  scrollBottom();
}

function hideTyping() {
  if (typingEl) { typingEl.remove(); typingEl = null; }
}

/* ============================================================
   MESSAGE RENDERERS
   ============================================================ */
function addUserMsg(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `
    <div class="msg-bubble">${esc(text)}</div>
    <div class="msg-time">${now()}</div>`;
  chatContainer.appendChild(row);
  scrollBottom();
}

function addBotText(text) {
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.innerHTML = `
    <div class="msg-bubble">${renderText(text)}</div>
    <div class="msg-time">${now()}</div>`;
  chatContainer.appendChild(row);
  scrollBottom();
  return row;
}

/* Quick action chips - shown once after greeting */
function addQuickActions() {
  const wrap = document.createElement('div');
  wrap.className = 'widget-row';
  wrap.innerHTML = `
    <div class="quick-actions">
      <div class="chips-label">Quick actions</div>
      <div class="chips-row">
        <button class="chip primary" onclick="quickAction('suggestions')">
          <span class="chip-icon">&#127869;</span> Today's Picks
        </button>
        <button class="chip" onclick="showCuisineSelector()">
          <span class="chip-icon">&#128269;</span> Search
        </button>
        <button class="chip" onclick="quickAction('history')">
          <span class="chip-icon">&#128337;</span> History
        </button>
        <button class="chip" onclick="triggerRefresh()">
          <span class="chip-icon">&#10024;</span> Refresh Suggestions
        </button>
      </div>
    </div>
    <div class="msg-time">${now()}</div>`;
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* Cuisine selector grid */
function showCuisineSelector() {
  const cuisines = [
    { label: 'Pizza',     icon: '&#127829;', cmd: 'pizza'     },
    { label: 'Biryani',   icon: '&#127859;', cmd: 'biryani'   },
    { label: 'Chinese',   icon: '&#129032;', cmd: 'chinese'   },
    { label: 'BBQ',       icon: '&#129363;', cmd: 'bbq'       },
    { label: 'Burgers',   icon: '&#127828;', cmd: 'burgers'   },
    { label: 'Desi',      icon: '&#127375;', cmd: 'desi'      },
    { label: 'Fast Food', icon: '&#127839;', cmd: 'fast food' },
    { label: 'Desserts',  icon: '&#127846;', cmd: 'dessert'   },
    { label: 'All',       icon: '&#127860;', cmd: 'all food'  },
  ];

  const wrap = document.createElement('div');
  wrap.className = 'widget-row';

  let grid = '<div class="cuisine-grid">';
  cuisines.forEach(c => {
    grid += `<button class="cuisine-chip" onclick="pickCuisine('${c.cmd}')">
      <span class="ci">${c.icon}</span>${esc(c.label)}
    </button>`;
  });
  grid += '</div>';

  wrap.innerHTML = `
    <div style="width:100%;max-width:520px;">
      <div class="chips-label" style="margin-bottom:8px;">What are you craving?</div>
      ${grid}
    </div>
    <div class="msg-time">${now()}</div>`;
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* Location chips */
function showLocationChips() {
  const locations = ['I-10', 'F-7', 'F-10', 'F-6', 'Gulberg', 'Blue Area', 'DHA Lahore', 'Bahria Town'];

  const wrap = document.createElement('div');
  wrap.className = 'widget-row';

  let chips = '';
  locations.forEach(loc => {
    chips += `<button class="loc-chip" onclick="pickLocation('${loc}')">${esc(loc)}</button>`;
  });
  chips += `<button class="loc-chip gps" id="gpsChip" onclick="useGPS()">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" style="margin-right:2px"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0013 3.06V1h-2v2.06A8.994 8.994 0 003.06 11H1v2h2.06A8.994 8.994 0 0011 20.94V23h2v-2.06A8.994 8.994 0 0020.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>
    Use GPS
  </button>`;

  wrap.innerHTML = `
    <div style="width:100%;max-width:520px;">
      <div class="chips-label" style="margin-bottom:8px;">Choose your area</div>
      <div class="location-row">${chips}</div>
    </div>
    <div class="msg-time">${now()}</div>`;
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* Restaurant cards */
function addRestaurantCards(restaurants) {
  const wrap = document.createElement('div');
  wrap.className = 'widget-row';

  const list = document.createElement('div');
  list.className = 'restaurant-list';

  restaurants.forEach((r, i) => {
    const rank = r.rank || (i + 1);
    const score = r.score ? Math.round(r.score) : null;

    let badgeClass = 'rank';
    let badgeVal = rank;
    let badgeLabel = '';
    if (score !== null) {
      badgeClass = score >= 70 ? 'green' : score >= 50 ? 'yellow' : 'red';
      badgeVal   = score;
      badgeLabel = '<div class="score-label">score</div>';
    }

    const metaParts = [];
    if (r.rating)        metaParts.push(`<span class="r-rating">&#9733; ${esc(String(r.rating))}</span>`);
    if (r.delivery_time) metaParts.push(`<span>${esc(r.delivery_time)}</span>`);
    const metaHtml = metaParts.join('');

    const dealHtml = r.deal ? `<span class="r-deal">${esc(r.deal)}</span>` : '';

    const tagsHtml = r.cuisines && r.cuisines.length
      ? '<div class="r-tags">' + r.cuisines.slice(0,3).map(c => `<span class="r-tag">${esc(c)}</span>`).join('') + '</div>'
      : '';

    const card = document.createElement('div');
    card.className = 'r-card';
    card.dataset.rank = rank;
    card.dataset.name = r.name || '';
    card.dataset.code = r.code || '';
    card.dataset.url  = r.url  || '';

    card.innerHTML = `
      <button class="r-block-btn" title="Block this restaurant" aria-label="Block ${esc(r.name || '')}"
        onclick="blockRestaurant(this,'${esc(r.name||'')}','${esc(r.code||'')}')">
        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.68L5.68 16.9A7.902 7.902 0 014 12zm8 8c-1.85 0-3.55-.63-4.9-1.68l11.22-11.22A7.902 7.902 0 0120 12c0 4.42-3.58 8-8 8z"/></svg>
      </button>
      <div class="r-card-top">
        <div class="score-badge ${badgeClass}">${badgeVal}${badgeLabel}</div>
        <div class="r-info">
          <div class="r-name">${esc(r.name || '')}</div>
          <div class="r-meta">${metaHtml} ${dealHtml}</div>
          ${tagsHtml}
        </div>
      </div>
      <div class="r-actions">
        <button class="r-action-btn" onclick="sendAutoMsg('${rank}')" aria-label="View menu for ${esc(r.name||'')}">
          <svg viewBox="0 0 24 24"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>
          Menu
        </button>
        <button class="r-action-btn order" onclick="orderRestaurant('${rank}','${esc(r.url||'')}')" aria-label="Order from ${esc(r.name||'')}">
          <svg viewBox="0 0 24 24"><path d="M19 9h-2c0-2.76-2.24-5-5-5S7 6.24 7 9H5c-1.1 0-2 .9-2 2v9c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-9c0-1.1-.9-2-2-2zm-7-3c1.66 0 3 1.34 3 3H9c0-1.66 1.34-3 3-3zm0 10c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></svg>
          Order
        </button>
      </div>`;

    list.appendChild(card);
  });

  const timeEl = document.createElement('div');
  timeEl.className = 'msg-time';
  timeEl.textContent = now();

  wrap.appendChild(list);
  wrap.appendChild(timeEl);
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* Menu items grouped by category */
function addMenuItems(payload) {
  // payload can be { restaurant, items } or an array
  let items = [];
  if (Array.isArray(payload)) {
    items = payload;
  } else if (payload && payload.items) {
    items = payload.items;
    lastMenuRestaurant = payload.restaurant || null;
  }
  lastMenuItems = items;

  // Group by category
  const grouped = {};
  items.forEach(item => {
    const cat = item.category || 'Menu';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(item);
  });

  const wrap = document.createElement('div');
  wrap.className = 'widget-row';

  const menuWrap = document.createElement('div');
  menuWrap.className = 'menu-wrap';

  Object.entries(grouped).forEach(([cat, catItems], ci) => {
    const catEl = document.createElement('div');
    catEl.className = 'menu-category' + (ci > 2 ? ' collapsed' : '');

    const headerEl = document.createElement('div');
    headerEl.className = 'menu-cat-header';
    headerEl.setAttribute('role', 'button');
    headerEl.setAttribute('aria-expanded', ci <= 2 ? 'true' : 'false');
    headerEl.innerHTML = `
      <span class="menu-cat-name">${esc(cat)}</span>
      <span class="menu-cat-count">
        ${catItems.length} item${catItems.length !== 1 ? 's' : ''}
        <svg class="menu-cat-chevron" viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
      </span>`;
    headerEl.addEventListener('click', () => {
      const collapsed = catEl.classList.toggle('collapsed');
      headerEl.setAttribute('aria-expanded', String(!collapsed));
    });

    const bodyEl = document.createElement('div');
    bodyEl.className = 'menu-items-body';

    catItems.forEach(item => {
      const row = document.createElement('div');
      row.className = 'menu-item';
      row.innerHTML = `
        <div class="menu-item-info">
          <div class="menu-item-name">${esc(item.name || '')}</div>
          ${item.description ? `<div class="menu-item-desc">${esc(item.description)}</div>` : ''}
        </div>
        <div class="menu-item-price">${esc(item.price_display || item.price || '')}</div>`;
      bodyEl.appendChild(row);
    });

    catEl.appendChild(headerEl);
    catEl.appendChild(bodyEl);
    menuWrap.appendChild(catEl);
  });

  const timeEl = document.createElement('div');
  timeEl.className = 'msg-time';
  timeEl.textContent = now();

  wrap.appendChild(menuWrap);
  wrap.appendChild(timeEl);
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* Order logger */
function showOrderLogger() {
  if (orderLoggerActive) return;
  orderLoggerActive = true;
  selectedOrderItems = new Set();

  const wrap = document.createElement('div');
  wrap.className = 'widget-row';
  wrap.id = 'orderLoggerWrap';

  let chipsHtml = '';
  if (lastMenuItems.length > 0) {
    // Show up to 16 most likely items (prioritise shorter names)
    const candidates = [...lastMenuItems]
      .sort((a, b) => (a.name || '').length - (b.name || '').length)
      .slice(0, 16);
    candidates.forEach((item, idx) => {
      chipsHtml += `<button class="order-item-chip" data-idx="${idx}" data-name="${esc(item.name||'')}"
        onclick="toggleOrderChip(this)">${esc(item.name || '')}</button>`;
    });
  }

  wrap.innerHTML = `
    <div class="order-logger">
      <div class="order-logger-title">What did you order? (tap items or type)</div>
      ${chipsHtml ? `<div class="order-logger-chips" id="orderChips">${chipsHtml}</div>` : ''}
      <div class="order-logger-input-row">
        <input type="text" class="order-logger-input" id="orderLoggerInput"
          placeholder="e.g. Chicken Biryani, Raita"
          autocomplete="off" onkeydown="loggerKeydown(event)"/>
        <button class="logger-btn submit" onclick="submitOrder()">Log</button>
        <button class="logger-btn skip" onclick="skipOrder()">Skip</button>
      </div>
    </div>
    <div class="msg-time">${now()}</div>`;

  chatContainer.appendChild(wrap);
  scrollBottom();

  // Focus the input
  setTimeout(() => {
    const inp = document.getElementById('orderLoggerInput');
    if (inp) inp.focus();
  }, 100);
}

function toggleOrderChip(btn) {
  const name = btn.dataset.name;
  if (selectedOrderItems.has(name)) {
    selectedOrderItems.delete(name);
    btn.classList.remove('selected');
  } else {
    selectedOrderItems.add(name);
    btn.classList.add('selected');
    // Sync text input
    const inp = document.getElementById('orderLoggerInput');
    if (inp) {
      const current = inp.value.trim();
      inp.value = current ? current + ', ' + name : name;
    }
  }
}

function loggerKeydown(e) {
  if (e.key === 'Enter') { e.preventDefault(); submitOrder(); }
}

function submitOrder() {
  const inp = document.getElementById('orderLoggerInput');
  let text = inp ? inp.value.trim() : '';

  // Merge selected chips into text if not already there
  if (selectedOrderItems.size > 0) {
    const typed = text.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
    const extras = [...selectedOrderItems].filter(item => !typed.includes(item.toLowerCase()));
    if (extras.length) {
      text = text ? text + ', ' + extras.join(', ') : extras.join(', ');
    }
  }

  if (!text) { text = 'something'; }
  dismissOrderLogger();
  sendAutoMsg(text);
}

function skipOrder() {
  dismissOrderLogger();
  sendAutoMsg('skip');
}

function dismissOrderLogger() {
  const el = document.getElementById('orderLoggerWrap');
  if (el) el.remove();
  orderLoggerActive = false;
}

/* History timeline */
function addHistoryView(orders) {
  if (!orders || orders.length === 0) {
    addBotText('No order history yet!');
    return;
  }

  const wrap = document.createElement('div');
  wrap.className = 'widget-row';

  const inner = document.createElement('div');
  inner.className = 'history-wrap';

  // Group by date
  const byDate = {};
  orders.forEach(o => {
    const dateKey = o.order_date || 'Unknown';
    if (!byDate[dateKey]) byDate[dateKey] = [];
    byDate[dateKey].push(o);
  });

  Object.entries(byDate).slice(0, 20).forEach(([date, dayOrders]) => {
    const header = document.createElement('div');
    header.className = 'history-date-header';
    header.textContent = date;
    inner.appendChild(header);

    dayOrders.forEach(o => {
      const entry = document.createElement('div');
      entry.className = 'history-entry';
      const itemsStr = o.items && o.items.length
        ? o.items.join(', ')
        : 'Items not recorded';
      entry.innerHTML = `
        <div class="history-dot"></div>
        <div class="history-entry-info">
          <div class="history-restaurant">${esc(o.restaurant_name || 'Unknown')}</div>
          <div class="history-items">${esc(itemsStr)}</div>
        </div>`;
      inner.appendChild(entry);
    });
  });

  const timeEl = document.createElement('div');
  timeEl.className = 'msg-time';
  timeEl.textContent = now();

  wrap.appendChild(inner);
  wrap.appendChild(timeEl);
  chatContainer.appendChild(wrap);
  scrollBottom();
}

/* ============================================================
   API CALLS
   ============================================================ */
async function postChat(message) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: SESSION_ID, message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiResetSession() {
  await fetch('/api/chat/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: SESSION_ID }),
  }).catch(() => {});
}

async function apiBlacklist(name, code) {
  const res = await fetch('/api/blacklist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ restaurant_name: name, restaurant_code: code, reason: 'user blocked via UI' }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiGeocodeCoords(lat, lng) {
  const res = await fetch(`/api/geocode?lat=${lat}&lng=${lng}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiHistory() {
  const res = await fetch('/api/history?days=30');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiTriggerRefresh() {
  const res = await fetch('/api/trigger-lunch-search', { method: 'POST' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ============================================================
   RESPONSE RENDERER
   ============================================================ */
// Detect if the bot is asking for order logging (so we show the helper)
function detectsOrderPrompt(responses) {
  return responses.some(r =>
    r.type === 'text' &&
    (r.content.includes("tell me what you got") ||
     r.content.includes("what you ordered") ||
     r.content.includes("Once you've ordered"))
  );
}

// Detect location ask
function detectsLocationAsk(responses) {
  return responses.some(r =>
    r.type === 'text' &&
    (r.content.includes('delivery area') ||
     r.content.includes('delivery location') ||
     r.content.includes('Where should I search'))
  );
}

async function renderResponses(responses, isInit) {
  for (let i = 0; i < responses.length; i++) {
    if (i > 0) await delay(220);
    const resp = responses[i];
    switch (resp.type) {
      case 'text':
        addBotText(resp.content);
        break;
      case 'restaurants':
        addRestaurantCards(Array.isArray(resp.content) ? resp.content : []);
        break;
      case 'menu':
        addMenuItems(resp.content);
        break;
      case 'history':
        addHistoryView(resp.content);
        break;
      default:
        if (typeof resp.content === 'string') addBotText(resp.content);
        else addBotText(JSON.stringify(resp.content));
    }
  }

  // Post-render actions
  if (isInit) {
    await delay(120);
    addQuickActions();
  }

  if (detectsLocationAsk(responses)) {
    await delay(100);
    showLocationChips();
  }

  if (detectsOrderPrompt(responses)) {
    await delay(80);
    showOrderLogger();
  }
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ============================================================
   USER ACTIONS
   ============================================================ */
async function sendAutoMsg(text) {
  if (isWaiting) return;
  addUserMsg(text);
  setInputEnabled(false);
  showTyping();

  try {
    const data = await postChat(text);
    hideTyping();
    await renderResponses(data.responses || [], false);
  } catch (err) {
    hideTyping();
    addBotText('Sorry, something went wrong. Please try again.');
    console.error('[chat]', err);
  }

  setInputEnabled(true);
}

async function handleSend() {
  if (isWaiting) return;
  const text = msgInput.value.trim();
  if (!text) return;
  msgInput.value = '';
  await sendAutoMsg(text);
}

/* Quick action buttons */
async function quickAction(cmd) {
  await sendAutoMsg(cmd);
}

/* Cuisine pick */
async function pickCuisine(cuisine) {
  await sendAutoMsg(cuisine);
}

/* Location pick */
async function pickLocation(loc) {
  await sendAutoMsg(loc);
}

/* GPS location */
async function useGPS() {
  const gpsChip = document.getElementById('gpsChip');
  if (!navigator.geolocation) {
    addBotText("Your browser doesn't support GPS. Please type your area.");
    return;
  }
  if (gpsChip) gpsChip.classList.add('loading');

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      try {
        const data = await apiGeocodeCoords(lat, lng);
        if (gpsChip) gpsChip.classList.remove('loading');
        if (data.location) {
          await sendAutoMsg(data.location);
        } else {
          addBotText("Couldn't resolve your GPS location. Please type your area.");
          setInputEnabled(true);
        }
      } catch {
        if (gpsChip) gpsChip.classList.remove('loading');
        addBotText("GPS lookup failed. Please type your area.");
        setInputEnabled(true);
      }
    },
    (err) => {
      if (gpsChip) gpsChip.classList.remove('loading');
      const msg = err.code === err.PERMISSION_DENIED
        ? "Location access denied. Please type your area instead."
        : "Couldn't get your location. Please type your area.";
      addBotText(msg);
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

/* Restaurant card actions */
async function orderRestaurant(rank, url) {
  // Open the restaurant URL in a new tab
  if (url) window.open(url, '_blank', 'noopener,noreferrer');
  // Also send the "order N" command to update agent state
  await sendAutoMsg('order ' + rank);
}

async function blockRestaurant(btn, name, code) {
  // Immediately animate card out for responsiveness
  const card = btn.closest('.r-card');
  if (card) card.classList.add('removing');

  try {
    await apiBlacklist(name, code);
    // Remove from DOM after animation
    setTimeout(() => { if (card && card.parentNode) card.remove(); }, 320);
    // Toast-style feedback via bot message
    addBotText(`**${name}** has been blocked and won't be suggested again.`);
  } catch (err) {
    if (card) card.classList.remove('removing');
    addBotText('Could not block that restaurant right now.');
    console.error('[blacklist]', err);
  }
}

/* Refresh suggestions */
async function triggerRefresh() {
  addUserMsg('Refresh Suggestions');
  setInputEnabled(false);
  showTyping();
  addBotText('Refreshing suggestions... this may take a moment.');

  try {
    await apiTriggerRefresh();
    hideTyping();
    // Now pull today's suggestions
    const data = await postChat('suggestions');
    await renderResponses(data.responses || [], false);
  } catch (err) {
    hideTyping();
    addBotText('Refresh failed. Please try again.');
    console.error('[refresh]', err);
  }

  setInputEnabled(true);
}

/* Reset session */
async function resetChat() {
  await apiResetSession();
  chatContainer.innerHTML = '';
  lastMenuItems       = [];
  lastMenuRestaurant  = null;
  orderLoggerActive   = false;
  selectedOrderItems  = new Set();
  initChat();
}

/* ============================================================
   INIT
   ============================================================ */
async function initChat() {
  setInputEnabled(false);
  showTyping();

  try {
    const data = await postChat('');
    hideTyping();
    await renderResponses(data.responses || [], true);
  } catch (err) {
    hideTyping();
    addBotText("Welcome! I'm having trouble connecting. Please refresh the page.");
    console.error('[init]', err);
  }

  setInputEnabled(true);
}

/* Keyboard */
msgInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

/* Boot */
initChat();
</script>
</body>
</html>"""
