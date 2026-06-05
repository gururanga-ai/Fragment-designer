"""
Manhattan Active UI Fragment Designer - Enhanced Version
========================================================
Features:
- Drag & Drop Canvas & Visual Resizing
- Chart Series Manager (pie, bar, line, column)
- Native Table with Pagination / AI / Checkboxes
- Top-Bar / Sidebar Filter Layout Manager
- Flyout-Card Wrapper Mode (100vw Drill-Down)
- Bulletproof Recursive JSON Import Engine
- Scale/Width Percentages per Component
- Blueprint Grid & Background Scale Coordinate System
- True MAWM Column Nesting (Config.Columns with key-value slots)
NEW ─ Full UIRiver Element Support:
  Display : text, key-value, pill, progress-bar
  Forms   : button, input, combobox, toggle-button, search
  Containers: card, banner, segment-panel, tab-group
- Correct UIRiver JSON (Element/Container + Config/Input/Style)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import json, copy, uuid, os, re
from collections import Counter
import sys, threading, urllib.request, urllib.error, base64, ssl

# ── macOS button colour fix ───────────────────────────────────────────────────
# On macOS the native Aqua renderer ignores fg/bg for activeforeground/
# activebackground, making button text invisible.  Patch the constructor once
# so every tk.Button in this process:
#   1. propagates fg → activeforeground and bg → activebackground
#   2. auto-corrects fg="black" on dark backgrounds to fg="white"
#   3. removes the highlight ring (highlightthickness=0)
def _btn_luminance(hex_color):
    """Return perceived luminance 0-1 for a CSS hex colour string."""
    try:
        c = hex_color.strip().lstrip('#')
        if len(c) == 3:
            c = c[0]*2 + c[1]*2 + c[2]*2
        r, g, b = int(c[0:2], 16)/255, int(c[2:4], 16)/255, int(c[4:6], 16)/255
        return 0.299*r + 0.587*g + 0.114*b
    except Exception:
        return 0.5   # unknown → neutral

_orig_tk_btn_init = tk.Button.__init__
def _patched_tk_btn_init(self, master=None, cnf={}, **kw):
    _cnf = dict(cnf)   # safe copy — never mutate the shared default {}
    _fg  = (kw.get('fg') or kw.get('foreground')
            or _cnf.get('fg') or _cnf.get('foreground'))
    _bg  = (kw.get('bg') or kw.get('background')
            or _cnf.get('bg') or _cnf.get('background'))
    # Auto-correct: black (or unset) text on a dark background → white text
    if (_bg and isinstance(_bg, str) and _bg.startswith('#')
            and _fg in ('black', '#000', '#000000', None)
            and _btn_luminance(_bg) < 0.45):
        _fg = 'white'
        kw['fg'] = _fg
    if _fg and 'activeforeground' not in kw and 'activeforeground' not in _cnf:
        kw['activeforeground'] = _fg
    if _bg and 'activebackground' not in kw and 'activebackground' not in _cnf:
        kw['activebackground'] = _bg
    if 'highlightthickness' not in kw and 'highlightthickness' not in _cnf:
        kw['highlightthickness'] = 0
    _orig_tk_btn_init(self, master, _cnf, **kw)
tk.Button.__init__ = _patched_tk_btn_init
# ─────────────────────────────────────────────────────────────────────────────

# ── OPTIONAL GLEAN INTEGRATION (graceful import) ─────────────────────
_GLEAN_REQUESTS_OK = False
try:
    import requests as _glean_req
    import browser_cookie3 as _glean_bc3
    _GLEAN_REQUESTS_OK = True
except ImportError:
    pass

_GLEAN_AGENT_ID  = "2491a8dae7254256975430b2c635a26b"
_GLEAN_API_BASE  = "https://manhattan-associates-be.glean.com/api/v1"
_GLEAN_API_PARAMS= {"clientVersion": "fe-release-2026-05-28-9a91fc9", "locale": "en"}

def _glean_build_session():
    """Read Chrome cookies and return a requests.Session for Glean API calls."""
    if not _GLEAN_REQUESTS_OK:
        raise RuntimeError("Install: pip install requests browser-cookie3")
    import time as _t
    sess = _glean_req.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Referer":    "https://app.glean.com/",
        "Origin":     "https://app.glean.com",
        "Accept":     "*/*",
    })
    for domain in ["manhattan-associates-be.glean.com", ".glean.com"]:
        try:
            jar = _glean_bc3.chrome(domain_name=domain)
            for ck in jar:
                sess.cookies.set(ck.name, ck.value, domain=ck.domain)
        except Exception:
            pass
    if not sess.cookies.get("glean-session-store", domain="manhattan-associates-be.glean.com"):
        raise RuntimeError("Glean session cookie not found. Log in to Glean in Chrome first.")
    return sess

def _glean_call_agent(prompt_text, on_partial=None, uploaded_file_ids=None):
    """
    Call the Fragment Designer Glean agent via /runworkflow (streaming).
    on_partial(str) is called with the growing response text as it streams.
    Returns the full response text.
    """
    from datetime import datetime
    import time as _t, json as _j
    sess = _glean_build_session()
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    agent_cfg = {
        "agent": "DEFAULT",
        "clientCapabilities": {
            "artifacts": {"allowedArtifactTypes": ["PAPER", "HTML_CODE", "IMAGE", "SPREADSHEET"]},
            "canRenderImages": True,
        },
        "mode": "DEFAULT",
        "toolSets": {"enableCompanyTools": True, "enableWebSearch": True},
        "useDeepResearch": False,
    }
    body = {
        "background": True,
        "agentConfig": agent_cfg,
        "enableTrace": True,
        "fields": {},
        "messages": [{
            "agentConfig": {"agent": "DEFAULT"},
            "author": "USER",
            "fragments": [{"text": prompt_text}],
            "messageType": "CONTENT",
            "ts": now_iso,
            "uploadedFileIds": uploaded_file_ids or [],
        }],
        "saveAsChat": True,
        "sourceInfo": {
            "feature": "AGENT",
            "initiator": "USER",
            "platform": "WEB",
            "isDebug": False,
        },
        "workflowId": _GLEAN_AGENT_ID,
        "sc": "",
        "sessionInfo": {
            "lastSeen": now_iso,
            "sessionTrackingToken": "fragdesigner-assist",
            "tabId": "fragdesigner-tab",
            "clickedInJsSession": True,
            "firstEngageTsSec": int(_t.time()),
        },
        "stream": True,
    }
    resp = sess.post(
        f"{_GLEAN_API_BASE}/runworkflow",
        params={"timezoneOffset": "240", **_GLEAN_API_PARAMS},
        data=_j.dumps(body),
        headers={"Content-Type": "text/plain"},
        stream=True, timeout=180,
    )
    if resp.status_code == 401:
        raise RuntimeError("Glean session expired — log in to Glean in Chrome and retry.")
    if not resp.ok:
        raise RuntimeError(f"Glean API error: HTTP {resp.status_code}")

    # Streaming: Glean sends delta tokens (one word/token per chunk).
    # We accumulate them. Snapshot detection: if a chunk's text starts with
    # what we already have, treat it as a snapshot replacement instead.
    full_raw = ""
    last_text = ""
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        full_raw += chunk
        for raw_line in chunk.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = _j.loads(line)
                for m in obj.get('messages', []):
                    if m.get('author') in ('USER',):
                        continue
                    chunk_text = ''.join(
                        f['text'] for f in m.get('fragments', [])
                        if isinstance(f, dict) and 'text' in f
                    )
                    if not chunk_text:
                        continue
                    # Snapshot detection: if this chunk already contains
                    # everything we've accumulated, it's a full snapshot
                    if last_text and chunk_text.startswith(last_text):
                        last_text = chunk_text      # snapshot — replace
                    else:
                        last_text += chunk_text     # delta — accumulate
                    if on_partial:
                        on_partial(last_text)
            except Exception:
                pass
    return last_text or full_raw

def _glean_extract_suggestions(text):
    """Parse suggestions JSON from a Glean response string."""
    import json as _j, re as _re
    for pat in [
        r'```json\s*(.*?)```',
        r'```\s*(.*?)```',
        r'(\{[^{}]*"suggestions"[^{}]*\[.*?\]\s*\})',
    ]:
        m = _re.search(pat, text, _re.DOTALL)
        if m:
            try:
                data = _j.loads(m.group(1).strip())
                if 'suggestions' in data:
                    return data['suggestions']
            except Exception:
                pass
    # bare JSON anywhere in text
    try:
        start = text.find('{"suggestions"')
        if start == -1: start = text.find('{ "suggestions"')
        if start != -1:
            data = _j.loads(text[start:])
            if 'suggestions' in data: return data['suggestions']
    except Exception: pass
    return []

def _glean_apply_suggestion(fragment_root, suggestion):
    """
    Apply a single suggestion dict to fragment_root in-place.
    Returns True on success, False on path-not-found.
    """
    import re as _re
    path = suggestion.get('path', '')
    fix_props = suggestion.get('fix_props') or {}
    remove_props = suggestion.get('remove_props') or []

    # Resolve path like "Fragment.Slots.Default[1].Slots.Left[0].Style"
    # Strip leading "Fragment." if present
    path = _re.sub(r'^Fragment\.?', '', path)
    node = fragment_root
    if not path:
        target = node
    else:
        parts = _re.split(r'\.(?![^\[]*\])', path)
        try:
            for part in parts:
                m = _re.match(r'^(\w+)\[(\d+)\]$', part)
                if m:
                    key, idx = m.group(1), int(m.group(2))
                    node = node[key][idx]
                elif part:
                    node = node[part]
            target = node
        except (KeyError, IndexError, TypeError):
            return False

    if not isinstance(target, dict):
        return False
    for k, v in fix_props.items():
        target[k] = v
    for k in remove_props:
        target.pop(k, None)
    return True

# ── VERSION & CONFLUENCE UPDATE-CHECK CONFIG ────────────────────────
APP_VERSION = "5.2.0"          # Bump this with each release

# ── VERSION CHECK — Confluence ──────────────────────────────────────
# The Confluence page body must contain one or more blocks like:
#   LATEST_VERSION: 1.2.0
#   DOWNLOAD_URL_WIN: https://...
#   DOWNLOAD_URL_MAC: https://...
# The app finds the highest LATEST_VERSION across all blocks.
CONFLUENCE_BASE_URL = "https://manhattanassociates.atlassian.net"
CONFLUENCE_PAGE_ID  = "7829028882"
CONFLUENCE_EMAIL    = os.getenv("FRAGDESG_CONFLUENCE_EMAIL", "")
CONFLUENCE_TOKEN    = os.getenv("FRAGDESG_CONFLUENCE_TOKEN", "")
# ─────────────────────────────────────────────────────────────────────

# ── MOUSE WHEEL / TOUCHPAD SCROLL HELPERS ──────────────────────────

def _wheel_scroll_units(e):
    """Normalize mouse wheel/touchpad input into canvas scroll units."""
    if hasattr(e, "delta"):
        if e.delta == 0:
            return 0
        if abs(e.delta) >= 120:
            return int(-1 * (e.delta / 120))
        return -1 if e.delta > 0 else 1
    if hasattr(e, "num"):
        return -1 if e.num == 4 else 1 if e.num == 5 else 0
    return 0

# ── ROBUST JSON CLEANER ─────────────────────────────────────────────
def _clean_json_str(s):
    """Strip BOM, invisible Unicode chars, JS-style comments (// and /* */), and trailing commas.
    Uses a character-level state machine so strings are never corrupted."""
    # Strip BOM and zero-width / invisible Unicode chars that json.loads rejects
    # but str.strip() silently ignores (e.g. U+200B copied from chat/editors).
    _INVISIBLE = (
        '\ufeff'   # BOM
        '\u200b'   # zero-width space
        '\u200c'   # zero-width non-joiner
        '\u200d'   # zero-width joiner
        '\u200e'   # left-to-right mark
        '\u200f'   # right-to-left mark
        '\u2060'   # word joiner
        '\u2061\u2062\u2063\u2064'  # invisible math operators
        '\ufffe'   # reversed BOM
        '\u00ad'   # soft hyphen
    )
    s = s.lstrip(_INVISIBLE).strip()
    # Fallback: skip any remaining invisible chars before the first { or [
    _j = next((i for i, c in enumerate(s) if c in ('{', '[')), None)
    if _j:
        s = s[_j:]
    result = []
    i = 0
    in_string = False
    while i < len(s):
        c = s[i]
        if in_string:
            result.append(c)
            if c == '\\':
                i += 1
                if i < len(s):
                    result.append(s[i])
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
                result.append(c)
            elif c == '/' and i + 1 < len(s):
                if s[i + 1] == '/':
                    while i < len(s) and s[i] != '\n':
                        i += 1
                    continue
                elif s[i + 1] == '*':
                    i += 2
                    while i < len(s) - 1:
                        if s[i] == '*' and s[i + 1] == '/':
                            i += 2
                            break
                        i += 1
                    continue
                else:
                    result.append(c)
            else:
                result.append(c)
        i += 1
    cleaned = ''.join(result)
    cleaned = re.sub(r',(?=\s*[}\]])', '', cleaned)
    return cleaned

# ── PALETTE & STYLING ───────────────────────────────────────────────
BG       = "#F8FAFC"
CARD_BG  = "#FFFFFF"
HDR_BG   = "#F1F5F9"
ACCENT   = "#1E3A8A"
GREEN    = "#16A34A"
RED      = "#DC2626"
ORANGE   = "#EA580C"
BLUE     = "#2563EB"
PURPLE   = "#7C3AED"
MUTED    = "#374151"
DARK     = "#111827"
SIDEBAR  = "#1E293B"
TOOL     = "#334155"
BORDER   = "#CBD5E1"
SEL      = "#3B82F6"
# ── Button palette (light backgrounds, like Apifrontendui.py) ────────
BTN_OK_BG   = "#DBEAFE"   # light blue  — Apply / Save / OK
BTN_OK_FG   = "#1E3A8A"   # dark navy text
BTN_DEL_BG  = "#FEE2E2"   # light red   — Delete / Remove
BTN_DEL_FG  = "#991B1B"   # dark red text
BTN_WARN_BG = "#FEF3C7"   # light amber — Clear / Warn
BTN_WARN_FG = "#92400E"   # dark amber text

COMP_COLORS = {
    "pie":           (GREEN,  "🥧"),
    "bar":           (ACCENT, "📊"),
    "line":          (PURPLE, "📈"),
    "column":        (ORANGE, "📉"),
    "spline":        (PURPLE, "〜"),
    "area":          (BLUE,   "▲"),
    "areaspline":    (GREEN,  "∿"),
    "scatter":       (ORANGE, "⁘"),
    "sunburst":      (ACCENT, "☀"),
    "waterfall":     (GREEN,  "⬇"),
    "table":         (DARK,   "📋"),
    "metrics":       (BLUE,   "🏷"),
    # ── UIRiver Elements ──
    "button":        (BLUE,   "🔘"),
    "pill":          (GREEN,  "🏷️"),
    "key-value":     (DARK,   "🔑"),
    "progress-bar":  (ORANGE, "▰"),
    "text":          (MUTED,  "🔤"),
    "banner":        (PURPLE, "📢"),
    "card":          (ACCENT, "🃏"),
    "input":         (BLUE,   "✏️"),
    "combobox":      (BLUE,   "🔽"),
    "toggle-button": (GREEN,  "🔄"),
    "search":        (DARK,   "🔍"),
    "segment-panel": (PURPLE, "📑"),
    "tab-group":     (ACCENT, "📂"),
    # Form inputs (expanded)
    "textarea":          (BLUE,   "📝"),
    "checkbox":          (GREEN,  "☑"),
    "dropdown":          (BLUE,   "▼"),
    "date-select":       (PURPLE, "📅"),
    "numeric-stepper":   (ORANGE, "🔢"),
    "currency-input":    (GREEN,  "💵"),
    # Display (expanded)
    "value":             (DARK,   "🏷"),
    "value-unit":        (MUTED,  "📏"),
    "icon":              (ACCENT, "✦"),
    "message":           (PURPLE, "💬"),
    "currency-format":   (GREEN,  "💲"),
    "key-value-detail":  (DARK,   "🗝"),
    # Actions (expanded)
    "button-icon":       (BLUE,   "●"),
    "action-button":     (ORANGE, "⚡"),
    "link":              (ACCENT, "🔗"),
    "related-link":      (PURPLE, "↗"),
    # Interactive
    "quick-filter":      (GREEN,  "⚡"),
    "filter-panel":      (DARK,   "🔎"),
    # Layout containers
    "accordion":         (ACCENT, "▸"),
    "expandable":        (BLUE,   "⊞"),
    "form":              (GREEN,  "📋"),
    "section":           (DARK,   "▦"),
    "list":              (MUTED,  "≡"),
    "stack":             (ACCENT, "■"),
    "flex":              (PURPLE, "↔"),
    "grid":              (ORANGE, "⊟"),
    "actions-popover":   (DARK,   "⬡"),
    "carousel":          (ACCENT, "🎠"),
}

COMP_DEFS = {
    "pie": {
        "label": "Pie Chart", "dataSourcePath": "StatusSummary", "backendVar": "object::StatusSummaryJs.result",
        "seriesMappings": [{"fieldMappings": {"STATUS_GROUP":"name", "MSG_COUNT":"y"},
            "seriesType":"pie","sourceDataPath":"StatusSummary",
            "staticOptions":{"name":"Messages","colorByPoint":True}}],
        "highchartsOptions": {
            "chart":{"type":"pie","marginTop":30},"title":{"text":""},
            "tooltip":{"pointFormat":"<b>{point.name}</b>: {point.y}"},
            "plotOptions":{"pie":{"allowPointSelect":True,"cursor":"pointer", "showInLegend": True,
                "dataLabels":{"enabled":True,"format":"<b>{point.name}</b>: {point.y}"}}},
            "legend":{"enabled":True,"layout":"horizontal"},
            "series":[{"name":"Messages"}]}},
    "bar": {
        "label": "Bar Chart", "dataSourcePath": "TypeDistribution", "backendVar": "object::TypeDistributionJs.result",
        "seriesMappings": [
            {"fieldMappings":{"MESSAGE_TYPE":"name", "MSG_COUNT":"y"},"seriesType":"bar",
             "sourceDataPath":"TypeDistribution","staticOptions":{"color":"#1E3A8A","name":"Total"}},
            {"fieldMappings":{"MESSAGE_TYPE":"name", "FAIL_COUNT":"y"},"seriesType":"bar",
             "sourceDataPath":"TypeDistribution","staticOptions":{"color":"#DC2626","name":"Failed"}}],
        "highchartsOptions": {
            "chart":{"type":"bar","marginLeft":180,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category","title":{"text":"Type","style":{"fontSize":"11px"}}},
            "yAxis":{"min":0,"title":{"text":"Count","style":{"fontSize":"11px"}}},
            "plotOptions":{"series":{"borderWidth":0,"stacking":"normal"}},
            "tooltip":{"shared":True,"useHTML":True,"headerFormat":"<b>{point.key}</b><br/>",
                "pointFormat":"<span style=\"color:{series.color}\">●</span> <b>{series.name}</b>: {point.y}<br/>"},
            "legend":{"enabled":True,"layout":"horizontal"},
            "series":[{"name":"Total"},{"name":"Failed"}]}},
    "line": {
        "label": "Line Chart", "dataSourcePath": "HourlyTrend", "backendVar": "object::HourlyTrendJs.result",
        "seriesMappings": [
            {"fieldMappings":{"HOUR_SLOT":"name", "MSG_COUNT":"y"},"seriesType":"line",
             "sourceDataPath":"HourlyTrend","staticOptions":{"color":"#1E3A8A","name":"Total"}}],
        "highchartsOptions": {
            "chart":{"type":"line","marginLeft":50,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category"},"yAxis":{"min":0},
            "plotOptions":{"line":{"marker":{"enabled":True,"radius":4}}},
            "tooltip":{"shared":True},"legend":{"enabled":True},"series":[{"name":"Total"}]}},
    "column": {
        "label": "Column Chart", "dataSourcePath": "TimelineSummary", "backendVar": "object::TimelineSummaryJs.result",
        "seriesMappings": [{"fieldMappings":{"TIME_SLOT":"name", "MSG_COUNT":"y"},"seriesType":"column",
            "sourceDataPath":"TimelineSummary","staticOptions":{"color":"#EA580C","name":"Value"}}],
        "highchartsOptions": {
            "chart":{"type":"column","marginTop":30},"title":{"text":""},
            "xAxis":{"type":"category"},"yAxis":{"min":0},
            "plotOptions":{"column":{"borderWidth":0,"stacking":"normal"}},"legend":{"enabled":True},
            "series":[{"name":"Value"}]}},
    "spline": {
        "label": "Spline Chart", "dataSourcePath": "HourlyTrend", "backendVar": "object::HourlyTrendJs.result",
        "seriesMappings": [{"fieldMappings":{"HOUR_SLOT":"name","MSG_COUNT":"y"},"seriesType":"spline","sourceDataPath":"HourlyTrend","staticOptions":{"color":"#7C3AED","name":"Total"}}],
        "highchartsOptions": {
            "chart":{"type":"spline","marginLeft":50,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category"},"yAxis":{"min":0},
            "plotOptions":{"spline":{"marker":{"enabled":True,"radius":4}}},"legend":{"enabled":True},"series":[{"name":"Total"}]}},
    "area": {
        "label": "Area Chart", "dataSourcePath": "HourlyTrend", "backendVar": "object::HourlyTrendJs.result",
        "seriesMappings": [{"fieldMappings":{"HOUR_SLOT":"name","MSG_COUNT":"y"},"seriesType":"area","sourceDataPath":"HourlyTrend","staticOptions":{"color":"#0EA5E9","name":"Total"}}],
        "highchartsOptions": {
            "chart":{"type":"area","marginLeft":50,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category"},"yAxis":{"min":0},
            "plotOptions":{"area":{"fillOpacity":0.3,"marker":{"enabled":False}}},"legend":{"enabled":True},"series":[{"name":"Total"}]}},
    "areaspline": {
        "label": "Area Spline Chart", "dataSourcePath": "HourlyTrend", "backendVar": "object::HourlyTrendJs.result",
        "seriesMappings": [{"fieldMappings":{"HOUR_SLOT":"name","MSG_COUNT":"y"},"seriesType":"areaspline","sourceDataPath":"HourlyTrend","staticOptions":{"color":"#10B981","name":"Total"}}],
        "highchartsOptions": {
            "chart":{"type":"areaspline","marginLeft":50,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category"},"yAxis":{"min":0},
            "plotOptions":{"areaspline":{"fillOpacity":0.3,"marker":{"enabled":False}}},"legend":{"enabled":True},"series":[{"name":"Total"}]}},
    "scatter": {
        "label": "Scatter Chart", "dataSourcePath": "ScatterData", "backendVar": "object::ScatterDataJs.result",
        "seriesMappings": [{"fieldMappings":{"X_VAL":"name","Y_VAL":"y"},"seriesType":"scatter","sourceDataPath":"ScatterData","staticOptions":{"color":"#F59E0B","name":"Data"}}],
        "highchartsOptions": {
            "chart":{"type":"scatter","marginLeft":50,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"title":{"text":"X"}},"yAxis":{"title":{"text":"Y"}},
            "plotOptions":{"scatter":{"marker":{"radius":5},"tooltip":{"pointFormat":"{point.x}, {point.y}"}}},"legend":{"enabled":True},"series":[{"name":"Data"}]}},
    "sunburst": {
        "label": "Sunburst Chart", "dataSourcePath": "HierarchyData", "backendVar": "object::HierarchyDataJs.result",
        "seriesMappings": [{"fieldMappings":{"ID":"name","PARENT":"parent","VALUE":"y"},"seriesType":"sunburst","sourceDataPath":"HierarchyData","staticOptions":{"colorByPoint":True,"name":"Hierarchy"}}],
        "highchartsOptions": {
            "chart":{"type":"sunburst","marginTop":30},
            "title":{"text":""},"tooltip":{"pointFormat":"<b>{point.name}</b>: {point.value}"},
            "series":[{"name":"Hierarchy","allowDrillToNode":True,"cursor":"pointer","dataLabels":{"format":"{point.name}","filter":{"property":"innerArcLength","operator":">","value":8}}}]}},
    "waterfall": {
        "label": "Waterfall Chart", "dataSourcePath": "WaterfallData", "backendVar": "object::WaterfallDataJs.result",
        "seriesMappings": [{"fieldMappings":{"CATEGORY":"name","VALUE":"y"},"seriesType":"waterfall","sourceDataPath":"WaterfallData","staticOptions":{"color":"#3B82F6","name":"Change"}}],
        "highchartsOptions": {
            "chart":{"type":"waterfall","marginLeft":60,"marginRight":50,"marginTop":30},
            "title":{"text":""},"xAxis":{"type":"category"},"yAxis":{"title":{"text":"Value"}},
            "plotOptions":{"waterfall":{"lineWidth":1}},"legend":{"enabled":True},"series":[{"name":"Change"}]}},
    "table": {
        "label": "Data Table", "dataSourcePath": "JournalData", "backendVar": "object::JournalDataJs.result",
        "columns": [
            {"field": "Message Type", "title": "Message Type"},
            {"field": "Total", "title": "Total"},
            {"field": "Failed", "title": "Failed"}
        ]
    },
    "metrics": {
        "label": "Metrics Panel", "dataSourcePath": "MetricsSummary", "backendVar": "object::MetricsSummaryJs.result",
        "metricsSpec": [
            {"label": "Total Messages", "field": "TOTAL_MSG", "unit": ""},
            {"label": "Failures",       "field": "FAILURES",  "unit": ""},
            {"label": "Failure %",      "field": "FAILURE_PCT","unit": "%"}
        ]
    }
}

CARD_W, CARD_H = 450, 400

# ── UIRIVER ELEMENT / CONTAINER DEFINITIONS ─────────────────────────────────
RIVER_ELEM_DEFS = {
    "button":        {"label": "Button",         "is_container": False, "default_config": {"LabelKey": "Click Me", "actionKey": "btn-action"}, "default_style": {"variant": "primary", "size": "small"}, "default_input": ""},
    "pill":          {"label": "Pill / Badge",   "is_container": False, "default_config": {"LabelKey": ""}, "default_style": {"pillBackgroundColor": "#E0F2FE", "pillTextColor": "#0369A1"}, "default_input": "STATUS_FIELD"},
    "key-value":     {"label": "Key-Value",       "is_container": False, "default_config": {"LabelKey": "Field Label", "AttributeType": "string"}, "default_style": {"color": "#111827"}, "default_input": "FIELD_NAME"},
    "progress-bar":  {"label": "Progress Bar",   "is_container": False, "default_config": {"LabelKey": "Progress"}, "default_style": {}, "default_input": "PROGRESS_FIELD"},
    "text":          {"label": "Text Display",   "is_container": False, "default_config": {"LabelKey": "Static Text"}, "default_style": {"color": "#111827"}, "default_input": ""},
    "banner":        {"label": "Banner",          "is_container": True,  "default_config": {"type": "info", "LabelKey": "Banner Message"}, "default_style": {}, "default_input": ""},
    "card":          {"label": "Card Container",  "is_container": True,  "default_config": {"title": "Card Title"}, "default_style": {}, "default_input": ""},
    "input":         {"label": "Text Input",      "is_container": False, "default_config": {"LabelKey": "Input Label", "name": "fieldName", "required": False}, "default_style": {}, "default_input": ""},
    "combobox":      {"label": "Combobox",        "is_container": False, "default_config": {"LabelKey": "Select Option", "name": "comboField"}, "default_style": {}, "default_input": ""},
    "toggle-button": {"label": "Toggle Button",  "is_container": False, "default_config": {"LabelKey": "Toggle", "name": "toggleField"}, "default_style": {}, "default_input": ""},
    "search":        {"label": "Search Box",      "is_container": False, "default_config": {"LabelKey": "Search...", "name": "searchField"}, "default_style": {}, "default_input": ""},
    "segment-panel": {"label": "Segment Panel",  "is_container": False, "default_config": {"EnableSegmentPanel": True, "EnableFilter": False, "Name": "", "SectionName": "", "Segments": [{"AttributeKey": "Tab 1", "AttributeValue": "seg1"}, {"AttributeKey": "Tab 2", "AttributeValue": "seg2"}]}, "default_style": {}, "default_input": ""},
    "tab-group":      {"label": "Tab Group",       "is_container": True,  "default_config": {"title": "Tabs"}, "default_style": {}, "default_input": ""},
    # ─ Form Inputs (expanded) ────────────────────────────────────────────
    "textarea":          {"label": "Text Area",        "is_container": False, "default_config": {"LabelKey": "Text Area", "name": "textareaField"}, "default_style": {}, "default_input": ""},
    "checkbox":          {"label": "Checkbox",          "is_container": False, "default_config": {"LabelKey": "Check Option", "name": "checkField"}, "default_style": {}, "default_input": ""},
    "dropdown":          {"label": "Dropdown",          "is_container": False, "default_config": {"LabelKey": "Select", "name": "dropField"}, "default_style": {}, "default_input": ""},
    "date-select":       {"label": "Date Picker",       "is_container": False, "default_config": {"LabelKey": "Select Date", "name": "dateField"}, "default_style": {}, "default_input": ""},
    "numeric-stepper":   {"label": "Numeric Stepper",   "is_container": False, "default_config": {"LabelKey": "Quantity", "name": "numField"}, "default_style": {}, "default_input": ""},
    "currency-input":    {"label": "Currency Input",    "is_container": False, "default_config": {"LabelKey": "Amount", "name": "currField", "locale": "en-US"}, "default_style": {}, "default_input": ""},
    # ─ Display (expanded) ──────────────────────────────────────────────
    "value":             {"label": "Value Display",     "is_container": False, "default_config": {}, "default_style": {}, "default_input": "FIELD_NAME"},
    "value-unit":        {"label": "Value + Unit",       "is_container": False, "default_config": {"unit": "kg"}, "default_style": {}, "default_input": "FIELD_NAME"},
    "icon":              {"label": "Icon",               "is_container": False, "default_config": {"icon": "info"}, "default_style": {}, "default_input": ""},
    "message":           {"label": "Message",            "is_container": False, "default_config": {"LabelKey": "Message text"}, "default_style": {}, "default_input": ""},
    "currency-format":   {"label": "Currency Display",   "is_container": False, "default_config": {"locale": "en-US"}, "default_style": {}, "default_input": "AMOUNT_FIELD"},
    "key-value-detail":  {"label": "Key-Value Detail",   "is_container": False, "default_config": {"LabelKey": "Detail Label", "AttributeType": "string"}, "default_style": {}, "default_input": "FIELD_NAME"},
    # ─ Actions (expanded) ────────────────────────────────────────────
    "button-icon":       {"label": "Icon Button",        "is_container": False, "default_config": {"icon": "edit", "actionKey": "icon-action"}, "default_style": {}, "default_input": ""},
    "action-button":     {"label": "Action Button",      "is_container": False, "default_config": {"LabelKey": "Action", "actionKey": "main-action"}, "default_style": {"variant": "secondary"}, "default_input": ""},
    "link":              {"label": "Link",                "is_container": False, "default_config": {"LabelKey": "Click Here", "href": "/route"}, "default_style": {}, "default_input": ""},
    "related-link":      {"label": "Related Link",        "is_container": False, "default_config": {"LabelKey": "View Related"}, "default_style": {}, "default_input": "ID_FIELD"},
    # ─ Interactive ────────────────────────────────────────────────
    "quick-filter":      {"label": "Quick Filter",        "is_container": False, "default_config": {"LabelKey": "Filter"}, "default_style": {}, "default_input": ""},
    "filter-panel":      {"label": "Filter Panel",        "is_container": False, "default_config": {"Attributes": []}, "default_style": {}, "default_input": ""},
    # ─ Layout Containers ──────────────────────────────────────────
    "accordion":         {"label": "Accordion",           "is_container": True,  "default_config": {"title": "Accordion"}, "default_style": {}, "default_input": ""},
    "expandable":        {"label": "Expandable",          "is_container": True,  "default_config": {"title": "Expandable Section"}, "default_style": {}, "default_input": ""},
    "form":              {"label": "Form Container",      "is_container": True,  "default_config": {"formId": "myForm"}, "default_style": {}, "default_input": ""},
    "section":           {"label": "Section",             "is_container": True,  "default_config": {"title": "Section Title"}, "default_style": {}, "default_input": ""},
    "list":              {"label": "List Container",      "is_container": True,  "default_config": {}, "default_style": {}, "default_input": ""},
    "stack":             {"label": "Stack Layout",        "is_container": True,  "default_config": {}, "default_style": {"direction": "vertical"}, "default_input": ""},
    "flex":              {"label": "Flex Layout",          "is_container": True,  "default_config": {}, "default_style": {"css": {"flexDirection": "row", "gap": "16px"}}, "default_input": ""},
    "grid":              {"label": "Grid Layout",          "is_container": True,  "default_config": {}, "default_style": {"css": {"gridTemplateColumns": "1fr 1fr", "gap": "16px"}}, "default_input": ""},
    "actions-popover":   {"label": "Actions Popover",       "is_container": True,  "default_config": {"LabelKey": "Export", "icon": "far-chevron-down"}, "default_style": {"css": {"height": "40px"}}, "default_input": ""},
    "carousel":          {"label": "Carousel",              "is_container": True,  "default_config": {"slidesPerPage": 5, "slidesPerMove": 5, "navigation": True, "pagination": False, "loop": False, "autoplay": False, "orientation": "horizontal"}, "default_style": {"width": "100%", "slideGap": "16px", "css": {}}, "default_input": ""},
}

CHART_TYPES  = {"pie", "bar", "line", "column", "metrics", "spline", "area", "areaspline", "scatter", "sunburst", "waterfall"}
RIVER_TYPES  = set(RIVER_ELEM_DEFS.keys())
# Layout wrapper containers that should be recursed THROUGH, not placed as cards
_STRUCTURAL  = {"flex", "sidebar", "sticky-header", "flyout-card"}
GX, GY = 16, 16

def _clean_carousel_fragment(node):
    """Recursively strip Init from carousel fragment template nodes."""
    if isinstance(node, dict):
        return {k: _clean_carousel_fragment(v) for k, v in node.items() if k != "Init"}
    if isinstance(node, list):
        return [_clean_carousel_fragment(i) for i in node]
    return node

def _is_insights_col(col_node):
    """Return (True, field, agent_id) if col_node is an insights lightbulb column, else (False,'','')."""
    for elem in col_node.get("Slots", {}).get("Default", []):
        if elem.get("Element") == "action-button":
            ag = (elem.get("Config", {})
                  .get("ActionConfig", {})
                  .get("Behavior", {})
                  .get("Flyout", {})
                  .get("AgentRef", {}))
            if ag.get("AgentId"):
                conds = elem.get("Conditions", [{}])
                cond_str = conds[0].get("Condition", "") if conds else ""
                field = cond_str.split(" ==")[0].strip() if " ==" in cond_str else "TicketsList"
                return True, field, ag["AgentId"]
    return False, "", ""

def _detect_table_insights(tbl_node):
    """Scan Config.Columns for an insights column. Returns (has_insights, field, agent_id)."""
    for col_node in tbl_node.get("Config", {}).get("Columns", []):
        found, field, agent_id = _is_insights_col(col_node)
        if found:
            return True, field, agent_id
    return False, "TicketsList", ""

_INTERNAL_META_KEYS = (
    "_segment", "_seg_dir", "_seg_gap", "_seg_pad", "_seg_flex",
    "_seg_css_full", "_seg_events", "_has_footer", "_ha_section",
)

def _strip_internal_meta(node):
    """Recursively strip ALL internal FragDesigner metadata keys (any key starting with '_')."""
    if isinstance(node, dict):
        for k in [k for k in list(node.keys()) if k.startswith("_")]:
            node.pop(k, None)
        for v in node.values():
            _strip_internal_meta(v)
    elif isinstance(node, list):
        for item in node:
            _strip_internal_meta(item)

# Backward-compatible alias
_strip_meta_keys = _strip_internal_meta

def _normalize_json(node):
    """Return a canonical form of a JSON node for semantic comparison.
    Sorts dict keys alphabetically and strips internal metadata keys.
    Use to compare two trees without being confused by key ordering or formatting."""
    if isinstance(node, dict):
        return {k: _normalize_json(v)
                for k, v in sorted(node.items())
                if not k.startswith("_")}
    if isinstance(node, list):
        return [_normalize_json(v) for v in node]
    return node

def _parse_col_link_events(col_node):
    """Parse field, link, and events from a column node. Module-level so _expand_slot can use it."""
    slots = col_node.get("Slots", {})
    field = ""
    link = None
    col_events = None
    for slot_items in slots.values():
        sl = slot_items if isinstance(slot_items, list) else [slot_items]
        for se in sl:
            if not isinstance(se, dict):
                continue
            elem = se.get("Element", "")
            if elem == "key-value" and not field:
                inp = se.get("Input", "")
                if inp:
                    field = inp
                _kv_clicks = se.get("Events", {}).get("Triggers", {}).get("OnClick", [])
                if _kv_clicks and col_events is None:
                    _kvc0 = _kv_clicks[0]
                    _kvp = _kvc0.get("Payload", {})
                    col_events = {
                        "event_id":       _kvc0.get("EventId", ""),
                        "container_id":   _kvc0.get("ContainerId", ""),
                        "filter_section": _kvp.get("filterSection", ""),
                        "filter_id":      _kvp.get("filterId", ""),
                        "input_expr":     _kvc0.get("Input", ""),
                    }
            elif elem == "link" and link is None:
                if not field:
                    field = se.get("Input", "")
                ll = se.get("Config", {}).get("LegacyLink", {})
                if ll.get("MenuId"):
                    rc = ll.get("RelationshipConfig", [{}])[0]
                    ref_keys = []
                    for rk in rc.get("ReferenceKeys", []):
                        if "FromAttribute" in rk:
                            ref_keys.append({"type": "field", "from_attr": rk["FromAttribute"],
                                             "to_attr": rk.get("ToAttribute", "")})
                        else:
                            ref_keys.append({"type": "filter", "to_attr": rk.get("ToAttribute", ""),
                                             "from_values": rk.get("FromValues", [])})
                    id_field = ref_keys[0]["from_attr"] if ref_keys and ref_keys[0]["type"] == "field" else ""
                    link = {"menu_id": ll.get("MenuId", ""), "rel_name": rc.get("RelationshipName", ""),
                            "from_entity": rc.get("FromEntity", "outputTable"), "to_entity": rc.get("ToEntity", ""),
                            "label_key": ll.get("LabelKey", ""), "id_field": id_field, "ref_keys": ref_keys}
                else:
                    _ec_clicks = se.get("Events", {}).get("Triggers", {}).get("OnClick", [])
                    if _ec_clicks:
                        _ec0 = _ec_clicks[0]
                        _payload = _ec0.get("Payload", {})
                        link = {
                            "event_type":     "event_click",
                            "event_id":       _ec0.get("EventId", ""),
                            "container_id":   _ec0.get("ContainerId", ""),
                            "filter_section": _payload.get("filterSection", ""),
                            "filter_id":      _payload.get("filterId", ""),
                            "input_expr":     _ec0.get("Input", ""),
                        }
    if not field:
        field = col_node.get("Config", {}).get("LabelKey", "Unknown")
    return field, link, col_events

def _extract_hc_adv(hc0):
    """Extract Advanced-tab-relevant fields from a highchartsOptions dict.
    Returns a nested dict that can be merged into a chart's hc at export time.
    Excludes 'series' and 'legend' which are managed separately."""
    adv = {}
    _c = hc0.get("chart", {})
    if isinstance(_c, dict):
        adv_c = {k: _c[k] for k in
                 ("height","marginLeft","marginRight","marginBottom",
                  "spacingLeft","spacingRight","spacingBottom",
                  "zoomType","panning","panKey")
                 if k in _c}
        if adv_c:
            adv["chart"] = adv_c
    for _ax in ("xAxis", "yAxis"):
        _v = hc0.get(_ax)
        if isinstance(_v, dict) and _v:
            adv[_ax] = {k: v for k, v in _v.items()}
    _pos = hc0.get("plotOptions", {}).get("series", {})
    if isinstance(_pos, dict):
        po_copy = {k: v for k, v in _pos.items() if k != "stacking"}
        if po_copy:
            adv.setdefault("plotOptions", {})["series"] = po_copy
    return adv

TOOLTIPS = {
    # ─ Charts & Table
    "pie":             "Pie Chart\nBreakdown by category (e.g. STATUS_GROUP → name, MSG_COUNT → y).\nSupports colorByPoint for automatic slice colours.",
    "bar":             "Bar Chart\nHorizontal comparison across categories. Supports multiple series\n(e.g. Total vs. Failed). Each series gets its own fieldMappings.",
    "line":            "Line Chart\nTrend over time. X = time slot, Y = count/value.\nSupports multiple overlaid series.",
    "column":          "Column Chart\nVertical bar chart, good for time-based or categorical data.\nSet TIME_SLOT → name and MSG_COUNT → y.",
    "spline":          "Spline Chart\nSmoothed line chart. Same data mapping as Line.\nGood for continuous trend data without sharp angles.",
    "area":            "Area Chart\nFilled area below the line. Good for showing volume over time.\nSet fillOpacity in plotOptions.area.",
    "areaspline":      "Area Spline Chart\nSmoothed filled-area chart. Combines spline and area.\nGood for soft trend visualization.",
    "scatter":         "Scatter Chart\nData points plotted by X/Y values.\nGood for correlation analysis. fieldMappings: X_VAL → name, Y_VAL → y.",
    "sunburst":        "Sunburst Chart\nHierarchical concentric ring chart. Requires ID, PARENT, VALUE fields.\nSupports drill-down. Good for category breakdowns.",
    "waterfall":       "Waterfall Chart\nShows cumulative effect of sequentially introduced values.\nGood for financial data. fieldMappings: CATEGORY → name, VALUE → y.",
    "table":           "Data Table\nFull-featured grid with sorting, pagination and optional row\nselection, footer totals and AI agentic actions.",
    "metrics":         "Metrics Panel\nKPI tile grid using UIRiver widget + card + key-value.\nEach tile shows a labeled value from the data source.\nAdd tiles with Label, Data Field Key and optional Unit suffix.",
    # ─ Filters
    "date":            "Date Range Filter\nAdds a date range picker to the filter panel.\nOutputs: Start date & End date attributes.",
    "textbox":         "Text Input Filter\nAdds a free-text search field to the filter panel.\nOutputs: a single text Attribute (key → EFW field).",
    "dropdown":        "Dropdown Filter\nAdds a Group-By select to the filter panel.\nOutputs: a single Select Attribute for EFW grouping.",
    # ─ Display
    "text":            "Text\nLocalized static text. Set LabelKey to the i18n key or\nliteral string. Supports color/font via Style.",
    "key-value":       "Key-Value\nLabeled data pair. LabelKey = visible label,\nInput = data-path for the value (e.g. CustomerName).",
    "key-value-detail":"Key-Value Detail\nEnhanced key-value with expand/collapse for nested data.\nSet LabelKey + Input + AttributeType (string/number/date).",
    "pill":            "Pill / Badge\nColored tag element. Set pillBackgroundColor &\npillTextColor in Style. Input = data field for the text.",
    "value":           "Value Display\nRaw value from the data source. Input = field path\nin the data object (e.g. TotalCount).",
    "value-unit":      "Value + Unit\nShows a numeric value with a measurement unit.\nSet unit in Config (e.g. \"kg\", \"ms\"). Input = field path.",
    "progress-bar":    "Progress Bar\nVisual progress indicator (0–100). Set LabelKey for the\nlabel. Input = numeric field from data source.",
    "currency-format": "Currency Display\nFormats a numeric field as locale currency (e.g. $1,234.56).\nSet locale in Config. Input = amount field path.",
    "icon":            "Icon\nVisual icon from the MAWC icon library.\nSet icon name in Config (e.g. \"info\", \"edit\", \"warning\").",
    "message":         "Message\nInformational message block. Set LabelKey for the text.\nSupports prefix/suffix slots for icons or badges.",
    # ─ Form Inputs
    "input":           "Text Input\nSingle-line text form control. Set name for form binding\nand required: true for validation.",
    "textarea":        "Text Area\nMulti-line text input. Good for descriptions or long text.\nSet name + LabelKey. Validation supported.",
    "combobox":        "Combobox\nSearchable dropdown with autocomplete. Set name +\ndata source for options. Supports filtering.",
    "checkbox":        "Checkbox\nBoolean toggle for forms. Set name + LabelKey.\nIntegrates with Angular reactive forms.",
    "date-select":     "Date Picker\nCalendar date input with locale formatting.\nSet name + LabelKey. Supports timezone display.",
    "numeric-stepper": "Numeric Stepper\nIncrement/decrement number input. Set name,\nLabelKey and optional step size in Config.",
    "currency-input":  "Currency Input\nLocale-aware monetary input with $ formatting.\nSet name + locale (e.g. en-US) in Config.",
    "toggle-button":   "Toggle Button\nOn/off switch control. Emits OnChange events.\nSet name + LabelKey. Integrates with reactive forms.",
    "search":          "Search Box\nText search with debounce. Triggers EFW filter\non input. Set name + LabelKey.",
    "quick-filter":    "Quick Filter\nPreset filter chip row for fast filtering.\nConfigure Segments array with LabelKey + Id per chip.",
    "segment-panel":   "Segment Panel\nTab-like segmented control for switching sections.\nSet Segments array: [{LabelKey, Id}, ...].",
    "filter-panel":    "Filter Panel\nAdvanced filter UI with multiple attribute filters.\nSet Attributes array with Input + Filter sub-config.",
    # ─ Actions
    "button":          "Button\nStandard action button. Set LabelKey for the text.\nConfigure Emitters → click → actions for behavior.",
    "button-icon":     "Icon Button\nCompact icon-only circular button. Set icon + actionKey.\nGood for edit/delete/expand in-line actions.",
    "action-button":   "Action Button\nButton bound to a complex action workflow.\nSet actionKey to the registered river-action key.",
    "link":            "Link\nNavigation link with routing support.\nSet LabelKey for display text + href or route path.",
    "related-link":    "Related Link\nLinks to a related entity record. Input = ID field\nfor the relationship (navigates on click).",
    # ─ Containers
    "card":            "Card Container\nWhite card with header, content and footer slots.\nSet title in Config. Supports Init for data loading.",
    "banner":          "Banner\nNotification banner bar. Set type (info / warning /\nerror / success) + LabelKey for the message.",
    "accordion":       "Accordion\nCollapsible sections list. Each section is a slot.\nGood for grouping settings or detail fields.",
    "expandable":      "Expandable\nSingle collapsible section with a title header.\nSet title in Config. Collapsed by default.",
    "form":            "Form Container\nWraps form elements in a reactive Angular form.\nSet formId in Config. Handles submit/reset.",
    "section":         "Section\nContent section with a title divider line.\nGroups related elements visually and semantically.",
    "list":            "List Container\nIterates over array data, rendering a slot template\nfor each item. Set Init to the array data source.",
    "stack":           "Stack Layout\nVertical or horizontal stack of child elements.\nSet direction: vertical | horizontal in Style.",
    "tab-group":       "Tab Group\nTabbed interface with named slot tabs.\nEach tab is a slot key. Supports personalization.",
    "flex":            "Flex Layout\nCSS flexbox container for responsive layouts.\nSet flexDirection, gap, justifyContent in Style.css.",
    "grid":            "Grid Layout\nCSS grid container. Set gridTemplateColumns\nand gap in Style.css (e.g. \"1fr 1fr\").",
    "carousel":        "Carousel\nScrollable slide show for repeating items (cards, tiles).\nSet slidesPerPage, slidesPerMove, navigation, pagination in Config.\nUse Fragment in Config for the item slot template.",
}

# ─────────────────────────────────────────────────────────────────
#  ELEMENT / CONTAINER EDIT SCHEMAS
# ─────────────────────────────────────────────────────────────────
ELEM_SCHEMAS = {
    "tab-group": {
        "desc": "Tabbed interface. Each tab Name must match a Slot key in the JSON.",
        "cfg": [
            ("preserveContent","Preserve Tab Content","bool","Keep tab DOM alive when switching — prevents data reload"),
            ("SelectedTabName","Default Active Tab",  "str", "Name of the tab shown on first load (must match a tab Name below)"),
            ("Personalizable", "Allow Personalization","bool","Let users reorder / hide tabs via the personalization sidebar"),
            ("__onoentab_source","OnOpenTab → SourceContainerId","str","ContainerId that emits the open-tab event (e.g. header-action-fragment)"),
            ("__onoentab_event", "OnOpenTab → EventId",          "str","EventId that triggers tab switching (e.g. open-tab-detail)"),
        ],
        "arr": ("Tabs","Tabs — one row per tab",[
            ("Name",    "Slot Name  (matches JSON Slot key)",180),
            ("LabelKey","Display Label / i18n Key",200),
            ("UID",     "UID  (required for personalization)",130),
        ]),
        "sty": [
            ("tabHeader.borderColor",     "Header Border Color","str","CSS color e.g. #CBD5E1"),
            ("tabHeader.hoverBorderColor","Hover Border Color", "str","CSS color on tab hover"),
            ("tabHeader.hoverTextColor",  "Hover Text Color",   "str","Text color on hover"),
            ("tabAlignment",              "Tab Alignment",      "enum","Alignment of tab labels",["start","center","end"]),
        ],
    },
    "card": {
        "desc": "White card container with header, body and footer slots.",
        "cfg": [
            ("title",    "Card Title",       "str", "Text shown in the card header bar"),
            ("direction","Content Direction","enum","Layout direction for card content",["row","column"]),
        ],
        "sty": [
            ("css.border",         "Border",       "str","e.g. 1px solid #CBD5E1"),
            ("css.borderRadius",   "Border Radius","str","e.g. 8px"),
            ("css.backgroundColor","Background",   "str","e.g. #FFFFFF or transparent"),
            ("css.minHeight",      "Min Height",   "str","e.g. 200px"),
        ],
    },
    "banner": {
        "desc": "Notification banner bar. Type controls colour and icon automatically.",
        "cfg": [
            ("type",    "Banner Type", "enum","Severity — controls colour and icon",["info","warning","error","success"]),
            ("LabelKey","Message Text","str", "i18n key or literal message string"),
        ],
    },
    "accordion": {"desc":"Collapsible sections list.","cfg":[("title","Section Title","str","Label in the collapsed panel header")]},
    "expandable": {"desc":"Single collapsible section.","cfg":[("title","Section Title","str","Label shown when collapsed")]},
    "form":       {"desc":"Reactive Angular form wrapper.","cfg":[("formId","Form ID","str","Unique name for the Angular reactive form group")]},
    "section":    {"desc":"Content section with a title divider line.","cfg":[("title","Section Title","str","Heading above the section content")]},
    "segment-panel": {
        "desc": "Segmented control — simple chips (EnableFilter=False) or filter quick-select (EnableFilter=True). In filter mode set Name+SectionName, EntityKey/Value, and add StaticList rows.",
        "cfg": [
            ("EnableSegmentPanel",  "Enable Segment Panel",  "bool", "Show as segment panel control (False = pure filter widget)"),
            ("EnableFilter",        "Enable Filter Mode",    "bool", "True = filter quick-select tied to agent filter; False = simple chip tabs"),
            ("Name",                "Filter Attr Name",      "str",  "Attribute name sent to agent, e.g. DATE_RANGE"),
            ("SectionName",         "Section Name",          "str",  "Filter section name, e.g. Filters"),
            ("Type",                "Data Type",             "str",  "Config.Type, e.g. string"),
            ("__filter_type",       "Filter Type",           "enum", "Singleselect or Multiselect when EnableFilter=True", ["Singleselect", "Multiselect"]),
            ("__placeholder_label", "Placeholder Label",     "str",  "Filter.Placeholder.LabelKey, e.g. 'Time Range:'"),
            ("__entity_key",        "Entity Key Field",      "str",  "Filter.EntityKey — field name used as display label, e.g. AttributeKey"),
            ("__entity_value",      "Entity Value Field",    "str",  "Filter.EntityValue — field name used as filter value, e.g. AttributeValue"),
        ],
        "arr": ("Segments","StaticList — one row per option",[
            ("AttributeKey",   "Label (AttributeKey)",    200),
            ("UID",            "UID",                     150),
            ("AttributeValue", "Value (AttributeValue)",  200),
        ]),
    },
    "button": {
        "desc": "Action button. Use Events (OnClick) to trigger show/hide of containers, or actionKey for river workflows.",
        "cfg": [
            ("LabelKey",           "Button Label",         "str",  "Display text or i18n key"),
            ("prefixName",         "Icon Prefix (opt.)",   "str",  "MAWC icon prefix e.g. far-filter  (leave blank if no icon)"),
            ("actionKey",          "Action Key (opt.)",    "str",  "River action key — leave blank when using Events.OnClick"),
            ("variant",            "Variant",              "enum", "Visual style", ["","primary","secondary","tertiary","danger","ghost"]),
            ("__onclick_container","OnClick → ContainerId","str",  "ContainerId targeted by the OnClick trigger"),
            ("__onclick_event",    "OnClick → EventId",    "str",  "EventId sent on click (e.g. show-chart, hide-chart, toggle-filter)"),
        ],
    },
    "actions-popover": {
        "desc": "Popover menu of actions (Export CSV, XLSX, etc.). Configured via ActionConfig.",
        "cfg": [
            ("LabelKey", "Button Label", "str",  "Display text e.g. Export"),
            ("icon",     "Chevron Icon", "str",  "Icon name e.g. far-chevron-down"),
        ],
    },
    "button-icon": {
        "desc": "Icon-only circular button for inline actions.",
        "cfg": [("icon","Icon Name","str","MAWC icon e.g. edit delete search more_vert"),("actionKey","Action Key","str","Registered river action key")],
    },
    "action-button": {
        "desc": "Button bound to a complex river action workflow.",
        "cfg": [("LabelKey","Button Label","str","Display text"),("actionKey","Action Key","str","Registered river action key"),("variant","Variant","enum","Visual style",["primary","secondary","tertiary"])],
    },
    "link": {
        "desc": "Navigation link. Use href for external URL or route for Angular routing.",
        "cfg": [("LabelKey","Link Text","str","Display text (i18n key or literal)"),("href","URL / Route","str","External URL or Angular route path")],
    },
    "related-link": {"desc":"Contextual link to a related entity record.","cfg":[("LabelKey","Link Text","str","Display text for the link")]},
    "input": {
        "desc": "Single-line text input integrated with Angular reactive forms.",
        "cfg": [
            ("LabelKey","Field Label","str", "Label shown above the input"),
            ("name",    "Form Name", "str", "Angular reactive form control name"),
            ("type",    "Input Type","enum","HTML input type",["text","email","password","number","tel"]),
            ("required","Required",  "bool","Mark as required — triggers validation display"),
        ],
    },
    "textarea":       {"desc":"Multi-line text area.","cfg":[("LabelKey","Field Label","str","Label above the textarea"),("name","Form Name","str","Reactive form control name"),("required","Required","bool","Mark as required")]},
    "combobox":       {"desc":"Searchable dropdown with autocomplete.","cfg":[("LabelKey","Field Label","str","Label above the combobox"),("name","Form Name","str","Reactive form control name")]},
    "dropdown":       {"desc":"Select list (static or dynamic).","cfg":[("LabelKey","Field Label","str","Label above the dropdown"),("name","Form Name","str","Reactive form control name")]},
    "checkbox":       {"desc":"Boolean toggle for reactive forms.","cfg":[("LabelKey","Checkbox Label","str","Text next to the checkbox"),("name","Form Name","str","Reactive form control name")]},
    "date-select":    {"desc":"Calendar date picker.","cfg":[("LabelKey","Field Label","str","Label above the picker"),("name","Form Name","str","Reactive form control name")]},
    "numeric-stepper":{"desc":"Increment/decrement number input.","cfg":[("LabelKey","Field Label","str","Label above the stepper"),("name","Form Name","str","Reactive form control name")]},
    "currency-input": {"desc":"Monetary input with locale formatting.","cfg":[("LabelKey","Field Label","str","Label above the input"),("name","Form Name","str","Reactive form control name"),("locale","Locale","str","e.g. en-US de-DE")]},
    "toggle-button":  {"desc":"On/off switch. Emits OnChange events.","cfg":[("LabelKey","Toggle Label","str","Text next to the toggle"),("name","Form Name","str","Reactive form control name")]},
    "search":         {"desc":"Search box with debounce. Triggers EFW filter on input.","cfg":[("LabelKey","Placeholder Text","str","Hint text inside the search box"),("name","Form Name","str","Reactive form control name")]},
    "quick-filter":   {"desc":"Preset filter chips for fast 1-click filtering.","arr":("Segments","Filter Chips — one row per chip",[("LabelKey","Chip Label / i18n Key",220),("Id","Filter ID",160)])},
    "filter-panel":   {"desc":"Advanced filter panel with multiple attribute filter controls."},
    "text":           {"desc":"Static or localized text display.","cfg":[("LabelKey","Text Content","str","i18n key or literal text string")],"sty":[("color","Text Color","str","CSS color e.g. #1E293B"),("fontSize","Font Size","str","e.g. 14px 1rem"),("fontWeight","Font Weight","enum","CSS font-weight",["normal","bold","600","700"])]},
    "key-value":      {"desc":"Labeled data pair. LabelKey = label, Input = data field path.","cfg":[("LabelKey","Label Text","str","Display label (i18n key or literal)"),("AttributeType","Attribute Type","enum","Data type for formatting",["string","number","date","currency"])]},
    "key-value-detail":{"desc":"Key-value with collapsible detail panel.","cfg":[("LabelKey","Label Text","str","Display label"),("AttributeType","Attribute Type","enum","Data type",["string","number","date","currency"])]},
    "pill":           {"desc":"Colored badge/tag. Input = data field for pill text.","sty":[("pillBackgroundColor","Background Color","str","CSS color e.g. #E0F2FE"),("pillTextColor","Text Color","str","CSS color e.g. #0369A1")]},
    "value":          {"desc":"Displays a raw field value. Set Input = field path in data source."},
    "value-unit":     {"desc":"Shows a numeric value with a unit label (e.g. 42 kg).","cfg":[("unit","Unit Label","str","Unit text after the value  e.g. kg ms % items")]},
    "progress-bar":   {"desc":"Visual progress bar. Input should be a 0–100 numeric field.","cfg":[("LabelKey","Label","str","Label above the progress bar")]},
    "currency-format":{"desc":"Formats a numeric field as locale-aware currency.","cfg":[("locale","Locale","str","e.g. en-US de-DE fr-FR")]},
    "icon":           {"desc":"Visual icon from the MAWC icon library.","cfg":[("icon","Icon Name","str","MAWC icon  e.g. info warning edit delete check_circle")]},
    "message":        {"desc":"Informational message block with optional icon slots.","cfg":[("LabelKey","Message Text","str","Display text (i18n key or literal)")]},
    "list":           {"desc":"Iterates over array data, rendering a slot template per item."},
    "carousel":       {"desc":"Scrollable carousel of repeating items. Set Config.Fragment for the item template.",
                       "cfg":[("slidesPerPage","Slides Per Page","int","Number of slides visible at once"),
                              ("slidesPerMove","Slides Per Move","int","Number of slides to advance per click"),
                              ("navigation","Show Nav Arrows","bool","Show previous/next navigation arrows"),
                              ("pagination","Show Pagination","bool","Show pagination dots below carousel"),
                              ("loop","Loop","bool","Wrap around when reaching end"),
                              ("autoplay","Autoplay","bool","Auto-advance slides"),
                              ("autoplayInterval","Autoplay Interval (ms)","int","Milliseconds between slides"),
                              ("orientation","Orientation","enum","Scroll direction",["horizontal","vertical"]),
                              ("dataSourcePath","Data Source Path","str","Sub-path within data for array items")],
                       "sty":[("width","Width","str","CSS width e.g. 100%"),
                              ("slideGap","Slide Gap","str","Gap between slides e.g. 16px"),
                              ("css.borderRadius","Border Radius","str","CSS border-radius"),
                              ("css.backgroundColor","Background Color","str","CSS background color"),
                              ("css.padding","Padding","str","CSS padding")]},
    "stack":          {"desc":"Vertical or horizontal stack of children.","sty":[("direction","Stack Direction","enum","Layout direction",["vertical","horizontal"])]},
    "flex":           {"desc":"CSS flexbox container for responsive layouts.","sty":[("css.flexDirection","Flex Direction","enum","Main axis direction",["row","column","row-reverse","column-reverse"]),("css.gap","Gap","str","Space between children e.g. 16px"),("css.justifyContent","Justify Content","enum","Main axis alignment",["flex-start","center","flex-end","space-between","space-around"]),("css.alignItems","Align Items","enum","Cross axis alignment",["flex-start","center","flex-end","stretch"]),("css.flexWrap","Flex Wrap","enum","Wrap behavior",["nowrap","wrap","wrap-reverse"])]},
    "grid":           {"desc":"CSS grid container for structured layouts.","sty":[("css.gridTemplateColumns","Template Columns","str","e.g. 1fr 1fr  or  repeat(3,1fr)"),("css.gap","Gap","str","Space between cells e.g. 16px"),("css.gridAutoRows","Auto Row Height","str","e.g. minmax(100px, auto)")]},
}

# ─────────────────────────────────────────────────────────────────
#  DRAG & RESIZE ENGINE
# ─────────────────────────────────────────────────────────────────
class CardDrag:
    def __init__(self, widget):
        self._w = widget; self._sx = self._sy = self._ox = self._oy = 0
        self._active = False; self._siblings = []; self._attach(widget)

    def _attach(self, w):
        if isinstance(w, tk.Button) or (isinstance(w, tk.Label) and w.cget("text") == "◢"): return
        w.bind("<ButtonPress-1>", self._p, add="+"); w.bind("<B1-Motion>", self._m, add="+"); w.bind("<ButtonRelease-1>", self._r, add="+")
        for c in w.winfo_children(): self._attach(c)

    def _p(self, e):
        self._sx, self._sy = e.x_root, e.y_root
        self._ox, self._oy = self._w.winfo_x(), self._w.winfo_y()
        self._active = False
        mc = self._w.master_card
        if hasattr(mc, 'app') and hasattr(mc.app, '_sel_card'):
            mc.app._sel_card(mc, e)

    def _m(self, e):
        dx, dy = e.x_root - self._sx, e.y_root - self._sy
        if not self._active and (abs(dx) > 5 or abs(dy) > 5):
            self._active = True
            self._w.lift()
        if self._active:
            pw, ph = self._w.master.winfo_width(), self._w.master.winfo_height()
            nx = max(0, min(self._ox+dx, pw - self._w.winfo_width()))
            ny = max(0, min(self._oy+dy, ph - self._w.winfo_height()))
            self._w.place(x=nx, y=ny)

    def _r(self, e):
        if self._active:
            app = self._w.master_card.app
            snap = getattr(app, '_snap_var', None)
            if snap and snap.get():
                # Snap final position to nearest GX/GY grid point
                fx = round(self._w.winfo_x() / GX) * GX
                fy = round(self._w.winfo_y() / GY) * GY
            else:
                fx, fy = self._w.winfo_x(), self._w.winfo_y()
            self._w.place(x=max(0, fx), y=max(0, fy)); self._active = False
            self._w.master_card._sync_dimensions()
            seg = getattr(self._w.master_card, 'segment', '')
            if seg:
                app = self._w.master_card.app
                app._recalc_seg_gap(seg)
                app._draw_gap_overlay()
            self._w.master_card.app.after(120, self._w.master_card.app._draw_grid)

# ─────────────────────────────────────────────────────────────────
#  FILTER ROW COMPONENT
# ─────────────────────────────────────────────────────────────────
class StaticListDialog(tk.Toplevel):
    """Modal dialog for configuring a filter's StaticList, EntityKey, EntityValue."""

    def __init__(self, parent, slv, ekv, evv, on_save=None):
        super().__init__(parent)
        self.title("Static List Configuration")
        self.resizable(True, False)
        self.configure(bg=BG)
        self._slv = slv; self._ekv = ekv; self._evv = evv
        self._on_save = on_save

        current_sl = slv.get().strip()
        current_ek = ekv.get().strip() or "key"
        current_ev = evv.get().strip() or "value"
        is_var = (not current_sl
                  or current_sl.startswith("{:")
                  or current_sl.startswith(":"))

        self._mode = tk.StringVar(value="var" if is_var else "inline")

        # ── header ────────────────────────────────────────────────────
        tk.Label(self, text="⚙  Configure Static List", bg=HDR_BG, fg=DARK,
                 font=("Helvetica", 11, "bold"), padx=12, pady=8,
                 anchor="w").pack(fill="x")

        body = tk.Frame(self, bg=BG, padx=14, pady=10)
        body.pack(fill="both", expand=True)

        # ── mode selector ─────────────────────────────────────────────
        mf = tk.Frame(body, bg=BG)
        mf.pack(fill="x", pady=(0, 10))
        tk.Radiobutton(mf, text="Variable Reference  (runtime injection by framework)",
                       variable=self._mode, value="var", bg=BG,
                       font=("Helvetica", 10, "bold"), cursor="hand2",
                       command=self._on_mode_change).pack(side="left", padx=(0, 24))
        tk.Radiobutton(mf, text="Inline Items  (hardcoded list)",
                       variable=self._mode, value="inline", bg=BG,
                       font=("Helvetica", 10, "bold"), cursor="hand2",
                       command=self._on_mode_change).pack(side="left")

        # ── variable reference panel ──────────────────────────────────
        self._var_panel = tk.Frame(body, bg=CARD_BG, bd=1, relief="solid",
                                   padx=12, pady=10)
        self._var_val = tk.StringVar(value=current_sl)
        vr = tk.Frame(self._var_panel, bg=CARD_BG)
        vr.pack(fill="x")
        tk.Label(vr, text="Variable:", bg=CARD_BG, fg=DARK,
                 font=("Helvetica", 9, "bold"), width=10, anchor="w").pack(side="left")
        ve = tk.Entry(vr, textvariable=self._var_val, width=36, font=("Helvetica", 10))
        ve.pack(side="left", padx=(4, 0))
        Tooltip(ve, "Runtime variable injected by the framework.\n"
                    "Format: {:myVariableName}\n"
                    "Examples:\n"
                    "  {:businessUnitData}\n"
                    "  {:filterPlanningModes}\n"
                    "  {:filterfailureReasons}")
        tk.Label(self._var_panel,
                 text="The framework replaces {:varName} with a dynamic list at runtime.\n"
                      "Use this when the list comes from a server-side data binding.",
                 bg=CARD_BG, fg=MUTED, font=("Helvetica", 8),
                 justify="left").pack(anchor="w", pady=(6, 0))

        # ── inline items panel ────────────────────────────────────────
        self._inline_panel = tk.Frame(body, bg=CARD_BG, bd=1, relief="solid",
                                      padx=12, pady=10)

        # EntityKey / EntityValue field name row
        ef = tk.Frame(self._inline_panel, bg=CARD_BG)
        ef.pack(fill="x", pady=(0, 8))
        tk.Label(ef, text="EntityKey field:", bg=CARD_BG, fg=DARK,
                 font=("Helvetica", 9, "bold")).pack(side="left")
        self._ek_e = tk.Entry(ef, width=16, font=("Helvetica", 9))
        self._ek_e.insert(0, current_ek)
        self._ek_e.pack(side="left", padx=(4, 16))
        Tooltip(self._ek_e, "The JSON property name used as the display label.\n"
                            "Examples: labelKey · AttributeKey · name · label")
        tk.Label(ef, text="EntityValue field:", bg=CARD_BG, fg=DARK,
                 font=("Helvetica", 9, "bold")).pack(side="left")
        self._ev_e = tk.Entry(ef, width=16, font=("Helvetica", 9))
        self._ev_e.insert(0, current_ev)
        self._ev_e.pack(side="left", padx=(4, 0))
        Tooltip(self._ev_e, "The JSON property name whose value is sent as the filter.\n"
                            "Examples: value · AttributeValue · id · code")

        # Column headers
        hdr = tk.Frame(self._inline_panel, bg="#1E293B")
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Key  (EntityKey value)", bg="#1E293B", fg=DARK,
                 font=("Helvetica", 8, "bold"), width=24, anchor="w",
                 padx=4).pack(side="left")
        tk.Label(hdr, text="  Value  (EntityValue value)", bg="#1E293B", fg=DARK,
                 font=("Helvetica", 8, "bold"), width=24, anchor="w",
                 padx=4).pack(side="left")

        # Scrollable rows area
        list_outer = tk.Frame(self._inline_panel, bg=CARD_BG,
                              highlightbackground=BORDER, highlightthickness=1)
        list_outer.pack(fill="x", pady=(0, 6))
        self._items_frame = tk.Frame(list_outer, bg=CARD_BG)
        self._items_frame.pack(fill="x", pady=2, padx=2)
        self._item_rows = []

        # Populate existing inline items
        if not is_var and current_sl:
            try:
                for item in json.loads(current_sl):
                    kv_val = item.get(current_ek) or next(iter(item.values()), "")
                    vv_list = list(item.values())
                    ev_val  = item.get(current_ev) or (vv_list[1] if len(vv_list) > 1 else kv_val)
                    self._add_item_row(str(kv_val), str(ev_val))
            except Exception:
                pass
        if not self._item_rows:
            self._add_item_row()

        # Add / Remove buttons
        btnr = tk.Frame(self._inline_panel, bg=CARD_BG)
        btnr.pack(fill="x")
        tk.Button(btnr, text="+ Add Row", bg=BTN_OK_BG, fg=BTN_OK_FG,
                  font=("Helvetica", 9), relief="flat", cursor="hand2",
                  padx=8, pady=3, command=lambda: self._add_item_row()
                  ).pack(side="left")
        tk.Button(btnr, text="✕ Remove Last", bg=BTN_DEL_BG, fg=BTN_DEL_FG,
                  font=("Helvetica", 9), relief="flat", cursor="hand2",
                  padx=8, pady=3, command=self._remove_last
                  ).pack(side="left", padx=6)

        # Show correct panel
        self._on_mode_change()

        # ── footer ────────────────────────────────────────────────────
        foot = tk.Frame(self, bg=HDR_BG, pady=8, padx=12)
        foot.pack(fill="x")
        tk.Button(foot, text="Cancel", bg="#94A3B8", fg="black", relief="flat",
                  cursor="hand2", font=("Helvetica", 10), padx=14, pady=4,
                  command=self.destroy).pack(side="right", padx=4)
        tk.Button(foot, text="  OK  ", bg=BTN_OK_BG, fg=BTN_OK_FG, relief="flat",
                  cursor="hand2", font=("Helvetica", 10, "bold"), padx=14, pady=4,
                  command=self._ok).pack(side="right", padx=4)

        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        # centre over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - self.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{max(px,0)}+{max(py,0)}")

    def _on_mode_change(self):
        if self._mode.get() == "var":
            self._inline_panel.pack_forget()
            self._var_panel.pack(fill="x", pady=4)
        else:
            self._var_panel.pack_forget()
            self._inline_panel.pack(fill="x", pady=4)

    def _add_item_row(self, k="", v=""):
        row = tk.Frame(self._items_frame, bg=CARD_BG)
        row.pack(fill="x", pady=1)
        kvar = tk.StringVar(value=k)
        vvar = tk.StringVar(value=v)
        tk.Entry(row, textvariable=kvar, width=24, font=("Helvetica", 9)
                 ).pack(side="left", padx=2)
        tk.Entry(row, textvariable=vvar, width=24, font=("Helvetica", 9)
                 ).pack(side="left", padx=2)
        self._item_rows.append((kvar, vvar, row))

    def _remove_last(self):
        if self._item_rows:
            _, __, row = self._item_rows.pop()
            row.destroy()

    def _ok(self):
        ek_name = self._ek_e.get().strip() or "key"
        ev_name = self._ev_e.get().strip() or "value"
        if self._mode.get() == "var":
            val = self._var_val.get().strip()
            # Normalise to {:varName} format
            if val and not val.startswith("{") and not val.startswith(":"):
                val = "{:" + val + "}"
            elif val.startswith(":") and not val.startswith("{:"):
                val = "{" + val + "}"
            self._slv.set(val)
        else:
            items = []
            for kvar, vvar, _ in self._item_rows:
                k, v = kvar.get().strip(), vvar.get().strip()
                if k or v:
                    items.append({ek_name: k, ev_name: v})
            self._slv.set(json.dumps(items) if items else "")
            self._ekv.set(ek_name)
            self._evv.set(ev_name)
        if self._on_save:
            self._on_save()
        self.destroy()


class FilterRow(tk.Frame):
    def __init__(self, parent, fid, ftype, app, ph="", static_list="", entity_key="", entity_value=""):
        super().__init__(parent, bg=BG, pady=4, padx=4)
        self.fid = fid; self.app = app
        self.lv  = tk.StringVar(value="Field Label")
        self.kv  = tk.StringVar(value="BACKEND_KEY")
        self.tv  = tk.StringVar(value=ftype)
        self.pv  = tk.StringVar(value=ph)
        self.slv = tk.StringVar(value=static_list)
        self.ekv = tk.StringVar(value=entity_key)
        self.evv = tk.StringVar(value=entity_value)

        # ── Row 1: type / label / key / placeholder / delete ─────────
        row1 = tk.Frame(self, bg=BG)
        row1.pack(fill="x")

        icon = "📅" if ftype=="date" else ("☑️" if ftype=="multiselect" else ("🔘" if ftype=="singleselect" else ("🔽" if ftype=="dropdown" else "✏️")))
        self._icon_lbl = tk.Label(row1, text=icon, bg=BG)
        self._icon_lbl.pack(side="left", padx=2)

        self._type_combo = ttk.Combobox(
            row1, textvariable=self.tv,
            values=["textbox", "date", "dropdown", "multiselect", "singleselect"],
            width=12, state="readonly")
        self._type_combo.pack(side="left", padx=2)
        Tooltip(self._type_combo,
                "Filter type:\n"
                "  textbox     — free-text entry (Textbox)\n"
                "  date        — date-range picker (Date-range)\n"
                "  dropdown    — single-select group-by (Select)\n"
                "  multiselect — multi-select with a static or variable list\n"
                "  singleselect— single-select with a static or variable list")

        lbl_e = tk.Entry(row1, textvariable=self.lv, width=16)
        lbl_e.pack(side="left", padx=2)
        Tooltip(lbl_e, "Display label shown above the filter input in the UI.\n"
                       "Example: Business Unit · Failure Reason Code")

        key_e = tk.Entry(row1, textvariable=self.kv, width=16)
        key_e.pack(side="left", padx=2)
        Tooltip(key_e, "Backend parameter name — must match the EFW input key.\n"
                       "Example: BusinessUnitId · FailureReasonCode · OrderType")

        ph_e = tk.Entry(row1, textvariable=self.pv, width=18)
        ph_e.pack(side="left", padx=2)
        Tooltip(ph_e, "Placeholder / hint text shown inside the empty input.\n"
                      "Example: Enter Business Unit · Select Reason Code")

        tk.Button(row1, text="✕", fg=RED, bg=BG, relief="flat", cursor="hand2",
                  command=lambda: self.app.remove_filter(self.fid)).pack(side="right", padx=4)

        # ── Row 2: StaticList editor (multiselect / singleselect only) ─
        self._row2 = tk.Frame(self, bg=BG)
        tk.Label(self._row2, text="List:", bg=BG, fg=MUTED,
                 font=("Helvetica", 8, "bold")).pack(side="left", padx=(22, 2))
        self._sl_btn = tk.Button(
            self._row2, text="📋 Edit List…", relief="flat",
            bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica", 8, "bold"),
            cursor="hand2", padx=6, pady=2,
            command=self._open_sl_dialog)
        self._sl_btn.pack(side="left", padx=2)
        Tooltip(self._sl_btn,
                "Open the Static List editor.\n\n"
                "Variable Reference — inject a runtime variable,\n"
                "  e.g. {:businessUnitData} or {:filterPlanningModes}.\n"
                "  The framework replaces it with the actual list.\n\n"
                "Inline Items — hardcode key/value pairs directly,\n"
                "  e.g. Deselected / Canceled / Both.\n"
                "  Set EntityKey and EntityValue field names to\n"
                "  control which JSON property is the label vs. the\n"
                "  filter value sent to the backend.")
        self._sl_summary = tk.Label(
            self._row2, text=self._sl_summary_text(), bg=BG,
            fg="#2563EB", font=("Helvetica", 8), cursor="hand2")
        self._sl_summary.pack(side="left", padx=4)
        self._sl_summary.bind("<Button-1>", lambda _e: self._open_sl_dialog())
        self.slv.trace_add("write", lambda *_: self._sl_summary.config(text=self._sl_summary_text()))

        self._update_row2_visibility()
        self._type_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_row2_visibility())

    # ── helpers ───────────────────────────────────────────────────────
    def _sl_summary_text(self):
        sl = self.slv.get().strip()
        if not sl:
            return "(no list configured — click Edit List)"
        if sl.startswith("{:") or sl.startswith(":"):
            return f"🔗 {sl}"
        try:
            items = json.loads(sl)
            return f"📋 {len(items)} inline item{'s' if len(items) != 1 else ''}"
        except Exception:
            return f"📋 {sl[:40]}{'…' if len(sl) > 40 else ''}"

    def _open_sl_dialog(self):
        StaticListDialog(self, self.slv, self.ekv, self.evv)

    def _update_row2_visibility(self):
        if self.tv.get() in ("multiselect", "singleselect"):
            self._row2.pack(fill="x")
        else:
            self._row2.pack_forget()

    def get_config(self):
        return {
            "label": self.lv.get(), "key": self.kv.get(),
            "type": self.tv.get(), "placeholder": self.pv.get(),
            "static_list": self.slv.get(), "entity_key": self.ekv.get(), "entity_value": self.evv.get()
        }

# ─────────────────────────────────────────────────────────────────
#  COMPONENT CARD
# ─────────────────────────────────────────────────────────────────
class CompCard(tk.Frame):
    def __init__(self, parent, cid, ctype, title, ds, bvar, app, cols=None, series=None, width=None, height=None, has_footer=False, css_width=None, css_height=None, has_checkboxes=True, has_agentic=True, agent_id="ext-mhetroubleshoot", agent_args=None, elem_config=None, elem_input=None, elem_style=None, has_multiselect=True, segment="", uid="", events=None, has_insights=False, insights_field="TicketsList", insights_agent_id=""):
        self.is_river_element = ctype in RIVER_TYPES
        if self.is_river_element:
            w = width if width else 260
            h = height if height else 160
        else:
            w = width if width else (800 if ctype == "table" else CARD_W)
            h = height if height else CARD_H
        super().__init__(parent, width=w, height=h, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=2, cursor="fleur")
        self.master_card = self
        self.cid=cid; self.ctype=ctype; self.title=title; self.ds=ds; self.bvar=bvar; self.app=app
        self.has_footer = has_footer
        self.has_checkboxes = has_checkboxes
        self.has_multiselect = has_multiselect
        self.has_agentic = has_agentic
        self.agent_id = agent_id
        self.agent_args = agent_args if agent_args is not None else []
        self.agent_question = ""
        self.segment = segment
        self.uid = uid
        self.events = events or {}
        self.has_insights = has_insights
        self.insights_field = insights_field if insights_field else "TicketsList"
        self.insights_agent_id = insights_agent_id if insights_agent_id else ""
        self.orig_chart_node  = None   # preserved for native-chart round-trip
        self.chart_stacking   = False  # True → stacking:"normal" in highchartsOptions
        self.chart_legend_enabled = True
        self.chart_legend_layout  = "horizontal"
        self.chart_legend_valign  = "bottom"
        self.chart_legend_align   = "center"
        self.chart_legend_y       = 0
        self.orig_full_node  = None   # preserved for supported-element round-trip
        # Edit-state flags: set True when user changes the respective section.
        # When all are False and orig_full_node is present, exporter returns orig_full_node verbatim.
        self._config_edited    = False
        self._style_edited     = False
        self._slots_edited     = False
        self._structure_edited = False
        self.orig_style_css = {}          # preserved for CSS round-trip (flex, minWidth, etc.)
        self.extra_css = {}               # additional CSS set via Align Fix (any property)
        # Tab-group marry/unmarry state
        self.is_tab_group = (ctype == "tab-group")
        self.unmarried_slot = None  # name of the currently unmarried slot
        # Tables default to 16px inner padding (matches exported JSON convention)
        self.card_padding = ({"top": 16, "right": 16, "bottom": 16, "left": 16}
                             if ctype == "table"
                             else {"top": 0, "right": 0, "bottom": 0, "left": 0})

        if self.is_river_element:
            rdef = RIVER_ELEM_DEFS[ctype]
            self.elem_config = elem_config if elem_config is not None else copy.deepcopy(rdef["default_config"])
            self.elem_input  = elem_input  if elem_input  is not None else rdef["default_input"]
            self.elem_style  = elem_style  if elem_style  is not None else copy.deepcopy(rdef["default_style"])
            self.css_width   = css_width   if css_width   else "auto"
            self.css_height  = css_height  if css_height  else "auto"
            self.columns = []; self.series = []; self.metrics = []
        else:
            self.elem_config = {}; self.elem_input = ""; self.elem_style = {}
            self.css_width = css_width if css_width else ("100%" if ctype in ("table", "metrics") else "calc(50% - 16px)")
            self.css_height = css_height if css_height else f"{h}px"
            self.columns = cols if cols is not None else copy.deepcopy(COMP_DEFS[ctype].get("columns", []))
            self.metrics = copy.deepcopy(COMP_DEFS[ctype].get("metricsSpec", []))
            if series is not None:
                self.series = series
            else:
                smaps = COMP_DEFS[ctype].get("seriesMappings", [])
                self.series = []
                for s in smaps:
                    fm = s.get("fieldMappings", {})
                    x_field = next((k for k, v in fm.items() if v == "name"), None)
                    fm_inverted = x_field is None
                    if x_field is None: x_field = fm.get("name", "")
                    y_field = next((k for k, v in fm.items() if v == "y"), None)
                    if y_field is None: y_field = fm.get("y", "")
                    opts = s.get("staticOptions", {})
                    color = opts.get("color", "colorByPoint" if opts.get("colorByPoint") else "")
                    self.series.append({"name": opts.get("name", "Series"), "x_field": x_field, "y_field": y_field, "color": color, "fm_inverted": fm_inverted})

        self.hc_adv = {}   # advanced highchartsOptions overrides (zoom, margins, axes, plotOptions)
        self.propagate(False); self._build(); self._dragger = CardDrag(self)

    def _build(self):
        for w in self.winfo_children(): w.destroy()

        # ── Tab-group: keep orig_full_node in sync with elem_config.Tabs ──────
        if self.is_tab_group:
            _tabs = (self.elem_config or {}).get("Tabs", [])
            if _tabs:
                if self.orig_full_node is None:
                    # First time tabs are defined — synthesize the full node skeleton
                    self.orig_full_node = {
                        "Container": "tab-group",
                        "Config":    dict(self.elem_config),
                        "Input":     self.elem_input or "",
                        "Style":     dict(self.elem_style) if self.elem_style else {},
                        "Slots":     {t.get("Name", t.get("LabelKey", f"Tab{i+1}")): []
                                      for i, t in enumerate(_tabs)},
                    }
                else:
                    # Tabs may have been added/renamed via Edit dialog — sync
                    self.orig_full_node.setdefault("Config", {})["Tabs"] = list(_tabs)
                    _slots = self.orig_full_node.setdefault("Slots", {})
                    for _t in _tabs:
                        _k = _t.get("Name", _t.get("LabelKey", ""))
                        if _k and _k not in _slots:
                            _slots[_k] = []

        col, icon = COMP_COLORS.get(self.ctype, (ACCENT, "📊"))

        h = tk.Frame(self, bg=HDR_BG, height=36); h.pack(fill="x"); h.pack_propagate(False)
        # Pack action buttons FIRST so they always reserve their space on the right
        self.header_buttons = []
        for txt, col2, cmd in [("✕", RED, lambda: self.app.remove_comp(self.cid)), ("✎", ACCENT, self._edit)]:
            btn = tk.Button(h, text=txt, bg=HDR_BG, fg=col2, relief="flat", font=("Helvetica", 10, "bold"), cursor="hand2", command=cmd)
            btn.pack(side="right", padx=3, pady=3)
            self.header_buttons.append(btn)
        tk.Label(h, text=f"{icon} {self.title}", bg=HDR_BG, fg=DARK, font=("Helvetica", 10, "bold")).pack(side="left", padx=8)
        if self.segment:
            seg_colors = ["#2563EB","#059669","#D97706","#DC2626","#7C3AED","#0891B2"]
            seg_col = seg_colors[hash(self.segment) % len(seg_colors)]
            _is_flyout = getattr(self.app, 'segment_dirs', {}).get(self.segment, {}).get('flyout', {}).get('enabled', False)
            _seg_lbl   = f"▸ {self.segment}  ⇄" if _is_flyout else f"▸ {self.segment}"
            tk.Label(h, text=_seg_lbl, bg=seg_col, fg="black", font=("Helvetica", 8, "bold"), padx=5).pack(side="left", padx=4)

        # Tab-group slot controls
        if self.is_tab_group and self.orig_full_node:
            self.slot_buttons = []
            slots = self.orig_full_node.get("Slots", {})
            tabs_cfg = self.orig_full_node.get("Config", {}).get("Tabs", [])
            slot_display = {t.get("Name", t.get("LabelKey", "")): t.get("LabelKey", t.get("Name", ""))
                            for t in tabs_cfg}
            for slot_name in slots.keys():
                disp_lbl = slot_display.get(slot_name, slot_name)
                short = disp_lbl[:10] + "…" if len(disp_lbl) > 11 else disp_lbl
                is_unmarried = (self.unmarried_slot == slot_name)
                btn_txt = f"⬢ {short}" if is_unmarried else f"⬡ {short}"
                btn_col = "#DC2626" if is_unmarried else "#2563EB"
                btn = tk.Button(h, text=btn_txt, bg=btn_col, fg="black", relief="flat",
                                font=("Helvetica", 8, "bold"), cursor="hand2",
                                command=lambda sn=slot_name: self._toggle_slot_marry(sn))
                btn.pack(side="left", padx=(2,0), pady=3)
                if is_unmarried:
                    # Eject button: returns slot cards to canvas permanently, clears slot
                    ej_btn = tk.Button(h, text="⊣", bg=BTN_OK_BG, fg=BTN_OK_FG, relief="flat",
                                       font=("Helvetica", 8, "bold"), cursor="hand2",
                                       command=lambda sn=slot_name: self._eject_slot(sn))
                    ej_btn.pack(side="left", padx=(0,1), pady=3)
                    Tooltip(ej_btn, "Eject — keep cards on canvas, clear this slot")
                add_btn = tk.Button(h, text="＋", bg=BTN_OK_BG, fg=BTN_OK_FG, relief="flat",
                                    font=("Helvetica", 8, "bold"), cursor="hand2",
                                    command=lambda sn=slot_name: self._add_cards_to_slot(sn))
                add_btn.pack(side="left", padx=(0,3), pady=3)
                Tooltip(add_btn, f"Assign canvas cards / segments into: {slot_name}")
                self.slot_buttons.append(btn)

        self.cv = tk.Canvas(self, bg="#FAFAFA", highlightthickness=0); self.cv.pack(fill="both", expand=True, padx=4, pady=2)
        self.dim_label = tk.Label(self.cv, text=f"Scale: {self.css_width}", bg="#FAFAFA", fg=MUTED, font=("Courier", 9, "bold")); self.dim_label.place(x=5, y=5)

        self.resizer = tk.Label(self, text="◢", bg=CARD_BG, fg=MUTED, cursor="sizing", font=("Helvetica", 12))
        self.resizer.place(relx=1.0, rely=1.0, anchor="se")
        self.resizer.bind("<ButtonPress-1>", self._start_resize)
        self.resizer.bind("<B1-Motion>", self._do_resize)
        self.resizer.bind("<ButtonRelease-1>", self._stop_resize)
        
        # Bind mouse wheel to enable scrolling when mouse is over cards
        def _card_wheel(e):
            steps = _wheel_scroll_units(e)
            if steps == 0:
                return
            if e.state & 0x1:  # Shift key pressed
                self.app._cv.xview_scroll(steps, "units")
            else:
                self.app._cv.yview_scroll(steps, "units")
        
        self.bind("<MouseWheel>", _card_wheel)
        h.bind("<MouseWheel>", _card_wheel)
        self.cv.bind("<MouseWheel>", _card_wheel)
        self.resizer.bind("<MouseWheel>", _card_wheel)
        for btn in self.header_buttons:
            btn.bind("<MouseWheel>", _card_wheel)
        
        self.after(60, self._preview)

    def _toggle_slot_marry(self, slot_name):
        """Toggle marry/unmarry state for a specific slot in tab-group."""
        if self.unmarried_slot == slot_name:
            # Marry back: collapse the slot
            self.unmarried_slot = None
            self._collapse_slot(slot_name)
        else:
            # Unmarry: expand the slot (ensure only one slot unmarried at a time)
            if self.unmarried_slot:
                self._collapse_slot(self.unmarried_slot)
            self.unmarried_slot = slot_name
            self._expand_slot(slot_name)
        self._build()  # Rebuild to update button states

    def _collect_slot_comps(self, nodes, comps_list):
        """Extract renderable components from slot content nodes (mirrors find_comps logic)."""
        if isinstance(nodes, list):
            for item in nodes:
                self._collect_slot_comps(item, comps_list)
            return
        if not isinstance(nodes, dict):
            return
        container = nodes.get("Container")
        element   = nodes.get("Element")
        # Native chart
        if container == "chart" and "Init" in nodes:
            comps_list.append({"_is_native_chart": True, "_node": nodes})
            return
        # Our generated grid+header format (charts exported by _comp_json)
        if container == "grid" and "header" in nodes.get("Slots", {}):
            comps_list.append({"_is_grid_chart": True, "_node": nodes})
            return
        # Table
        if container == "table":
            for _tc in nodes.get("Slots", {}).get("Default", []):
                if isinstance(_tc, dict) and _tc.get("Container") == "footer-container":
                    nodes["_has_footer"] = True
                    break
            comps_list.append(nodes)
            return
        # AgentRef → passthrough placeholder
        if "AgentRef" in nodes:
            agent_id = nodes["AgentRef"].get("AgentId", "AgentRef")
            comps_list.append({"_is_passthrough": True, "_node": nodes, "_label": agent_id})
            return
        # River elements (not structural)
        if element in RIVER_TYPES or (container in RIVER_TYPES and container not in
                {None, "flex", "grid", "sidebar", "card", "header", "stack"}):
            comps_list.append({"_is_river_elem": True, "_node": nodes})
            return
        # Unknown element
        if element and element not in RIVER_TYPES:
            comps_list.append({"_is_passthrough": True, "_node": nodes})
            return
        # flex/grid: detect KPI metrics group or named segment before generic recursion
        if container in ("flex", "grid") and "Init" not in nodes:
            default_items = nodes.get("Slots", {}).get("Default", [])
            kpi = [item for item in default_items
                   if isinstance(item, dict) and item.get("Container") == "card"
                   and "Init" in item
                   and any(isinstance(e, dict) and e.get("Element") == "key-value"
                           for e in item.get("Slots", {}).get("Default", []))]
            dict_items = [x for x in default_items if isinstance(x, dict)]
            if kpi and len(kpi) == len(dict_items):
                comps_list.append({"_is_metrics_group": True, "_cards": kpi,
                                   "_style": nodes.get("Style", {}),
                                   "_config": nodes.get("Config", {}),
                                   "_segment": nodes.get("Config", {}).get("SectionName", "")})
                return
            section_name = nodes.get("Config", {}).get("SectionName", "")
            if section_name:
                # Named section: collect from ALL slot arrays (Default, Left, Right, content…)
                # and tag every inner comp with segment metadata.
                # This handles sections whose children are river elements, sidebar, nested
                # flex, or any mix — not just chart/table/grid.
                _ncss = nodes.get("Style", {}).get("css", {})
                inner_comps = []
                for _skey, _sval in nodes.get("Slots", {}).items():
                    if isinstance(_sval, list):
                        for ch in _sval:
                            self._collect_slot_comps(ch, inner_comps)
                for ic in inner_comps:
                    if isinstance(ic, dict):
                        ic.setdefault("_segment",      section_name)
                        ic.setdefault("_seg_dir",      _ncss.get("flexDirection", "row"))
                        ic.setdefault("_seg_gap",      _ncss.get("gap", "0rem"))
                        ic.setdefault("_seg_pad",      _ncss.get("padding", ""))
                        ic.setdefault("_seg_flex",     _ncss.get("flex", ""))
                        ic.setdefault("_seg_css_full", dict(_ncss))
                comps_list.extend(inner_comps)
                return  # always stop here — don't re-process via _RECURSE
        # Structural containers: recurse into Slots values only (not all keys)
        _RECURSE = {None, "flex", "grid", "sidebar", "card", "header", "stack",
                    "flyout-layout", "flyout-card", "header-action", "footer-container",
                    "fragment-switch", "fragment-switcher", "field"}
        if container in _RECURSE:
            for slot_items in nodes.get("Slots", {}).values():
                if isinstance(slot_items, list):
                    for item in slot_items:
                        self._collect_slot_comps(item, comps_list)
            return
        # Skip empty tab-groups (all slot arrays are empty) — avoids duplicate phantom cards
        if container == "tab-group":
            if all(not v for v in nodes.get("Slots", {}).values()):
                return
        # Unknown container → passthrough
        comps_list.append({"_is_passthrough": True, "_node": nodes})

    def _expand_slot(self, slot_name):
        """Expand a slot: extract its components and add to canvas as editable cards."""
        if not self.orig_full_node:
            return

        slot_items = self.orig_full_node.get("Slots", {}).get(slot_name, [])
        if not isinstance(slot_items, list):
            slot_items = [slot_items] if slot_items else []

        # Save outer Init wrapper (unnamed flex with Init) for round-trip on collapse.
        # These wrappers carry slot-level API init config that must survive expand/collapse.
        if not hasattr(self, '_slot_outer_wrappers'):
            self._slot_outer_wrappers = {}
        if (len(slot_items) == 1 and isinstance(slot_items[0], dict)
                and slot_items[0].get("Container") == "flex"
                and "Init" in slot_items[0]
                and not slot_items[0].get("Config", {}).get("SectionName", "")):
            _ow = copy.deepcopy(slot_items[0])
            _ow.setdefault("Slots", {})["Default"] = []
            self._slot_outer_wrappers[slot_name] = _ow
        else:
            self._slot_outer_wrappers.pop(slot_name, None)

        # Position cards below the tab-group card, wrapping at 1600px
        tg_x = self.winfo_x()
        tg_y = self.winfo_y() + self.winfo_height() + 24
        cur_x = tg_x; cur_y = tg_y; row_max_h = 0
        _WRAP_AT = 1600

        slot_comps = []
        self._collect_slot_comps(slot_items, slot_comps)

        if not slot_comps:
            # Nothing extractable → show a single placeholder
            slot_comps = [{"_is_slot_placeholder": True}]

        for comp in slot_comps:
            cid = str(uuid.uuid4())[:8]
            card = None

            if comp.get("_is_slot_placeholder"):
                card = CompCard(self.app._cf, cid, "key-value",
                                f"[{slot_name}] — no editable content", "", "", self.app,
                                width=340, height=100)
                card.elem_input = slot_name

            elif comp.get("_is_passthrough"):
                node = comp["_node"]
                lbl = comp.get("_label") or node.get("Container") or node.get("Element") or "unknown"
                display = f"[AgentRef: {lbl}]" if "AgentRef" in node else f"[{lbl}]"
                card = CompCard(self.app._cf, cid, "key-value",
                                display, "", "", self.app, width=320, height=80)
                card.elem_input = lbl
                card._tg_passthrough_node = node

            elif comp.get("_is_metrics_group"):
                kpi = comp.get("_cards", [])
                metrics_list = []
                for child in kpi:
                    kvs = [e for e in child.get("Slots", {}).get("Default", [])
                           if isinstance(e, dict) and e.get("Element") == "key-value"]
                    label = ""; field = ""; unit = ""
                    for kv in kvs:
                        cfg = kv.get("Config", {})
                        if cfg.get("LabelKey") and not label:
                            label = cfg["LabelKey"]
                    for kv in reversed(kvs):
                        inp = kv.get("Input", "")
                        if inp and " | " not in inp:
                            field = inp
                            unit = kv.get("Config", {}).get("postValueSeparator", "").strip()
                            break
                    if label or field:
                        metrics_list.append({"label": label, "field": field, "unit": unit})
                ds = kpi[0].get("Init", {}).get("DataSourcePath", "") if kpi else ""
                seg = comp.get("_segment", "")
                card = CompCard(self.app._cf, cid, "metrics",
                                seg or "Metrics", ds, f"object::{ds}Js.result" if ds else "",
                                self.app, width=max(300, 120 * max(1, len(metrics_list))), height=150)
                if metrics_list:
                    card.metrics = metrics_list
                card._tg_metrics_group = comp

            elif comp.get("_is_river_elem"):
                en = comp["_node"]
                ctype = en.get("Element") or en.get("Container", "button")
                if ctype not in RIVER_TYPES:
                    ctype = "key-value"

                if ctype == "filter-panel":
                    # Show filter-panel as a passthrough card on the canvas so the
                    # user can see and edit it.  _tg_passthrough_node preserves the
                    # original JSON for round-trip through _collapse_slot.
                    pos = en.get("Config", {}).get("Position", "")
                    attr_count = len(en.get("Config", {}).get("Attributes", []))
                    for _sec in en.get("Config", {}).get("Sections", []):
                        attr_count += len(_sec.get("Attributes", []))
                    _pos_lbl = {"left": "Left", "right": "Right", "top": "Top",
                                "none": "None"}.get(pos, pos or "Sidebar")
                    _fp_title = (f"🔎 Filter — {_pos_lbl} ({attr_count} attr)"
                                 if attr_count else f"🔎 Filter — {_pos_lbl}")
                    card = CompCard(self.app._cf, cid, "filter-panel", _fp_title,
                                    "", "", self.app, width=280, height=70)
                    card._tg_passthrough_node = en
                else:
                    title = en.get("Config", {}).get("LabelKey", ctype)
                    card = CompCard(self.app._cf, cid, ctype, title, "", "", self.app,
                                    width=260, height=100,
                                    elem_config=dict(en.get("Config") or {}),
                                    elem_input=en.get("Input", ""),
                                    elem_style=dict(en.get("Style") or {}),
                                    uid=en.get("UID", ""),
                                    events=dict(en.get("Events") or {}))

            elif comp.get("_is_native_chart"):
                node = comp["_node"]
                sm = node.get("Config", {}).get("dataMapping", {}).get("seriesMappings", [])
                ctype = (node.get("Config", {}).get("highchartsOptions", {})
                         .get("chart", {}).get("type") or
                         (sm[0].get("seriesType", "column") if sm else "column"))
                ds    = node.get("Init", {}).get("DataSourcePath", "")
                title = node.get("Config", {}).get("chartMetadata", {}).get("name", "") or ds or "Chart"
                series = self._parse_series_import(sm)
                card = CompCard(self.app._cf, cid, ctype, title, ds,
                                f"object::{ds}Js.result", self.app,
                                series=series, width=400, height=300)
                card.orig_chart_node = node
                _hc_imp = node.get("Config", {}).get("highchartsOptions", {})
                card.hc_adv = _extract_hc_adv(_hc_imp)
                _po = _hc_imp.get("plotOptions", {})
                card.chart_stacking = bool(
                    _po.get("series", {}).get("stacking")
                    or _po.get("bar", {}).get("stacking")
                    or _po.get("column", {}).get("stacking")
                )
                _lg = _hc_imp.get("legend", {})
                if _lg:
                    card.chart_legend_enabled = _lg.get("enabled", True)
                    card.chart_legend_layout  = _lg.get("layout", "horizontal")
                    card.chart_legend_valign  = _lg.get("verticalAlign", "bottom")
                    card.chart_legend_align   = _lg.get("align", "center")
                    card.chart_legend_y       = _lg.get("y", 0)

            elif comp.get("_is_grid_chart"):
                # Chart stored in designer's grid+header wrapper (from _comp_json)
                node = comp["_node"]
                inner = None
                try:
                    inner = node["Slots"]["content"][0]["Slots"]["Default"][0]
                except (KeyError, IndexError, TypeError):
                    pass
                if inner and inner.get("Container") == "chart":
                    sm = inner.get("Config", {}).get("dataMapping", {}).get("seriesMappings", [])
                    ctype = (inner.get("Config", {}).get("highchartsOptions", {})
                             .get("chart", {}).get("type") or
                             (sm[0].get("seriesType", "column") if sm else "column"))
                    ds = inner.get("Init", {}).get("DataSourcePath", "")
                    try:
                        title = node["Slots"]["header"][0]["Slots"]["Left"][0]["Config"]["LabelKey"]
                    except (KeyError, IndexError, TypeError):
                        title = ds or "Chart"
                    series = self._parse_series_import(sm)
                    card = CompCard(self.app._cf, cid, ctype, title, ds,
                                    f"object::{ds}Js.result", self.app,
                                    series=series, width=400, height=300)
                    card.orig_full_node = node  # preserve grid+header for collapse round-trip
                    if inner is not None:
                        _hc_gi = inner.get("Config", {}).get("highchartsOptions", {})
                        card.hc_adv = _extract_hc_adv(_hc_gi)
                        _po_gi = _hc_gi.get("plotOptions", {})
                        card.chart_stacking = bool(
                            _po_gi.get("series", {}).get("stacking")
                            or _po_gi.get("bar", {}).get("stacking")
                            or _po_gi.get("column", {}).get("stacking")
                        )
                        _lg_gi = _hc_gi.get("legend", {})
                        if _lg_gi:
                            card.chart_legend_enabled = _lg_gi.get("enabled", True)
                            card.chart_legend_layout  = _lg_gi.get("layout", "horizontal")
                            card.chart_legend_valign  = _lg_gi.get("verticalAlign", "bottom")
                            card.chart_legend_align   = _lg_gi.get("align", "center")
                            card.chart_legend_y       = _lg_gi.get("y", 0)
                else:
                    card = CompCard(self.app._cf, cid, "key-value",
                                    f"[grid: {node.get('Container','?')}]", "", "", self.app,
                                    width=320, height=80)
                    card._tg_passthrough_node = node

            elif comp.get("Container") == "table":
                node = comp
                title = node.get("Config", {}).get("title", "Table")
                ds    = node.get("Init", {}).get("DataSourcePath", "")
                raw_cols = node.get("Config", {}).get("Columns", [])
                cols = []
                for cn in raw_cols:
                    if _is_insights_col(cn)[0]:
                        continue
                    _pf, _pl, _pe = _parse_col_link_events(cn)
                    _title = cn.get("Config", {}).get("LabelKey", _pf or "col")
                    cols.append({"field": _title, "title": _title, "link": _pl, "events": _pe})
                _ins_pc, _ins_f_pc, _ins_a_pc = _detect_table_insights(node)
                _hf  = node.get("_has_footer", False)
                _hcb = node.get("Config", {}).get("SelectionConfig", {}).get("ShowSelection", False)
                _hms = node.get("Config", {}).get("SelectionConfig", {}).get("SupportMultiSelect", True)
                _hag = "AgenticActions" in node.get("Slots", {})
                _aid = ""; _aargs = []; _aquestion = ""
                if _hag:
                    try:
                        _ag_cfg    = (node["Slots"]["AgenticActions"][0]["Slots"]["Menu"][0]
                                      ["Emitters"]["click"]["actions"][0]["config"])
                        _aid       = _ag_cfg.get("agentId", "")
                        _aargs     = _ag_cfg.get("actionArguments", [])
                        _aquestion = _ag_cfg.get("question", "")
                    except Exception:
                        pass
                # Extract table-specific color properties from Style
                _so = node.get("Style", {})
                _table_style = {
                    "textColor": _so.get("textColor", ""),
                    "rowEvenBackgroundColor": _so.get("rowEvenBackgroundColor", ""),
                    "rowOddBackgroundColor": _so.get("rowOddBackgroundColor", ""),
                    "headerBackgroundColor": _so.get("headerBackgroundColor", ""),
                    "tableBorderColor": _so.get("tableBorderColor", ""),
                    "hoverBackgroundColor": _so.get("hoverBackgroundColor", "")
                }
                card = CompCard(self.app._cf, cid, "table", title, ds,
                                f"object::{ds}Js.result", self.app,
                                cols=cols, width=800, height=300, css_width="100%",
                                has_insights=_ins_pc, insights_field=_ins_f_pc,
                                insights_agent_id=_ins_a_pc,
                                has_footer=_hf, has_checkboxes=_hcb,
                                has_multiselect=_hms, has_agentic=_hag,
                                agent_id=_aid, agent_args=_aargs)
                card.agent_question = _aquestion
                card.table_style = _table_style
                card.orig_full_node = node

            if card is None:
                continue

            # Apply segment info from _collect_slot_comps tagging
            seg = comp.get("_segment", "")
            if seg:
                card.segment = seg
                if seg not in self.app.segment_dirs:
                    _ncss = comp.get("_seg_css_full", {})
                    self.app.segment_dirs[seg] = {
                        "direction":    comp.get("_seg_dir", "row"),
                        "gap":          comp.get("_seg_gap", "0rem"),
                        "section_name": seg,
                        "padding":      self.app._parse_css_padding_dict(
                                            comp.get("_seg_pad", "")),
                        "extra_css":    {k: v for k, v in _ncss.items()
                                         if k not in {"flexDirection","gap","padding",
                                                       "flex","backgroundColor","width",
                                                       "boxSizing","minHeight","height"}},
                    }
                    if "1" in str(comp.get("_seg_flex", "")):
                        self.app.segment_dirs[seg]["expand_fill"] = True

            cw = card.winfo_reqwidth(); ch = card.winfo_reqheight()
            if cur_x > tg_x and cur_x + cw > tg_x + _WRAP_AT:
                cur_x = tg_x; cur_y += row_max_h + 16; row_max_h = 0
            card.place(x=cur_x, y=cur_y)
            card.bind("<Button-1>", lambda e, cd=card: self.app._sel_card(cd, e))
            self.app.cards[cid] = card
            card._tg_parent = self.cid
            card._tg_slot   = slot_name
            cur_x += cw + 16
            row_max_h = max(row_max_h, ch)

    def _parse_series_import(self, sm):
        """Parse series mappings from import JSON."""
        series = []
        for s in sm:
            fm = s.get("fieldMappings", {})
            x_field = next((k for k, v in fm.items() if v == "name"), None)
            fm_inverted = x_field is None
            if x_field is None: x_field = fm.get("name", "")
            y_field = next((k for k, v in fm.items() if v == "y"), None)
            if y_field is None: y_field = fm.get("y", "")
            opts = s.get("staticOptions", {})
            color = opts.get("color", "colorByPoint" if opts.get("colorByPoint") else "")
            series.append({"name": opts.get("name", "Series"), "x_field": x_field,
                           "y_field": y_field, "color": color, "fm_inverted": fm_inverted})
        return series

    def _add_cards_to_slot(self, slot_name):
        """Open picker to assign existing canvas cards / segments into a tab slot."""
        TabSlotPickerDialog(self.app, self, slot_name)

    def _eject_slot(self, slot_name):
        """Eject slot: keep expanded cards as standalone canvas cards, clear slot content."""
        # Detach all cards owned by this slot from the tab group
        for cid, card in list(self.app.cards.items()):
            if getattr(card, '_tg_parent', None) == self.cid and \
               getattr(card, '_tg_slot', None) == slot_name:
                card._tg_parent = None
                card._tg_slot   = None
        # Clear the slot content so it's empty in the export
        if self.orig_full_node is not None:
            self.orig_full_node.setdefault("Slots", {})[slot_name] = []
        self.unmarried_slot = None
        self.rebuild()

    def _slot_content_summary(self, slot_name):
        """Return a short human-readable description of a slot's current content."""
        if not self.orig_full_node:
            return "empty"
        items = self.orig_full_node.get("Slots", {}).get(slot_name, [])
        comps = []
        self._collect_slot_comps(items if isinstance(items, list) else [items], comps)
        if not comps:
            return "empty"
        count = len(comps)
        return f"{count} component{'s' if count != 1 else ''}"

    def _collapse_slot(self, slot_name):
        """Collapse a slot: collect modified card JSON, update orig_full_node, remove cards.

        Filter-panel nodes are now shown as passthrough cards on the canvas so they
        are included in slot_cards and round-trip via _tg_passthrough_node.
        They are always written first in the slot JSON so the structure is preserved.
        Segment-group flex wrappers are reconstructed so SectionName is not lost.
        """
        to_remove = []
        slot_cards = []
        for cid, card in sorted(self.app.cards.items(),
                                key=lambda kv: (kv[1].winfo_y(), kv[1].winfo_x())):
            if (getattr(card, '_tg_parent', None) == self.cid
                    and getattr(card, '_tg_slot', None) == slot_name):
                to_remove.append(cid)
                slot_cards.append(card)

        def _card_json(card):
            pt = getattr(card, '_tg_passthrough_node', None)
            mg = getattr(card, '_tg_metrics_group', None)
            if pt is not None:
                return pt
            if mg is not None:
                return CompCard._rebuild_metrics_group_node(card, mg)
            if getattr(card, 'ctype', '') == "filter-panel":
                # Fresh filter-panel (no passthrough) — build from UI filter rows so
                # Attributes are populated from self.app.filters, not an empty skeleton.
                _fp_elem, _ = self.app._build_filter_element()
                _fp_pos = self.app.filter_pos.get() or "left"
                _fp_elem.setdefault("Config", {})["Position"] = _fp_pos
                return _fp_elem
            return self.app._comp_json(card)

        def _is_fp(card):
            pt = getattr(card, '_tg_passthrough_node', None)
            if pt is not None:
                return (pt.get("Element") == "filter-panel"
                        or pt.get("Container") == "filter-panel")
            return getattr(card, 'ctype', '') == "filter-panel"

        # Separate filter-panel cards from content cards so FP always goes first.
        fp_cards      = [c for c in slot_cards if _is_fp(c)]
        content_cards = [c for c in slot_cards if not _is_fp(c)]

        # ── Rebuild content cards, grouping segments into flex wrappers ──────
        rebuilt = []
        seen_segs = set()
        seg_card_map = {}
        for card in content_cards:
            seg = getattr(card, 'segment', '')
            if seg:
                seg_card_map.setdefault(seg, []).append(card)

        for card in content_cards:
            seg = getattr(card, 'segment', '')
            if seg and seg not in seen_segs:
                seen_segs.add(seg)
                seg_dir = self.app.segment_dirs.get(seg, {})
                seg_json = [_card_json(sc) for sc in seg_card_map[seg]]
                if seg_dir.get("container_type") == "header-action":
                    # Preserve header-action container type instead of wrapping as flex
                    _ha_cfg    = seg_dir.get("config") or {"SectionName": seg_dir.get("section_name", seg)}
                    _ha_sty    = seg_dir.get("style")  or {"css": {}}
                    _ha_events = seg_dir.get("events")
                    _ha_node   = {
                        "Container": "header-action",
                        "Config":    _ha_cfg,
                        "Style":     _ha_sty,
                        "Slots":     {"Left": seg_json},
                    }
                    if _ha_events:
                        _ha_node["Events"] = _ha_events
                    rebuilt.append(_ha_node)
                else:
                    _seg_css_out = {
                        "flexDirection": seg_dir.get("direction", "row"),
                        "gap":           seg_dir.get("gap", "0rem"),
                    }
                    _seg_css_out.update(seg_dir.get("extra_css", {}))
                    rebuilt.append({
                        "Container": "flex",
                        "Config":    {"SectionName": seg},
                        "Style":     {"css": _seg_css_out},
                        "Slots":     {"Default": seg_json},
                    })
            elif seg:
                pass  # already emitted as part of its segment group above
            else:
                rebuilt.append(_card_json(card))

        # ── Write back: filter-panels first, then content ──────────────────
        final = [_card_json(c) for c in fp_cards] + rebuilt
        # Restore outer Init wrapper if the slot had one before expansion
        _slot_ow = getattr(self, '_slot_outer_wrappers', {}).get(slot_name)
        if _slot_ow and final:
            _ow_node = copy.deepcopy(_slot_ow)
            _ow_node.setdefault("Slots", {})["Default"] = final
            final = [_ow_node]
        if self.orig_full_node is not None and final:
            self.orig_full_node.setdefault("Slots", {})[slot_name] = final

        for cid in to_remove:
            self.app.remove_comp(cid)

    @staticmethod
    def _rebuild_metrics_group_node(card, orig_group):
        """Rebuild a slot metrics-group node from the current card.metrics state."""
        orig_kpi = orig_group.get("_cards", [])
        new_kpi = []
        for i, m in enumerate(card.metrics or []):
            if i < len(orig_kpi):
                tile = copy.deepcopy(orig_kpi[i])
            else:
                ds = card.ds or ""
                tile = {"Container": "card",
                        "Init": {"Type": "value-array", "DataSourcePath": ds},
                        "Style": {}, "Slots": {"Default": []}}
            kvs = [e for e in tile.get("Slots", {}).get("Default", [])
                   if isinstance(e, dict) and e.get("Element") == "key-value"]
            for kv in kvs:
                if kv.get("Config", {}).get("LabelKey"):
                    kv.setdefault("Config", {})["LabelKey"] = m.get("label", "")
                elif kv.get("Input") is not None:
                    kv["Input"] = m.get("field", "")
                    if m.get("unit"):
                        kv.setdefault("Config", {})["postValueSeparator"] = f" {m['unit']}"
            new_kpi.append(tile)
        orig_cfg = orig_group.get("_config", {})
        result = {"Container": "flex",
                  "Style": orig_group.get("_style", {}),
                  "Slots": {"Default": new_kpi}}
        if orig_cfg:
            result["Config"] = orig_cfg
        return result

    def _start_resize(self, event):
        self.start_x = event.x_root; self.start_y = event.y_root; self.start_w = self.winfo_width(); self.start_h = self.winfo_height()

    def _do_resize(self, event):
        new_w = max(1, self.start_w + (event.x_root - self.start_x)); new_h = max(1, self.start_h + (event.y_root - self.start_y))
        self.config(width=new_w, height=new_h); self._preview()

    def _stop_resize(self, event):
        self._preview()
        self._sync_dimensions()
        self.app._debug_log_event("CARD_RESIZE",
            f"Resized {self.ctype} '{self.title}' → {self.css_width} x {self.css_height}")
        if self.segment:
            self.app._recalc_seg_gap(self.segment)
            self.app._draw_gap_overlay()
        self.app.after(120, self.app._draw_grid)

    def _sync_dimensions(self):
        self.css_width = f"{self.winfo_width()}px"
        self.css_height = f"{self.winfo_height()}px"
        self.dim_label.config(text=f"Scale: {self.css_width} x {self.css_height}")

    def _preview(self, event=None):
        self.cv.delete("drawing"); W = self.winfo_width() - 12; H = self.winfo_height() - 40
        if W <= 0 or H <= 0: return
        
        if self.ctype == "metrics":
            tiles = self.metrics if self.metrics else [{"label": "Metric", "field": "FIELD", "unit": ""}]
            n = len(tiles); cols_n = min(n, 4); tile_w = max(60, (W-20)//(cols_n or 1)); tile_h = 60
            for i, m in enumerate(tiles):
                col_i = i % cols_n; row_i = i // cols_n
                x0 = 10 + col_i * (tile_w + 6); y0 = 36 + row_i * (tile_h + 8)
                x1 = x0 + tile_w; y1 = y0 + tile_h
                self.cv.create_rectangle(x0, y0, x1, y1, fill=CARD_BG, outline=BORDER, tags="drawing")
                unit = f" {m['unit']}" if m.get("unit") else ""
                self.cv.create_text((x0+x1)//2, y0+14, text=m["label"], fill=MUTED, font=("Helvetica", 8), tags="drawing")
                self.cv.create_text((x0+x1)//2, y0+36, text=f"—{unit}", fill=BLUE, font=("Helvetica", 11, "bold"), tags="drawing")
            self.cv.create_text(W//2, 20, text=self.title, fill=DARK, font=("Helvetica", 9, "bold"), tags="drawing")
        elif self.ctype == "table":
            for i in range(min(10, H//30)):
                y = i * 30 + 30; self.cv.create_rectangle(10, y, W-10, y+28, fill=HDR_BG if i==0 else CARD_BG, outline=BORDER, tags="drawing")
            if self.columns:
                col_w = (W-20) / max(1, len(self.columns))
                for i, c in enumerate(self.columns): self.cv.create_text(10 + i*col_w + col_w/2, 44, text=c['title'], font=("Helvetica", 9, "bold"), fill=DARK, tags="drawing")
        elif self.ctype == "pie":
            segs=[130,90,70,70]; cols=[GREEN,RED,ORANGE,BLUE]
            r=min(W,H)//2-14; cx=W//2; cy=H//2; st=0
            for s,c in zip(segs,cols): self.cv.create_arc(cx-r,cy-r,cx+r,cy+r,start=st,extent=s, fill=c,outline="white",width=2, tags="drawing"); st+=s
        elif self.ctype in ("bar","column"):
            vals=[70,110,45,90,60]; mv=max(vals); bw=max(8,(W-60)//len(vals)-6); ox=40; base=H-16
            for i,v in enumerate(vals):
                bh=int(v/mv*(H-40)); x0=ox+i*(bw+6); tc=ACCENT if self.ctype=="bar" else ORANGE
                self.cv.create_rectangle(x0,base-bh,x0+bw,base,fill=tc,outline="white", tags="drawing")
            self.cv.create_line(36,20,36,base,fill=BORDER, tags="drawing"); self.cv.create_line(36,base,W-10,base,fill=BORDER, tags="drawing")
        elif self.ctype == "line":
            pts1=[30,H-30, 80,H-60, 130,H-40, 180,H-80, W-20,H-50]
            self.cv.create_line(pts1,fill=ACCENT,width=3,smooth=True, tags="drawing")
            for i in range(0,len(pts1),2): self.cv.create_oval(pts1[i]-4,pts1[i+1]-4,pts1[i]+4,pts1[i+1]+4,fill=ACCENT,outline="white", tags="drawing")
            self.cv.create_line(26,20,26,H-20,fill=BORDER, tags="drawing"); self.cv.create_line(26,H-20,W-10,H-20,fill=BORDER, tags="drawing")
        elif self.ctype in ("spline", "areaspline"):
            pts1=[30,H-30, 80,H-55, 130,H-42, 180,H-78, W-20,H-48]
            if self.ctype == "areaspline":
                pts_poly = [26,H-20] + pts1 + [W-20,H-20]
                self.cv.create_polygon(pts_poly, fill="#C7D2FE", outline="", smooth=True, tags="drawing")
            self.cv.create_line(pts1,fill=PURPLE,width=3,smooth=True, tags="drawing")
            self.cv.create_line(26,20,26,H-20,fill=BORDER, tags="drawing"); self.cv.create_line(26,H-20,W-10,H-20,fill=BORDER, tags="drawing")
        elif self.ctype == "area":
            pts1=[30,H-30, 80,H-55, 130,H-42, 180,H-78, W-20,H-48]
            pts_poly = [26,H-20] + pts1 + [W-20,H-20]
            self.cv.create_polygon(pts_poly, fill="#BAE6FD", outline="", smooth=True, tags="drawing")
            self.cv.create_line(pts1,fill="#0EA5E9",width=2,smooth=True, tags="drawing")
            self.cv.create_line(26,20,26,H-20,fill=BORDER, tags="drawing"); self.cv.create_line(26,H-20,W-10,H-20,fill=BORDER, tags="drawing")
        elif self.ctype == "scatter":
            import random as _rnd; _rnd.seed(42)
            self.cv.create_line(26,20,26,H-20,fill=BORDER, tags="drawing"); self.cv.create_line(26,H-20,W-10,H-20,fill=BORDER, tags="drawing")
            for _ in range(16):
                px=_rnd.randint(34,W-14); py=_rnd.randint(24,H-24)
                self.cv.create_oval(px-5,py-5,px+5,py+5,fill=ORANGE,outline="white",width=1,tags="drawing")
        elif self.ctype == "sunburst":
            import math as _m
            cx2=W//2; cy2=H//2
            colors=["#2563EB","#EA580C","#16A34A","#9333EA","#DC2626","#0891B2"]
            r_inner=min(W,H)//6; r_outer=min(W,H)//2-10
            slices=[(90,90),(180,60),(240,75),(315,45),(0,90)]
            for i,(st,ext) in enumerate(slices):
                self.cv.create_arc(cx2-r_outer,cy2-r_outer,cx2+r_outer,cy2+r_outer,start=st,extent=ext,fill=colors[i%len(colors)],outline="white",width=2,tags="drawing")
            self.cv.create_oval(cx2-r_inner,cy2-r_inner,cx2+r_inner,cy2+r_inner,fill="white",outline="white",tags="drawing")
        elif self.ctype == "waterfall":
            vals=[40,25,-15,35,-20,55]; base=H-20; mx=max(abs(v) for v in vals) or 1
            bw=max(8,(W-40)//(len(vals) or 1)-4); x0=28; cur=0
            for v in vals:
                bh=int(abs(v)/mx*(H-50)); fill2=GREEN if v>0 else RED
                y_top=base-(cur+max(v,0))*bh//max(abs(v),1); y_bot=base-cur*bh//max(abs(v),1) if v>0 else base-(cur+v)*bh//max(abs(v),1)
                yb=base-int((cur+(v if v>0 else 0))/mx*(H-50))
                yt=base-int((cur+v if v>0 else cur)/mx*(H-50))
                self.cv.create_rectangle(x0,min(yb,yt),x0+bw,base,fill=fill2,outline="white",tags="drawing")
                x0+=bw+4; cur+=v
            self.cv.create_line(26,20,26,base,fill=BORDER,tags="drawing"); self.cv.create_line(26,base,W-10,base,fill=BORDER,tags="drawing")
        # ── UIRiver element previews ────────────────────────────────────────────
        elif self.ctype == "button":
            bw=min(140,W-20); bh=34; bx=W//2-bw//2; by=H//2-bh//2
            self.cv.create_rectangle(bx,by,bx+bw,by+bh,fill=BLUE,outline="",tags="drawing")
            self.cv.create_text(W//2,H//2,text=self.elem_config.get("LabelKey","Click Me"),fill="white",font=("Helvetica",10,"bold"),tags="drawing")
        elif self.ctype == "actions-popover":
            bw=min(140,W-20); bh=34; bx=W//2-bw//2; by=H//2-bh//2
            self.cv.create_rectangle(bx,by,bx+bw,by+bh,fill="#475569",outline="",tags="drawing")
            lbl=self.elem_config.get("LabelKey","Export")
            self.cv.create_text(W//2-8,H//2,text=lbl,fill="white",font=("Helvetica",10,"bold"),tags="drawing")
            self.cv.create_text(W//2+len(lbl)*4+4,H//2+1,text="▾",fill="white",font=("Helvetica",9),tags="drawing")
        elif self.ctype == "pill":
            txt=self.elem_input or "VALUE"; bg2=self.elem_style.get("pillBackgroundColor","#E0F2FE"); tc2=self.elem_style.get("pillTextColor","#0369A1")
            tw=max(80,len(txt)*9+20); th=26; tx=W//2-tw//2; ty=H//2-th//2
            self.cv.create_rectangle(tx,ty,tx+tw,ty+th,fill=bg2,outline=bg2,tags="drawing")
            self.cv.create_text(W//2,H//2,text=txt,fill=tc2,font=("Helvetica",9,"bold"),tags="drawing")
        elif self.ctype == "key-value":
            lbl2=self.elem_config.get("LabelKey","Label"); inp2=self.elem_input or "value"
            self.cv.create_text(12,H//2-14,text=lbl2+":",anchor="w",fill=MUTED,font=("Helvetica",9),tags="drawing")
            self.cv.create_text(12,H//2+8,text=inp2,anchor="w",fill=DARK,font=("Helvetica",10,"bold"),tags="drawing")
        elif self.ctype == "progress-bar":
            self.cv.create_rectangle(16,H//2-12,W-16,H//2+12,fill="#1E293B",outline=BORDER,tags="drawing")
            self.cv.create_rectangle(16,H//2-12,16+int((W-32)*0.65),H//2+12,fill=ORANGE,outline="",tags="drawing")
            self.cv.create_text(W//2,H//2,text="65%",fill="white",font=("Helvetica",9,"bold"),tags="drawing")
            self.cv.create_text(W//2,H//2-24,text=self.elem_config.get("LabelKey","Progress"),fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "text":
            self.cv.create_text(W//2,H//2,text=self.elem_config.get("LabelKey","Text Display"),fill=DARK,font=("Helvetica",11),tags="drawing")
        elif self.ctype == "banner":
            bc={"info":"#EFF6FF","warning":"#FFFBEB","error":"#FEF2F2","success":"#F0FDF4"}.get(self.elem_config.get("type","info"),"#EFF6FF")
            self.cv.create_rectangle(8,H//2-22,W-8,H//2+22,fill=bc,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2,H//2,text=self.elem_config.get("LabelKey","Banner Message"),fill=DARK,font=("Helvetica",10),tags="drawing")
        elif self.ctype == "card":
            self.cv.create_rectangle(8,8,W-8,H-8,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_rectangle(8,8,W-8,38,fill=HDR_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2,23,text=self.elem_config.get("title","Card Title"),fill=DARK,font=("Helvetica",10,"bold"),tags="drawing")
            self.cv.create_text(W//2,(38+H-8)//2,text="[ content slots ]",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype in ("input","combobox","search"):
            self.cv.create_rectangle(16,H//2-18,W-16,H//2+18,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(26,H//2,text=self.elem_config.get("LabelKey","Field..."),anchor="w",fill=MUTED,font=("Helvetica",10),tags="drawing")
            if self.ctype=="combobox": self.cv.create_text(W-26,H//2,text="▼",anchor="e",fill=MUTED,font=("Helvetica",9),tags="drawing")
            elif self.ctype=="search": self.cv.create_text(W-26,H//2,text="🔍",anchor="e",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "toggle-button":
            self.cv.create_text(W//2,H//2-26,text=self.elem_config.get("LabelKey","Toggle"),fill=DARK,font=("Helvetica",9),tags="drawing")
            self.cv.create_rectangle(W//2-28,H//2-12,W//2+28,H//2+12,fill="#1E293B",outline=BORDER,tags="drawing")
            self.cv.create_oval(W//2-26,H//2-10,W//2-2,H//2+10,fill="white",outline=BORDER,tags="drawing")
        elif self.ctype == "segment-panel":
            _sp_ec = self.elem_config or {}
            _sp_filter_on = _sp_ec.get("EnableFilter", False)
            segs = _sp_ec.get("Segments", [{"AttributeKey":"Tab 1"},{"AttributeKey":"Tab 2"}])
            sw = max(1,(W-20)//max(1,len(segs)))
            for i,s in enumerate(segs):
                x0=10+i*sw; x1=x0+sw-2
                fill2 = GREEN if _sp_filter_on else (ACCENT if i==0 else HDR_BG)
                tc3 = "white" if (i==0 or _sp_filter_on) else DARK
                self.cv.create_rectangle(x0,H//2-16,x1,H//2+16,fill=fill2,outline=BORDER,tags="drawing")
                lbl_sp = s.get("AttributeKey", s.get("LabelKey", f"Tab {i+1}"))
                self.cv.create_text((x0+x1)//2,H//2,text=lbl_sp,fill=tc3,font=("Helvetica",9),tags="drawing")
            if _sp_filter_on:
                _fname = _sp_ec.get("Name","")
                _fph   = _sp_ec.get("__placeholder_label","")
                _label = _fph or (_fname and f"Filter: {_fname}") or "Filter Mode"
                self.cv.create_text(W//2,H//2-22,text=_label,
                                    fill=GREEN,font=("Helvetica",7,"bold"),tags="drawing")
        elif self.ctype == "tab-group":
            orig = getattr(self, "orig_full_node", None)
            if orig:
                tabs_cfg = orig.get("Config", {}).get("Tabs", [])
                slots    = orig.get("Slots", {})
                if tabs_cfg:
                    tab_entries = [(t.get("Name", t.get("LabelKey", f"Tab {i+1}")),
                                    t.get("LabelKey", t.get("Name", f"Tab {i+1}")))
                                   for i, t in enumerate(tabs_cfg)]
                else:
                    tab_entries = [(k, k) for k in slots.keys()]
            else:
                # No tabs defined yet — show setup hint
                self.cv.create_rectangle(8, 8, W-8, H-8, fill="#FFF7ED", outline="#FED7AA", tags="drawing")
                self.cv.create_text(W//2, H//2-12, text="📂 Tab Group",
                                    fill="#C2410C", font=("Helvetica", 10, "bold"), tags="drawing")
                self.cv.create_text(W//2, H//2+8, text="Click ✎ to add tabs, then use ＋ to assign layouts",
                                    fill="#EA580C", font=("Helvetica", 8), tags="drawing")
                return
            n = max(1, len(tab_entries)); tw = max(30, (W - 20) // n)
            for i, (slot_key, lbl3) in enumerate(tab_entries):
                x0 = 10 + i * tw; x1 = x0 + tw - 2
                is_um = (self.unmarried_slot == slot_key)
                fill3 = "#DCFCE7" if is_um else (CARD_BG if i == 0 else HDR_BG)
                self.cv.create_rectangle(x0, 8, x1, 34, fill=fill3, outline=BORDER, tags="drawing")
                disp = lbl3[:9]+"…" if len(lbl3) > 10 else lbl3
                fc3 = "#15803D" if is_um else DARK
                self.cv.create_text((x0+x1)//2, 21, text=disp, fill=fc3,
                                    font=("Helvetica", 8, "bold" if is_um else "normal"), tags="drawing")
            self.cv.create_rectangle(8, 34, W-8, H-8, fill=CARD_BG, outline=BORDER, tags="drawing")
            if self.unmarried_slot:
                status = f"✏  editing: {self.unmarried_slot}"
                self.cv.create_text(W//2, (34+H-8)//2, text=status, fill="#15803D",
                                    font=("Helvetica", 9, "bold"), tags="drawing")
            elif orig:
                # Show content summary for each slot
                summary_lines = []
                for slot_key, _ in tab_entries:
                    items = slots.get(slot_key, [])
                    comps = []
                    self._collect_slot_comps(items if isinstance(items, list) else [items], comps)
                    if comps:
                        types = []
                        for c in comps:
                            if c.get("_is_native_chart") or (isinstance(c, dict) and c.get("Container") == "chart"):
                                types.append("chart")
                            elif isinstance(c, dict) and c.get("Container") == "table":
                                types.append("table")
                            elif c.get("_is_metrics_group"):
                                types.append("metrics")
                            elif c.get("_is_passthrough"):
                                types.append("agent")
                            elif c.get("_is_river_elem"):
                                types.append(c["_node"].get("Container") or c["_node"].get("Element", "?"))
                            elif isinstance(c, dict) and c.get("Container") == "grid":
                                types.append("chart")
                        ct = Counter(types)
                        summary_lines.append(f"{slot_key}: " + ", ".join(f"{v}×{k}" for k,v in ct.items()))
                    else:
                        summary_lines.append(f"{slot_key}: —")
                body_y0 = 38; line_h = min(18, max(12, (H - 46) // max(1, len(summary_lines))))
                for li, line in enumerate(summary_lines[:max(1, (H-46)//14)]):
                    self.cv.create_text(14, body_y0 + li * line_h, text=line, anchor="w",
                                        fill=MUTED, font=("Courier", 8), tags="drawing")
            else:
                self.cv.create_text(W//2, (34+H-8)//2, text="[ tab content ]",
                                    fill=MUTED, font=("Helvetica", 9), tags="drawing")
        elif self.ctype == "textarea":
            self.cv.create_rectangle(14,H//2-30,W-14,H//2+30,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(20,H//2-18,text=self.elem_config.get("LabelKey","Text Area")+"...",anchor="w",fill=MUTED,font=("Helvetica",9),tags="drawing")
            for dy in (-4,6,16): self.cv.create_line(20,H//2+dy,W-24,H//2+dy,fill="#1E293B",tags="drawing")
        elif self.ctype == "checkbox":
            bx=W//2-50; by=H//2-10
            self.cv.create_rectangle(bx,by,bx+20,by+20,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(bx+26,H//2,text=self.elem_config.get("LabelKey","Option"),anchor="w",fill=DARK,font=("Helvetica",10),tags="drawing")
        elif self.ctype == "dropdown":
            self.cv.create_rectangle(14,H//2-16,W-14,H//2+16,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(20,H//2,text=self.elem_config.get("LabelKey","Select..."),anchor="w",fill=MUTED,font=("Helvetica",10),tags="drawing")
            self.cv.create_text(W-22,H//2,text="\u25bc",anchor="e",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "date-select":
            self.cv.create_rectangle(14,H//2-16,W-14,H//2+16,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(20,H//2,text=self.elem_config.get("LabelKey","MM/DD/YYYY"),anchor="w",fill=MUTED,font=("Helvetica",10),tags="drawing")
            self.cv.create_text(W-22,H//2,text="[cal]",anchor="e",fill=PURPLE,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "numeric-stepper":
            self.cv.create_rectangle(W//2-40,H//2-16,W//2+40,H//2+16,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2,H//2,text="0",fill=DARK,font=("Helvetica",12,"bold"),tags="drawing")
            self.cv.create_rectangle(W//2-38,H//2-14,W//2-16,H//2+14,fill=HDR_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2-27,H//2,text="\u2212",fill=DARK,font=("Helvetica",11),tags="drawing")
            self.cv.create_rectangle(W//2+16,H//2-14,W//2+38,H//2+14,fill=HDR_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2+27,H//2,text="+",fill=DARK,font=("Helvetica",11),tags="drawing")
        elif self.ctype == "currency-input":
            self.cv.create_rectangle(14,H//2-16,W-14,H//2+16,fill=CARD_BG,outline=BORDER,tags="drawing")
            self.cv.create_rectangle(14,H//2-16,36,H//2+16,fill=HDR_BG,outline="",tags="drawing")
            self.cv.create_text(25,H//2,text="$",fill=GREEN,font=("Helvetica",11,"bold"),tags="drawing")
            self.cv.create_text(44,H//2,text="0.00",anchor="w",fill=MUTED,font=("Helvetica",10),tags="drawing")
        elif self.ctype == "value":
            self.cv.create_text(W//2,H//2,text=self.elem_input or "FIELD_VALUE",fill=DARK,font=("Helvetica",14,"bold"),tags="drawing")
        elif self.ctype == "value-unit":
            unit=self.elem_config.get("unit","kg")
            self.cv.create_text(W//2-10,H//2,text="123",anchor="e",fill=DARK,font=("Helvetica",14,"bold"),tags="drawing")
            self.cv.create_text(W//2-8,H//2+4,text=unit,anchor="w",fill=MUTED,font=("Helvetica",10),tags="drawing")
        elif self.ctype == "icon":
            self.cv.create_text(W//2,H//2,text="\u2139",fill=ACCENT,font=("Helvetica",28),tags="drawing")
            self.cv.create_text(W//2,H//2+24,text=self.elem_config.get("icon","info"),fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "message":
            self.cv.create_rectangle(10,H//2-20,W-10,H//2+20,fill="#EFF6FF",outline="#BFDBFE",tags="drawing")
            self.cv.create_text(W//2,H//2,text=self.elem_config.get("LabelKey","Message text"),fill=ACCENT,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "currency-format":
            self.cv.create_text(W//2,H//2,text="$1,234.56",fill=GREEN,font=("Helvetica",14,"bold"),tags="drawing")
            self.cv.create_text(W//2,H//2+18,text=self.elem_input or "AMOUNT_FIELD",fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "key-value-detail":
            lbl2=self.elem_config.get("LabelKey","Detail Label"); inp2=self.elem_input or "value"
            self.cv.create_text(12,H//2-18,text=lbl2+":",anchor="w",fill=MUTED,font=("Helvetica",9),tags="drawing")
            self.cv.create_text(12,H//2+2,text=inp2,anchor="w",fill=DARK,font=("Helvetica",10,"bold"),tags="drawing")
            self.cv.create_text(W-18,H//2-6,text="\u25be",anchor="e",fill=MUTED,font=("Helvetica",10),tags="drawing")
        elif self.ctype == "button-icon":
            r=22; cx2=W//2; cy2=H//2
            self.cv.create_oval(cx2-r,cy2-r,cx2+r,cy2+r,fill=BLUE,outline="",tags="drawing")
            self.cv.create_text(cx2,cy2,text="\u270e",fill="white",font=("Helvetica",14),tags="drawing")
        elif self.ctype == "action-button":
            bw=min(150,W-20); bh=34; bx=W//2-bw//2; by=H//2-bh//2
            self.cv.create_rectangle(bx,by,bx+bw,by+bh,fill=ORANGE,outline="",tags="drawing")
            self.cv.create_text(W//2,H//2,text="\u26a1 "+self.elem_config.get("LabelKey","Action"),fill="white",font=("Helvetica",9,"bold"),tags="drawing")
        elif self.ctype == "link":
            lbl4=self.elem_config.get("LabelKey","Click Here")
            self.cv.create_text(W//2,H//2,text=lbl4,fill=ACCENT,font=("Helvetica",10,"underline"),tags="drawing")
        elif self.ctype == "related-link":
            lbl5=self.elem_config.get("LabelKey","View Related")
            self.cv.create_text(W//2,H//2,text=lbl5+" \u2197",fill=PURPLE,font=("Helvetica",10,"underline"),tags="drawing")
        elif self.ctype == "quick-filter":
            chips=[("All",True),("Active",False),("Done",False)]
            tw2=(W-20)//len(chips); cx3=10
            for lbl6,sel2 in chips:
                fill4=ACCENT if sel2 else HDR_BG; tc4="white" if sel2 else DARK
                self.cv.create_rectangle(cx3,H//2-12,cx3+tw2-4,H//2+12,fill=fill4,outline=BORDER,tags="drawing")
                self.cv.create_text(cx3+tw2//2-2,H//2,text=lbl6,fill=tc4,font=("Helvetica",8),tags="drawing")
                cx3+=tw2
        elif self.ctype == "filter-panel":
            self.cv.create_text(W//2,H//2-16,text=">> Filter Panel",fill=DARK,font=("Helvetica",10,"bold"),tags="drawing")
            self.cv.create_rectangle(16,H//2-2,W-16,H//2+16,fill=HDR_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(W//2,H//2+7,text="[ attributes ]",fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "accordion":
            for i,lbl7 in enumerate(["Section 1","Section 2"]):
                y7=H//4+i*(H//3)
                self.cv.create_rectangle(8,y7,W-8,y7+26,fill=HDR_BG,outline=BORDER,tags="drawing")
                self.cv.create_text(18,y7+13,text="\u25b8 "+lbl7,anchor="w",fill=DARK,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "expandable":
            self.cv.create_rectangle(8,12,W-8,40,fill=HDR_BG,outline=BORDER,tags="drawing")
            self.cv.create_text(18,26,text="\u25b8 "+self.elem_config.get("title","Expandable Section"),anchor="w",fill=DARK,font=("Helvetica",9),tags="drawing")
            self.cv.create_rectangle(8,40,W-8,H-8,fill="#F8FAFC",outline=BORDER,tags="drawing")
            self.cv.create_text(W//2,(40+H-8)//2,text="[ content ]",fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "form":
            self.cv.create_rectangle(8,8,W-8,H-8,fill="#F0FDF4",outline="#86EFAC",tags="drawing")
            self.cv.create_text(W//2,22,text="[form] "+self.elem_config.get("formId","Form"),fill=GREEN,font=("Helvetica",9,"bold"),tags="drawing")
            self.cv.create_text(W//2,H//2,text="[ form fields ]",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "section":
            self.cv.create_line(8,28,W-8,28,fill=BORDER,tags="drawing")
            self.cv.create_text(14,20,text=self.elem_config.get("title","Section Title"),anchor="w",fill=DARK,font=("Helvetica",10,"bold"),tags="drawing")
            self.cv.create_text(W//2,(28+H-8)//2,text="[ slot content ]",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "list":
            for i in range(3):
                y8=16+i*28; self.cv.create_rectangle(14,y8,W-14,y8+22,fill=CARD_BG,outline=BORDER,tags="drawing")
                self.cv.create_text(20,y8+11,text=f"\u2022  Item {i+1}",anchor="w",fill=DARK,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "stack":
            for i in range(3):
                y9=12+i*36; self.cv.create_rectangle(20,y9,W-20,y9+30,fill=HDR_BG,outline=BORDER,tags="drawing")
                self.cv.create_text(W//2,y9+15,text=f"Item {i+1}",fill=MUTED,font=("Helvetica",9),tags="drawing")
        elif self.ctype == "flex":
            cols3=3; cw3=(W-20)//cols3
            for i in range(cols3):
                x0=10+i*cw3; self.cv.create_rectangle(x0,H//2-20,x0+cw3-6,H//2+20,fill=HDR_BG,outline=BORDER,tags="drawing")
                self.cv.create_text(x0+cw3//2-3,H//2,text=f"Col {i+1}",fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "grid":
            rows2=2; cols4=2; cw4=(W-20)//cols4; ch4=(H-20)//rows2
            for r in range(rows2):
                for c in range(cols4):
                    x0=10+c*cw4; y0=10+r*ch4
                    self.cv.create_rectangle(x0,y0,x0+cw4-4,y0+ch4-4,fill=HDR_BG,outline=BORDER,tags="drawing")
                    self.cv.create_text(x0+cw4//2-2,y0+ch4//2-2,text=f"{r+1},{c+1}",fill=MUTED,font=("Helvetica",8),tags="drawing")
        elif self.ctype == "carousel":
            spp=min(3, int(self.elem_config.get("slidesPerPage",3)) if self.elem_config else 3)
            sw=max(30,(W-30)//(spp or 1)); nav=self.elem_config.get("navigation",True) if self.elem_config else True
            has_frag = bool(self.elem_config.get("Fragment") if self.elem_config else False)
            for i in range(spp):
                x0=15+i*(sw+4)
                fill2 = "#E0F2FE" if has_frag else HDR_BG
                self.cv.create_rectangle(x0,22,x0+sw-2,H-14,fill=fill2,outline=BORDER,tags="drawing")
                self.cv.create_text(x0+sw//2-1,H//2-4,text=f"[{i+1}]",fill=MUTED,font=("Helvetica",8),tags="drawing")
                if has_frag:
                    frag_cont = (self.elem_config.get("Fragment") or {}).get("Container","card")
                    self.cv.create_text(x0+sw//2-1,H//2+8,text=frag_cont,fill="#0369A1",font=("Helvetica",7),tags="drawing")
                else:
                    self.cv.create_text(x0+sw//2-1,H//2+8,text="no template",fill=MUTED,font=("Helvetica",7),tags="drawing")
            if nav:
                self.cv.create_text(7,H//2,text="◄",fill=ACCENT,font=("Helvetica",10,"bold"),tags="drawing")
                self.cv.create_text(W-7,H//2,text="►",fill=ACCENT,font=("Helvetica",10,"bold"),tags="drawing")
            # "Set Template" / "Unmarry" buttons at bottom of carousel card
            has_married = bool((self.elem_config or {}).get("_married_cards"))
            btn_lbl = "📦 Change Template" if has_frag else "📦 Set Item Template"
            btn_bg  = "#0369A1" if has_frag else "#7C3AED"
            self._carousel_btn = tk.Button(
                self.cv, text=btn_lbl, bg=btn_bg, fg="black",
                font=("Helvetica", 8, "bold"), relief="flat", cursor="hand2",
                command=self._pick_carousel_fragment)
            if has_married:
                self.cv.create_window(W//2 - 52, H-8, window=self._carousel_btn, anchor="s", tags="drawing")
                self._unmarry_btn = tk.Button(
                    self.cv, text="🔓 Unmarry", bg="#DC2626", fg="black",
                    font=("Helvetica", 8, "bold"), relief="flat", cursor="hand2",
                    command=self._unmarry_carousel)
                self.cv.create_window(W//2 + 42, H-8, window=self._unmarry_btn, anchor="s", tags="drawing")
            else:
                self.cv.create_window(W//2, H-8, window=self._carousel_btn, anchor="s", tags="drawing")

    def _edit(self): EditDialog(self.app, self)

    def _pick_carousel_fragment(self):
        """Open picker to select an existing canvas card as the carousel item template."""
        CarouselFragmentPicker(self.app, self)

    def _unmarry_carousel(self):
        """Restore married cards back onto the canvas and clear the carousel template."""
        married = (self.elem_config or {}).get("_married_cards")
        if not married:
            return
        cx, cy, ch = self.winfo_x(), self.winfo_y(), self.winfo_height()
        fallback_y = cy + ch + 20
        for i, cb in enumerate(married):
            ctype = cb["ctype"]
            cid = str(uuid.uuid4())[:8]
            cw = cb["w"] or (260 if ctype in RIVER_TYPES else CARD_W)
            cht = cb["h"] or (160 if ctype in RIVER_TYPES else CARD_H)
            ox = cb.get("x", cx + i * (cw + 16))
            oy = cb.get("y", fallback_y)
            card = CompCard(self.app._cf, cid, ctype, cb["title"], cb["ds"], cb["bvar"], self.app,
                            copy.deepcopy(cb["columns"]), copy.deepcopy(cb["series"]),
                            cw, cht, cb["has_footer"], cb["css_width"], cb["css_height"],
                            cb["has_checkboxes"], cb["has_agentic"], cb["agent_id"],
                            cb.get("agent_args", []),
                            elem_config=copy.deepcopy(cb["elem_config"]),
                            elem_input=cb["elem_input"],
                            elem_style=copy.deepcopy(cb["elem_style"]),
                            has_multiselect=cb["has_multiselect"],
                            segment=cb["segment"], uid=cb["uid"],
                            events=copy.deepcopy(cb["events"]),
                            has_insights=cb.get("has_insights", False),
                            insights_field=cb.get("insights_field", "TicketsList"),
                            insights_agent_id=cb.get("insights_agent_id", ""))
            if ctype == "metrics" and cb.get("metrics"):
                card.metrics = copy.deepcopy(cb["metrics"])
            if ctype == "table":
                card.agent_question = cb.get("agent_question", "")
            card.extra_css = copy.deepcopy(cb.get("extra_css", {}))
            card.place(x=ox, y=oy)
            card.bind("<Button-1>", lambda e, cd=card: self.app._sel_card(cd, e))
            self.app.cards[cid] = card
        cfg = dict(self.elem_config)
        cfg.pop("Fragment", None)
        cfg.pop("_married_cards", None)
        self.elem_config = cfg
        self.rebuild()

    def set_selected(self, v): self.config(highlightbackground=SEL if v else BORDER, highlightthickness=3 if v else 2)
    def rebuild(self): self._build(); self._dragger = CardDrag(self)

# ─────────────────────────────────────────────────────────────────
#  CAROUSEL FRAGMENT PICKER
# ─────────────────────────────────────────────────────────────────
class CarouselFragmentPicker(tk.Toplevel):
    """
    Dialog that lists all existing canvas cards and lets the user select one
    (or a group of selected cards) to use as the carousel's Config.Fragment.
    """
    def __init__(self, app, carousel_card):
        super().__init__(app)
        self.app = app
        self.carousel_card = carousel_card
        self.title("Set Carousel Item Template")
        self.geometry("640x480")
        self.configure(bg=BG)
        self.grab_set()
        self._build()

    def _build(self):
        tk.Label(self, text="Select a container card to use as the carousel item template",
                 bg=BG, fg=DARK, font=("Helvetica", 11, "bold")).pack(pady=(14, 4), padx=20, anchor="w")

        # Current template status
        cur_frag = self.carousel_card.elem_config.get("Fragment")
        if cur_frag:
            cur_type = cur_frag.get("Container") or cur_frag.get("Element", "?")
            cur_lbl = f"Current template: {cur_type}"
            cur_col = "#0369A1"
        else:
            cur_lbl = "No item template set"
            cur_col = "#94A3B8"
        tk.Label(self, text=cur_lbl, bg=BG, fg=cur_col,
                 font=("Helvetica", 9, "italic")).pack(padx=20, anchor="w")

        info = tk.Frame(self, bg="#EFF6FF", relief="groove", bd=1)
        info.pack(fill="x", padx=20, pady=(6, 2))
        tk.Label(info, bg="#EFF6FF", fg="#1E40AF", font=("Helvetica", 8),
                 text="Tip: select a single container (card, flex, grid…) — its full JSON will become Config.Fragment.\n"
                      "You can also select multiple cards which will be wrapped in a flex/card container.",
                 justify="left", padx=8, pady=5).pack(anchor="w")

        # List frame
        lf = tk.Frame(self, bg=BG); lf.pack(fill="both", expand=True, padx=20, pady=(6, 0))
        cols = ("Type", "Title / Label", "Segment", "Width")
        self._tree = ttk.Treeview(lf, columns=cols, show="headings", height=12, selectmode="extended")
        for c, w in zip(cols, [100, 220, 110, 80]):
            self._tree.heading(c, text=c); self._tree.column(c, width=w)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self._tree.pack(side="left", fill="both", expand=True)

        # Populate — exclude the carousel card itself
        self._cid_map = {}  # tree iid -> card
        for card in sorted(self.app.cards.values(), key=lambda c: (c.winfo_y(), c.winfo_x())):
            if card.cid == self.carousel_card.cid:
                continue
            iid = self._tree.insert("", "end", values=(
                card.ctype,
                card.title or card.elem_config.get("LabelKey", ""),
                card.segment or "—",
                card.css_width,
            ))
            self._cid_map[iid] = card

        self._tree.bind("<Double-1>", lambda e: self._apply())

        # Pre-select cards that are currently selected on the canvas
        for iid, card in self._cid_map.items():
            if card.cid in self.app._sel_set:
                self._tree.selection_add(iid)

        btns = tk.Frame(self, bg=BG); btns.pack(pady=12)
        tk.Button(btns, text="Use Selected as Template", bg=BTN_OK_BG, fg=BTN_OK_FG,
                  font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self._apply).pack(side="left", padx=6)
        tk.Button(btns, text="💒 Marry (assign + remove)", bg=BTN_OK_BG, fg=BTN_OK_FG,
                  font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self._marry).pack(side="left", padx=6)
        tk.Button(btns, text="Clear Template", bg="#F87171", fg="black",
                  font=("Helvetica", 10), relief="flat", padx=14, pady=6,
                  cursor="hand2", command=self._clear).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", bg=BORDER, fg=DARK,
                  font=("Helvetica", 10), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self.destroy).pack(side="left", padx=6)

    def _get_selected_cards(self):
        sel = self._tree.selection()
        return [self._cid_map[iid] for iid in sel if iid in self._cid_map]

    def _apply(self):
        cards = self._get_selected_cards()
        if not cards:
            messagebox.showwarning("No Selection", "Please select at least one card.", parent=self)
            return
        if len(cards) == 1:
            frag_json = self.app._comp_json(cards[0])
        else:
            # Wrap multiple selections in a flex card
            frag_json = {
                "Container": "card",
                "Style": {"css": {"display": "flex", "flexDirection": "column", "gap": "8px"}},
                "Slots": {"Default": [self.app._comp_json(c) for c in cards]}
            }
        cfg = dict(self.carousel_card.elem_config)
        cfg["Fragment"] = frag_json
        self.carousel_card.elem_config = cfg
        self.carousel_card.rebuild()
        self.destroy()

    def _clear(self):
        cfg = dict(self.carousel_card.elem_config)
        cfg.pop("Fragment", None)
        cfg.pop("_married_cards", None)
        self.carousel_card.elem_config = cfg
        self.carousel_card.rebuild()
        self.destroy()

    def _marry(self):
        """Assign selected cards as Fragment AND remove them from the canvas (reversible)."""
        cards = self._get_selected_cards()
        if not cards:
            messagebox.showwarning("No Selection", "Please select at least one card.", parent=self)
            return
        if len(cards) == 1:
            frag_json = self.app._comp_json(cards[0])
        else:
            frag_json = {
                "Container": "card",
                "Style": {"css": {"display": "flex", "flexDirection": "column", "gap": "8px"}},
                "Slots": {"Default": [self.app._comp_json(c) for c in cards]}
            }
        # Store card metadata so they can be restored on unmarry
        married_meta = []
        for c in cards:
            married_meta.append({
                "ctype": c.ctype, "title": c.title, "ds": c.ds, "bvar": c.bvar,
                "css_width": c.css_width, "css_height": c.css_height,
                "extra_css": copy.deepcopy(getattr(c, "extra_css", {})),
                "has_footer": getattr(c, "has_footer", False),
                "has_checkboxes": getattr(c, "has_checkboxes", True),
                "has_multiselect": getattr(c, "has_multiselect", True),
                "has_agentic": getattr(c, "has_agentic", True),
                "agent_id": getattr(c, "agent_id", "ext-mhetroubleshoot"),
                "agent_args": list(getattr(c, "agent_args", [])),
                "agent_question": getattr(c, "agent_question", ""),
                "columns": copy.deepcopy(c.columns),
                "series": copy.deepcopy(c.series),
                "metrics": copy.deepcopy(c.metrics),
                "elem_config": copy.deepcopy(c.elem_config),
                "elem_input": c.elem_input,
                "elem_style": copy.deepcopy(c.elem_style),
                "segment": c.segment, "uid": c.uid,
                "events": copy.deepcopy(c.events),
                "w": c.winfo_width(), "h": c.winfo_height(),
                "x": c.winfo_x(), "y": c.winfo_y(),
                "has_insights": getattr(c, "has_insights", False),
                "insights_field": getattr(c, "insights_field", "TicketsList"),
                "insights_agent_id": getattr(c, "insights_agent_id", ""),
            })
        # Remove source cards from canvas
        for c in cards:
            self.app.remove_comp(c.cid)
        cfg = dict(self.carousel_card.elem_config)
        cfg["Fragment"] = frag_json
        cfg["_married_cards"] = married_meta
        self.carousel_card.elem_config = cfg
        self.carousel_card.rebuild()
        self.destroy()


# ─────────────────────────────────────────────────────────────────
#  TAB SLOT PICKER — assign canvas layouts into a tab-group slot
# ─────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────
#  ASSIGN TO TAB — card-first workflow
#  Select cards/segments first, then pick tab group + slot
# ─────────────────────────────────────────────────────────────────
class AssignToTabDialog(tk.Toplevel):
    """Card-first 'Assign to Tab Slot' dialog.

    User selects cards on canvas, clicks '🗂 → Tab'.
    Dialog shows:
      Left  — cards/segments to assign (pre-checked if selected)
      Right — pick target tab-group card + which slot to marry into
    On confirm the content is married into the slot (removed from canvas).
    """
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Assign Layout to Tab Slot")
        self.geometry("860x560")
        self.configure(bg=BG)
        self.grab_set()
        self._seg_iids  = {}   # iid → segment_name
        self._card_iids = {}   # iid → CompCard
        self._build()

    def _build(self):
        tk.Label(self, text="Assign layout to a Tab Group slot",
                 bg=BG, fg=DARK, font=("Helvetica", 12, "bold")).pack(pady=(14, 2), padx=20, anchor="w")
        tk.Label(self,
                 text="Left: choose what to assign.  Right: choose the tab group and slot.  "
                      "Married items are removed from the canvas.",
                 bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(padx=20, anchor="w")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        # ── LEFT PANE: content to assign ──────────────────────────────
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="What to assign:", bg=BG, fg=DARK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w")

        tree_frm = tk.Frame(left, bg=BG)
        tree_frm.pack(fill="both", expand=True)
        cols = ("kind", "name", "detail")
        self._tree = ttk.Treeview(tree_frm, columns=cols, show="headings",
                                   selectmode="extended", height=16)
        for col, hdr, w in [("kind","Type",90), ("name","Name",240), ("detail","Contents",160)]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w, anchor="w")
        self._tree.tag_configure("segment", background="#E0F2FE", font=("Helvetica", 10, "bold"))
        self._tree.tag_configure("card",    background="#F8FAFC")
        self._tree.tag_configure("hint",    foreground="#94A3B8")
        tsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=tsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        tsb.pack(side="left", fill="y")

        seg_dirs = getattr(self.app, 'segment_dirs', {})
        for sn in sorted(seg_dirs.keys()):
            cards_in = sorted(
                [c for c in self.app.cards.values()
                 if c.segment == sn and not getattr(c, '_tg_parent', None)
                 and c.cid not in {tc.cid for tc in self.app.cards.values() if tc.ctype == "tab-group"}],
                key=lambda c: (c.winfo_y(), c.winfo_x()))
            if not cards_in:
                continue
            detail = ", ".join(f"{v}×{k}" for k, v in Counter(c.ctype for c in cards_in).items())
            iid = self._tree.insert("", "end", tags=("segment",),
                                    values=("▸ Segment", sn, f"{len(cards_in)} cards: {detail}"))
            self._seg_iids[iid] = sn

        ungrouped = sorted(
            [c for c in self.app.cards.values()
             if not c.segment and not getattr(c, '_tg_parent', None)
             and c.ctype not in ("tab-group", "filter-panel")],
            key=lambda c: (c.winfo_y(), c.winfo_x()))
        for card in ungrouped:
            iid = self._tree.insert("", "end", tags=("card",),
                                    values=(card.ctype, card.title or card.ctype, card.ds or "—"))
            self._card_iids[iid] = card

        if not self._seg_iids and not self._card_iids:
            self._tree.insert("", "end", tags=("hint",),
                              values=("—", "(no available cards)", "—"))

        # Pre-select canvas-selected cards/segments
        for iid, card in self._card_iids.items():
            if card.cid in self.app._sel_set:
                self._tree.selection_add(iid)
        # Pre-select segments whose cards are all selected
        for iid, sn in self._seg_iids.items():
            seg_cards = [c for c in self.app.cards.values() if c.segment == sn]
            if seg_cards and all(c.cid in self.app._sel_set for c in seg_cards):
                self._tree.selection_add(iid)

        # Divider
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)

        # ── RIGHT PANE: target tab group + slot ───────────────────────
        right = tk.Frame(body, bg=BG, width=260)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Target Tab Group:", bg=BG, fg=DARK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 4))

        # Collect tab-group cards
        tg_cards = [c for c in self.app.cards.values() if c.ctype == "tab-group"]
        tg_labels = [f"📂 {c.title or 'Tab Group'}" for c in tg_cards]
        self._tg_cards = tg_cards

        if not tg_cards:
            tk.Label(right, text="No Tab Group on canvas.\nDrop a Tab Group element first.",
                     bg=BG, fg="#DC2626", font=("Helvetica", 9),
                     justify="left").pack(anchor="w", pady=8)
        else:
            self._tg_var = tk.StringVar()
            self._tg_combo = ttk.Combobox(right, textvariable=self._tg_var,
                                           values=tg_labels, state="readonly",
                                           width=28, font=("Helvetica", 10))
            self._tg_combo.current(0)
            self._tg_combo.pack(anchor="w", fill="x")
            self._tg_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_slots())

            tk.Label(right, text="Target Slot:", bg=BG, fg=DARK,
                     font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(14, 4))
            self._slot_var = tk.StringVar()
            self._slot_combo = ttk.Combobox(right, textvariable=self._slot_var,
                                             state="readonly", width=28,
                                             font=("Helvetica", 10))
            self._slot_combo.pack(anchor="w", fill="x")
            self._refresh_slots()

            tk.Label(right,
                     text="\nTip: segments appear in blue.\n"
                          "Selecting a segment assigns all\n"
                          "its cards as one group.",
                     bg=BG, fg=MUTED, font=("Helvetica", 9),
                     justify="left").pack(anchor="w", pady=(12, 0))

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(4, 0))
        if tg_cards:
            tk.Button(btns, text="💒 Marry Selected", bg=BTN_OK_BG, fg=BTN_OK_FG,
                      font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=6,
                      cursor="hand2", command=self._assign).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", bg=BORDER, fg=DARK,
                  font=("Helvetica", 10), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self.destroy).pack(side="left", padx=6)

        if tg_cards:
            # Full-canvas assign — uses _build_fragment() so filter-panel,
            # sidebar, flyout-card, header-action are all included correctly.
            tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(8, 0))
            fc_row = tk.Frame(self, bg="#FFF7ED"); fc_row.pack(fill="x", padx=16, pady=4)
            tk.Label(fc_row,
                     text="Or assign the ENTIRE canvas layout (includes filter panel, sidebar, header-action):  →",
                     bg="#FFF7ED", fg="#92400E", font=("Helvetica", 9, "bold")).pack(side="left", padx=(0, 8))
            tk.Button(fc_row, text="🗺 Assign Full Canvas to Slot",
                      bg="#D97706", fg="black", font=("Helvetica", 9, "bold"),
                      relief="flat", padx=12, pady=4, cursor="hand2",
                      command=self._assign_full_canvas).pack(side="left")

    def _refresh_slots(self):
        idx = self._tg_combo.current()
        if idx < 0 or idx >= len(self._tg_cards):
            return
        tg = self._tg_cards[idx]
        slots = list((tg.orig_full_node or {}).get("Slots", {}).keys()) if tg.orig_full_node else []
        self._slot_combo["values"] = slots
        if slots:
            self._slot_combo.current(0)

    def _assign(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select cards or a segment on the left.", parent=self)
            return
        idx = self._tg_combo.current()
        if idx < 0 or idx >= len(self._tg_cards):
            messagebox.showwarning("No Tab Group", "Select a tab group on the right.", parent=self)
            return
        slot_name = self._slot_var.get().strip()
        if not slot_name:
            messagebox.showwarning("No Slot", "Select a slot on the right.", parent=self)
            return

        tab_card  = self._tg_cards[idx]
        new_json  = []
        cards_to_remove = []

        for iid in sel:
            if iid in self._seg_iids:
                sn = self._seg_iids[iid]
                seg_cards = sorted(
                    [c for c in self.app.cards.values()
                     if c.segment == sn and not getattr(c, '_tg_parent', None)],
                    key=lambda c: (c.winfo_y(), c.winfo_x()))
                if not seg_cards:
                    continue
                seg_dir = self.app.segment_dirs.get(sn, {})
                new_json.append({
                    "Container": "flex",
                    "Config":    {"SectionName": sn},
                    "Style":     {"css": {"flexDirection": seg_dir.get("direction", "row"),
                                          "gap":           seg_dir.get("gap", "0px")}},
                    "Slots":     {"Default": [self.app._comp_json(c) for c in seg_cards]},
                })
                cards_to_remove.extend(seg_cards)
            elif iid in self._card_iids:
                card = self._card_iids[iid]
                new_json.append(self.app._comp_json(card))
                cards_to_remove.append(card)

        if not new_json:
            messagebox.showwarning("Nothing to assign", "No cards or segments were resolved.", parent=self)
            return

        slot = tab_card.orig_full_node.setdefault("Slots", {})
        existing = slot.get(slot_name, [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        slot[slot_name] = existing + new_json

        for c in cards_to_remove:
            self.app.remove_comp(c.cid)
        tab_card.rebuild()
        self.destroy()

    def _assign_full_canvas(self):
        """Build full fragment JSON (via _build_fragment) and store as slot content.

        This is the correct path when the canvas has a filter-panel, sidebar,
        flyout-card, or header-action — those structures are built correctly
        only by _build_fragment(), not by the card-by-card _comp_json() path.
        """
        idx = self._tg_combo.current()
        if idx < 0 or idx >= len(self._tg_cards):
            messagebox.showwarning("No Tab Group", "Select a tab group on the right.", parent=self)
            return
        slot_name = self._slot_var.get().strip()
        if not slot_name:
            messagebox.showwarning("No Slot", "Select a slot on the right.", parent=self)
            return

        # Exclude tab-group cards themselves from the canvas snapshot
        # (they live outside the layout being assigned)
        canvas_has_content = any(c.ctype != "tab-group" and not getattr(c, '_tg_parent', None)
                                 for c in self.app.cards.values())
        if not canvas_has_content:
            messagebox.showwarning("Empty", "No layout cards on canvas to assign.", parent=self)
            return

        data = self.app._build_fragment()
        node = data.get("Fragment", data)

        tab_card = self._tg_cards[idx]
        slot = tab_card.orig_full_node.setdefault("Slots", {})
        existing = slot.get(slot_name, [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        slot[slot_name] = existing + [node]

        # Remove all non-tab-group non-child canvas cards (they are now inside the slot)
        for cid, card in list(self.app.cards.items()):
            if card.ctype != "tab-group" and not getattr(card, '_tg_parent', None):
                self.app.remove_comp(cid)

        tab_card.rebuild()
        messagebox.showinfo("Done",
                            f"Full canvas layout assigned to slot '{slot_name}'.\n"
                            "Click ⬡ on the tab group to expand and inspect.", parent=self)
        self.destroy()


class TabSlotPickerDialog(tk.Toplevel):
    """Picker to marry canvas cards/segments into a tab-group slot.

    Segments appear as selectable groups — picking a segment row
    marries ALL cards in that segment (wrapped in their flex container).
    Individual ungrouped cards appear below segments.
    On confirm, selected content is appended to the slot JSON and the
    source cards are removed from the canvas.
    """
    def __init__(self, app, tab_card, slot_name):
        super().__init__(app)
        self.app       = app
        self.tab_card  = tab_card
        self.slot_name = slot_name
        self._seg_iids = {}   # iid → segment_name
        self._card_iids = {}  # iid → CompCard
        self.title(f"Marry Layout → {slot_name}")
        self.geometry("760x560")
        self.configure(bg=BG)
        self.grab_set()
        self._build()

    def _build(self):
        tk.Label(self, text=f"Marry layout into slot:  {self.slot_name}",
                 bg=BG, fg=DARK, font=("Helvetica", 11, "bold")).pack(pady=(14, 2), padx=20, anchor="w")
        tk.Label(self,
                 text="Select a segment (entire layout) or individual cards. "
                      "Married items are removed from the canvas.",
                 bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(padx=20, anchor="w")

        frm = tk.Frame(self, bg=BG); frm.pack(fill="both", expand=True, padx=16, pady=10)
        cols = ("kind", "name", "detail")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings",
                                   selectmode="extended", height=18)
        for col, hdr, w in [("kind","Type",100), ("name","Name / Label",300), ("detail","Contents",240)]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w, anchor="w")
        self._tree.tag_configure("segment",  background="#E0F2FE", font=("Helvetica", 10, "bold"))
        self._tree.tag_configure("card",     background="#F8FAFC")
        self._tree.tag_configure("empty",    foreground="#94A3B8")
        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        # ── Populate segments ──────────────────────────────────────────
        seg_dirs = getattr(self.app, 'segment_dirs', {})
        for sn in sorted(seg_dirs.keys()):
            cards_in = sorted(
                [c for c in self.app.cards.values()
                 if c.segment == sn
                 and not getattr(c, '_tg_parent', None)
                 and c.cid != self.tab_card.cid],
                key=lambda c: (c.winfo_y(), c.winfo_x()))
            if not cards_in:
                continue
            ctypes = Counter(c.ctype for c in cards_in)
            detail = ", ".join(f"{v}×{k}" for k, v in ctypes.items())
            iid = self._tree.insert("", "end", tags=("segment",),
                                    values=("▸ Segment", sn,
                                            f"{len(cards_in)} cards: {detail}"))
            self._seg_iids[iid] = sn

        # ── Populate ungrouped cards ───────────────────────────────────
        ungrouped = sorted(
            [c for c in self.app.cards.values()
             if not c.segment
             and not getattr(c, '_tg_parent', None)
             and c.cid != self.tab_card.cid
             and c.ctype != "tab-group"
             and c.ctype != "filter-panel"],
            key=lambda c: (c.winfo_y(), c.winfo_x()))
        for card in ungrouped:
            iid = self._tree.insert("", "end", tags=("card",),
                                    values=(card.ctype, card.title or card.ctype,
                                            card.ds or "—"))
            self._card_iids[iid] = card

        if not self._seg_iids and not self._card_iids:
            self._tree.insert("", "end", tags=("empty",),
                              values=("—", "(no available layouts or cards)", "—"))

        # Pre-select canvas-selected items
        for iid, card in self._card_iids.items():
            if card.cid in self.app._sel_set:
                self._tree.selection_add(iid)
        self._tree.bind("<Double-1>", lambda e: self._assign())

        btns = tk.Frame(self, bg=BG); btns.pack(pady=(4, 0))
        tk.Button(btns, text="💒 Marry Selected", bg=BTN_OK_BG, fg=BTN_OK_FG,
                  font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self._assign).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", bg=BORDER, fg=DARK,
                  font=("Helvetica", 10), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self.destroy).pack(side="left", padx=6)

        # Full-canvas path — filter-panel, sidebar, flyout-card all handled correctly
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(8, 0))
        fc_row = tk.Frame(self, bg="#FFF7ED"); fc_row.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(fc_row,
                 text="Or assign the ENTIRE canvas layout (includes filter panel, sidebar, header-action):  →",
                 bg="#FFF7ED", fg="#92400E", font=("Helvetica", 9, "bold")).pack(side="left", padx=(0, 8))
        tk.Button(fc_row, text="🗺 Assign Full Canvas",
                  bg="#D97706", fg="black", font=("Helvetica", 9, "bold"),
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self._assign_full_canvas).pack(side="left")

    def _assign_full_canvas(self):
        """Store _build_fragment() output directly into this slot."""
        canvas_has_content = any(c.ctype != "tab-group" and not getattr(c, '_tg_parent', None)
                                 for c in self.app.cards.values())
        if not canvas_has_content:
            messagebox.showwarning("Empty", "No layout cards on canvas to assign.", parent=self)
            return
        data = self.app._build_fragment()
        node = data.get("Fragment", data)
        slot = self.tab_card.orig_full_node.setdefault("Slots", {})
        existing = slot.get(self.slot_name, [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        slot[self.slot_name] = existing + [node]
        for cid, card in list(self.app.cards.items()):
            if card.ctype != "tab-group" and not getattr(card, '_tg_parent', None):
                self.app.remove_comp(cid)
        self.tab_card.rebuild()
        messagebox.showinfo("Done",
                            f"Full canvas layout assigned to slot '{self.slot_name}'.\n"
                            "Click ⬡ on the tab group to expand and inspect.", parent=self)
        self.destroy()

    def _assign(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a segment or card first.", parent=self)
            return

        new_json = []
        cards_to_remove = []

        for iid in sel:
            if iid in self._seg_iids:
                sn = self._seg_iids[iid]
                seg_cards = sorted(
                    [c for c in self.app.cards.values() if c.segment == sn
                     and not getattr(c, '_tg_parent', None)],
                    key=lambda c: (c.winfo_y(), c.winfo_x()))
                if not seg_cards:
                    continue
                seg_dir = self.app.segment_dirs.get(sn, {})
                direction = seg_dir.get("direction", "row")
                gap       = seg_dir.get("gap", "0px")
                seg_node = {
                    "Container": "flex",
                    "Config": {"SectionName": sn},
                    "Style": {"css": {"flexDirection": direction, "gap": gap}},
                    "Slots": {"Default": [self.app._comp_json(c) for c in seg_cards]}
                }
                new_json.append(seg_node)
                cards_to_remove.extend(seg_cards)
            elif iid in self._card_iids:
                card = self._card_iids[iid]
                new_json.append(self.app._comp_json(card))
                cards_to_remove.append(card)

        if not new_json:
            return
        slot = self.tab_card.orig_full_node.setdefault("Slots", {})
        existing = slot.get(self.slot_name, [])
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        slot[self.slot_name] = existing + new_json
        for c in cards_to_remove:
            self.app.remove_comp(c.cid)
        self.tab_card.rebuild()
        self.destroy()


# ─────────────────────────────────────────────────────────────────
#  EDIT DIALOG (Includes Series Mappings)
# ─────────────────────────────────────────────────────────────────
class EditDialog(tk.Toplevel):
    def __init__(self, app, card):
        super().__init__(app); self.app=app; self.card=card
        self.title("Edit Component Settings")
        _is_chart = card.ctype not in ("table", "metrics") and card.ctype not in RIVER_TYPES
        self.geometry("780x900" if card.ctype == "tab-group" else ("780x860" if _is_chart else "780x750"))
        self.configure(bg=BG); self.grab_set(); self._build()

    def _build(self):
        self.tree = None; self.schema_vars = {}; self.sty_vars = {}
        self.arr_tree = None; self.arr_schema_cols = []; self.arr_key = None
        tk.Label(self,text=f"Edit  {self.card.ctype.replace('-',' ').title()}",bg=BG,fg=DARK,font=("Helvetica",12,"bold")).pack(pady=12,padx=20,anchor="w")
        f=tk.Frame(self,bg=BG); f.pack(padx=20,pady=4,fill="x")
        
        # ── Collect datamaps from variable pool + existing canvas cards ──
        _pool      = getattr(self.app, '_var_pool', {})
        _all_ds    = sorted(set(
            [c.ds for c in self.app.cards.values() if c.ds] +
            list(_pool.keys())
        ))
        _all_bvar  = sorted(set(
            [c.bvar for c in self.app.cards.values() if c.bvar] +
            list(_pool.values())
        ))
        # ds → bvar lookup (pool takes precedence)
        _ds_to_bvar = {c.ds: c.bvar for c in self.app.cards.values() if c.ds and c.bvar}
        _ds_to_bvar.update(_pool)

        _FIELD_HELP = {
            "tv":  "Display name shown on the canvas card.\nAlso used as Config.title in the exported Fragment JSON.",
            "ctv": "Highcharts series type that determines how data is visualised.\n"
                   "Affects dataMapping fieldMappings — different types expect\n"
                   "different axis field names.",
            "dsv": "DataSourcePath — the data key this component reads from the API response.\n"
                   "Must match a key in the Action JSON's dataMap.\n\n"
                   "Dropdown is populated from:\n"
                   "  1. The Variable Pool (🗃 toolbar button — import Action JSON)\n"
                   "  2. Data sources already used by other cards on the canvas\n\n"
                   "Selecting a pool key auto-fills the Backend Variable field.\n"
                   "Example keys: 'JournalData', 'TimelineSummary', 'Filters'",
            "bvv": "Backend variable — the EFW step output variable mapped to this data source.\n"
                   "Standard format:  object::{DataSourceKey}Js.result\n\n"
                   "Select from the dropdown or type a custom value.\n"
                   "Example: 'object::DataJs.result', 'object::TimelineSummaryJs.result'\n\n"
                   "Tip: selecting a Data Source auto-fills this field.",
            "wsv": "CSS width applied to this component's wrapper div.\n"
                   "Example: '100%' (fill row), '300px' (fixed), 'fit-content'",
            "hsv": "CSS height applied to this component's wrapper div.\n"
                   "Example: 'fit-content' (auto), '260px' (fixed), '100%' (fill parent)",
        }

        self.vs={}; fields = [("Title","tv",self.card.title), ("Data Source","dsv",self.card.ds), ("Backend Var","bvv",self.card.bvar), ("Width (CSS)","wsv",self.card.css_width), ("Height (CSS)","hsv",self.card.css_height)]
        if self.card.ctype not in RIVER_TYPES and self.card.ctype not in ("table", "metrics"): fields.insert(1, ("Chart Type","ctv",self.card.ctype))
        if self.card.ctype in RIVER_TYPES:
            if self.card.ctype == "carousel":
                fields = [("Title","tv",self.card.title),("Data Source","dsv",self.card.ds),("Width (CSS)","wsv",self.card.css_width),("Height (CSS)","hsv",self.card.css_height)]
            else:
                fields = [("Title","tv",self.card.title),("Width (CSS)","wsv",self.card.css_width),("Height (CSS)","hsv",self.card.css_height)]

        for i,(lbl,vn,val) in enumerate(fields):
            v = tk.StringVar(value=val); self.vs[vn] = v
            lf = tk.Frame(f, bg=BG); lf.grid(row=i, column=0, sticky="w", pady=5)
            tk.Label(lf, text=lbl+":", bg=BG, fg=DARK, font=("Helvetica",10)).pack(side="left")
            if vn in _FIELD_HELP:
                ih = tk.Label(lf, text=" ⓘ", bg=BG, fg="#60A5FA",
                              font=("Helvetica",9), cursor="hand2")
                ih.pack(side="left")
                Tooltip(ih, _FIELD_HELP[vn])

            if vn == "ctv":
                ttk.Combobox(f, textvariable=v,
                             values=[k for k in COMP_DEFS.keys() if k not in ("table","metrics")],
                             width=28, state="readonly").grid(row=i, column=1, padx=10, pady=5)
            elif vn in ("wsv", "hsv"):
                ttk.Combobox(f, textvariable=v,
                             values=["fit-content","100%","50%","calc(50% - 8px)","calc(33% - 8px)",
                                     "24px","32px","40px","48px","60px","80px","100px","120px",
                                     "160px","200px","240px","260px","300px","360px","450px","600px"],
                             width=28).grid(row=i, column=1, padx=10, pady=5)
            elif vn == "dsv":
                dsf = tk.Frame(f, bg=BG); dsf.grid(row=i, column=1, sticky="w", padx=10, pady=5)
                ds_cb = ttk.Combobox(dsf, textvariable=v, values=_all_ds,
                                     width=26, font=("Helvetica",10))
                ds_cb.pack(side="left")
                # Auto-fill bvar when a known DS is selected
                def _on_ds_pick(_e, _v=v):
                    ds = _v.get()
                    bvar_v = self.vs.get("bvv")
                    if bvar_v is None: return
                    if ds in _ds_to_bvar:
                        bvar_v.set(_ds_to_bvar[ds])
                    elif ds and not bvar_v.get():
                        bvar_v.set(f"object::{ds}Js.result")
                ds_cb.bind("<<ComboboxSelected>>", _on_ds_pick)
                tk.Label(dsf, text=" ← dataMap key", bg=BG, fg="#64748B",
                         font=("Helvetica",8)).pack(side="left")
            elif vn == "bvv":
                bvf = tk.Frame(f, bg=BG); bvf.grid(row=i, column=1, sticky="w", padx=10, pady=5)
                bv_cb = ttk.Combobox(bvf, textvariable=v, values=_all_bvar,
                                     width=26, font=("Helvetica",10))
                bv_cb.pack(side="left")
                tk.Label(bvf, text=" ← EFW output var", bg=BG, fg="#64748B",
                         font=("Helvetica",8)).pack(side="left")
            else:
                tk.Entry(f, textvariable=v, width=32,
                         font=("Helvetica",10)).grid(row=i, column=1, padx=10, pady=5)

        seg_row = len(fields)
        tk.Label(f, text="Segment:", bg=BG, fg=DARK, font=("Helvetica",10)).grid(row=seg_row, column=0, sticky="w", pady=6)
        sf = tk.Frame(f, bg=BG); sf.grid(row=seg_row, column=1, sticky="w", pady=6)
        self.vs["seg"] = tk.StringVar(value=getattr(self.card, 'segment', ''))
        existing_segs = [""] + sorted({c.segment for c in self.app.cards.values() if c.segment})
        seg_cb = ttk.Combobox(sf, textvariable=self.vs["seg"], values=existing_segs, width=18, font=("Helvetica",10))
        seg_cb.pack(side="left", padx=(0,8))
        tk.Label(sf, text="Direction:", bg=BG, fg=DARK, font=("Helvetica",9)).pack(side="left")
        cur_seg = getattr(self.card, 'segment', '')
        cur_dir = self.app.segment_dirs.get(cur_seg, {}).get("direction", "row") if cur_seg else "row"
        self.vs["seg_dir"] = tk.StringVar(value=cur_dir)
        ttk.Combobox(sf, textvariable=self.vs["seg_dir"], values=["row","column"], width=8, state="readonly", font=("Helvetica",10)).pack(side="left", padx=(4,0))
        tk.Label(sf, text="Gap:", bg=BG, fg=DARK, font=("Helvetica",9)).pack(side="left", padx=(8,0))
        self.vs["seg_gap"] = tk.StringVar(value=self.app.segment_dirs.get(cur_seg, {}).get("gap", "0rem") if cur_seg else "0rem")
        ttk.Combobox(sf, textvariable=self.vs["seg_gap"], values=["0rem","0.5rem","1rem","1.5rem","2rem"], width=7, font=("Helvetica",10)).pack(side="left", padx=(4,0))
            
        if self.card.ctype == "metrics":
            tk.Label(self, text="KPI Tiles  (label shown in card, field = data key, unit = optional suffix):",
                     bg=BG, fg=DARK, font=("Helvetica", 10, "bold")).pack(padx=20, pady=(10,0), anchor="w")
            mf = tk.Frame(self, bg=BG); mf.pack(fill="both", expand=True, padx=20, pady=5)
            self.tree = ttk.Treeview(mf, columns=("Label","Field","Unit"), show="headings", height=8)
            self.tree.heading("Label", text="Display Label"); self.tree.heading("Field", text="Data Field Key"); self.tree.heading("Unit", text="Unit (opt.)")
            self.tree.column("Label", width=200); self.tree.column("Field", width=200); self.tree.column("Unit", width=80)
            self.tree.pack(side="left", fill="both", expand=True)
            for m in self.card.metrics:
                self.tree.insert("", "end", values=(m.get("label",""), m.get("field",""), m.get("unit","")))
            self.tree.bind("<Double-1>", lambda e: self._edit_item())
            bf_m = tk.Frame(mf, bg=BG); bf_m.pack(side="right", fill="y", padx=5)
            tk.Button(bf_m, text="+ Add",  width=8, command=self._add_item).pack(pady=4)
            tk.Button(bf_m, text="- Del",  width=8, command=self._del_item).pack(pady=4)
            tk.Button(bf_m, text="\u25b2 Up",   width=8, command=lambda: self._move_item(-1)).pack(pady=4)
            tk.Button(bf_m, text="\u25bc Down", width=8, command=lambda: self._move_item(1)).pack(pady=4)
        elif self.card.ctype == "table":
            self.vs["footer"] = tk.BooleanVar(value=getattr(self.card, 'has_footer', False))
            self.vs["checkboxes"]   = tk.BooleanVar(value=getattr(self.card, 'has_checkboxes', True))
            self.vs["multiselect"]  = tk.BooleanVar(value=getattr(self.card, 'has_multiselect', True))
            self.vs["agentic"] = tk.BooleanVar(value=getattr(self.card, 'has_agentic', True))
            self.vs["agent_id"] = tk.StringVar(value=getattr(self.card, 'agent_id', 'ext-mhetroubleshoot'))
            self.vs["agent_question"] = tk.StringVar(value=getattr(self.card, 'agent_question', ''))

            tf1 = tk.Frame(f, bg=BG)
            tf1.grid(row=len(fields)+1, column=1, sticky="w", pady=(6,2))
            tk.Checkbutton(tf1, text="Pagination Footer", variable=self.vs["footer"],      bg=BG, font=("Helvetica",9,"bold")).pack(side="left", padx=(0,10))
            tk.Checkbutton(tf1, text="Row Checkboxes",   variable=self.vs["checkboxes"],   bg=BG, font=("Helvetica",9,"bold")).pack(side="left", padx=(0,10))
            tk.Checkbutton(tf1, text="Multi-Select",     variable=self.vs["multiselect"],  bg=BG, font=("Helvetica",9,"bold")).pack(side="left")

            tf2 = tk.Frame(f, bg=BG)
            tf2.grid(row=len(fields)+2, column=1, sticky="w", pady=(0,4))
            tk.Checkbutton(tf2, text="AI Menu", variable=self.vs["agentic"], bg=BG, font=("Helvetica",9,"bold")).pack(side="left", padx=(0,5))
            tk.Label(tf2, text="Agent ID:", bg=BG, font=("Helvetica",9)).pack(side="left")
            tk.Entry(tf2, textvariable=self.vs["agent_id"], width=18, font=("Helvetica",9)).pack(side="left", padx=5)

            tk.Label(f, text="Question to Agent:", bg=BG, fg=DARK,
                     font=("Helvetica",9)).grid(row=len(fields)+3, column=0, sticky="nw", pady=(0,4))
            tf2b = tk.Frame(f, bg=BG)
            tf2b.grid(row=len(fields)+3, column=1, sticky="ew", pady=(0,4))
            tk.Entry(tf2b, textvariable=self.vs["agent_question"], width=52,
                     font=("Helvetica",9)).pack(fill="x", pady=(2,0))

            tk.Label(f, text="Action Arguments:", bg=BG, fg=DARK,
                     font=("Helvetica",9)).grid(row=len(fields)+4, column=0, sticky="nw", pady=(4,2))
            tf3 = tk.Frame(f, bg=BG)
            tf3.grid(row=len(fields)+4, column=1, sticky="ew", pady=(4,2))
            tk.Label(tf3, text="Column field names passed to the agent (comma-separated):",
                     bg=BG, fg=MUTED, font=("Helvetica",8)).pack(anchor="w")
            _args_default = ", ".join(getattr(self.card, 'agent_args', []))
            self.vs["agent_args"] = tk.StringVar(value=_args_default)
            tk.Entry(tf3, textvariable=self.vs["agent_args"], width=52,
                     font=("Helvetica",9)).pack(fill="x", pady=(2,0))

            self.vs["insights"] = tk.BooleanVar(value=getattr(self.card, 'has_insights', False))
            self.vs["insights_field"] = tk.StringVar(value=getattr(self.card, 'insights_field', 'TicketsList'))
            self.vs["insights_agent_id"] = tk.StringVar(value=getattr(self.card, 'insights_agent_id', ''))
            tk.Label(f, text="Insights Column:", bg=BG, fg=DARK,
                     font=("Helvetica",9)).grid(row=len(fields)+5, column=0, sticky="nw", pady=(4,2))
            tf_ins = tk.Frame(f, bg=BG)
            tf_ins.grid(row=len(fields)+5, column=1, sticky="ew", pady=(4,2))
            tk.Checkbutton(tf_ins, text="💡 Enable", variable=self.vs["insights"],
                           bg=BG, font=("Helvetica",9,"bold")).pack(side="left", padx=(0,8))
            tk.Label(tf_ins, text="Field:", bg=BG, font=("Helvetica",9)).pack(side="left")
            tk.Entry(tf_ins, textvariable=self.vs["insights_field"], width=16,
                     font=("Helvetica",9)).pack(side="left", padx=(3,8))
            tk.Label(tf_ins, text="Agent ID:", bg=BG, font=("Helvetica",9)).pack(side="left")
            tk.Entry(tf_ins, textvariable=self.vs["insights_agent_id"], width=22,
                     font=("Helvetica",9)).pack(side="left", padx=3)

            self._col_links  = {c['field']: c['link']   for c in self.card.columns if c.get('link')}
            self._col_events = {c['field']: c['events'] for c in self.card.columns if c.get('events')}

            def _link_label(lk, ev=None):
                parts = []
                if lk:
                    if lk.get("event_type") == "event_click":
                        _eid = lk.get("event_id", "")
                        _fid = lk.get("filter_id", "")
                        _iex = lk.get("input_expr", "")
                        parts.append(f"🎯 {_eid}" + (" [map]" if _iex else (f" [{_fid}]" if _fid else "")))
                    else:
                        parts.append(f"🔗 {lk.get('menu_id','') or lk.get('to_entity','') or 'link'}")
                if ev:
                    _eid2 = ev.get("event_id", "")
                    _fid2 = ev.get("filter_id", "")
                    _iex2 = ev.get("input_expr", "")
                    tag = f"⚡ {_eid2}" + (" [map]" if _iex2 else (f" [{_fid2}]" if _fid2 else ""))
                    if not lk:
                        parts.append(tag)
                    else:
                        parts.append(f"+{tag}")
                return "  ".join(parts)

            tk.Label(self, text="Manage Columns (Ordered Sequence):", bg=BG, fg=DARK, font=("Helvetica", 10, "bold")).pack(padx=20, pady=(10,0), anchor="w")
            cf = tk.Frame(self, bg=BG); cf.pack(fill="both", expand=True, padx=20, pady=5)
            self.tree = ttk.Treeview(cf, columns=("Field", "Title", "Lnk"), show="headings", height=8)
            self.tree.heading("Field", text="Data Key"); self.tree.heading("Title", text="Display Title"); self.tree.heading("Lnk", text="Link / Event")
            self.tree.column("Field", width=170); self.tree.column("Title", width=120); self.tree.column("Lnk", width=210, anchor="w")
            self.tree.pack(side="left", fill="both", expand=True)
            for col in self.card.columns:
                self.tree.insert("", "end", values=(col['field'], col['title'],
                    _link_label(col.get('link'), col.get('events'))))
            self.tree.bind("<Double-1>", lambda e: self._edit_item())
            bf_t = tk.Frame(cf, bg=BG); bf_t.pack(side="right", fill="y", padx=5)
            tk.Button(bf_t, text="+ Add",   width=9, command=self._add_item).pack(pady=3)
            tk.Button(bf_t, text="- Del",   width=9, command=self._del_item).pack(pady=3)
            tk.Button(bf_t, text="▲ Up",    width=9, command=lambda: self._move_item(-1)).pack(pady=3)
            tk.Button(bf_t, text="▼ Down",  width=9, command=lambda: self._move_item(1)).pack(pady=3)
            tk.Button(bf_t, text="🔗 Link",  width=9, command=self._edit_col_link).pack(pady=4)
            tk.Button(bf_t, text="⚡ Event", width=9, command=self._edit_col_event).pack(pady=4)
        elif self.card.ctype in RIVER_TYPES:
            schema = ELEM_SCHEMAS.get(self.card.ctype, {})
            # ── description banner ──────────────────────────────
            desc = schema.get("desc", "")
            if desc:
                db = tk.Frame(self, bg="#EFF6FF", relief="groove", bd=1)
                db.pack(fill="x", padx=20, pady=(4,0))
                tk.Label(db, text=f"ℹ  {desc}", bg="#EFF6FF", fg="#1E40AF",
                         font=("Helvetica",9), wraplength=700, justify="left",
                         padx=10, pady=6).pack(anchor="w")
            # ── Input field (non-containers) ────────────────────
            rdef = RIVER_ELEM_DEFS[self.card.ctype]
            if not rdef["is_container"]:
                ir = tk.Frame(self, bg=BG); ir.pack(fill="x", padx=20, pady=(8,0))
                ir.columnconfigure(1, weight=1)
                lf0 = tk.Frame(ir, bg=BG); lf0.grid(row=0, column=0, sticky="nw", padx=(0,12))
                tk.Label(lf0, text="Data Path  (Input)", bg=BG, fg=DARK,
                         font=("Helvetica",9,"bold")).pack(anchor="w")
                tk.Label(lf0, text="Field path in data source  e.g. CustomerName", bg=BG, fg=MUTED,
                         font=("Helvetica",7)).pack(anchor="w")
                self.vs["elem_input"] = tk.StringVar(value=self.card.elem_input or "")
                tk.Entry(ir, textvariable=self.vs["elem_input"], width=40,
                         font=("Helvetica",10)).grid(row=0, column=1, sticky="ew", pady=4)
            # ── Scrollable body ─────────────────────────────────
            outer = tk.Frame(self, bg=BG); outer.pack(fill="both", expand=True, padx=20, pady=(6,0))
            bcanv = tk.Canvas(outer, bg=BG, highlightthickness=0)
            bscrl = ttk.Scrollbar(outer, orient="vertical", command=bcanv.yview)
            bcanv.configure(yscrollcommand=bscrl.set)
            bscrl.pack(side="right", fill="y")
            bcanv.pack(side="left", fill="both", expand=True)
            body = tk.Frame(bcanv, bg=BG)
            _bwin = bcanv.create_window((0,0), window=body, anchor="nw")
            body.bind("<Configure>", lambda e: (bcanv.configure(scrollregion=bcanv.bbox("all")),
                                                bcanv.itemconfig(_bwin, width=bcanv.winfo_width())))
            bcanv.bind("<Configure>", lambda e: bcanv.itemconfig(_bwin, width=e.width))
            bcanv.bind("<MouseWheel>", lambda e: bcanv.yview_scroll(_wheel_scroll_units(e), "units"))
            # ── Config fields ───────────────────────────────────
            cfg_fields = schema.get("cfg", [])
            if cfg_fields:
                sh = tk.Frame(body, bg=BG); sh.pack(fill="x", pady=(6,0))
                tk.Label(sh, text="Configuration", bg=BG, fg=DARK,
                         font=("Helvetica",10,"bold")).pack(anchor="w")
                tk.Frame(sh, bg=BORDER, height=1).pack(fill="x", pady=(2,4))
                cf2 = tk.Frame(sh, bg=BG); cf2.pack(fill="x"); cf2.columnconfigure(1, weight=1)
                for ri, fld in enumerate(cfg_fields):
                    key, lbl, ftype, fdesc = fld[0], fld[1], fld[2], fld[3]
                    opts = fld[4] if len(fld) > 4 else []
                    if key == "__onclick_container":
                        _oc = getattr(self.card, "events", {}).get("Triggers", {}).get("OnClick", [{}])
                        cur = _oc[0].get("ContainerId", "") if _oc else ""
                    elif key == "__onclick_event":
                        _oc = getattr(self.card, "events", {}).get("Triggers", {}).get("OnClick", [{}])
                        cur = _oc[0].get("EventId", "") if _oc else ""
                    else:
                        cur = self.card.elem_config.get(key, "")
                    lf1 = tk.Frame(cf2, bg=BG); lf1.grid(row=ri, column=0, sticky="nw", padx=(0,10), pady=5)
                    tk.Label(lf1, text=lbl, bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                             width=24, anchor="w", justify="left").pack(anchor="w")
                    tk.Label(lf1, text=fdesc, bg=BG, fg=MUTED, font=("Helvetica",7),
                             wraplength=195, justify="left").pack(anchor="w")
                    if ftype == "bool":
                        raw = cur
                        if isinstance(raw, str): raw = raw.lower() in ("true","1","yes")
                        var = tk.BooleanVar(value=bool(raw))
                        self.schema_vars[key] = var
                        tk.Checkbutton(cf2, variable=var, bg=BG).grid(row=ri, column=1, sticky="w", pady=5)
                    elif ftype == "enum":
                        var = tk.StringVar(value=str(cur) if cur != "" else (opts[0] if opts else ""))
                        self.schema_vars[key] = var
                        ttk.Combobox(cf2, textvariable=var, values=opts, width=32,
                                     state="readonly").grid(row=ri, column=1, sticky="w", padx=4, pady=5)
                    elif key == "__onclick_container":
                        _cid_opts = ["header-action-fragment"] + sorted(
                            {d.get("section_name", sn) for sn, d in self.app.segment_dirs.items()
                             if d.get("section_name", sn)} - {"header-action-fragment"})
                        var = tk.StringVar(value=str(cur) if cur != "" else "header-action-fragment")
                        self.schema_vars[key] = var
                        ttk.Combobox(cf2, textvariable=var, values=_cid_opts, width=38
                                     ).grid(row=ri, column=1, sticky="ew", padx=4, pady=5)
                    elif key == "__onclick_event":
                        _evt_opts = ["toggle-filter","show-chart","hide-chart","show-metrics",
                                     "hide-metrics","view-switch","show-table","hide-table"]
                        var = tk.StringVar(value=str(cur) if cur != "" else "")
                        self.schema_vars[key] = var
                        ttk.Combobox(cf2, textvariable=var, values=_evt_opts, width=38
                                     ).grid(row=ri, column=1, sticky="ew", padx=4, pady=5)
                    else:
                        var = tk.StringVar(value=str(cur) if cur != "" else "")
                        self.schema_vars[key] = var
                        tk.Entry(cf2, textvariable=var, width=38, font=("Helvetica",10)
                                 ).grid(row=ri, column=1, sticky="ew", padx=4, pady=5)
            # ── Array field ─────────────────────────────────────
            arr_spec = schema.get("arr")
            if arr_spec:
                arr_key_name, arr_lbl, arr_cols = arr_spec[0], arr_spec[1], arr_spec[2]
                self.arr_key = arr_key_name; self.arr_schema_cols = arr_cols
                ah = tk.Frame(body, bg=BG); ah.pack(fill="x", pady=(10,0))
                tk.Label(ah, text=arr_lbl, bg=BG, fg=DARK, font=("Helvetica",10,"bold")).pack(anchor="w")
                tk.Frame(ah, bg=BORDER, height=1).pack(fill="x", pady=(2,4))
                af = tk.Frame(ah, bg=BG); af.pack(fill="x")
                col_keys = [c[0] for c in arr_cols]
                self.arr_tree = ttk.Treeview(af, columns=col_keys, show="headings", height=5)
                for ck, cl, cw in arr_cols:
                    self.arr_tree.heading(ck, text=cl); self.arr_tree.column(ck, width=cw)
                self.arr_tree.pack(side="left", fill="both", expand=True)
                self.arr_tree.bind("<Double-1>", lambda e: self._arr_edit())
                for item in (self.card.elem_config.get(arr_key_name, []) or []):
                    if isinstance(item, dict):
                        self.arr_tree.insert("", "end", values=tuple(str(item.get(c[0],"")) for c in arr_cols))
                abf = tk.Frame(af, bg=BG); abf.pack(side="right", fill="y", padx=4)
                tk.Button(abf, text="+ Add",  width=8, command=self._arr_add).pack(pady=3)
                tk.Button(abf, text="- Del",  width=8, command=self._arr_del).pack(pady=3)
                tk.Button(abf, text="▲ Up",   width=8, command=lambda: self._move_item(-1)).pack(pady=3)
                tk.Button(abf, text="▼ Down", width=8, command=lambda: self._move_item(1)).pack(pady=3)
            # ── Tab-group: filter panel per slot ────────────────
            if self.card.ctype == "tab-group":
                self._slot_fp_vars = {}
                _tg_orig  = getattr(self.card, 'orig_full_node', None) or {}
                _tg_tabs  = _tg_orig.get("Config", {}).get("Tabs", [])
                _tg_slots = _tg_orig.get("Slots", {})
                # derive ordered slot names: from Tabs list, falling back to Slots keys
                _sn_list = [t.get("Name", t.get("LabelKey", ""))
                            for t in _tg_tabs if t.get("Name") or t.get("LabelKey")]
                if not _sn_list:
                    _sn_list = list(_tg_slots.keys())
                if _sn_list:
                    fph = tk.Frame(body, bg=BG); fph.pack(fill="x", pady=(10, 0))
                    tk.Label(fph, text="Filter Panel per Slot", bg=BG, fg=DARK,
                             font=("Helvetica", 10, "bold")).pack(anchor="w")
                    tk.Frame(fph, bg=BORDER, height=1).pack(fill="x", pady=(2, 4))
                    tk.Label(fph, bg=BG, fg=MUTED, font=("Helvetica", 8),
                             text="Check each slot that needs a filter, then pick position "
                                  "(left sidebar / right sidebar / top bar / none).").pack(
                                      anchor="w", pady=(0, 4))

                    def _find_slot_fp(items):
                        for _it in (items if isinstance(items, list) else [items]):
                            if isinstance(_it, dict):
                                if (_it.get("Element") == "filter-panel"
                                        or _it.get("Container") == "filter-panel"):
                                    return _it
                                for _sv in _it.get("Slots", {}).values():
                                    _r = _find_slot_fp(
                                        _sv if isinstance(_sv, list) else [_sv])
                                    if _r: return _r
                        return None

                    # header row
                    _hr = tk.Frame(fph, bg=BG); _hr.pack(fill="x", pady=(0, 2))
                    tk.Label(_hr, text="Slot", bg=BG, fg=MUTED,
                             font=("Helvetica", 8, "bold"), width=18, anchor="w").pack(side="left")
                    tk.Label(_hr, text="Has Filter", bg=BG, fg=MUTED,
                             font=("Helvetica", 8, "bold"), width=10).pack(side="left")
                    tk.Label(_hr, text="Position", bg=BG, fg=MUTED,
                             font=("Helvetica", 8, "bold")).pack(side="left", padx=(4, 0))

                    for _sn in _sn_list:
                        if not _sn: continue
                        _sitems = _tg_slots.get(_sn, [])
                        if not isinstance(_sitems, list):
                            _sitems = [_sitems] if _sitems else []
                        _fp = _find_slot_fp(_sitems)
                        _cur_has = _fp is not None
                        _cur_pos = ((_fp.get("Config", {}).get("Position", "left") or "left")
                                    if _fp else "none")
                        _hv = tk.BooleanVar(value=_cur_has)
                        _pv = tk.StringVar(value=_cur_pos if _cur_has else "none")
                        self._slot_fp_vars[_sn] = {"has": _hv, "pos": _pv, "fp_node": _fp}

                        _row = tk.Frame(fph, bg="#1A2744"); _row.pack(fill="x", pady=1)
                        tk.Label(_row, text=f"  {_sn}", bg="#1A2744", fg=DARK,
                                 font=("Helvetica", 9, "bold"), width=18,
                                 anchor="w").pack(side="left", padx=(4, 0))
                        tk.Checkbutton(_row, variable=_hv, bg="#1A2744",
                                       activebackground="#1A2744",
                                       command=lambda pv=_pv, hv=_hv: pv.set(
                                           "left" if hv.get() else "none")
                                       ).pack(side="left", padx=(8, 0))
                        ttk.Combobox(_row, textvariable=_pv,
                                     values=["none", "left", "right", "top"],
                                     width=9, state="readonly").pack(side="left", padx=(16, 4))
                        _ac = len((_fp or {}).get("Config", {}).get("Attributes", []))
                        for _s in (_fp or {}).get("Config", {}).get("Sections", []):
                            _ac += len(_s.get("Attributes", []))
                        tk.Label(_row, text=f"{_ac} attr" if _ac else "",
                                 bg="#1A2744", fg=MUTED,
                                 font=("Helvetica", 8)).pack(side="left", padx=4)

            # ── Style fields ────────────────────────────────────
            sty_fields = schema.get("sty", [])
            if sty_fields:
                sth = tk.Frame(body, bg=BG); sth.pack(fill="x", pady=(10,0))
                tk.Label(sth, text="Style", bg=BG, fg=DARK, font=("Helvetica",10,"bold")).pack(anchor="w")
                tk.Frame(sth, bg=BORDER, height=1).pack(fill="x", pady=(2,4))
                sf = tk.Frame(sth, bg=BG); sf.pack(fill="x"); sf.columnconfigure(1, weight=1)
                cur_sty = self.card.elem_style or {}
                for ri, fld in enumerate(sty_fields):
                    dk, lbl, ftype, fdesc = fld[0], fld[1], fld[2], fld[3]
                    opts = fld[4] if len(fld) > 4 else []
                    parts = dk.split("."); sv = cur_sty
                    for p in parts: sv = sv.get(p, "") if isinstance(sv, dict) else ""
                    lf2 = tk.Frame(sf, bg=BG); lf2.grid(row=ri, column=0, sticky="nw", padx=(0,10), pady=4)
                    tk.Label(lf2, text=lbl, bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                             width=24, anchor="w", justify="left").pack(anchor="w")
                    tk.Label(lf2, text=fdesc, bg=BG, fg=MUTED, font=("Helvetica",7),
                             wraplength=195, justify="left").pack(anchor="w")
                    if ftype == "enum":
                        var = tk.StringVar(value=str(sv) if sv else (opts[0] if opts else ""))
                        self.sty_vars[dk] = var
                        ttk.Combobox(sf, textvariable=var, values=opts, width=32,
                                     state="readonly").grid(row=ri, column=1, sticky="w", padx=4, pady=4)
                    else:
                        var = tk.StringVar(value=str(sv) if sv else "")
                        self.sty_vars[dk] = var
                        tk.Entry(sf, textvariable=var, width=38, font=("Helvetica",10)
                                 ).grid(row=ri, column=1, sticky="ew", padx=4, pady=4)
            # ── Fallback for types with no schema ────────────────
            if not cfg_fields and not arr_spec and not sty_fields:
                fbt = tk.Frame(body, bg=BG); fbt.pack(fill="both", expand=True, pady=4)
                self.tree = ttk.Treeview(fbt, columns=("Key","Value"), show="headings", height=6)
                self.tree.heading("Key", text="Config Key"); self.tree.heading("Value", text="Value")
                self.tree.column("Key", width=180); self.tree.column("Value", width=300)
                self.tree.pack(side="left", fill="both", expand=True)
                self.tree.bind("<Double-1>", lambda e: self._edit_item())
                for k, v in self.card.elem_config.items():
                    disp_v = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    self.tree.insert("", "end", values=(k, disp_v))
                fbf = tk.Frame(fbt, bg=BG); fbf.pack(side="right", fill="y", padx=4)
                tk.Button(fbf, text="+ Add",  width=8, command=self._add_item).pack(pady=3)
                tk.Button(fbf, text="- Del",  width=8, command=self._del_item).pack(pady=3)
                tk.Button(fbf, text="▲ Up",   width=8, command=lambda: self._move_item(-1)).pack(pady=3)
                tk.Button(fbf, text="▼ Down", width=8, command=lambda: self._move_item(1)).pack(pady=3)
        else:
            # ── Notebook: "Series & Legend" / "Advanced" ───────────────────────
            _nb = ttk.Notebook(self)
            _nb.pack(fill="both", expand=True, padx=8, pady=(6,0))
            _tab1 = tk.Frame(_nb, bg=BG)
            _nb.add(_tab1, text="  Series & Legend  ")
            _tab2 = tk.Frame(_nb, bg=BG)
            _nb.add(_tab2, text="  Advanced  ")

            # ── Series & Legend tab ────────────────────────────────────────────
            if self.card.ctype in ("bar", "column"):
                _sf = tk.Frame(_tab1, bg=BG); _sf.pack(padx=12, pady=(8,0), anchor="w")
                _stk_init = getattr(self.card, 'chart_stacking', False)
                if not _stk_init:
                    _cn0 = getattr(self.card, 'orig_chart_node', None)
                    _fn0 = getattr(self.card, 'orig_full_node', None)
                    if _cn0 is not None:
                        _po0 = _cn0.get("Config", {}).get("highchartsOptions", {}).get("plotOptions", {})
                        _stk_init = bool(
                            _po0.get("series", {}).get("stacking")
                            or _po0.get("bar", {}).get("stacking")
                            or _po0.get("column", {}).get("stacking")
                        )
                    elif _fn0 is not None:
                        try:
                            _ic0 = _fn0["Slots"]["content"][0]["Slots"]["Default"][0]
                            _po0 = _ic0.get("Config", {}).get("highchartsOptions", {}).get("plotOptions", {})
                            _stk_init = bool(
                                _po0.get("series", {}).get("stacking")
                                or _po0.get("bar", {}).get("stacking")
                                or _po0.get("column", {}).get("stacking")
                            )
                        except: pass
                    if _stk_init:
                        self.card.chart_stacking = _stk_init
                self.vs["chart_stacking"] = tk.BooleanVar(value=_stk_init)
                tk.Checkbutton(_sf, text="Stacked", variable=self.vs["chart_stacking"],
                               bg=BG, fg=DARK, font=("Helvetica", 9, "bold")).pack(side="left")
                tk.Label(_sf, text=" — groups series into a stacked bar/column (stacking: normal)",
                         bg=BG, fg=MUTED, font=("Helvetica", 8)).pack(side="left")

            _lg_f = tk.LabelFrame(_tab1, text="Legend", bg=BG, fg=DARK,
                                  font=("Helvetica", 9, "bold"), padx=8, pady=6)
            _lg_f.pack(padx=12, pady=(10, 0), fill="x")
            _lg_enabled_init = getattr(self.card, 'chart_legend_enabled', True)
            self.vs["legend_enabled"] = tk.BooleanVar(value=_lg_enabled_init)
            tk.Checkbutton(_lg_f, text="Show Legend", variable=self.vs["legend_enabled"],
                           bg=BG, fg=DARK, font=("Helvetica", 9)).grid(row=0, column=0, columnspan=4, sticky="w")
            _fields = [
                ("layout",       "Layout",         ["horizontal", "vertical", "proximate"],
                 getattr(self.card, 'chart_legend_layout', "horizontal")),
                ("verticalAlign", "Vertical Align", ["bottom", "top", "middle"],
                 getattr(self.card, 'chart_legend_valign', "bottom")),
                ("align",        "Align",          ["center", "left", "right"],
                 getattr(self.card, 'chart_legend_align', "center")),
            ]
            for _ci, (_key, _lbl, _opts, _init) in enumerate(_fields):
                tk.Label(_lg_f, text=_lbl + ":", bg=BG, fg=DARK,
                         font=("Helvetica", 9)).grid(row=1, column=_ci * 2, sticky="e", padx=(6 if _ci else 0, 2), pady=4)
                _var = tk.StringVar(value=_init)
                self.vs[f"legend_{_key}"] = _var
                ttk.Combobox(_lg_f, textvariable=_var, values=_opts, state="readonly",
                             width=12).grid(row=1, column=_ci * 2 + 1, sticky="w", padx=(0, 8))
            tk.Label(_lg_f, text="Y offset:", bg=BG, fg=DARK,
                     font=("Helvetica", 9)).grid(row=2, column=0, sticky="e", padx=(0, 2), pady=4)
            self.vs["legend_y"] = tk.StringVar(value=str(getattr(self.card, 'chart_legend_y', 0)))
            tk.Entry(_lg_f, textvariable=self.vs["legend_y"], width=6,
                     font=("Helvetica", 9)).grid(row=2, column=1, sticky="w")
            tk.Label(_lg_f, text="(px, negative moves up)", bg=BG, fg=MUTED,
                     font=("Helvetica", 8)).grid(row=2, column=2, columnspan=4, sticky="w", padx=4)

            tk.Label(_tab1, text="Manage Series (Multiple Field Mappings per Chart):", bg=BG, fg=DARK, font=("Helvetica", 10, "bold")).pack(padx=12, pady=(10,0), anchor="w")
            tk.Label(_tab1, text='↕ Flip — click checkbox to swap mapping direction: {"name": field, "y": field} instead of {field: "name", field: "y"}',
                     bg=BG, fg=MUTED, font=("Helvetica", 8)).pack(padx=12, anchor="w")
            cf = tk.Frame(_tab1, bg=BG); cf.pack(fill="both", expand=True, padx=12, pady=5)
            self.tree = ttk.Treeview(cf, columns=("Name", "X Field", "Y Field", "Color", "Flip"), show="headings", height=7)
            self.tree.heading("Name", text="Series Name"); self.tree.heading("X Field", text="X Axis Field"); self.tree.heading("Y Field", text="Y Axis Field"); self.tree.heading("Color", text="Color/Hex"); self.tree.heading("Flip", text="↕ Flip")
            self.tree.column("Name", width=100); self.tree.column("X Field", width=120); self.tree.column("Y Field", width=120); self.tree.column("Color", width=80); self.tree.column("Flip", width=44, anchor="center")
            self.tree.pack(side="left", fill="both", expand=True)
            for s in self.card.series:
                self.tree.insert("", "end", values=(s['name'], s['x_field'], s['y_field'], s['color'], "✓" if s.get("fm_inverted", False) else ""))
            _last_flip_click = [False]
            def _flip_toggle(event):
                col = self.tree.identify_column(event.x)
                _last_flip_click[0] = col == "#5"
                if col == "#5":
                    item = self.tree.identify_row(event.y)
                    if item:
                        vals = list(self.tree.item(item, "values"))
                        vals[4] = "" if vals[4] == "✓" else "✓"
                        self.tree.item(item, values=vals)
            self.tree.bind("<Button-1>", _flip_toggle)
            self.tree.bind("<Double-1>", lambda e: None if _last_flip_click[0] else self._edit_item())
            bf = tk.Frame(cf, bg=BG); bf.pack(side="right", fill="y", padx=5)
            tk.Button(bf, text="+ Add",  width=8, command=self._add_item).pack(pady=4)
            tk.Button(bf, text="- Del",  width=8, command=self._del_item).pack(pady=4)
            tk.Button(bf, text="▲ Up",   width=8, command=lambda: self._move_item(-1)).pack(pady=4)
            tk.Button(bf, text="▼ Down", width=8, command=lambda: self._move_item(1)).pack(pady=4)

            # ── Advanced tab: highchartsOptions editor ─────────────────────────
            _adv_c = tk.Canvas(_tab2, bg=BG, highlightthickness=0)
            _adv_sb = ttk.Scrollbar(_tab2, orient="vertical", command=_adv_c.yview)
            _adv_f = tk.Frame(_adv_c, bg=BG)
            _adv_f.bind("<Configure>", lambda e: _adv_c.configure(scrollregion=_adv_c.bbox("all")))
            _adv_c.create_window((0, 0), window=_adv_f, anchor="nw")
            _adv_c.configure(yscrollcommand=_adv_sb.set)
            _adv_sb.pack(side="right", fill="y")
            _adv_c.pack(side="left", fill="both", expand=True)
            _adv_c.bind("<MouseWheel>", lambda e: _adv_c.yview_scroll(int(-1*(e.delta/120)), "units"))

            def _load_hc():
                cn = getattr(self.card, 'orig_chart_node', None)
                if cn:
                    return cn.get("Config", {}).get("highchartsOptions", {})
                fn = getattr(self.card, 'orig_full_node', None)
                if fn:
                    try:
                        return fn["Slots"]["content"][0]["Slots"]["Default"][0].get("Config", {}).get("highchartsOptions", {})
                    except: pass
                return {}

            _hc0  = _load_hc()
            _hcc  = _hc0.get("chart", {})
            _hcx  = _hc0.get("xAxis", {}) if isinstance(_hc0.get("xAxis"), dict) else {}
            _hcy  = _hc0.get("yAxis", {}) if isinstance(_hc0.get("yAxis"), dict) else {}
            _hcpo = _hc0.get("plotOptions", {}).get("series", {})
            _hcdl = _hcpo.get("dataLabels", {}) if isinstance(_hcpo.get("dataLabels"), dict) else {}

            # ── Inline tooltip text for every advanced chart field ─────────────
            _FIELD_TIPS = {
                "hc_chart_height":          "Chart pixel height.\nLeave blank to let the chart fill its container (recommended).\nExample: 400",
                "hc_chart_zoomType":        "Zoom Type — lets users drag to zoom on the chart.\n• xy — zoom both axes\n• x — zoom horizontal only\n• y — zoom vertical only\n• (blank) — no zoom\nZoom resets on double-click.",
                "hc_chart_marginLeft":      "Pixels of space between the left edge of the SVG and the plot area.\nUseful when Y-axis labels are long and get clipped.",
                "hc_chart_marginRight":     "Pixels of space on the right side of the plot area.",
                "hc_chart_marginBottom":    "Pixels of space below the plot area.\nIncrease when X-axis labels are large.",
                "hc_chart_spacingBottom":   "Spacing between the chart edge and the plot border (bottom).\nDiffers from margin: spacing applies before the axis.",
                "hc_chart_spacingLeft":     "Spacing between the left chart edge and the plot area.",
                "hc_chart_spacingRight":    "Spacing between the right chart edge and the plot area.",
                "hc_chart_panning":         "Panning — lets users click-and-drag to pan the chart after zooming.\nBest used together with Zoom Type.\nPan Key sets which modifier key the user holds while panning.",
                "hc_chart_panKey":          "Pan Key — modifier key the user holds to pan (drag) the chart.\n• shift — hold Shift then drag\n• ctrl — hold Ctrl then drag\n• alt — hold Alt then drag\nOnly applies when Panning is enabled.",
                "hc_xaxis_min":             "Minimum value shown on the X axis.\nLeave blank for Highcharts to auto-calculate from data.",
                "hc_xaxis_gridLineWidth":   "Width in pixels of the vertical grid lines on the X axis.\n0 = hidden, 1 = subtle, 2+ = prominent.",
                "hc_xaxis_crosshair":       "Crosshair — draws a vertical line that follows the user's cursor\nacross the chart, making it easier to read exact X-axis values.\nMost useful on line, spline and area charts.",
                "hc_xaxis_scrollbar":       "X-axis Scrollbar — adds a scrollbar below the X axis\nso users can pan through a large dataset.\nBest combined with Zoom Type x.",
                "hc_xaxis_labels_fontSize": "Font size for X-axis tick labels (e.g. category names, dates).\nExample: 11px",
                "hc_yaxis_gridLineWidth":   "Width in pixels of the horizontal grid lines on the Y axis.\n0 = hidden, 1 = subtle (default), 2+ = prominent.",
                "hc_yaxis_reversedStacks":  "Reversed Stacks — when ON, the last series is drawn at the bottom\nof a stacked bar/column instead of the top.\nDefault Highcharts behaviour is reversed (ON).",
                "hc_yaxis_labels_enabled":  "Show Y-axis labels (the numeric values along the left/right edge).\nUncheck to hide them for a cleaner look.",
                "hc_yaxis_stackLabels_enabled": "Stack Labels — show the total value printed on top of each\nstacked bar or column.",
                "hc_yaxis_stackLabels_format":  "Number format for stack labels using Highcharts format strings.\nExample: {total:,.0f}  →  1,234\n         {total:.1f}%  →  12.3%",
                "hc_yaxis_stackLabels_fontSize":"Font size for stack total labels.\nExample: 11px",
                "hc_po_pointWidth":         "Fixed pixel width for each bar/column point.\nOverrides the auto-calculated width.\nLeave blank to let Highcharts fit bars to the available space.",
                "hc_po_maxPointWidth":      "Maximum pixel width a bar/column can grow to.\nPrevents very wide bars on sparse data sets.",
                "hc_po_pointPadding":       "Padding on each side of a point, as a fraction of the point width.\nDefault 0.1.  0 = bars touch each other.",
                "hc_po_groupPadding":       "Padding between groups of bars in a grouped chart.\nDefault 0.2.  0 = groups touch each other.",
                "hc_po_dl_enabled":         "Data Labels — print the value directly on top of (or inside)\neach bar, column, slice or point.\nUseful for dashboards where users need exact numbers.",
                "hc_po_dl_inside":          "Inside — place data labels inside the bar/column rather than above it.\nOften cleaner for tall bars.",
                "hc_po_dl_format":          "Highcharts format string for data labels.\nExamples:\n  {point.y:,.0f}   → 1,234\n  {point.y:.1f}%  → 12.3%\n  {point.name}    → category name",
                "hc_po_dl_fontSize":        "Font size for data labels printed on each bar/point.\nExample: 11px",
            }

            def _ef(parent, row, col, label, key, default, width=9):
                lbl = tk.Label(parent, text=label+":", bg=BG, fg=DARK, font=("Helvetica",9))
                lbl.grid(row=row, column=col*2, sticky="e", padx=(8,2), pady=3)
                v = tk.StringVar(value="" if default is None else str(default))
                self.vs[key] = v
                e = tk.Entry(parent, textvariable=v, width=width, font=("Helvetica",9))
                e.grid(row=row, column=col*2+1, sticky="w", padx=(0,8))
                tip = _FIELD_TIPS.get(key)
                if tip: Tooltip(lbl, tip); Tooltip(e, tip)

            def _bf(parent, row, col, label, key, default):
                v = tk.BooleanVar(value=bool(default))
                self.vs[key] = v
                cb = tk.Checkbutton(parent, text=label, variable=v, bg=BG, fg=DARK,
                                    font=("Helvetica",9))
                cb.grid(row=row, column=col*2, columnspan=2, sticky="w", padx=(8,0), pady=3)
                tip = _FIELD_TIPS.get(key)
                if tip: Tooltip(cb, tip)

            def _cf2(parent, row, col, label, key, opts, default, width=10):
                lbl = tk.Label(parent, text=label+":", bg=BG, fg=DARK, font=("Helvetica",9))
                lbl.grid(row=row, column=col*2, sticky="e", padx=(8,2), pady=3)
                v = tk.StringVar(value="" if default is None else str(default))
                self.vs[key] = v
                cb = ttk.Combobox(parent, textvariable=v, values=opts, width=width)
                cb.grid(row=row, column=col*2+1, sticky="w", padx=(0,8))
                tip = _FIELD_TIPS.get(key)
                if tip: Tooltip(lbl, tip); Tooltip(cb, tip)

            # ─ Chart ──────────────────────────────────────────────────────────
            _s_chart = tk.LabelFrame(_adv_f, text="Chart", bg=BG, fg=DARK,
                                     font=("Helvetica",9,"bold"), padx=8, pady=4)
            _s_chart.pack(fill="x", padx=12, pady=(8,3))
            _ef(_s_chart,  0, 0, "Height",         "hc_chart_height",        _hcc.get("height","auto"))
            _cf2(_s_chart, 0, 1, "Zoom Type",       "hc_chart_zoomType",      ["xy","x","y",""],             _hcc.get("zoomType","xy"))
            _ef(_s_chart,  1, 0, "Margin Left",     "hc_chart_marginLeft",    _hcc.get("marginLeft",""))
            _ef(_s_chart,  1, 1, "Margin Right",    "hc_chart_marginRight",   _hcc.get("marginRight",""))
            _ef(_s_chart,  2, 0, "Margin Bottom",   "hc_chart_marginBottom",  _hcc.get("marginBottom",""))
            _ef(_s_chart,  2, 1, "Spacing Bottom",  "hc_chart_spacingBottom", _hcc.get("spacingBottom",""))
            _ef(_s_chart,  3, 0, "Spacing Left",    "hc_chart_spacingLeft",   _hcc.get("spacingLeft",""))
            _ef(_s_chart,  3, 1, "Spacing Right",   "hc_chart_spacingRight",  _hcc.get("spacingRight",""))
            _bf(_s_chart,  4, 0, "Panning",         "hc_chart_panning",       _hcc.get("panning", False))
            _cf2(_s_chart, 4, 1, "Pan Key",         "hc_chart_panKey",        ["shift","ctrl","alt"],        _hcc.get("panKey","shift"))

            # ─ X Axis ─────────────────────────────────────────────────────────
            _s_xa = tk.LabelFrame(_adv_f, text="X Axis", bg=BG, fg=DARK,
                                  font=("Helvetica",9,"bold"), padx=8, pady=4)
            _s_xa.pack(fill="x", padx=12, pady=3)
            _ef(_s_xa, 0, 0, "Min",              "hc_xaxis_min",           _hcx.get("min",""))
            _ef(_s_xa, 0, 1, "Grid Line Width",  "hc_xaxis_gridLineWidth", _hcx.get("gridLineWidth",""))
            _bf(_s_xa, 1, 0, "Crosshair",        "hc_xaxis_crosshair",     _hcx.get("crosshair", False))
            _bf(_s_xa, 1, 1, "Scrollbar",        "hc_xaxis_scrollbar",
                (_hcx.get("scrollbar",{}).get("enabled", False) if isinstance(_hcx.get("scrollbar"), dict) else False))
            _ef(_s_xa, 2, 0, "Labels Font Size", "hc_xaxis_labels_fontSize",
                (_hcx.get("labels",{}).get("style",{}).get("fontSize","") if isinstance(_hcx.get("labels"), dict) else ""))

            # ─ Y Axis ─────────────────────────────────────────────────────────
            _s_ya = tk.LabelFrame(_adv_f, text="Y Axis", bg=BG, fg=DARK,
                                  font=("Helvetica",9,"bold"), padx=8, pady=4)
            _s_ya.pack(fill="x", padx=12, pady=3)
            _ef(_s_ya, 0, 0, "Grid Line Width",   "hc_yaxis_gridLineWidth",  _hcy.get("gridLineWidth",""))
            _bf(_s_ya, 0, 1, "Reversed Stacks",   "hc_yaxis_reversedStacks", _hcy.get("reversedStacks", False))
            _bf(_s_ya, 1, 0, "Show Y Labels",     "hc_yaxis_labels_enabled",
                (_hcy.get("labels",{}).get("enabled", True) if isinstance(_hcy.get("labels"), dict) else True))
            _bf(_s_ya, 2, 0, "Stack Labels",      "hc_yaxis_stackLabels_enabled",
                (_hcy.get("stackLabels",{}).get("enabled", False) if isinstance(_hcy.get("stackLabels"), dict) else False))
            _ef(_s_ya, 3, 0, "Stack Format",      "hc_yaxis_stackLabels_format",
                (_hcy.get("stackLabels",{}).get("format","{total:,.0f}") if isinstance(_hcy.get("stackLabels"), dict) else "{total:,.0f}"), width=16)
            _ef(_s_ya, 3, 1, "Stack Font Size",   "hc_yaxis_stackLabels_fontSize",
                (_hcy.get("stackLabels",{}).get("style",{}).get("fontSize","") if isinstance(_hcy.get("stackLabels"), dict) else ""))

            # ─ Plot Options ───────────────────────────────────────────────────
            _s_po = tk.LabelFrame(_adv_f, text="Plot Options (series)", bg=BG, fg=DARK,
                                  font=("Helvetica",9,"bold"), padx=8, pady=4)
            _s_po.pack(fill="x", padx=12, pady=3)
            _ef(_s_po, 0, 0, "Point Width",     "hc_po_pointWidth",    _hcpo.get("pointWidth",""))
            _ef(_s_po, 0, 1, "Max Point Width", "hc_po_maxPointWidth", _hcpo.get("maxPointWidth",""))
            _ef(_s_po, 1, 0, "Point Padding",   "hc_po_pointPadding",  _hcpo.get("pointPadding",""))
            _ef(_s_po, 1, 1, "Group Padding",   "hc_po_groupPadding",  _hcpo.get("groupPadding",""))
            _bf(_s_po, 2, 0, "Data Labels",     "hc_po_dl_enabled",    _hcdl.get("enabled", False))
            _bf(_s_po, 2, 1, "Labels Inside",   "hc_po_dl_inside",     _hcdl.get("inside", True))
            _ef(_s_po, 3, 0, "Labels Format",   "hc_po_dl_format",     _hcdl.get("format","{point.y:,.0f}"), width=16)
            _ef(_s_po, 3, 1, "Labels Font",     "hc_po_dl_fontSize",
                (_hcdl.get("style",{}).get("fontSize","") if isinstance(_hcdl.get("style"), dict) else ""))

        btns=tk.Frame(self,bg=BG); btns.pack(pady=12)
        tk.Button(btns,text="Apply",bg=BTN_OK_BG, fg=BTN_OK_FG,font=("Helvetica",10,"bold"),relief="flat",padx=16,pady=6,cursor="hand2",command=self._apply).pack(side="left",padx=6)
        tk.Button(btns,text="Cancel",bg=BORDER,fg=DARK,font=("Helvetica",10),relief="flat",padx=16,pady=6,cursor="hand2",command=self.destroy).pack(side="left",padx=6)

    def _add_item(self):
        if self.card.ctype == "metrics":
            new_vals = self._row_edit_dialog("Add KPI Tile",
                ["Display Label (e.g. Total Messages)", "Data Field Key (e.g. TOTAL_MSG)", "Unit (e.g. % or leave blank)"],
                ["", "", ""])
            if new_vals: self.tree.insert("", "end", values=new_vals)
        elif self.card.ctype == "table":
            f = simpledialog.askstring("Add Column", "Enter pure Data Key (e.g. Failure %):", parent=self)
            if f:
                t = simpledialog.askstring("Add Column", "Enter Display Title:", parent=self)
                if t: self.tree.insert("", "end", values=(f, t))
        elif self.card.ctype in RIVER_TYPES:
            k = simpledialog.askstring("Add Config", "Config Key (e.g. LabelKey):", parent=self)
            if k:
                v = simpledialog.askstring("Add Config", f"Value for '{k}':", initialvalue="", parent=self)
                if v is not None: self.tree.insert("", "end", values=(k, v))
        else:
            n = simpledialog.askstring("Add Series", "Series Name (e.g. Total):", parent=self)
            if n:
                x = simpledialog.askstring("Add Series", "X Axis Field (e.g. MESSAGE_TYPE):", parent=self)
                y = simpledialog.askstring("Add Series", "Y Axis Field (e.g. MSG_COUNT):", parent=self)
                c = simpledialog.askstring("Add Series", "Color (Hex or 'colorByPoint'):", initialvalue="colorByPoint", parent=self)
                self.tree.insert("", "end", values=(n, x, y, c, ""))

    def _del_item(self):
        sel = self.tree.selection(); 
        if sel: self.tree.delete(sel[0])

    def _row_edit_dialog(self, title, col_labels, current_vals):
        """Show a single modal window with one Entry per column. Returns tuple of new values or None."""
        result = [None]
        dlg = tk.Toplevel(self); dlg.title(title); dlg.configure(bg=BG)
        dlg.grab_set(); dlg.transient(self)
        entry_vars = []; first_widget = None
        for i, lbl in enumerate(col_labels):
            row = tk.Frame(dlg, bg=BG); row.pack(fill="x", padx=18, pady=5)
            tk.Label(row, text=lbl + ":", bg=BG, fg=DARK,
                     font=("Helvetica", 9, "bold"), width=26, anchor="w").pack(side="left")
            var = tk.StringVar(value=current_vals[i] if i < len(current_vals) else "")
            e = tk.Entry(row, textvariable=var, width=36, font=("Helvetica", 10))
            e.pack(side="left", padx=(4, 0))
            entry_vars.append(var)
            if first_widget is None: first_widget = e
        def _ok():
            result[0] = tuple(v.get() for v in entry_vars)
            dlg.destroy()
        def _cancel(): dlg.destroy()
        bf = tk.Frame(dlg, bg=BG); bf.pack(pady=10)
        tk.Button(bf, text="OK", bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica", 9, "bold"),
                  padx=14, pady=4, cursor="hand2", command=_ok).pack(side="left", padx=6)
        tk.Button(bf, text="Cancel", bg=BORDER, fg=DARK, font=("Helvetica", 9),
                  padx=14, pady=4, cursor="hand2", command=_cancel).pack(side="left", padx=6)
        if first_widget: first_widget.focus_set()
        dlg.bind("<Return>", lambda e: _ok())
        dlg.bind("<Escape>", lambda e: _cancel())
        self.wait_window(dlg)
        return result[0]

    def _edit_item(self):
        if not self.tree: return
        sel = self.tree.selection()
        if not sel: return
        item = sel[0]; vals = self.tree.item(item, "values")
        if self.card.ctype == "metrics":
            new_vals = self._row_edit_dialog("Edit KPI Tile",
                ["Display Label", "Data Field Key", "Unit (optional)"], vals)
            if new_vals: self.tree.item(item, values=new_vals)
        elif self.card.ctype == "table":
            new_vals = self._row_edit_dialog("Edit Column",
                ["Data Key  (e.g. FAILURE_PCT)", "Display Title"], vals)
            if new_vals: self.tree.item(item, values=new_vals)
        elif self.card.ctype in RIVER_TYPES:
            new_vals = self._row_edit_dialog("Edit Config",
                ["Config Key", "Value  (JSON arrays/objects OK)"], vals)
            if new_vals: self.tree.item(item, values=new_vals)
        else:
            new_vals = self._row_edit_dialog("Edit Series",
                ["Series Name", "X Axis Field", "Y Axis Field", "Color / Hex"], vals[:4])
            if new_vals:
                flip_val = vals[4] if len(vals) > 4 else ""
                self.tree.item(item, values=(*new_vals, flip_val))

    def _arr_edit(self):
        if not self.arr_tree: return
        sel = self.arr_tree.selection()
        if not sel: return
        item = sel[0]; vals = self.arr_tree.item(item, "values")
        col_labels = [cl for _, cl, _ in self.arr_schema_cols]
        new_vals = self._row_edit_dialog("Edit Item", col_labels, vals)
        if new_vals: self.arr_tree.item(item, values=new_vals)

    def _arr_add(self):
        col_labels = [cl for _, cl, _ in self.arr_schema_cols]
        new_vals = self._row_edit_dialog("Add Item", col_labels, [""] * len(col_labels))
        if new_vals: self.arr_tree.insert("", "end", values=new_vals)

    def _arr_del(self):
        sel = self.arr_tree.selection()
        if sel: self.arr_tree.delete(sel[0])

    def _move_item(self, direction):
        tree = self.arr_tree if self.arr_tree else self.tree
        if not tree: return
        sel = tree.selection()
        if not sel: return
        item = sel[0]; idx = tree.index(item); tree.move(item, tree.parent(item), idx + direction)

    def _edit_col_link(self):
        if not self.tree: return
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("Select Column", "Select a column row first.", parent=self); return
        vals = self.tree.item(sel[0], "values")
        field = vals[0]; title = vals[1]
        self.grab_release()
        dlg = LinkDialog(self, field, title, self._col_links.get(field))
        self.wait_window(dlg)
        self.grab_set()
        if dlg.result is None: return
        _ev3 = getattr(self, '_col_events', {}).get(field)
        if dlg.result == {}:
            self._col_links.pop(field, None)
            _lbl3 = ""
            if _ev3:
                _lbl3 = f"⚡ {_ev3.get('event_id','')}" + (f" [{_ev3.get('filter_id','')}]" if _ev3.get('filter_id') else "")
            self.tree.item(sel[0], values=(field, title, _lbl3))
        else:
            self._col_links[field] = dlg.result
            lk2 = dlg.result
            if lk2.get("event_type") == "event_click":
                _eid2 = lk2.get("event_id", "")
                _fid2 = lk2.get("filter_id", "")
                _lbl2 = f"🎯 {_eid2}" + (f" [{_fid2}]" if _fid2 else "")
            else:
                _lbl2 = f"🔗 {lk2.get('menu_id','') or lk2.get('to_entity','') or 'link'}"
            if _ev3:
                _lbl2 += f"  +⚡{_ev3.get('event_id','')}"
            self.tree.item(sel[0], values=(field, title, _lbl2))
        # Mark card as config-edited so exporter rebuilds from card state rather than orig_full_node
        self.card._config_edited = True

    def _edit_col_event(self):
        if not self.tree: return
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("Select Column", "Select a column row first.", parent=self); return
        vals = self.tree.item(sel[0], "values")
        field = vals[0]; title = vals[1]
        existing = getattr(self, '_col_events', {}).get(field, {})

        dlg = tk.Toplevel(self)
        dlg.title(f"Column Events — {title}")
        dlg.geometry("580x420"); dlg.configure(bg=BG)
        dlg.transient(self); dlg.grab_set()

        tk.Label(dlg, text=f"OnClick event for column: {title}", bg=BG, fg=DARK,
                 font=("Helvetica",11,"bold")).pack(padx=16, pady=(12,4), anchor="w")
        tk.Label(dlg, text=(
            "Adds Events.Triggers.OnClick to the column's slot element.\n"
            "Use 'Input expression' for map({tabName:..., filterId:..., filterValue:...}) style events.\n"
            "Or use filterSection/filterId fields for Payload-based events."
        ), bg=BG, fg=MUTED, font=("Helvetica",8), justify="left").pack(padx=16, anchor="w")

        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(8,4))

        f = tk.Frame(dlg, bg=BG); f.pack(fill="x", padx=16); f.columnconfigure(1, weight=1)
        fields_ev = [
            ("event_id",       "EventId",                        existing.get("event_id",       "open-tab-detail")),
            ("container_id",   "ContainerId",                    existing.get("container_id",   "header-action-fragment")),
            ("filter_section", "Payload → filterSection (opt.)", existing.get("filter_section", "Filters")),
            ("filter_id",      "Payload → filterId (opt.)",      existing.get("filter_id",      "")),
        ]
        _ev_vars = {}
        for i, (key, lbl, val) in enumerate(fields_ev):
            tk.Label(f, text=lbl+":", bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                     width=32, anchor="w").grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=val); _ev_vars[key] = v
            tk.Entry(f, textvariable=v, width=28, font=("Helvetica",10)
                     ).grid(row=i, column=1, sticky="ew", padx=(4,0), pady=4)

        # Input expression field (for map({tabName:..., filterValue:...}) style)
        tk.Label(f, text="Input expression (opt.):", bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                 width=32, anchor="w").grid(row=len(fields_ev), column=0, sticky="nw", pady=4)
        _expr_frame = tk.Frame(f, bg=BG)
        _expr_frame.grid(row=len(fields_ev), column=1, sticky="ew", padx=(4,0), pady=4)
        _expr_text = tk.Text(_expr_frame, height=3, width=30, font=("Helvetica",9),
                             wrap="word", relief="solid", bd=1)
        _expr_text.pack(fill="x", expand=True)
        _expr_text.insert("1.0", existing.get("input_expr", ""))
        tk.Label(f, text="e.g. map({tabName: 'Tab1', filterId: 'X', filterValue: FIELD})",
                 bg=BG, fg=MUTED, font=("Helvetica",7)).grid(
                 row=len(fields_ev)+1, column=1, sticky="w", padx=(4,0))

        result = [None]
        def _save():
            d = {k: v.get().strip() for k, v in _ev_vars.items()}
            d["input_expr"] = _expr_text.get("1.0", "end").strip()
            result[0] = d
            dlg.destroy()
        def _clear():
            result[0] = {}
            dlg.destroy()

        bf = tk.Frame(dlg, bg=BG); bf.pack(pady=10)
        tk.Button(bf, text="Apply",        bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica",10,"bold"),
                  padx=12, pady=4, cursor="hand2", command=_save).pack(side="left", padx=6)
        tk.Button(bf, text="Clear Events", bg=BTN_WARN_BG, fg=BTN_WARN_FG, font=("Helvetica",10),
                  padx=12, pady=4, cursor="hand2", command=_clear).pack(side="left", padx=6)
        tk.Button(bf, text="Cancel",       bg=BORDER, fg=DARK,   font=("Helvetica",10),
                  padx=12, pady=4, cursor="hand2", command=dlg.destroy).pack(side="left", padx=6)

        self.grab_release(); dlg.focus_force()
        self.wait_window(dlg); self.grab_set()

        if result[0] is None: return
        if not hasattr(self, '_col_events'): self._col_events = {}

        _lk4 = self._col_links.get(field)
        if result[0] == {}:
            self._col_events.pop(field, None)
            _lbl4 = ""
            if _lk4:
                if _lk4.get("event_type") == "event_click":
                    _lbl4 = f"🎯 {_lk4.get('event_id','')}" + (f" [{_lk4.get('filter_id','')}]" if _lk4.get('filter_id') else "")
                else:
                    _lbl4 = f"🔗 {_lk4.get('menu_id','') or _lk4.get('to_entity','') or 'link'}"
        else:
            self._col_events[field] = result[0]
            _eid4 = result[0].get("event_id","")
            _fid4 = result[0].get("filter_id","")
            _has_expr4 = bool(result[0].get("input_expr", ""))
            _ev_part = f"⚡ {_eid4}" + (f" [map]" if _has_expr4 else (f" [{_fid4}]" if _fid4 else ""))
            if _lk4:
                if _lk4.get("event_type") == "event_click":
                    _lbl4 = f"🎯 {_lk4.get('event_id','')}"
                else:
                    _lbl4 = f"🔗 {_lk4.get('menu_id','') or _lk4.get('to_entity','') or 'link'}"
                _lbl4 += f"  +{_ev_part}"
            else:
                _lbl4 = _ev_part
        self.tree.item(sel[0], values=(field, title, _lbl4))
        # Mark card as config-edited so exporter rebuilds from card state rather than orig_full_node
        self.card._config_edited = True

    def _apply(self):
        self.card.title = self.vs["tv"].get()
        if "dsv" in self.vs: self.card.ds = self.vs["dsv"].get()
        if "bvv" in self.vs: self.card.bvar = self.vs["bvv"].get()
        self.card.css_width = self.vs["wsv"].get()
        self.card.css_height = self.vs["hsv"].get()
        if "ctv" in self.vs: self.card.ctype = self.vs["ctv"].get()
        
        try:
            if "px" in self.card.css_width: self.card.config(width=int(self.card.css_width.replace("px","").strip()))
            if "px" in self.card.css_height: self.card.config(height=int(self.card.css_height.replace("px","").strip()))
        except: pass
        
        if self.card.ctype == "metrics":
            self.card.metrics = [{"label": self.tree.item(r,"values")[0], "field": self.tree.item(r,"values")[1], "unit": self.tree.item(r,"values")[2]} for r in self.tree.get_children()]
        elif self.card.ctype == "table":
            self.card.has_footer      = self.vs["footer"].get()
            self.card.has_checkboxes   = self.vs["checkboxes"].get()
            self.card.has_multiselect  = self.vs["multiselect"].get()
            self.card.has_agentic      = self.vs["agentic"].get()
            self.card.agent_id         = self.vs["agent_id"].get()
            raw_args = self.vs.get("agent_args", tk.StringVar()).get()
            self.card.agent_args = [a.strip() for a in raw_args.split(",") if a.strip()]
            self.card.agent_question = self.vs.get("agent_question", tk.StringVar()).get()
            self.card.columns = [{"field": self.tree.item(item, "values")[0], "title": self.tree.item(item, "values")[1], "link": self._col_links.get(self.tree.item(item, "values")[0]), "events": getattr(self, '_col_events', {}).get(self.tree.item(item, "values")[0])} for item in self.tree.get_children()]
            self.card.has_insights     = self.vs["insights"].get()
            self.card.insights_field   = self.vs["insights_field"].get() or "TicketsList"
            self.card.insights_agent_id = self.vs["insights_agent_id"].get()
        elif self.card.ctype in RIVER_TYPES:
            self.card.elem_input = self.vs.get("elem_input", tk.StringVar()).get()
            new_cfg = dict(self.card.elem_config)
            # schema cfg/bool/enum fields — only write non-empty values
            onclick_container = onclick_event = ""
            for key, var in self.schema_vars.items():
                val = var.get()
                if key == "__onclick_container": onclick_container = val; continue
                if key == "__onclick_event":     onclick_event = val; continue
                if val != "" or key in new_cfg:  # keep existing keys; only add new if non-empty
                    if val == "" and key not in dict(self.card.elem_config):
                        continue  # don't inject empty keys that weren't originally in config
                    new_cfg[key] = val
            # rebuild OnClick event from the two helper fields
            if onclick_container or onclick_event:
                evts = dict(self.card.events)
                evts.setdefault("Triggers", {})["OnClick"] = [{"ContainerId": onclick_container, "EventId": onclick_event}]
                self.card.events = evts
            # strip keys whose value is empty string and weren't in original imported config
            new_cfg = {k: v for k, v in new_cfg.items() if v != "" or k in self.card.elem_config}
            # schema array field
            if self.arr_tree and self.arr_key:
                items = []
                for row_id in self.arr_tree.get_children():
                    vals = self.arr_tree.item(row_id, "values")
                    items.append({self.arr_schema_cols[i][0]: vals[i] for i in range(len(self.arr_schema_cols))})
                new_cfg[self.arr_key] = items
            # fallback: generic tree (types with no schema)
            elif self.tree:
                new_cfg = {}
                for item in self.tree.get_children():
                    k, v = self.tree.item(item, "values")[0], self.tree.item(item, "values")[1]
                    try: new_cfg[k] = json.loads(v)
                    except: new_cfg[k] = v
            self.card.elem_config = new_cfg
            # schema style fields
            new_sty = dict(self.card.elem_style or {})
            for dot_key, var in self.sty_vars.items():
                val = var.get()
                parts = dot_key.split(".")
                if len(parts) == 1:
                    new_sty[parts[0]] = val
                else:
                    if parts[0] not in new_sty or not isinstance(new_sty[parts[0]], dict):
                        new_sty[parts[0]] = {}
                    new_sty[parts[0]][parts[1]] = val
            self.card.elem_style = new_sty

            # ── Tab-group: apply per-slot filter panel config ──────────────
            if self.card.ctype == "tab-group" and hasattr(self, '_slot_fp_vars'):
                _tg_orig = getattr(self.card, 'orig_full_node', None)
                if _tg_orig is not None:
                    for _sn, _fv in self._slot_fp_vars.items():
                        _has   = _fv["has"].get()
                        _pos   = _fv["pos"].get()
                        _sitems = _tg_orig.get("Slots", {}).get(_sn, [])
                        if not isinstance(_sitems, list):
                            _sitems = [_sitems] if _sitems else []

                        # Strip ALL existing filter-panel nodes from slot items
                        def _strip_fp(items):
                            out = []
                            for _it in items:
                                if isinstance(_it, dict) and (
                                        _it.get("Element") == "filter-panel"
                                        or _it.get("Container") == "filter-panel"):
                                    continue
                                out.append(_it)
                            return out

                        _cleaned = _strip_fp(_sitems)

                        if _has and _pos != "none":
                            # Reuse existing node (preserves Attributes) or build from UI rows
                            _old_fp = _fv.get("fp_node")
                            if _old_fp:
                                _new_fp = copy.deepcopy(_old_fp)
                            else:
                                # No existing filter in slot — populate from UI filter rows so
                                # Attributes are not empty when the user checks "Has Filter".
                                _new_fp, _ = self.app._build_filter_element()
                            _new_fp.setdefault("Config", {})["Position"] = _pos
                            _tg_orig["Slots"][_sn] = [_new_fp] + _cleaned

                            # Refresh any expanded canvas card for this slot
                            for _cc in list(self.app.cards.values()):
                                if (getattr(_cc, '_tg_parent', None) == self.card.cid
                                        and getattr(_cc, '_tg_slot', None) == _sn
                                        and getattr(_cc, '_tg_passthrough_node', None) is not None):
                                    _pt = _cc._tg_passthrough_node
                                    if (isinstance(_pt, dict) and (
                                            _pt.get("Element") == "filter-panel"
                                            or _pt.get("Container") == "filter-panel")):
                                        _cc._tg_passthrough_node = _new_fp
                                        _pos_lbl = {"left": "Left", "right": "Right",
                                                    "top": "Top"}.get(_pos, _pos)
                                        _ac = len(_new_fp.get("Config", {}).get("Attributes", []))
                                        _cc.title = (f"🔎 Filter — {_pos_lbl} ({_ac} attr)"
                                                     if _ac else f"🔎 Filter — {_pos_lbl}")
                                        _cc.rebuild()
                        else:
                            _tg_orig["Slots"][_sn] = _cleaned
                            # Remove expanded canvas filter-panel card if present
                            for _cc in list(self.app.cards.values()):
                                if (getattr(_cc, '_tg_parent', None) == self.card.cid
                                        and getattr(_cc, '_tg_slot', None) == _sn):
                                    _pt = getattr(_cc, '_tg_passthrough_node', None)
                                    if (isinstance(_pt, dict) and (
                                            _pt.get("Element") == "filter-panel"
                                            or _pt.get("Container") == "filter-panel")):
                                        self.app.remove_comp(_cc.cid)

        else:
            self.card.series = [{"name": self.tree.item(item, "values")[0], "x_field": self.tree.item(item, "values")[1], "y_field": self.tree.item(item, "values")[2], "color": self.tree.item(item, "values")[3], "fm_inverted": (self.tree.item(item, "values")[4] == "✓") if len(self.tree.item(item, "values")) > 4 else False} for item in self.tree.get_children()]
            # Apply stacking toggle to chart card and update orig_chart_node
            if "chart_stacking" in self.vs:
                _stacking = self.vs["chart_stacking"].get()
                self.card.chart_stacking = _stacking
                _stk_val = "normal" if _stacking else None
                _cn = getattr(self.card, 'orig_chart_node', None)
                if _cn is not None:
                    _po = _cn.setdefault("Config", {}).setdefault("highchartsOptions", {}).setdefault("plotOptions", {})
                    for _pk in ("series", self.card.ctype):
                        _po.setdefault(_pk, {})
                        if _stk_val: _po[_pk]["stacking"] = _stk_val
                        else: _po[_pk].pop("stacking", None)
                _fn = getattr(self.card, 'orig_full_node', None)
                if _fn is not None:
                    try:
                        _ic_fn = _fn["Slots"]["content"][0]["Slots"]["Default"][0]
                        _po_fn = _ic_fn.setdefault("Config", {}).setdefault("highchartsOptions", {}).setdefault("plotOptions", {})
                        for _pk in ("series", self.card.ctype):
                            _po_fn.setdefault(_pk, {})
                            if _stk_val: _po_fn[_pk]["stacking"] = _stk_val
                            else: _po_fn[_pk].pop("stacking", None)
                    except: pass

            # Apply legend options to card attrs and orig nodes
            if "legend_enabled" in self.vs:
                try: _ly = int(self.vs["legend_y"].get())
                except ValueError: _ly = 0
                self.card.chart_legend_enabled = self.vs["legend_enabled"].get()
                self.card.chart_legend_layout  = self.vs["legend_layout"].get()
                self.card.chart_legend_valign  = self.vs["legend_verticalAlign"].get()
                self.card.chart_legend_align   = self.vs["legend_align"].get()
                self.card.chart_legend_y       = _ly
                _lg_val = {
                    "enabled":       self.card.chart_legend_enabled,
                    "layout":        self.card.chart_legend_layout,
                    "verticalAlign": self.card.chart_legend_valign,
                    "align":         self.card.chart_legend_align,
                    "y":             self.card.chart_legend_y,
                }
                _cn = getattr(self.card, 'orig_chart_node', None)
                if _cn is not None:
                    _cn.setdefault("Config", {}).setdefault("highchartsOptions", {})["legend"] = _lg_val
                _fn = getattr(self.card, 'orig_full_node', None)
                if _fn is not None:
                    try:
                        _ic_lg = _fn["Slots"]["content"][0]["Slots"]["Default"][0]
                        _ic_lg.setdefault("Config", {}).setdefault("highchartsOptions", {})["legend"] = _lg_val
                    except: pass

            # Apply Advanced highchartsOptions
            if "hc_chart_height" in self.vs:
                def _sv(key):
                    v = self.vs.get(key)
                    return v.get() if v else ""
                def _bv(key):
                    v = self.vs.get(key)
                    return v.get() if isinstance(v, tk.BooleanVar) else False
                def _iv(key):
                    raw = _sv(key)
                    try: return int(raw)
                    except: return None
                def _fv(key):
                    raw = _sv(key)
                    try: return float(raw)
                    except: return None

                def _patch_hc(hc):
                    c = hc.setdefault("chart", {})
                    if _sv("hc_chart_height"):       c["height"]       = _sv("hc_chart_height")
                    if _iv("hc_chart_marginLeft") is not None:  c["marginLeft"]  = _iv("hc_chart_marginLeft")
                    if _iv("hc_chart_marginRight") is not None: c["marginRight"] = _iv("hc_chart_marginRight")
                    if _iv("hc_chart_marginBottom") is not None: c["marginBottom"] = _iv("hc_chart_marginBottom")
                    if _iv("hc_chart_spacingLeft") is not None:  c["spacingLeft"]  = _iv("hc_chart_spacingLeft")
                    if _iv("hc_chart_spacingRight") is not None: c["spacingRight"] = _iv("hc_chart_spacingRight")
                    if _iv("hc_chart_spacingBottom") is not None: c["spacingBottom"] = _iv("hc_chart_spacingBottom")
                    if _sv("hc_chart_zoomType"): c["zoomType"] = _sv("hc_chart_zoomType")
                    c["panning"] = _bv("hc_chart_panning")
                    if _sv("hc_chart_panKey"): c["panKey"] = _sv("hc_chart_panKey")

                    xa = hc.setdefault("xAxis", {})
                    if _iv("hc_xaxis_min") is not None: xa["min"] = _iv("hc_xaxis_min")
                    if _iv("hc_xaxis_gridLineWidth") is not None: xa["gridLineWidth"] = _iv("hc_xaxis_gridLineWidth")
                    xa["crosshair"] = _bv("hc_xaxis_crosshair")
                    xa.setdefault("scrollbar", {})["enabled"] = _bv("hc_xaxis_scrollbar")
                    if _sv("hc_xaxis_labels_fontSize"):
                        xa.setdefault("labels", {}).setdefault("style", {})["fontSize"] = _sv("hc_xaxis_labels_fontSize")

                    ya = hc.setdefault("yAxis", {})
                    if _iv("hc_yaxis_gridLineWidth") is not None: ya["gridLineWidth"] = _iv("hc_yaxis_gridLineWidth")
                    ya["reversedStacks"] = _bv("hc_yaxis_reversedStacks")
                    ya.setdefault("labels", {})["enabled"] = _bv("hc_yaxis_labels_enabled")
                    sl = ya.setdefault("stackLabels", {})
                    sl["enabled"] = _bv("hc_yaxis_stackLabels_enabled")
                    if _sv("hc_yaxis_stackLabels_format"):  sl["format"] = _sv("hc_yaxis_stackLabels_format")
                    if _sv("hc_yaxis_stackLabels_fontSize"): sl.setdefault("style", {})["fontSize"] = _sv("hc_yaxis_stackLabels_fontSize")

                    pos = hc.setdefault("plotOptions", {}).setdefault("series", {})
                    if _iv("hc_po_pointWidth") is not None:    pos["pointWidth"]    = _iv("hc_po_pointWidth")
                    if _iv("hc_po_maxPointWidth") is not None: pos["maxPointWidth"] = _iv("hc_po_maxPointWidth")
                    if _fv("hc_po_pointPadding") is not None:  pos["pointPadding"]  = _fv("hc_po_pointPadding")
                    if _fv("hc_po_groupPadding") is not None:  pos["groupPadding"]  = _fv("hc_po_groupPadding")
                    dl = pos.setdefault("dataLabels", {})
                    dl["enabled"] = _bv("hc_po_dl_enabled")
                    dl["inside"]  = _bv("hc_po_dl_inside")
                    if _sv("hc_po_dl_format"):   dl["format"] = _sv("hc_po_dl_format")
                    if _sv("hc_po_dl_fontSize"): dl.setdefault("style", {})["fontSize"] = _sv("hc_po_dl_fontSize")

                # Store on card so native-chart export path also applies these settings
                _adv_fresh = {}
                _patch_hc(_adv_fresh)
                self.card.hc_adv = _adv_fresh

                _cn = getattr(self.card, 'orig_chart_node', None)
                if _cn is not None:
                    _patch_hc(_cn.setdefault("Config", {}).setdefault("highchartsOptions", {}))
                _fn = getattr(self.card, 'orig_full_node', None)
                if _fn is not None:
                    try:
                        _ic_adv = _fn["Slots"]["content"][0]["Slots"]["Default"][0]
                        _patch_hc(_ic_adv.setdefault("Config", {}).setdefault("highchartsOptions", {}))
                    except: pass

        new_seg = self.vs["seg"].get().strip()
        self.card.segment = new_seg
        if new_seg:
            self.app.segment_dirs.setdefault(new_seg, {"direction": "row", "gap": "0rem", "section_name": new_seg})
            self.app.segment_dirs[new_seg]["direction"] = self.vs["seg_dir"].get()
            self.app.segment_dirs[new_seg]["gap"] = self.vs["seg_gap"].get()
            _ACTION_BTNS = {"button", "button-icon", "action-button", "actions-popover", "link"}
            if self.card.ctype in _ACTION_BTNS and not self.app.segment_dirs[new_seg].get("container_type"):
                self.app.segment_dirs[new_seg]["container_type"] = "header-action"
                self.app.segment_dirs[new_seg].setdefault("config", {"SectionName": new_seg})
                self.app.segment_dirs[new_seg].setdefault("style", {"css": {}})
        # Mark card as config-edited so exporter rebuilds from card state rather than orig_full_node.
        self.card._config_edited = True
        # ── Debug log card edit ──────────────────────────────────────
        _dbg_seg = getattr(self.card, 'segment', '') or ''
        _dbg_title = getattr(self.card, 'title', '')
        _dbg_detail = (f"Edited {self.card.ctype} card '{_dbg_title}'"
                       + (f" segment='{_dbg_seg}'" if _dbg_seg else "")
                       + f" w={getattr(self.card,'css_width','')} h={getattr(self.card,'css_height','')}")
        self.app._debug_log_event("CARD_EDIT", _dbg_detail)
        self.card.rebuild(); self.destroy()

# ───────────────────────────────────────────────────────────────
#  LINK DIALOG  (LegacyLink config per table column)
# ───────────────────────────────────────────────────────────────
class LinkDialog(tk.Toplevel):
    """Modal dialog to configure a column link — EventId-based tab navigation or legacy drill-through.
    result == None  → user cancelled (no change)
    result == {}    → user cleared the link
    result == {...} → new/updated link config (includes event_type key)
    """
    def __init__(self, parent, col_field, col_title, existing_link=None):
        super().__init__(parent)
        self.title(f"Configure Link — {col_title}")
        self.geometry("650x600"); self.configure(bg=BG)
        self.result = None
        lk = existing_link or {}
        self._col_field = col_field
        self._col_title = col_title

        # ── Mode selector ──────────────────────────────────────────
        mode_fr = tk.Frame(self, bg=BG); mode_fr.pack(fill="x", padx=16, pady=(10,4))
        tk.Label(mode_fr, text="Link Type:", bg=BG, fg=DARK,
                 font=("Helvetica",10,"bold")).pack(side="left")
        _init_mode = lk.get("event_type", "legacy")
        if _init_mode not in ("event_click", "legacy"): _init_mode = "legacy"
        self._mode = tk.StringVar(value=_init_mode)
        tk.Radiobutton(mode_fr, text="🎯 Event Click  (EventId / tab navigation)",
                       variable=self._mode, value="event_click",
                       bg=BG, fg=DARK, font=("Helvetica",9),
                       activebackground=BG, command=self._refresh_mode
                       ).pack(side="left", padx=(12,0))
        tk.Radiobutton(mode_fr, text="🔗 Legacy Link  (drill-through / navigate)",
                       variable=self._mode, value="legacy",
                       bg=BG, fg=DARK, font=("Helvetica",9),
                       activebackground=BG, command=self._refresh_mode
                       ).pack(side="left", padx=(12,0))

        # ── Scrollable body ────────────────────────────────────────
        self._body = tk.Frame(self, bg=BG); self._body.pack(fill="both", expand=True, padx=16)

        # ── Buttons ────────────────────────────────────────────────
        btns = tk.Frame(self, bg=BG); btns.pack(pady=10)
        tk.Button(btns, text="Apply",      bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica",10,"bold"),
                  padx=14, pady=5, cursor="hand2", command=self._apply).pack(side="left", padx=6)
        tk.Button(btns, text="Clear Link", bg=BTN_WARN_BG, fg=BTN_WARN_FG, font=("Helvetica",10),
                  padx=14, pady=5, cursor="hand2", command=self._clear).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel",     bg=BORDER, fg=DARK,   font=("Helvetica",10),
                  padx=14, pady=5, cursor="hand2", command=self.destroy).pack(side="left", padx=6)

        self._lk = lk
        self._ev_vs = {}; self._leg_vs = {}; self._rk_tree = None
        self._refresh_mode()
        self.transient(parent)
        self.update_idletasks()
        self.lift(); self.focus_force()
        self.grab_set()

    def _refresh_mode(self):
        for w in self._body.winfo_children(): w.destroy()
        if self._mode.get() == "event_click":
            self._build_event_click()
        else:
            self._build_legacy()

    def _build_event_click(self):
        lk = self._lk if self._lk.get("event_type") == "event_click" else {}
        f = tk.Frame(self._body, bg=BG); f.pack(fill="x", pady=4)
        f.columnconfigure(1, weight=1)
        fields = [
            ("event_id",       "EventId",                        lk.get("event_id",       "open-tab-detail")),
            ("container_id",   "ContainerId",                    lk.get("container_id",   "header-action-fragment")),
            ("filter_section", "Payload → filterSection (opt.)", lk.get("filter_section", "Filters")),
            ("filter_id",      "Payload → filterId (opt.)",      lk.get("filter_id",      "")),
        ]
        self._ev_vs = {}
        for i, (key, lbl, val) in enumerate(fields):
            tk.Label(f, text=lbl+":", bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                     width=34, anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            v = tk.StringVar(value=val); self._ev_vs[key] = v
            tk.Entry(f, textvariable=v, width=34, font=("Helvetica",10)
                     ).grid(row=i, column=1, sticky="ew", padx=(4,0), pady=5)
        tk.Label(self._body, text=(
            "Generates:  Element:'link'  with  Events.Triggers.OnClick → EventId + ContainerId.\n"
            "When filterSection + filterId are set, a Payload is added so the tab-group\n"
            "OnOpenTab listener can set Filters.<filterId> = <field value> and re-invoke the agent."
        ), bg=BG, fg=MUTED, font=("Helvetica",8), justify="left").pack(anchor="w", pady=(8,0))

    def _build_legacy(self):
        lk = self._lk if self._lk.get("event_type","legacy") == "legacy" else {}
        f = tk.Frame(self._body, bg=BG); f.pack(fill="x")
        f.columnconfigure(1, weight=1)
        fields_def = [
            ("menu_id",     "Menu ID",                   lk.get("menu_id",     "")),
            ("rel_name",    "Relationship Name",         lk.get("rel_name",    f"{self._col_field}_rel")),
            ("from_entity", "From Entity",               lk.get("from_entity", "outputTable")),
            ("to_entity",   "To Entity",                 lk.get("to_entity",   "")),
            ("label_key",   "Label Key",                 lk.get("label_key",   self._col_title)),
            ("id_field",    "ID Field (holds link IDs)", lk.get("id_field",    self._col_field)),
        ]
        self._leg_vs = {}
        for i, (key, label, val) in enumerate(fields_def):
            tk.Label(f, text=label+":", bg=BG, fg=DARK, font=("Helvetica",9,"bold"),
                     width=26, anchor="w").grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=val); self._leg_vs[key] = v
            tk.Entry(f, textvariable=v, width=34, font=("Helvetica",10)
                     ).grid(row=i, column=1, sticky="ew", padx=(4,0), pady=4)
        tk.Label(self._body, text="Reference Keys:", bg=BG, fg=DARK,
                 font=("Helvetica",10,"bold")).pack(padx=0, pady=(8,0), anchor="w")
        tk.Label(self._body, text="  → field: maps a data field to a target attribute     = filter: applies a fixed filter value",
                 bg=BG, fg=MUTED, font=("Helvetica",8)).pack(anchor="w")
        rk_inner = tk.Frame(self._body, bg=BG); rk_inner.pack(fill="both", expand=True, pady=4)
        self._rk_tree = ttk.Treeview(rk_inner, columns=("type","attr","value"), show="headings", height=5)
        self._rk_tree.heading("type", text="Type")
        self._rk_tree.heading("attr", text="From Attr  /  To Attr")
        self._rk_tree.heading("value", text="To Attr  /  From Values")
        self._rk_tree.column("type", width=75); self._rk_tree.column("attr", width=190); self._rk_tree.column("value", width=200)
        self._rk_tree.pack(side="left", fill="both", expand=True)
        self._rk_tree.bind("<Double-1>", lambda e: self._edit_rk())
        for rk in lk.get("ref_keys", []):
            if rk.get("type") == "field":
                self._rk_tree.insert("","end",values=("→ field",rk.get("from_attr",""),rk.get("to_attr","")))
            else:
                self._rk_tree.insert("","end",values=("= filter",rk.get("to_attr",""),",".join(rk.get("from_values",[]))))
        rkbf = tk.Frame(rk_inner, bg=BG); rkbf.pack(side="right", fill="y", padx=4)
        tk.Button(rkbf, text="+ Field",  width=9, command=self._add_field).pack(pady=3)
        tk.Button(rkbf, text="+ Filter", width=9, command=self._add_filter).pack(pady=3)
        tk.Button(rkbf, text="✎ Edit",   width=9, command=self._edit_rk).pack(pady=3)
        tk.Button(rkbf, text="- Del",    width=9, command=lambda: self._rk_tree.delete(self._rk_tree.selection()[0]) if self._rk_tree.selection() else None).pack(pady=3)

    def _add_field(self):
        self.grab_release()
        from_a = simpledialog.askstring("Add Field Key","From Attribute (IDs field, e.g. InPickingTaskIds):",parent=self)
        if not from_a: self.grab_set(); return
        to_a = simpledialog.askstring("Add Field Key","To Attribute (target key, e.g. TaskId):",parent=self)
        self.grab_set()
        if to_a is not None and self._rk_tree: self._rk_tree.insert("","end",values=("→ field",from_a,to_a))

    def _add_filter(self):
        self.grab_release()
        to_a = simpledialog.askstring("Add Filter","To Attribute (e.g. Status):",parent=self)
        if not to_a: self.grab_set(); return
        vals = simpledialog.askstring("Add Filter","From Values — comma-separated (e.g. 1000,7000):",parent=self)
        self.grab_set()
        if vals is not None and self._rk_tree: self._rk_tree.insert("","end",values=("= filter",to_a,vals))

    def _edit_rk(self):
        if not self._rk_tree: return
        sel = self._rk_tree.selection()
        if not sel: return
        iid = sel[0]
        t, a, v = self._rk_tree.item(iid,"values")
        self.grab_release()
        if t == "→ field":
            new_a = simpledialog.askstring("Edit Field Key","From Attribute:",initialvalue=a,parent=self)
            if new_a is None: self.grab_set(); return
            new_v = simpledialog.askstring("Edit Field Key","To Attribute:",initialvalue=v,parent=self)
            self.grab_set()
            if new_v is not None: self._rk_tree.item(iid,values=("→ field",new_a,new_v))
        else:
            new_a = simpledialog.askstring("Edit Filter","To Attribute:",initialvalue=a,parent=self)
            if new_a is None: self.grab_set(); return
            new_v = simpledialog.askstring("Edit Filter","From Values (comma-separated):",initialvalue=v,parent=self)
            self.grab_set()
            if new_v is not None: self._rk_tree.item(iid,values=("= filter",new_a,new_v))

    def _clear(self):
        self.result = {}; self.destroy()

    def _apply(self):
        if self._mode.get() == "event_click":
            ev = self._ev_vs
            self.result = {
                "event_type":     "event_click",
                "event_id":       ev["event_id"].get().strip(),
                "container_id":   ev["container_id"].get().strip(),
                "filter_section": ev["filter_section"].get().strip(),
                "filter_id":      ev["filter_id"].get().strip(),
            }
        else:
            if not self._rk_tree: self.destroy(); return
            ref_keys = []
            for iid in self._rk_tree.get_children():
                t, a, v = self._rk_tree.item(iid,"values")
                if t == "→ field":
                    ref_keys.append({"type":"field","from_attr":a,"to_attr":v})
                else:
                    ref_keys.append({"type":"filter","to_attr":a,
                                     "from_values":[x.strip() for x in v.split(",") if x.strip()]})
            lv = self._leg_vs
            self.result = {
                "event_type":  "legacy",
                "menu_id":     lv["menu_id"].get().strip(),
                "rel_name":    lv["rel_name"].get().strip(),
                "from_entity": lv["from_entity"].get().strip(),
                "to_entity":   lv["to_entity"].get().strip(),
                "label_key":   lv["label_key"].get().strip(),
                "id_field":    lv["id_field"].get().strip(),
                "ref_keys":    ref_keys,
            }
        self.destroy()

# ───────────────────────────────────────────────────────────────
#  TOOLTIP WIDGET
# ───────────────────────────────────────────────────────────────
class Tooltip:
    """Dark hover tooltip shown to the right of the hovered widget."""
    _active = None

    def __init__(self, widget, text):
        self._w  = widget
        self._tx = text
        widget.bind("<Enter>",       self._show, add="+")
        widget.bind("<Leave>",       self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _=None):
        Tooltip._destroy_active()
        x = self._w.winfo_rootx() + self._w.winfo_width() + 6
        y = self._w.winfo_rooty()
        tip = tk.Toplevel(self._w)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)
        outer = tk.Frame(tip, bg="#1E293B", highlightbackground="#475569",
                         highlightthickness=1)
        outer.pack()
        tk.Label(outer, text=self._tx, bg="#1E293B", fg="#F1F5F9",
                 font=("Helvetica", 9), justify="left",
                 wraplength=280, padx=12, pady=8).pack()
        Tooltip._active = tip

    def _hide(self, _=None):
        Tooltip._destroy_active()

    @staticmethod
    def _destroy_active():
        if Tooltip._active:
            try: Tooltip._active.destroy()
            except: pass
            Tooltip._active = None

# ═══════════════════════════════════════════════════════════════════════════════
#  V6 LAYOUT HELPERS  — used exclusively by AlignFixDialog
#  All names are prefixed _af_ to avoid any collision with V5 globals.
# ═══════════════════════════════════════════════════════════════════════════════

_AF_LOCKED_CONTAINERS = {
    "table", "chart", "search", "segment-panel",
    "agentic-actions", "menu-item", "footer",
}
_AF_LAYOUT_CSS_PROPS = [
    "flexDirection","flex","flexWrap","alignItems","justifyContent",
    "alignContent","alignSelf",
    "width","height","minWidth","minHeight","maxWidth","maxHeight",
    "gap","padding","margin",
    "gridTemplateColumns","gridTemplateRows","gridTemplateAreas",
    "gridArea","gridColumn","gridRow",
    "overflow","overflowX","overflowY",
    "boxSizing",
    "background","border","borderRadius","boxShadow",
    "position","top","right","bottom","left","zIndex",
]
# Top-level Style keys (e.g. Style.flex) that are equivalent to Style.css counterparts.
# The CSS editor reads these as fallback and writes through to Style.css (normalising).
_AF_STYLE_TOP_KEYS = {
    "flex", "padding", "margin", "width", "height",
    "minWidth", "minHeight", "maxWidth", "maxHeight",
    "background", "border", "borderRadius", "overflow",
}
_AF_VAR = {
    "--manh-summary-bar-background-color":    "#e8ecf0",
    "--manh-river-table-text-color":          "#333",
    "--manh-river-table-even-rows":           "#fff",
    "--manh-river-table-odd-rows":            "#fafafa",
    "--manh-river-table-header-row":          "#f0f2f5",
    "--manh-river-table-border-color":        "#e0e0e0",
    "--manh-river-hover-background":          "#e8f0fe",
    "--manh-agent-usage-dashboard-agent-tile-header-text-color": "#5b6d8a",
}
_AF_C_BG  = "#1e1e2e"
_AF_C_FG  = "#cdd6f4"
_AF_C_SEL = "#313244"
_AF_C_ACC = "#89b4fa"
_AF_SCHEMATIC_COLORS = {
    "flex":             ("#dbeafe", "#3b82f6"),
    "grid":             ("#ede9fe", "#6366f1"),
    "header-action":    ("#ccfbf1", "#0891b2"),
    "header":           ("#e9d5ff", "#a78bfa"),
    "table":            ("#dcfce7", "#16a34a"),
    "chart":            ("#fff7ed", "#ea580c"),
    "search":           ("#e0f2fe", "#0284c7"),
    "segment-panel":    ("#fce7f3", "#db2777"),
    "footer-container": ("#f1f5f9", "#64748b"),
    "footer":           ("#f8fafc", "#94a3b8"),
    "card":             ("#dbeafe", "#2563eb"),
    "sidebar":          ("#e0e7ff", "#4f46e5"),
    "default":          ("#f1f5f9", "#64748b"),
}
_AF_AUTO_H = {"header-action": 54, "header": 36, "footer-container": 36, "footer": 36}
_AF_VW, _AF_VH = 1920, 1080
_AF_NEW_NODES = {
    "flex-col":  {"Container":"flex","Style":{"css":{"flexDirection":"column","gap":"16px","flex":"1","minHeight":"0"}},"Slots":{"Default":[]}},
    "flex-row":  {"Container":"flex","Style":{"css":{"flexDirection":"row","gap":"16px","flex":"1","overflow":"hidden"}},"Slots":{"Default":[]}},
    "grid":      {"Container":"grid","Style":{"css":{"flex":"1","display":"grid","gridTemplateAreas":'"header" "content"',"gridTemplateRows":"auto 1fr"}},"Slots":{"header":[],"content":[]}},
    "table":     {"Container":"table","Config":{"title":"New Table","pageSize":25,"AutoGenerateColumns":False,"SelectionConfig":{"ShowSelection":False,"SupportMultiSelect":False},"Columns":[],"FilterConfig":{"filters":[]}},"Style":{"flex":"1"},"Slots":{"Default":[]}},
    "chart":     {"Container":"chart","Init":{"Type":"value-array","DataSourcePath":""},"Style":{"contentPadding":"0","css":{"flex":"1"}},"Config":{"chartMetadata":{"applyAspectRatio":False,"chartWidth":"100%","showChartHeader":False,"showChartTitle":False,"showHighchartsTitle":False,"showLegend":True},"dataMapping":{"seriesMappings":[]},"highchartsOptions":{"chart":{"type":"column"},"plotOptions":{"column":{"stacking":"normal","borderWidth":0}},"legend":{"enabled":True}}}},
    "header-action":{"Container":"header-action","Style":{"padding":"10px","css":{"background":"var(--manh-summary-bar-background-color)"},"leftActionsCss":{"css":{"gap":"0rem"}}},"Slots":{"Left":[],"Right":[]}},
}

from dataclasses import dataclass as _af_dataclass
from typing import Optional as _AF_Optional

@_af_dataclass
class _AFNodeRef:
    node: dict
    parent: _AF_Optional[dict]
    parent_slot: _AF_Optional[str]
    index: _AF_Optional[int]
    path: str
    depth: int = 0
    locked: bool = False


def _af_resolve_var(val: str) -> str:
    if not isinstance(val, str): return str(val)
    for k, v in _AF_VAR.items():
        val = val.replace(f"var({k})", v)
    val = re.sub(r'var\(--[\w-]+(?:,\s*[^)]+)?\)', '#888', val)
    return val


def _af_style_inline(node: dict) -> str:
    style = node.get("Style") or {}
    css   = style.get("css") or {}
    _UIR  = {"flex":"flex","padding":"padding","margin":"margin","width":"width",
              "height":"height","minWidth":"min-width","minHeight":"min-height",
              "maxWidth":"max-width","maxHeight":"max-height","background":"background",
              "border":"border","borderRadius":"border-radius","overflow":"overflow"}
    decls: dict = {}
    for uk, cp in _UIR.items():
        if uk in style and uk != "css":
            decls[cp] = _af_resolve_var(str(style[uk]))
    for k, v in css.items():
        val = _af_resolve_var(str(v))
        if k.startswith("--"):
            decls[k] = val
        else:
            decls[re.sub(r'(?<!^)(?=[A-Z])','-',k).lower()] = val
    return "; ".join(f"{k}: {v}" for k, v in decls.items())


def _af_px_val(val, ref: float = 1200.0):
    if isinstance(val,(int,float)): return float(val)
    if not isinstance(val,str): return None
    v = val.strip()
    try:
        if v.endswith("px"):  return float(v[:-2])
        if v.endswith("rem"): return float(v[:-3])
        if v.endswith("vw"):  return float(v[:-2])/100*1920
        if v.endswith("vh"):  return float(v[:-2])/100*1080
        if v.endswith("%"):   return float(v[:-1])/100*ref
        return float(v)
    except ValueError: return None


def _af_parse_padding(s) -> tuple:
    parts = str(s or "0").strip().split()
    vals  = [(_af_px_val(p) or 0) for p in parts]
    n = len(vals)
    if n==0: return (0,0,0,0)
    if n==1: return (vals[0],)*4
    if n==2: return (vals[0],vals[1],vals[0],vals[1])
    if n==3: return (vals[0],vals[1],vals[2],vals[1])
    return (vals[0],vals[1],vals[2],vals[3])


def _af_node_label(node: dict) -> str:
    ctype = node.get("Container") or node.get("Element","?")
    parts = [ctype]
    uid = node.get("UID")
    if uid: parts.append(f"#{uid}")
    cfg = node.get("Config") or {}
    title = cfg.get("title") or cfg.get("LabelKey") or cfg.get("Name")
    if title: parts.append(f'"{title}"')
    init = node.get("Init") or {}
    if isinstance(init,dict):
        dsp = init.get("DataSourcePath") or init.get("Type","")
        if dsp: parts.append(f"[{dsp}]")
    return " ".join(parts)


def _af_is_locked(node: dict) -> bool:
    if node.get("_unlocked"):
        return False
    return (node.get("Container") in _AF_LOCKED_CONTAINERS or bool(node.get("Element")))


def _af_get_css(node: dict) -> dict:
    return node.setdefault("Style",{}).setdefault("css",{})


def _af_move_child(parent: dict, slot: str, old: int, new: int) -> bool:
    items = parent.get("Slots",{}).get(slot,[])
    n = len(items)
    if not (0<=old<n and 0<=new<n and old!=new): return False
    items.insert(new, items.pop(old))
    return True


def _af_diff_trees(a, b, path, out):
    if type(a)!=type(b):
        out.append(f"CHANGED {path}\n  was: {repr(a)[:80]}\n  now: {repr(b)[:80]}"); return
    if isinstance(a,dict):
        for k in sorted(set(a)|set(b)):
            np=f"{path}.{k}" if path else k
            if k not in a: out.append(f"ADDED   {np}")
            elif k not in b: out.append(f"REMOVED {np}")
            else: _af_diff_trees(a[k],b[k],np,out)
    elif isinstance(a,list):
        if len(a)!=len(b): out.append(f"RESIZED {path}  {len(a)} → {len(b)}")
        else:
            for i,(x,y) in enumerate(zip(a,b)): _af_diff_trees(x,y,f"{path}[{i}]",out)
    elif a!=b: out.append(f"CHANGED {path}\n  was: {repr(a)[:80]}\n  now: {repr(b)[:80]}")


# ── standalone V6 layout engine (used by Designer._draw_grid) ─────────────────

def _af_flex_sizes_standalone(children, available, is_row, is_grid):
    """Compute flex child sizes — standalone (no self dependency)."""
    VREF = _AF_VW if is_row else _AF_VH
    specs = []
    for i, child in enumerate(children):
        ctype = child.get("Container", "")
        css   = (child.get("Style") or {}).get("css") or {}
        style = child.get("Style") or {}
        if is_grid:
            specs.append(("fixed", _AF_AUTO_H.get(ctype, 36)) if i == 0 else ("flex", 1.0))
            continue
        flex_s = str(css.get("flex") or style.get("flex", "")).strip()
        parts  = flex_s.split()
        placed = False
        if parts:
            try:
                grow = float(parts[0])
                if len(parts) == 1:
                    specs.append(("fixed", _AF_AUTO_H.get(ctype, 40)) if grow == 0
                                  else ("flex", max(grow, 0.1)))
                    placed = True
                elif len(parts) >= 3:
                    shrink = float(parts[1]); basis = parts[2]
                    if grow == 0 and shrink == 0:
                        px = _af_px_val(basis, VREF)
                        if px: specs.append(("fixed", px)); placed = True
                    elif basis in ("0", "0px", "0rem"):
                        specs.append(("flex", max(grow, 0.1))); placed = True
                    elif basis == "auto":
                        specs.append(("flex", max(grow, 0.1))); placed = True
                    elif grow > 0:
                        specs.append(("flex", max(grow, 0.1))); placed = True
            except (ValueError, IndexError):
                pass
        if placed: continue
        dim  = "width" if is_row else "height"
        done = False
        for k in (dim, "min" + dim[0].upper() + dim[1:]):
            v = css.get(k) or style.get(k)
            if v:
                pv = _af_px_val(str(v), VREF)
                if pv and str(v) not in ("100%", "100vh", "100vw"):
                    specs.append(("fixed", pv)); done = True; break
        if done: continue
        if not is_row and ctype in _AF_AUTO_H:
            specs.append(("fixed", _AF_AUTO_H[ctype])); continue
        specs.append(("flex", 1.0))
    fixed_t = sum(v for k, v in specs if k == "fixed")
    flex_t  = sum(v for k, v in specs if k == "flex") or 1e-9
    flex_av = max(available - fixed_t, len(specs) * 4)
    result  = [max(v if k == "fixed" else v / flex_t * flex_av, 2) for k, v in specs]
    total   = sum(result)
    if total > 1 and abs(total - available) > 0.5:
        f = available / total; result = [r * f for r in result]
    return result


def _af_compute_layout_tree(node, x, y, w, h, path):
    """Recursive layout engine — mirrors AlignFixDialog._compute_layout."""
    result = [(node, x, y, w, h, path)]
    if not isinstance(node, dict) or w <= 0 or h <= 0:
        return result
    ctype    = node.get("Container", "")
    css      = (node.get("Style") or {}).get("css") or {}
    style    = node.get("Style") or {}
    is_grid  = (ctype == "grid")
    is_row   = css.get("flexDirection", "column") in ("row", "row-reverse")
    pt, pr, pb, pl = _af_parse_padding(css.get("padding") or style.get("padding", "0"))
    gap  = _af_px_val(str(css.get("gap", "0"))) or 0
    ix, iy = x + pl, y + pt
    iw, ih = max(w - pl - pr, 0), max(h - pt - pb, 0)
    slots = node.get("Slots") or {}
    if is_grid:
        raw   = css.get("grid-template-areas", "")
        order = re.findall(r'"([^"]+)"', raw) or list(slots.keys())
        kids  = []
        for sn in order:
            for i, ch in enumerate(slots.get(sn) or []):
                if isinstance(ch, dict): kids.append((ch, f"{path}.{sn}[{i}]"))
    else:
        kids = [(ch, f"{path}.Default[{i}]")
                for i, ch in enumerate(slots.get("Default") or []) if isinstance(ch, dict)]
    if not kids: return result
    n     = len(kids)
    avail = iw if is_row else ih
    sizes = _af_flex_sizes_standalone([k for k, _ in kids],
                                       avail - gap * max(n-1, 0), is_row, is_grid)
    cursor = 0.0
    for (child, cp), size in zip(kids, sizes):
        if is_row: cx2, cy2, cw2, ch2 = ix+cursor, iy, size, ih
        else:      cx2, cy2, cw2, ch2 = ix, iy+cursor, iw, size
        result.extend(_af_compute_layout_tree(child, cx2, cy2,
                                               max(cw2, 0), max(ch2, 0), cp))
        cursor += size + gap
    return result


# ── Live-preview HTTP server ───────────────────────────────────────────────────
try:
    import http.server  as _af_http_mod
    import socketserver as _af_sock_mod
    import threading    as _af_thread_mod
    _AF_HAS_HTTPSERVER = True
except ImportError:
    _AF_HAS_HTTPSERVER = False

try:
    from tkinterweb import HtmlFrame as _AF_HtmlFrame
    _AF_HAS_TKWEB = True
except ImportError:
    _AF_HAS_TKWEB = False

class _AFPreviewServer:
    """Tiny per-dialog HTTP server: GET / → HTML page, GET /version → change counter."""
    def __init__(self):
        self._html = b"<html><body style='font:13px sans-serif;padding:20px'>Loading...</body></html>"
        self._ver  = 0
        self._lock = _af_thread_mod.Lock()
        self._srv  = None
        self._port = 0

    def start(self):
        if not _AF_HAS_HTTPSERVER: return 0
        _s = self
        class _H(_af_http_mod.BaseHTTPRequestHandler):
            def do_GET(H):
                with _s._lock:
                    if H.path == "/version":
                        d = str(_s._ver).encode()
                    else:
                        d = _s._html
                    H.send_response(200)
                    ct = "text/plain" if H.path == "/version" else "text/html;charset=utf-8"
                    H.send_header("Content-Type", ct)
                    H.send_header("Content-Length", str(len(d)))
                    H.send_header("Cache-Control", "no-store")
                    H.end_headers()
                    H.wfile.write(d)
            def log_message(H, *a): pass
        self._srv = _af_sock_mod.TCPServer(("127.0.0.1", 0), _H)
        self._port = self._srv.server_address[1]
        t = _af_thread_mod.Thread(target=self._srv.serve_forever, daemon=True)
        t.start()
        return self._port

    def update(self, html_str):
        with self._lock:
            self._html = (html_str.encode("utf-8")
                          if isinstance(html_str, str) else html_str)
            self._ver += 1

    def stop(self):
        if self._srv:
            try: self._srv.shutdown()
            except Exception: pass

    @property
    def port(self): return self._port

    @property
    def url(self): return f"http://127.0.0.1:{self._port}"


# ═══════════════════════════════════════════════════════════════════════════════
#  ALIGN FIX DIALOG  — V6 layout designer embedded in V5
# ═══════════════════════════════════════════════════════════════════════════════

# ── GLEAN AI CHAT DIALOG ───────────────────────────────────────────────────────
class GleanChatDialog(tk.Toplevel):
    """
    Chat window that sends the current fragment JSON to the Glean Fragment Designer
    agent and shows the response with a Review & Apply suggestions panel.
    """
    _AGENT_URL = f"https://app.glean.com/chat/agents/{_GLEAN_AGENT_ID}"

    def __init__(self, parent, fragment_root: dict, on_apply_cb=None, validation_issues=None):
        super().__init__(parent)
        self.title("✨ Glean AI — Fragment Advisor")
        self.geometry("780x680")
        self.minsize(600, 500)
        self.configure(bg="#0F172A")
        self.fragment_root     = fragment_root
        self.on_apply_cb       = on_apply_cb
        self._validation_issues = validation_issues or []   # list of (node,path,prop,msg)
        self._thinking         = False
        self._suggestions      = []
        self._suggestion_vars  = []
        self._chat_history     = []
        self._partial_text     = ""         # accumulates raw streaming text
        self._partial_start    = False      # True once streaming has begun this turn
        self._th_btn_tag       = None       # current thinking-section button tag
        self._th_body_tag      = None       # current thinking-section body tag
        self._think_counter    = 0          # incremented each turn for unique tag names
        self._attachments      = []
        self._build_ui()
        # Hide instead of destroy on close so chat history survives
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        # Show welcome message
        self._append_message("ai",
            "👋 Hello! I'm your Fragment Design AI advisor.\n\n"
            "Describe what you'd like to improve — for example:\n"
            "• \"Make the table headers darker\"\n"
            "• \"The background colors don't match the design\"\n"
            "• \"Suggest layout improvements for this fragment\"\n\n"
            "I'll analyze the fragment JSON and return specific, actionable suggestions.")

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg="#1E293B", pady=8)
        top.pack(fill=tk.X)
        tk.Label(top, text="✨", bg="#1E293B", fg="#A78BFA",
                 font=("Helvetica",16)).pack(side=tk.LEFT, padx=(12,4))
        tk.Label(top, text="Glean AI — Fragment Advisor", bg="#1E293B",
                 fg="white", font=("Helvetica",11,"bold")).pack(side=tk.LEFT)
        tk.Label(top, text="Agent: Fragment Designer", bg="#1E293B",
                 fg="#64748B", font=("Helvetica",9)).pack(side=tk.LEFT, padx=12)
        self._mkbtn(top, "↗ Open in Browser", "#1E293B", "#60A5FA",
                    lambda: __import__('webbrowser').open(self._AGENT_URL),
                    font=("Helvetica",8)
                    ).pack(side=tk.RIGHT, padx=10)
        self._mkbtn(top, "🗑 Clear", "#1E293B", "#94A3B8",
                    self._clear_chat,
                    font=("Helvetica",8)
                    ).pack(side=tk.RIGHT, padx=4)

        # Main body: chat + suggestions
        body = tk.Frame(self, bg="#0F172A"); body.pack(fill=tk.BOTH, expand=True)

        # Chat display
        chat_frame = tk.Frame(body, bg="#0F172A"); chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,0))
        self._chat_text = tk.Text(chat_frame, bg="#0F172A", fg="#E2E8F0",
                                   font=("Helvetica",11), wrap=tk.WORD,
                                   state=tk.DISABLED, relief="flat",
                                   selectbackground="#1E40AF", insertbackground="white",
                                   spacing3=4)
        _sb = ttk.Scrollbar(chat_frame, command=self._chat_text.yview)
        _sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._chat_text.pack(fill=tk.BOTH, expand=True)
        self._chat_text.config(yscrollcommand=_sb.set)
        # Text tags
        self._chat_text.tag_configure("you_hdr",  font=("Helvetica",9,"bold"),
                                       foreground="#60A5FA", spacing1=10)
        self._chat_text.tag_configure("ai_hdr",   font=("Helvetica",9,"bold"),
                                       foreground="#A78BFA", spacing1=10)
        self._chat_text.tag_configure("you_body", font=("Helvetica",11),
                                       foreground="#CBD5E1", lmargin1=8, lmargin2=8)
        self._chat_text.tag_configure("ai_body",  font=("Helvetica",11),
                                       foreground="#E2E8F0", lmargin1=8, lmargin2=8,
                                       spacing3=6)
        self._chat_text.tag_configure("thinking", font=("Helvetica",10,"italic"),
                                       foreground="#64748B", spacing1=8)
        self._chat_text.tag_configure("error",    font=("Helvetica",10),
                                       foreground="#F87171", spacing1=6)
        self._chat_text.tag_configure("th_btn",   font=("Helvetica",9,"italic"),
                                       foreground="#94A3B8", spacing1=6, lmargin1=8)
        self._chat_text.tag_configure("th_body",  font=("Courier",9),
                                       foreground="#94A3B8", lmargin1=20, lmargin2=20,
                                       spacing3=1, elide=True)

        # Thinking indicator label
        self._thinking_var = tk.StringVar(value="")
        tk.Label(body, textvariable=self._thinking_var,
                 bg="#0F172A", fg="#64748B", font=("Helvetica",9,"italic")
                 ).pack(fill=tk.X, padx=12)

        # Suggestions panel (hidden until suggestions arrive)
        self._sugg_outer = tk.Frame(body, bg="#1E293B")
        # (populated dynamically in _show_suggestions_panel)

        # Divider + attachment chips row (hidden when empty)
        tk.Frame(body, bg="#334155", height=1).pack(fill=tk.X, pady=0)
        self._chips_frame = tk.Frame(body, bg="#1E293B")
        # (populated dynamically by _refresh_chips — packs itself before _input_bar)

        # Input bar
        self._input_bar = tk.Frame(body, bg="#1E293B", pady=8)
        self._input_bar.pack(fill=tk.X)
        input_bar = self._input_bar

        # Attach button
        self._mkbtn(input_bar, "📎", "#1E293B", "#94A3B8",
                    self._add_attachment,
                    font=("Helvetica",13), padx=6, pady=4
                    ).pack(side=tk.LEFT, padx=(8,2))

        self._input_var = tk.StringVar()
        inp_f = tk.Frame(input_bar, bg="#0F172A", highlightbackground="#334155",
                         highlightthickness=1)
        inp_f.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4,6))
        self._input_entry = tk.Entry(inp_f, textvariable=self._input_var,
                                      bg="#0F172A", fg="white",
                                      insertbackground="white", relief="flat",
                                      font=("Helvetica",11))
        self._input_entry.pack(fill=tk.X, padx=10, pady=8)
        self._input_entry.bind("<Return>", lambda e: self._send())
        self._input_entry.bind("<Shift-Return>", lambda e: None)

        self._send_btn = self._mkbtn(input_bar, "Send  ➤", "#7C3AED", "white",
                                     self._send,
                                     font=("Helvetica",10,"bold"), padx=14, pady=8)
        self._send_btn.pack(side=tk.LEFT, padx=(0,10))

    # ── Attachment helpers ─────────────────────────────────────────────────────
    def _add_attachment(self):
        from tkinter import filedialog as _fd
        path = _fd.askopenfilename(
            parent=self,
            title="Attach file to Glean prompt",
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("Python files", "*.py"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception as ex:
            self._append_message("error", f"Could not read file: {ex}")
            return
        name = os.path.basename(path)
        # Truncate very large files to avoid overwhelming the prompt
        MAX = 40_000
        if len(content) > MAX:
            content = content[:MAX] + f"\n…[truncated at {MAX} chars]"
        self._attachments.append({"name": name, "content": content})
        self._refresh_chips()

    def _remove_attachment(self, idx):
        if 0 <= idx < len(self._attachments):
            self._attachments.pop(idx)
        self._refresh_chips()

    def _refresh_chips(self):
        for w in self._chips_frame.winfo_children():
            w.destroy()
        if not self._attachments:
            self._chips_frame.pack_forget()
            return
        self._chips_frame.pack(fill=tk.X, before=self._input_bar)
        inner = tk.Frame(self._chips_frame, bg="#1E293B")
        inner.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(inner, text="Attached:", bg="#1E293B", fg="#64748B",
                 font=("Helvetica",8,"bold")).pack(side=tk.LEFT, padx=(0,6))
        for i, att in enumerate(self._attachments):
            chip = tk.Frame(inner, bg="#334155", padx=6, pady=2)
            chip.pack(side=tk.LEFT, padx=2)
            tk.Label(chip, text=att["name"], bg="#334155", fg="#CBD5E1",
                     font=("Helvetica",8)).pack(side=tk.LEFT)
            idx = i
            self._mkbtn(chip, "✕", "#334155", "#CBD5E1",
                        lambda i=idx: self._remove_attachment(i),
                        font=("Helvetica",8), padx=2, pady=0
                        ).pack(side=tk.LEFT, padx=(3,0))

    # ── Chat helpers ───────────────────────────────────────────────────────────
    def _append_message(self, role, text):
        """Append a message bubble to the chat text widget."""
        self._chat_history.append((role, text))
        self._chat_text.config(state=tk.NORMAL)
        if role == "you":
            self._chat_text.insert(tk.END, "\n  You\n", "you_hdr")
            self._chat_text.insert(tk.END, f"  {text}\n", "you_body")
        elif role == "ai":
            self._chat_text.insert(tk.END, "\n  ✨ Glean AI\n", "ai_hdr")
            self._chat_text.insert(tk.END, f"  {text}\n", "ai_body")
        elif role == "error":
            self._chat_text.insert(tk.END, f"\n  ⚠ {text}\n", "error")
        self._chat_text.config(state=tk.DISABLED)
        self._chat_text.see(tk.END)

    # ── Mac-safe button helper ─────────────────────────────────────────────────
    @staticmethod
    def _mkbtn(parent, text, bg, fg, cmd, font=("Helvetica",9,"bold"), **kw):
        """Label-based button — bg and fg are always honoured on macOS.
        tk.Button ignores bg on macOS Aqua; tk.Label does not."""
        def _hov(c, d=22):
            try:
                c = c.lstrip('#')
                r,g,b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
                return f"#{max(0,min(255,r+d)):02x}{max(0,min(255,g+d)):02x}{max(0,min(255,b+d)):02x}"
            except Exception:
                return '#' + c
        hover = _hov(bg)
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
                     cursor="hand2", relief="flat", **kw)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e, w=b: w.config(bg=hover))
        b.bind("<Leave>",    lambda e, w=b: w.config(bg=bg))
        return b

    # ── Thinking-section helpers ────────────────────────────────────────────────
    def _set_btn_text(self, btn_tag, new_label):
        """Replace the text range carrying btn_tag in-place (preserves position)."""
        ranges = self._chat_text.tag_ranges(btn_tag)
        if not ranges:
            return
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.delete(ranges[0], ranges[1])
        self._chat_text.insert(ranges[0], new_label, btn_tag)
        self._chat_text.config(state=tk.DISABLED)

    def _set_partial(self, text):
        """Stream text live into a collapsible thinking section in the chat."""
        self._partial_text = text

        def _update():
            self._chat_text.config(state=tk.NORMAL)

            if not self._partial_start:
                # ── First chunk: create the thinking section ──────────────────
                self._think_counter += 1
                self._th_btn_tag  = f"_thbtn{self._think_counter}"
                self._th_body_tag = f"_thbod{self._think_counter}"
                self._chat_text.tag_configure(self._th_btn_tag,
                    font=("Helvetica", 9, "italic"), foreground="#94A3B8",
                    spacing1=8, lmargin1=10)
                self._chat_text.tag_configure(self._th_body_tag,
                    font=("Courier", 9), foreground="#94A3B8",
                    lmargin1=22, lmargin2=22, spacing3=1, elide=False)

                self._chat_text.insert(tk.END,
                    f"  💭 Thinking ▼  (streaming…)\n", self._th_btn_tag)
                self._chat_text.mark_set("_th_s", tk.END)
                self._chat_text.mark_gravity("_th_s", tk.LEFT)
                self._chat_text.insert(tk.END, text, self._th_body_tag)
                self._chat_text.mark_set("_th_e", tk.END)
                self._chat_text.mark_gravity("_th_e", tk.RIGHT)

                # Wire toggle
                _btn = self._th_btn_tag; _bod = self._th_body_tag
                _exp = [True]
                def _toggle(e, b=_btn, d=_bod, s=_exp):
                    if s[0]:
                        self._chat_text.tag_configure(d, elide=True)
                        self._set_btn_text(b, "  💭 Thinking ▶  (click to show)")
                        s[0] = False
                    else:
                        self._chat_text.tag_configure(d, elide=False)
                        self._set_btn_text(b, "  💭 Thinking ▼  (click to hide)")
                        s[0] = True
                self._chat_text.tag_bind(self._th_btn_tag, "<Button-1>", _toggle)
                self._chat_text.tag_bind(self._th_btn_tag, "<Enter>",
                    lambda e: self._chat_text.config(cursor="hand2"))
                self._chat_text.tag_bind(self._th_btn_tag, "<Leave>",
                    lambda e: self._chat_text.config(cursor=""))
                self._partial_start = True
            else:
                # ── Subsequent chunks: update body in-place ───────────────────
                self._chat_text.delete("_th_s", "_th_e")
                self._chat_text.insert("_th_s", text, self._th_body_tag)

            self._chat_text.config(state=tk.DISABLED)
            self._chat_text.see(tk.END)
        self.after(0, _update)

    def _clear_chat(self):
        """Clear all chat messages and start a fresh session."""
        self._chat_history.clear()
        self._partial_start = False
        self._partial_text  = ""
        self._th_btn_tag    = None
        self._th_body_tag   = None
        self._chat_text.config(state=tk.NORMAL)
        self._chat_text.delete("1.0", tk.END)
        self._chat_text.config(state=tk.DISABLED)
        self._sugg_outer.pack_forget()
        self._suggestions.clear()
        self._suggestion_vars.clear()
        self._append_message("ai",
            "🗑 Chat cleared. I still have the same fragment — ask anything.")

    def _set_thinking(self, val: bool):
        self._thinking = val
        self.after(0, lambda: self._send_btn.config(state=tk.DISABLED if val else tk.NORMAL))
        if not val:
            self.after(0, lambda: self._thinking_var.set(""))

    # ── Send message ──────────────────────────────────────────────────────────
    def _send(self):
        text = self._input_var.get().strip()
        if not text or self._thinking:
            return
        self._input_var.set("")
        self._partial_start = False
        self._partial_text  = ""

        # Show what the user typed, plus attachment names
        display_user = text
        if self._attachments:
            names = ", ".join(a["name"] for a in self._attachments)
            display_user += f"\n  📎 {names}"
        self._append_message("you", display_user)
        self._set_thinking(True)

        # Build prompt: user message + validation issues + fragment JSON + attachments
        frag_json = json.dumps(self.fragment_root, indent=2)

        issues_block = ""
        if self._validation_issues:
            issues_block = "\n\n<validation_issues>\n"
            for _, path, prop, msg in self._validation_issues[:30]:
                prop_str = f"  [{prop}]" if prop else ""
                issues_block += f"  • {path}{prop_str}: {msg}\n"
            issues_block += "</validation_issues>"

        att_block = ""
        for att in self._attachments:
            att_block += f"\n\n<attachment name=\"{att['name']}\">\n{att['content']}\n</attachment>"

        prompt = (
            f"{text}\n\n"
            "Please analyze the fragment JSON below and return a structured JSON object with "
            "specific CSS/style suggestions in this EXACT format:\n"
            "{\n"
            '  "suggestions": [\n'
            '    {\n'
            '      "issue_id": "unique_id",\n'
            '      "path": "Fragment.Slots.Default[0].Style",\n'
            '      "prop": "cssPropertyName",\n'
            '      "suggestion_label": "Short label",\n'
            '      "message": "Explanation of what and why",\n'
            '      "fix_props": {"prop1": "value1"},\n'
            '      "remove_props": [],\n'
            '      "confidence": "high",\n'
            '      "safe_to_auto_apply": true\n'
            '    }\n'
            '  ]\n'
            "}\n\n"
            f"<fragment_json>\n{frag_json}\n</fragment_json>"
            f"{issues_block}"
            f"{att_block}"
        )

        # Clear attachments after sending
        self._attachments.clear()
        self._refresh_chips()

        def _worker():
            try:
                full_response = _glean_call_agent(prompt, on_partial=self._set_partial)
                suggestions   = _glean_extract_suggestions(full_response)
                # Strip only the JSON block, keep any natural language text
                import re as _re
                display_text = _re.sub(r'```(?:json)?\s*\{[^`]*?\}[^`]*?\s*```', '', full_response, flags=_re.DOTALL).strip()
                if not display_text and suggestions:
                    display_text = f"Analysis complete — {len(suggestions)} suggestion(s) found. See the panel below."
                elif not display_text:
                    display_text = full_response.strip() or "No response received from Glean."
                self.after(0, lambda: self._on_response(display_text, suggestions))
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_response(self, text, suggestions):
        self._set_thinking(False)
        if self._partial_start and self._th_btn_tag:
            # Collapse thinking section and update header to show char count
            n = len(self._partial_text)
            self._chat_text.config(state=tk.NORMAL)
            self._chat_text.tag_configure(self._th_body_tag, elide=True)
            self._set_btn_text(self._th_btn_tag,
                f"  💭 Thinking ▶  ({n:,} chars — click to show)")
            self._chat_text.config(state=tk.DISABLED)
        self._partial_text  = ""
        self._partial_start = False
        self._append_message("ai", text)
        self._suggestions = suggestions
        if suggestions:
            self._show_suggestions_panel(suggestions)

    def _on_error(self, msg):
        self._set_thinking(False)
        self._partial_text  = ""
        self._partial_start = False
        self._append_message("error", msg)

    # ── Suggestions panel ──────────────────────────────────────────────────────
    def _show_suggestions_panel(self, suggestions):
        """Build / rebuild the suggestions review panel."""
        for w in self._sugg_outer.winfo_children():
            w.destroy()
        self._suggestion_vars.clear()

        hdr = tk.Frame(self._sugg_outer, bg="#1E293B")
        hdr.pack(fill=tk.X, padx=8, pady=(6,2))
        tk.Label(hdr, text=f"  🔍 {len(suggestions)} Suggestion(s) — review and apply",
                 bg="#1E293B", fg="#A78BFA", font=("Helvetica",10,"bold")).pack(side=tk.LEFT)
        self._mkbtn(hdr, "✓ Apply All Safe", "#065F46", "white",
                    self._apply_all_safe, padx=10
                    ).pack(side=tk.RIGHT, padx=4)
        self._mkbtn(hdr, "✓ Apply Selected", "#1D4ED8", "white",
                    self._apply_selected, padx=10
                    ).pack(side=tk.RIGHT, padx=4)

        scroll_f = tk.Frame(self._sugg_outer, bg="#1E293B")
        scroll_f.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,6))

        for i, s in enumerate(suggestions):
            var = tk.BooleanVar(value=bool(s.get("safe_to_auto_apply", False)))
            self._suggestion_vars.append(var)
            conf_color = {"high":"#4ADE80","medium":"#FCD34D","low":"#F87171"}.get(
                s.get("confidence",""), "#94A3B8")
            row = tk.Frame(scroll_f, bg="#273344", pady=4, padx=6)
            row.pack(fill=tk.X, pady=2)
            tk.Checkbutton(row, variable=var, bg="#273344",
                           activebackground="#273344").pack(side=tk.LEFT)
            tk.Label(row, text=s.get("suggestion_label","Suggestion"),
                     bg="#273344", fg="white", font=("Helvetica",10,"bold"),
                     anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            tk.Label(row, text=s.get("confidence","").upper(),
                     bg="#273344", fg=conf_color,
                     font=("Helvetica",8,"bold")).pack(side=tk.LEFT, padx=6)
            # Tooltip-style message on hover
            _msg = s.get("message","")
            if _msg:
                Tooltip(row, _msg[:200])

        self._sugg_outer.pack(fill=tk.X, before=self._input_entry.master.master, padx=4, pady=0)

    def _apply_all_safe(self):
        safe = [s for s in self._suggestions if s.get("safe_to_auto_apply")]
        self._do_apply(safe)

    def _apply_selected(self):
        selected = [s for s,v in zip(self._suggestions, self._suggestion_vars) if v.get()]
        self._do_apply(selected)

    def _do_apply(self, subset):
        if not subset:
            self._append_message("error", "No suggestions selected.")
            return
        applied, failed = 0, 0
        applied_labels = []
        for s in subset:
            if _glean_apply_suggestion(self.fragment_root, s):
                applied += 1
                applied_labels.append(s.get("suggestion_label", "fix"))
            else:
                failed += 1
        # Show in-chat result notification
        if applied:
            lines = [f"✅ Applied {applied} fix(es) to the fragment:"]
            for lbl in applied_labels:
                lines.append(f"   • {lbl}")
            if failed:
                lines.append(f"⚠ {failed} could not be applied (path not found).")
            lines.append("\n💡 Open Align Fix to validate the changes look correct.")
            self._append_message("ai", "\n".join(lines))
        else:
            self._append_message("error",
                f"All {failed} suggestion(s) failed (paths not found in fragment).")
        # Show Validate button
        self._show_validate_bar(applied)
        if self.on_apply_cb:
            self.on_apply_cb()
        self._sugg_outer.pack_forget()
        self._suggestions.clear()
        self._suggestion_vars.clear()

    def _show_validate_bar(self, applied_count):
        """Show a banner with a button to open Align Fix for validation."""
        if applied_count == 0:
            return
        bar = tk.Frame(self, bg="#064E3B", pady=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(bar, text=f"✅ {applied_count} fix(es) applied —",
                 bg="#064E3B", fg="#6EE7B7", font=("Helvetica",9,"bold")
                 ).pack(side=tk.LEFT, padx=(12,4))
        tk.Label(bar, text="open Align Fix to validate layout",
                 bg="#064E3B", fg="#A7F3D0", font=("Helvetica",9)
                 ).pack(side=tk.LEFT)
        def _open_af():
            bar.destroy()
            if self.on_apply_cb:
                self.on_apply_cb()   # triggers parent to rebuild
        self._mkbtn(bar, "🔧 Open Align Fix", "#065F46", "white",
                    _open_af, padx=10, pady=2
                    ).pack(side=tk.RIGHT, padx=10)
        self._mkbtn(bar, "✕", "#064E3B", "#6EE7B7",
                    bar.destroy, font=("Helvetica",9), padx=6
                    ).pack(side=tk.RIGHT, padx=2)


class AlignFixDialog(tk.Toplevel):
    """
    Full V6 layout schematic/CSS editor, launched from V5's Align Fix button.
    Loads the current V5 fragment JSON, lets the user restructure layout,
    then offers to apply CSS changes back to V5 card objects.
    """

    def __init__(self, parent, fragment_root: dict, v5_designer=None):
        super().__init__(parent)
        self.title("Align Fix — Layout Designer (V6 Engine)")
        self.geometry("1600x920")
        self.minsize(1000, 640)
        self.configure(bg=_AF_C_BG)

        self.fragment_root       = fragment_root
        self.orig_snapshot       = copy.deepcopy(fragment_root)
        self._v5                 = v5_designer       # reference to V5 Designer
        self.tree_id_map: dict[str, _AFNodeRef] = {}
        self._selected_slot_ref: _AF_Optional[_AFNodeRef] = None
        self._selected_preview_node = None
        self._layout_canvas          = None
        self._click_zones: list      = []
        self._sx: float              = 1.0
        self._sy: float              = 1.0
        self._resize_state           = None
        self._canvas_tooltip         = None
        self._canvas_tooltip_path    = None
        self._center_nb              = None   # ttk.Notebook for Schematic / Live HTML tabs
        self._html_view              = None   # tkinterweb HtmlFrame (if available)
        self._preview_server         = None   # _AFPreviewServer instance

        # Start the live-preview HTTP server
        if _AF_HAS_HTTPSERVER:
            self._preview_server = _AFPreviewServer()
            self._preview_server.start()

        self._build_ui()
        self._apply_theme()
        self._rebuild_tree()
        if self.tree_id_map:
            first = next(iter(self.tree_id_map))
            self.tree.selection_set(first)
            self.tree.see(first)
            self._on_tree_select()

    # ── theme ──────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        st = ttk.Style(self)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("AF.TFrame",      background=_AF_C_BG)
        st.configure("AF.TLabel",      background=_AF_C_BG, foreground=_AF_C_FG)
        st.configure("AF.TLabelframe", background=_AF_C_BG, foreground=_AF_C_ACC)
        st.configure("AF.TLabelframe.Label", background=_AF_C_BG, foreground=_AF_C_ACC,
                     font=("TkDefaultFont",9,"bold"))
        st.configure("AF.Treeview",    background=_AF_C_SEL, foreground=_AF_C_FG,
                     rowheight=22, fieldbackground=_AF_C_SEL)
        try:
            st.configure("AF.TNotebook",     background=_AF_C_BG)
            st.configure("AF.TNotebook.Tab", background="#313244", foreground=_AF_C_FG,
                         padding=(10,4), font=("TkDefaultFont",9))
            st.map("AF.TNotebook.Tab",
                   background=[("selected","#45475a")],
                   foreground=[("selected","#ffffff")])
        except tk.TclError:
            pass   # some theme variants don't support all TNotebook options
        st.map("AF.Treeview",
               background=[("selected","#45475a")],
               foreground=[("selected",_AF_C_FG)])
        st.configure("AF.Treeview.Heading", background="#313244",
                     foreground=_AF_C_ACC, relief="flat")

    # ── ui builder ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        tb = tk.Frame(self, bg="#1a1b2e", pady=4)
        tb.pack(fill=tk.X)

        def _tb(text, cmd, bg, tip):
            b = self._tbtn(tb, text, cmd, bg)
            b.pack(side=tk.LEFT, padx=2)
            self._tip(b, tip)
            return b

        _tb("📋 Paste JSON", self._paste_json, "#1E40AF",
            "Load a JSON fragment into the editor.\n"
            "Paste from clipboard or type/edit directly in the popup dialog.")
        _tb("💾 Save & Copy", self._save_and_copy, "#065F46",
            "Apply all layout edits back to V5's in-memory fragment AND copy the\n"
            "full JSON to the clipboard in one click.\n"
            "Use 'Export JSON' from V5's main toolbar to also save to a file.")
        tk.Frame(tb, bg="#45475a", width=1).pack(side=tk.LEFT, padx=6, fill=tk.Y, pady=2)
        _tb("➕ Add Container", self._add_child_dialog, "#065F46",
            "Add a new child container (flex-col, flex-row, grid, table, chart…)\n"
            "inside the currently selected node's Default slot.")
        _tb("🗑 Delete", self._delete_selected_node, "#7f1d1d",
            "Remove the selected node from its parent slot.\n"
            "Cannot be undone — use 'Diff vs Original' to review changes first.")
        _tb("🎯 Auto-tune", self._auto_tune, "#7c3aed",
            "Automatically assign flex values to every child container based on\n"
            "its type and whether it has an explicit width/height.\n"
            "• flex row children → 1 1 0 (equal share) or 0 0 auto (fixed)\n"
            "• flex col children → 1 (fill) or 0 0 auto (header/footer)")
        _tb("🔓 Unlock All", self._unlock_all, "#0f766e",
            "Remove the locked flag from ALL nodes so their CSS can be edited.\n"
            "Normally tables, charts, search bars etc. are locked to prevent\n"
            "accidental changes to their internal structure.")
        _tb("🔒 Re-lock All", self._relock_all, "#374151",
            "Re-apply the default locked state to all naturally-locked node types\n"
            "(table, chart, search, segment-panel, agentic-actions, footer).\n"
            "Use after editing locked nodes to restore protection.")
        tk.Frame(tb, bg="#45475a", width=1).pack(side=tk.LEFT, padx=6, fill=tk.Y, pady=2)
        _tb("🔍 Diff vs Original", self._show_diff, "#374151",
            "Show a line-by-line diff comparing the current tree against the\n"
            "snapshot taken when the fragment was first loaded.\n"
            "Only Style.css changes and slot reorders should appear.")
        _tb("🧹 Clean Empty CSS", self._clean_css, "#374151",
            "Scan every node and remove any CSS properties whose value is\n"
            "empty or null, keeping the JSON tidy before export.")
        tk.Frame(tb, bg="#45475a", width=1).pack(side=tk.LEFT, padx=6, fill=tk.Y, pady=2)
        self._glean_btn = _tb("✨ Glean AI", self._open_glean_chat, "#4C1D95",
            "Open the Glean AI advisor.\n"
            "Ask natural-language questions about your fragment;\n"
            "Glean will return reviewable CSS fix suggestions.\n"
            "(Requires browser_cookie3 + requests installed and Chrome logged in to Glean)")

        self.status_var = tk.StringVar(value="Align Fix loaded")
        tk.Label(tb, textvariable=self.status_var, bg="#1a1b2e",
                 fg="#a6e3a1", font=("TkDefaultFont",9)).pack(side=tk.RIGHT,padx=10)

        # breadcrumb
        bc = tk.Frame(self, bg="#1a1b2e", pady=1)
        bc.pack(fill=tk.X)
        self.breadcrumb_var = tk.StringVar(value="")
        tk.Label(bc, textvariable=self.breadcrumb_var,
                 bg="#1a1b2e", fg="#a6adc8",
                 font=("Courier",8)).pack(side=tk.LEFT, padx=6)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = tk.Frame(paned, bg=_AF_C_BG)
        paned.add(left, weight=1)
        self._build_left(left)

        mid = tk.Frame(paned, bg=_AF_C_BG)
        paned.add(mid, weight=3)
        self._build_center(mid)

        right = tk.Frame(paned, bg=_AF_C_BG)
        paned.add(right, weight=1)
        self._build_right(right)

        # ── Container placement panel (V5 cards → slots) ──────────────────────
        if self._v5:
            self._build_placement_panel()

    def _tbtn(self, p, text, cmd, bg="#374151"):
        def _hov(c, d=22):
            try:
                c = c.lstrip('#')
                r,g,b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
                return f"#{max(0,min(255,r+d)):02x}{max(0,min(255,g+d)):02x}{max(0,min(255,b+d)):02x}"
            except Exception:
                return c
        hover = _hov(bg)
        b = tk.Label(p, text=text, bg=bg, fg="white",
                     font=("TkDefaultFont",9), cursor="hand2",
                     relief=tk.FLAT, padx=8, pady=3)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",    lambda e, w=b: w.config(bg=hover))
        b.bind("<Leave>",    lambda e, w=b: w.config(bg=bg))
        return b

    def _tip(self, widget, text):
        """Attach a hover tooltip to any widget."""
        _tw = [None]; _job = [None]
        def _show():
            if _tw[0]: return
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tw = tk.Toplevel(self)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            tk.Label(tw, text=text, bg="#ffffcc", fg="#111827",
                     relief="solid", bd=1, padx=8, pady=4,
                     font=("TkDefaultFont",9), wraplength=320,
                     justify=tk.LEFT).pack()
            _tw[0] = tw
        def _enter(e):
            _job[0] = widget.after(500, _show)
        def _hide(e=None):
            if _job[0]: widget.after_cancel(_job[0]); _job[0] = None
            if _tw[0]: _tw[0].destroy(); _tw[0] = None
        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _hide)
        widget.bind("<Destroy>", _hide)

    # ── left: tree ─────────────────────────────────────────────────────────────
    def _build_left(self, p):
        tk.Label(p, text="Fragment Tree", bg=_AF_C_BG, fg=_AF_C_FG,
                 font=("TkDefaultFont",10,"bold")).pack(anchor=tk.W,padx=4,pady=(4,0))
        fr = tk.Frame(p, bg=_AF_C_BG)
        fr.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.tree = ttk.Treeview(fr, columns=("type","slot","lk"),
                                  show="tree headings", selectmode="browse",
                                  style="AF.Treeview")
        self.tree.heading("#0",   text="Node")
        self.tree.heading("type", text="Type")
        self.tree.heading("slot", text="Slot")
        self.tree.heading("lk",   text="")
        self.tree.column("#0",   width=200, stretch=True)
        self.tree.column("type", width=90,  stretch=False)
        self.tree.column("slot", width=65,  stretch=False)
        self.tree.column("lk",   width=22,  stretch=False)
        vsb = ttk.Scrollbar(fr,orient=tk.VERTICAL,   command=self.tree.yview)
        hsb = ttk.Scrollbar(fr,orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,  xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure("layout",  foreground=_AF_C_FG)
        self.tree.tag_configure("locked",  foreground="#a6adc8")
        self.tree.tag_configure("element", foreground="#89dceb")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<ButtonRelease-1>",  self._on_tree_click_lock)

        # Slot list
        sep_lf = ttk.LabelFrame(p, text="Slot Items", padding=2, style="AF.TLabelframe")
        sep_lf.pack(fill=tk.X, padx=4, pady=(2,0))
        lf = tk.Frame(sep_lf, bg=_AF_C_BG)
        lf.pack(fill=tk.BOTH)
        self.slot_list = tk.Listbox(
            lf, height=4, selectmode=tk.SINGLE,
            bg="#313244", fg=_AF_C_FG, selectbackground="#45475a",
            selectforeground=_AF_C_FG, activestyle="none",
            font=("Courier",9), relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        slot_sb = ttk.Scrollbar(lf, command=self.slot_list.yview)
        self.slot_list.configure(yscrollcommand=slot_sb.set)
        slot_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.slot_list.pack(fill=tk.BOTH, expand=True)
        self.slot_list.bind("<<ListboxSelect>>", self._on_slot_select)
        self.slot_list.bind("<Double-Button-1>",  self._on_slot_double)
        slot_row = tk.Frame(sep_lf, bg=_AF_C_BG)
        slot_row.pack(fill=tk.X, pady=(2,0))
        self.slot_choice = ttk.Combobox(slot_row, state="readonly", width=12)
        self.slot_choice.pack(side=tk.LEFT, padx=2)
        self.slot_choice.bind("<<ComboboxSelected>>", self._on_slot_choice)
        self.slot_path_var = tk.StringVar(value="")
        tk.Label(slot_row, textvariable=self.slot_path_var,
                 bg=_AF_C_BG, fg=_AF_C_ACC,
                 font=("TkDefaultFont",8)).pack(side=tk.LEFT,padx=4)
        br = tk.Frame(sep_lf, bg=_AF_C_BG)
        br.pack(fill=tk.X, pady=(1,0))
        b_up   = self._tbtn(br,"▲  Up",  self._move_up,   "#374151"); b_up.pack(side=tk.LEFT,padx=2)
        b_down = self._tbtn(br,"▼  Down",self._move_down, "#374151"); b_down.pack(side=tk.LEFT,padx=2)
        self._tip(b_up,   "Move the selected child one position UP in the current slot list.")
        self._tip(b_down, "Move the selected child one position DOWN in the current slot list.")

        # Info text
        info_lf = ttk.LabelFrame(p, text="Selected Node", padding=4, style="AF.TLabelframe")
        info_lf.pack(fill=tk.X, padx=4, pady=(4,4))
        self.info_text = tk.Text(info_lf, height=4, bg="#313244", fg=_AF_C_FG,
                                  font=("Courier",8), relief=tk.FLAT,
                                  state=tk.DISABLED, insertbackground=_AF_C_FG,
                                  highlightthickness=0)
        self.info_text.pack(fill=tk.X)

    # ── center: schematic canvas ───────────────────────────────────────────────
    def _build_center(self, p):
        hdr = tk.Frame(p, bg=_AF_C_BG)
        hdr.pack(fill=tk.X, padx=4, pady=(4,0))
        tk.Label(hdr, text="  Depth:", bg=_AF_C_BG, fg="#a6adc8").pack(side=tk.LEFT)
        self._depth_var = tk.IntVar(value=99)
        for d, lbl in ((1,"1"),(2,"2"),(3,"3"),(99,"All")):
            rb = tk.Radiobutton(hdr, text=lbl, variable=self._depth_var, value=d,
                                bg=_AF_C_BG, fg=_AF_C_FG, selectcolor="#45475a",
                                activebackground=_AF_C_BG, activeforeground=_AF_C_FG,
                                command=self._reload_preview)
            rb.pack(side=tk.LEFT)
            tips = {1:"Schematic: show only the top-level fragment outline.",
                    2:"Schematic: show fragment + immediate children.",
                    3:"Schematic: show two levels of nesting.",
                    99:"Schematic: show full tree (default)."}
            self._tip(rb, tips[d])
        tk.Label(hdr, text="  Click box to select · double-click to edit",
                 bg=_AF_C_BG, fg="#a6adc8", font=("TkDefaultFont",8)).pack(side=tk.LEFT, padx=(8,0))

        self._center_nb = None   # no notebook — plain canvas

        # ── Schematic canvas (full panel) ─────────────────────────────────────
        canvas_fr = tk.Frame(p, bg=_AF_C_BG)
        canvas_fr.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4,0))
        self._layout_canvas = tk.Canvas(canvas_fr, bg="#1a1b2e",
                                         highlightthickness=1,
                                         highlightbackground="#313244")
        vsb = ttk.Scrollbar(canvas_fr, orient=tk.VERTICAL,
                             command=self._layout_canvas.yview)
        hsb = ttk.Scrollbar(canvas_fr, orient=tk.HORIZONTAL,
                             command=self._layout_canvas.xview)
        self._layout_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        self._layout_canvas.pack(fill=tk.BOTH, expand=True)
        self._layout_canvas.bind("<Button-1>",       self._on_canvas_press)
        self._layout_canvas.bind("<Double-Button-1>",self._on_canvas_double)
        self._layout_canvas.bind("<Button-3>",       self._on_canvas_right)
        self._layout_canvas.bind("<B1-Motion>",      self._on_canvas_drag)
        self._layout_canvas.bind("<ButtonRelease-1>",self._on_canvas_release)
        self._layout_canvas.bind("<Motion>",         self._on_canvas_hover)
        self._layout_canvas.bind("<Leave>",          lambda e: self._hide_canvas_tooltip())
        self._layout_canvas.bind("<Configure>",      lambda e: self._reload_preview())

        # ── warnings + validate bar (always visible below notebook) ──────────
        warn_bar = tk.Frame(p, bg=_AF_C_BG)
        warn_bar.pack(fill=tk.X, padx=4, pady=(2,0))
        self._warn_var = tk.StringVar(value="")
        self._warn_lbl = tk.Label(warn_bar, textvariable=self._warn_var,
                                   bg="#451a03", fg="#fbbf24",
                                   font=("TkDefaultFont",8), wraplength=800,
                                   justify=tk.LEFT, padx=6, pady=3)
        self._warn_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._warn_lbl.pack_forget()
        b_val = self._tbtn(warn_bar, "Validate Layout", self._run_validate, "#1d4ed8")
        b_val.pack(side=tk.RIGHT, padx=2)
        self._tip(b_val,
                  "Scan the whole fragment tree for common layout mistakes:\n"
                  "• Child has fixed px height while parent has padding\n"
                  "• alignItems set on a non-flex / leaf node\n"
                  "• Flex children missing minHeight: 0\n"
                  "Results appear in the orange warning bar.")

    # ── live HTML preview tab ─────────────────────────────────────────────────
    def _active_preview_server(self):
        """AlignFix always uses its own server so it reflects the edited fragment."""
        return self._preview_server

    def _build_preview_tab(self, p):
        """Embed the same HTML preview quality as the home screen Preview button."""
        srv = self._active_preview_server()

        if _AF_HAS_TKWEB and srv:
            # ── Thin control bar ─────────────────────────────────────────────
            bar = tk.Frame(p, bg="#0f172a", pady=3)
            bar.pack(fill=tk.X)
            self._preview_live_var = tk.StringVar(value="● Live")
            tk.Label(bar, textvariable=self._preview_live_var,
                     bg="#0f172a", fg="#22c55e",
                     font=("TkDefaultFont",8,"bold")).pack(side=tk.LEFT, padx=8)
            tk.Label(bar, text="Updates every 400 ms as you edit CSS",
                     bg="#0f172a", fg="#475569",
                     font=("TkDefaultFont",8)).pack(side=tk.LEFT)
            b_rf = tk.Button(bar, text="↺", bg="#1e293b", fg="#94A3B8",
                             relief=tk.FLAT, padx=6, pady=1, cursor="hand2",
                             font=("TkDefaultFont",9),
                             command=lambda: self._force_preview_reload())
            b_rf.pack(side=tk.RIGHT, padx=4)
            self._tip(b_rf, "Force-reload the preview from the current fragment immediately.")

            # ── tkinterweb frame filling the rest ─────────────────────────────
            try:
                hf = _AF_HtmlFrame(p, messages_enabled=False,
                                   horizontal_scrollbar=True, vertical_scrollbar=True)
                hf.pack(fill=tk.BOTH, expand=True)
                self._html_view = hf
                # Load an initial "loading" page; real content pushed on first update
                hf.load_website(srv.url)
                return
            except Exception:
                self._html_view = None

        # ── Fallback: tkinterweb not installed ────────────────────────────────
        self._html_view = None
        outer = tk.Frame(p, bg="#0f172a")
        outer.pack(fill=tk.BOTH, expand=True)
        card = tk.Frame(outer, bg="#1e293b")
        card.place(relx=0.5, rely=0.45, anchor="center")
        tk.Label(card, text="📦  Install tkinterweb for embedded preview",
                 bg="#1e293b", fg="#f59e0b",
                 font=("TkDefaultFont",12,"bold")).pack(padx=32, pady=(24,6))
        tk.Label(card, text="pip install tkinterweb",
                 bg="#0f172a", fg="#67e8f9",
                 font=("Courier",12)).pack(padx=32, pady=4)
        tk.Label(card, text="Restart the designer after installing.",
                 bg="#1e293b", fg="#64748b",
                 font=("TkDefaultFont",10)).pack(padx=32, pady=(4,24))

    def _force_preview_reload(self):
        """Regenerate HTML, push to server, then reload the embedded frame."""
        self._update_html_preview(force=True)
        if self._html_view and self._active_preview_server():
            try:
                self._html_view.load_website(self._active_preview_server().url)
            except Exception:
                pass

    def _on_center_tab_change(self, event=None):
        """When Live HTML tab becomes visible: push fresh HTML and reload frame."""
        if self._center_nb is None: return
        try:
            idx = self._center_nb.index("current")
        except tk.TclError:
            return
        if idx == 1:
            self._force_preview_reload()

    def _get_preview_html(self):
        """Generate the same full-quality HTML as the home screen Preview button."""
        if not self.fragment_root:
            return ("<html><body style='font:13px sans-serif;padding:20px;color:#888'>"
                    "No fragment loaded</body></html>")
        try:
            frag_copy = copy.deepcopy(self.fragment_root)
            _strip_internal_meta(frag_copy)
            json_str = json.dumps(frag_copy, indent=2)
            if self._v5 and hasattr(self._v5, "_build_preview_html"):
                return self._v5._build_preview_html(json_str)
            return self._simple_fragment_html(json_str)
        except Exception as e:
            return (f"<html><body style='font:13px monospace;padding:20px;color:#dc2626'>"
                    f"<b>Preview error:</b><br>{e}</body></html>")

    def _simple_fragment_html(self, json_str):
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<style>*{box-sizing:border-box}body{font-family:sans-serif;font-size:12px;"
            "background:#f1f5f9;padding:16px}</style></head>"
            "<body><pre style='background:white;padding:16px;border-radius:8px;"
            "border:1px solid #e2e8f0;overflow:auto;font-size:11px'>"
            + json_str.replace("<","&lt;").replace(">","&gt;") +
            "</pre></body></html>"
        )

    def _schedule_html_update(self):
        """Debounce: push HTML 350 ms after the last change."""
        if hasattr(self, "_html_debounce"):
            try: self.after_cancel(self._html_debounce)
            except Exception: pass
        self._html_debounce = self.after(350, self._update_html_preview)

    def _update_html_preview(self, force=False):
        """Push regenerated HTML to the server. tkinterweb polls via JS and auto-reloads."""
        if not self.fragment_root: return
        srv = self._active_preview_server()
        if not srv: return
        try:
            html = self._get_preview_html()
            # Inject auto-reload polling script so tkinterweb/browser refreshes automatically
            script = (
                "<script>(function(){"
                "var lv=null;"
                "setInterval(function(){"
                "fetch('/version').then(function(r){return r.text();}).then(function(v){"
                "if(lv===null){lv=v;}else if(v!==lv){lv=v;location.reload();}"
                "}).catch(function(){});},400);"
                "})();</script>"
            )
            if "</body>" in html:
                html = html.replace("</body>", script + "</body>", 1)
            else:
                html += script
            srv.update(html)
        except Exception:
            pass

    # ── right: CSS editor ─────────────────────────────────────────────────────
    def _build_right(self, p):
        tk.Label(p, text="Layout CSS Editor", bg=_AF_C_BG, fg=_AF_C_FG,
                 font=("TkDefaultFont",10,"bold")).pack(anchor=tk.W,padx=4,pady=(4,0))
        self.lock_warn_var = tk.StringVar(value="")
        lock_row = tk.Frame(p, bg=_AF_C_BG)
        lock_row.pack(anchor=tk.W, padx=4, fill=tk.X)
        tk.Label(lock_row, textvariable=self.lock_warn_var, bg=_AF_C_BG,
                 fg="#f38ba8", font=("TkDefaultFont",8,"italic")).pack(side=tk.LEFT)
        self._unlock_btn = tk.Button(lock_row, text="🔓 Unlock",
                                      command=self._toggle_lock_selected,
                                      bg="#7c3aed", fg="black", relief=tk.FLAT,
                                      padx=6, pady=1, cursor="hand2",
                                      font=("TkDefaultFont",8))
        self._unlock_btn.pack(side=tk.LEFT, padx=(6,0))
        self._tip(self._unlock_btn,
                  "Toggle lock on the selected node.\n"
                  "Locked nodes (table, chart, search…) cannot have their CSS edited\n"
                  "until unlocked. Unlocking lets you set flex/width/height on them.")
        outer = tk.Frame(p, bg=_AF_C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        cv = tk.Canvas(outer, bg=_AF_C_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._css_canvas = cv
        inner = tk.Frame(cv, bg=_AF_C_BG)
        wid = cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",   lambda e: cv.itemconfig(wid, width=e.width))
        cv.bind("<MouseWheel>",  lambda e: cv.yview_scroll(-1*(e.delta//120),"units"))
        self.css_vars: dict[str,tk.StringVar] = {}
        self.css_entries: dict[str,ttk.Entry] = {}
        for prop in _AF_LAYOUT_CSS_PROPS:
            row = tk.Frame(inner, bg=_AF_C_BG)
            row.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(row, text=prop, width=22, anchor=tk.E,
                     bg=_AF_C_BG, fg=_AF_C_ACC).pack(side=tk.LEFT)
            var = tk.StringVar()
            self.css_vars[prop] = var
            e = ttk.Entry(row, textvariable=var, width=20)
            e.pack(side=tk.LEFT, padx=(4,0), fill=tk.X, expand=True)
            self.css_entries[prop] = e
            e.bind("<Return>",   lambda ev, pr=prop: self._apply_css_prop(pr, True))
            e.bind("<FocusOut>", lambda ev, pr=prop: self._apply_css_prop(pr, True))

        btn_fr = tk.Frame(p, bg=_AF_C_BG)
        btn_fr.pack(fill=tk.X, padx=4, pady=4)
        b_apply = self._tbtn(btn_fr,"Apply All",self._apply_all_css, "#065F46")
        b_apply.pack(side=tk.LEFT,padx=2)
        self._tip(b_apply,
                  "Write every filled field in the CSS editor to the selected node's\n"
                  "Style.css in one shot. Also migrates any top-level Style.flex /\n"
                  "Style.padding etc. into Style.css to normalise the node.")
        b_reset = self._tbtn(btn_fr,"Reset CSS",self._reset_node_css,"#7f1d1d")
        b_reset.pack(side=tk.LEFT,padx=2)
        self._tip(b_reset,
                  "Clear ALL CSS from the selected node — both Style.css and any\n"
                  "top-level Style.flex/padding/height keys. Cannot be undone.")

        def _qbtn(parent, text, bg, tip, cmd):
            def _hov(c, d=22):
                try:
                    c = c.lstrip('#')
                    r,g,b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
                    return f"#{max(0,min(255,r+d)):02x}{max(0,min(255,g+d)):02x}{max(0,min(255,b+d)):02x}"
                except Exception:
                    return c
            hover = _hov(bg)
            b = tk.Label(parent, text=text, bg=bg, fg="white",
                         relief=tk.FLAT, padx=5, pady=2, cursor="hand2",
                         font=("TkDefaultFont",8))
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e, w=b: w.config(bg=hover))
            b.bind("<Leave>",    lambda e, w=b: w.config(bg=bg))
            b.pack(side=tk.LEFT, padx=2, pady=2)
            self._tip(b, tip)

        # Quick flex presets
        qf = ttk.LabelFrame(p, text="Quick Flex (grow · shrink · basis)",
                             padding=4, style="AF.TLabelframe")
        qf.pack(fill=tk.X, padx=4, pady=(2,2))
        for val, tip, bg in [
            ("1 1 auto", "flex: 1 1 auto\nItem grows AND shrinks. Starts at its natural content size.\nTypical for panels that should share space proportionally.", "#1d4ed8"),
            ("1 1 0",    "flex: 1 1 0\nItem grows AND shrinks. Starts at zero — forces strictly equal sharing.\nBest for side-by-side columns that must all be the same width.", "#0f766e"),
            ("0 0 auto", "flex: 0 0 auto\nItem is fixed — does NOT grow or shrink.\nUse for sidebars, headers, footers with a known/natural size.", "#7c3aed"),
            ("1",        "flex: 1\nShorthand for 'grow to fill remaining space'.\nQuick way to make one item expand while siblings stay fixed.", "#065F46"),
        ]:
            def _mk(v=val):
                def _f(): self.css_vars["flex"].set(v); self._apply_css_prop("flex",True)
                return _f
            _qbtn(qf, f"flex:{val}", bg, tip, _mk())

        qg = ttk.LabelFrame(p, text="Quick Gap", padding=4, style="AF.TLabelframe")
        qg.pack(fill=tk.X, padx=4, pady=(0,4))
        for sz, tip in [
            ("0",    "gap: 0 — no space between children."),
            ("4px",  "gap: 4px — tight spacing, good for compact toolbars."),
            ("8px",  "gap: 8px — small spacing."),
            ("12px", "gap: 12px — medium spacing."),
            ("16px", "gap: 16px — standard card-row spacing."),
            ("24px", "gap: 24px — generous spacing between sections."),
        ]:
            def _mgp(s=sz):
                def _f(): self.css_vars["gap"].set(s); self._apply_css_prop("gap",True)
                return _f
            _qbtn(qg, sz, "#374151", tip, _mgp())

        qa = ttk.LabelFrame(p, text="Quick alignItems (parent → cross axis)",
                             padding=4, style="AF.TLabelframe")
        qa.pack(fill=tk.X, padx=4, pady=(0,4))
        for val, tip, bg in [
            ("stretch",    "alignItems: stretch (default)\nAll children expand to fill the parent's cross-axis size.\nIn a row: all items become equal height. Best for card rows.", "#0f766e"),
            ("flex-start", "alignItems: flex-start\nChildren align to the start of the cross axis (top in a row).\nEach keeps its own natural height — heights may differ.", "#1d4ed8"),
            ("flex-end",   "alignItems: flex-end\nChildren align to the end of the cross axis (bottom in a row).", "#7c3aed"),
            ("center",     "alignItems: center\nChildren are centred on the cross axis.", "#065F46"),
        ]:
            def _mai(v=val):
                def _f(): self.css_vars["alignItems"].set(v); self._apply_css_prop("alignItems",True)
                return _f
            _qbtn(qa, val, bg, tip, _mai())

        qs = ttk.LabelFrame(p, text="Quick alignSelf (child override)",
                             padding=4, style="AF.TLabelframe")
        qs.pack(fill=tk.X, padx=4, pady=(0,4))
        for val, tip, bg in [
            ("stretch",    "alignSelf: stretch\nThis child stretches to fill the parent's cross size,\noverriding the parent's alignItems.", "#0f766e"),
            ("flex-start", "alignSelf: flex-start\nThis child aligns to the cross-start (top in a row),\noverriding the parent's alignItems.", "#1d4ed8"),
            ("flex-end",   "alignSelf: flex-end\nThis child aligns to the cross-end.", "#7c3aed"),
            ("auto",       "alignSelf: auto\nInherits alignment from the parent's alignItems (default behaviour).", "#374151"),
        ]:
            def _mas(v=val):
                def _f(): self.css_vars["alignSelf"].set(v); self._apply_css_prop("alignSelf",True)
                return _f
            _qbtn(qs, val, bg, tip, _mas())

        qh = ttk.LabelFrame(p, text="Quick Height", padding=4, style="AF.TLabelframe")
        qh.pack(fill=tk.X, padx=4, pady=(0,4))
        for val, tip, bg in [
            ("100%",        "height: 100%\nChild fills the full height of its parent.\nRequires the parent to have an explicit height defined.", "#0f766e"),
            ("auto",        "height: auto\nHeight is determined by the content inside.\nDefault behaviour — the element grows with its content.", "#374151"),
            ("fit-content", "height: fit-content\nShrinks to wrap content tightly, like auto, but respects min/max.", "#1d4ed8"),
            ("0",           "height: 0\nCollapses the element to zero height.\nCombine with overflow:hidden to fully hide content.", "#7c3aed"),
        ]:
            def _mah(v=val):
                def _f(): self.css_vars["height"].set(v); self._apply_css_prop("height",True)
                return _f
            _qbtn(qh, val, bg, tip, _mah())

        qmh = ttk.LabelFrame(p, text="Quick minHeight", padding=4, style="AF.TLabelframe")
        qmh.pack(fill=tk.X, padx=4, pady=(0,4))
        for val, tip, bg in [
            ("0",     "minHeight: 0\nAllows a flex item to shrink BELOW its content height.\nEssential for nested scrollable containers — without this\nthe inner scroll never activates.", "#7c3aed"),
            ("auto",  "minHeight: auto (default)\nFlex item cannot shrink smaller than its content.\nMay prevent inner scroll from working in nested layouts.", "#374151"),
            ("100px", "minHeight: 100px\nItem will always be at least 100px tall.", "#0f766e"),
            ("200px", "minHeight: 200px\nItem will always be at least 200px tall.", "#065F46"),
        ]:
            def _mamh(v=val):
                def _f(): self.css_vars["minHeight"].set(v); self._apply_css_prop("minHeight",True)
                return _f
            _qbtn(qmh, val, bg, tip, _mamh())

        qov = ttk.LabelFrame(p, text="Quick Overflow", padding=4, style="AF.TLabelframe")
        qov.pack(fill=tk.X, padx=4, pady=(0,4))
        for val, tip, bg in [
            ("hidden",  "overflow: hidden\nContent that exceeds the box is clipped and invisible.\nUse to prevent child content from spilling out of a container.", "#1d4ed8"),
            ("auto",    "overflow: auto\nScrollbars appear only when content overflows.\nBest for scrollable panels — combine with minHeight:0 on flex items.", "#0f766e"),
            ("visible", "overflow: visible (default)\nContent is allowed to overflow the boundary without clipping.", "#374151"),
            ("scroll",  "overflow: scroll\nScrollbars always visible even if content fits.\nRarely needed — prefer 'auto'.", "#7c3aed"),
        ]:
            def _mov(v=val):
                def _f(): self.css_vars["overflow"].set(v); self._apply_css_prop("overflow",True)
                return _f
            _qbtn(qov, val, bg, tip, _mov())

        # ── Quick Fix Panel ───────────────────────────────────────────────────
        # Preset multi-property fixes based on the Flex Layout Behavior Guide
        _QUICK_FIXES = [
            ("Parent row equal heights",
             {"flexDirection":"row","alignItems":"stretch","minHeight":"0"},
             "Sets up a flex ROW container so all children stretch to equal height.\n"
             "alignItems:stretch is the default but often gets overridden — reset it here."),
            ("Fixed right sidebar 380px",
             {"flex":"0 0 380px","width":"380px","height":"100%","alignSelf":"stretch","overflow":"hidden"},
             "Locks this child to exactly 380px wide, full height, no overflow.\n"
             "Use on the right sidebar child of a flex-row parent."),
            ("Flexible left panel",
             {"flex":"1 1 auto","height":"100%","minWidth":"0","minHeight":"0"},
             "The left/main content child that should fill remaining space.\n"
             "minWidth:0 + minHeight:0 allow it to shrink properly inside nested flex."),
            ("Nested scrollable content",
             {"minHeight":"0","overflow":"auto"},
             "Inner container that needs to scroll vertically.\n"
             "minHeight:0 lets the flex item shrink below content size so scroll activates."),
            ("Child fill height",
             {"height":"100%"},
             "Makes this child fill the full height of its parent.\n"
             "Requires the parent to have an explicit height (not 'auto')."),
            ("Prevent overflow",
             {"overflow":"hidden"},
             "Clips any content that exceeds this box — prevents child from spilling out."),
            ("Flex safe min-height",
             {"minHeight":"0"},
             "Without minHeight:0 a flex item cannot shrink below its content.\n"
             "This is the most common reason inner scrollbars don't activate."),
        ]
        qfix = ttk.LabelFrame(p, text="Quick Fix Presets  (Behavior Guide)", padding=4, style="AF.TLabelframe")
        qfix.pack(fill=tk.X, padx=4, pady=(0,4))
        tk.Label(qfix, text="Select a node, then apply a preset to write multiple CSS values at once.",
                 bg=_AF_C_BG, fg="#a6adc8", font=("TkDefaultFont",8), wraplength=240).pack(anchor=tk.W)
        for label, props, tip in _QUICK_FIXES:
            row_f = tk.Frame(qfix, bg=_AF_C_BG)
            row_f.pack(fill=tk.X, pady=1)
            desc_lbl = tk.Label(row_f, text=label, bg=_AF_C_BG, fg=_AF_C_FG,
                                font=("TkDefaultFont",8), anchor=tk.W, width=24)
            desc_lbl.pack(side=tk.LEFT)
            vals_text = "  ".join(f"{k}:{v}" for k,v in props.items())
            val_lbl = tk.Label(row_f, text=vals_text, bg=_AF_C_BG, fg=_AF_C_ACC,
                               font=("Courier",7), anchor=tk.W)
            val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2,4))
            def _mk_fix(p2=props):
                def _f(): self._apply_quick_fix(p2)
                return _f
            b = tk.Button(row_f, text="Apply", bg="#1d4ed8", fg="white",
                          relief=tk.FLAT, padx=6, pady=1, cursor="hand2",
                          font=("TkDefaultFont",8), command=_mk_fix())
            b.pack(side=tk.RIGHT)
            self._tip(b, tip)
            self._tip(desc_lbl, tip)

    # ── container placement panel (V5 cards → slots) ──────────────────────────
    def _build_placement_panel(self):
        pf = ttk.LabelFrame(self, text="Container Placement  (V5 cards → AlignFix slots)",
                             padding=4, style="AF.TLabelframe")
        pf.pack(fill=tk.X, padx=4, pady=(0,4))
        desc = tk.Label(pf,
            text="Select a V5 card below, then select a slot node in the tree, then click 'Place Here'.",
            bg=_AF_C_BG, fg="#a6adc8", font=("TkDefaultFont",8))
        desc.pack(anchor=tk.W)
        row = tk.Frame(pf, bg=_AF_C_BG)
        row.pack(fill=tk.X)
        self._v5_card_var = tk.StringVar()
        cards = self._v5.cards if self._v5 else {}
        card_choices = [f"{cid}: {getattr(c,'title',cid)} [{getattr(c,'ctype','?')}]"
                        for cid, c in cards.items()]
        self._v5_card_combo = ttk.Combobox(row, textvariable=self._v5_card_var,
                                            values=card_choices or ["(no V5 cards)"],
                                            state="readonly", width=40)
        self._v5_card_combo.pack(side=tk.LEFT, padx=4)
        if card_choices:
            self._v5_card_combo.set(card_choices[0])
        b_place   = self._tbtn(row, "Place Here →", self._place_v5_card, "#0f766e")
        b_place.pack(side=tk.LEFT, padx=4)
        self._tip(b_place,
                  "Insert the selected V5 card's JSON node as a child of the selected\n"
                  "tree node. If the target has multiple slots you will be asked which one.")
        b_refresh = self._tbtn(row, "Refresh Cards", self._refresh_card_list, "#374151")
        b_refresh.pack(side=tk.LEFT)
        self._tip(b_refresh, "Reload the V5 card list from the current canvas (use after adding cards in V5).")

    def _refresh_card_list(self):
        if not self._v5: return
        cards = self._v5.cards
        choices = [f"{cid}: {getattr(c,'title',cid)} [{getattr(c,'ctype','?')}]"
                   for cid, c in cards.items()]
        self._v5_card_combo["values"] = choices or ["(no V5 cards)"]

    def _place_v5_card(self):
        """Insert the selected V5 card's JSON into the selected tree slot."""
        if not self._v5: return
        ref = self._selected_slot_ref
        if not ref:
            messagebox.showinfo("No Selection","Select a container in the tree first.",parent=self); return
        slots_available = [k for k,v in (ref.node.get("Slots") or {}).items() if isinstance(v,list)]
        if not slots_available:
            messagebox.showinfo("No Slots","Selected node has no slots.",parent=self); return
        sel = self._v5_card_var.get()
        if not sel or sel.startswith("("):
            messagebox.showinfo("No Card","Select a V5 card first.",parent=self); return
        cid = sel.split(":")[0].strip()
        card = self._v5.cards.get(cid)
        if not card:
            messagebox.showwarning("Not Found",f"Card {cid} not found.",parent=self); return
        # Ask which slot
        if len(slots_available) == 1:
            slot = slots_available[0]
        else:
            from tkinter import simpledialog
            slot = simpledialog.askstring("Choose Slot",
                f"Available slots: {', '.join(slots_available)}\nEnter slot name:",
                initialvalue="Default", parent=self)
            if not slot: return
        # Build a minimal node from the V5 card
        ctype_map = {
            "table": "table", "chart": "chart", "search": "search",
            "segment-panel": "segment-panel", "flex": "flex", "grid": "grid",
            "header-action": "header-action",
        }
        ct = getattr(card,"ctype","flex")
        node = {"Container": ctype_map.get(ct, ct)}
        if hasattr(card,"title") and card.title:
            node.setdefault("Config",{})["title"] = card.title
        node.setdefault("Slots",{})["Default"] = []
        ref.node.setdefault("Slots",{}).setdefault(slot,[]).append(node)
        self._rebuild_tree(reselect_path=ref.path)
        self._reload_preview()
        self.status_var.set(f"Placed {card.title or cid} into {slot}")

    # ── apply back to V5 ──────────────────────────────────────────────────────
    def _apply_to_v5(self):
        """Silently sync fragment edits back to V5 in-memory state. Returns diff count."""
        if not self._v5: return 0
        diffs: list = []
        _af_diff_trees(self.orig_snapshot, self.fragment_root, "root", diffs)
        frag = self.fragment_root.get("Fragment", self.fragment_root)
        self._v5.imported_fragment_root = copy.deepcopy(frag)
        self.orig_snapshot = copy.deepcopy(self.fragment_root)
        outer_css = (frag.get("Style") or {}).get("css") or {}
        if outer_css.get("gap"):    self._v5.layout_prefs["gap"]     = outer_css["gap"]
        if outer_css.get("padding"):self._v5.layout_prefs["padding"] = outer_css["padding"]
        return len(diffs)

    def _save_and_copy(self):
        """Apply edits to V5 + copy JSON + refresh the browser preview."""
        if not self.fragment_root:
            self.status_var.set("Nothing loaded"); return
        export = copy.deepcopy(self.fragment_root)
        self._clean_internal_keys(export)
        self.clipboard_clear()
        self.clipboard_append(json.dumps(export, indent=2))
        n = self._apply_to_v5() if self._v5 else 0
        # Push to the main designer's live preview server so the browser refreshes
        self._push_to_main_preview()
        msg = f"Saved to V5 ({n} change{'s' if n!=1 else ''}) + copied + browser refreshed"
        if not self._v5:
            msg = "Copied JSON to clipboard + browser refreshed"
        self.status_var.set(msg)

    def _push_to_main_preview(self):
        """Refresh the browser preview using the exact same logic as the Preview button."""
        if not self._v5: return
        srv = getattr(self._v5, '_live_preview_server', None)
        if not srv: return
        try:
            # _build_fragment() is identical to what the Preview button calls —
            # it picks up the imported_fragment_root we just updated via _apply_to_v5()
            frag = self._v5._build_fragment()
            html = self._v5._build_preview_html(json.dumps(frag, indent=2))
            html = self._v5._inject_live_reload_script(html, srv)
            srv.update(html)
        except Exception:
            pass

    # ═══════ layout engine (mirrors fragdesgV6.py) ════════════════════════════

    def _reload_preview(self):
        c = self._layout_canvas
        if c is None: return
        c.delete("all")
        self._click_zones = []
        cw = max(c.winfo_width(), 20)
        ch = max(c.winfo_height(), 20)
        if not self.fragment_root:
            c.create_text(cw//2,ch//2,text="No fragment loaded",fill="#444",font=("TkDefaultFont",11))
            return
        frag  = self.fragment_root.get("Fragment",{})
        items = self._compute_layout(frag, 0, 0, _AF_VW, _AF_VH, "Fragment")
        sx = (cw-2) / _AF_VW
        sy = (ch-2) / _AF_VH
        self._sx, self._sy = sx, sy
        for node, vx, vy, vw, vh, path in items:
            cx2 = 1 + vx*sx;  cy2 = 1 + vy*sy
            self._draw_wireframe(c, node, cx2, cy2, max(vw*sx,2), max(vh*sy,2), path)
        c.configure(scrollregion=c.bbox("all") or (0,0,cw,ch))
        # Draw resize handles on the selected node (on top of everything)
        self._draw_resize_handles(c)

    def _draw_resize_handles(self, c):
        """Draw visible drag handles on the selected node's edges."""
        sel = self._selected_preview_node
        if not sel: return
        box = next((z for z in self._click_zones if z[4] is sel), None)
        if not box: return
        x1, y1, x2, y2 = box[:4]
        w, h = x2 - x1, y2 - y1
        if w < 10 or h < 10: return
        HS = 8   # handle size in pixels
        H2 = HS // 2
        # Define handle positions: (cx, cy, direction-tag)
        handles = [
            (x2,       y1+h//2,  "h"),    # right edge — resize width
            (x1+w//2,  y2,       "v"),    # bottom edge — resize height
            (x2,       y2,       "both"), # bottom-right corner — resize both
        ]
        for hx, hy, _ in handles:
            # Shadow
            c.create_rectangle(hx-H2+1, hy-H2+1, hx+H2+1, hy+H2+1,
                                fill="#1e3a5f", outline="")
            # Handle body
            c.create_rectangle(hx-H2, hy-H2, hx+H2, hy+H2,
                                fill="#3b82f6", outline="white", width=1)
        # Show current dimensions near bottom-right corner
        css   = (sel.get("Style") or {}).get("css") or {}
        style = (sel.get("Style") or {})
        dims  = "  ".join(f"{k}:{css.get(k) or style.get(k)}"
                          for k in ("flex","width","height","minHeight")
                          if css.get(k) or style.get(k))
        if dims and w > 60:
            c.create_text(x2-4, y2-4, text=dims, fill="#3b82f6",
                          font=("Courier", max(int(min(w/18, 7)), 5)), anchor="se")

    def _compute_layout(self, node, x, y, w, h, path, _depth=0):
        result = [(node,x,y,w,h,path)]
        if not isinstance(node,dict) or w<=0 or h<=0: return result
        # Stop recursing when we've reached the user-selected depth limit
        if _depth >= self._depth_var.get(): return result
        ctype    = node.get("Container","")
        css      = (node.get("Style") or {}).get("css") or {}
        style    = node.get("Style") or {}
        is_grid  = (ctype=="grid")
        is_row   = css.get("flexDirection","column") in ("row","row-reverse")
        pt,pr,pb,pl = _af_parse_padding(css.get("padding") or style.get("padding","0"))
        gap  = _af_px_val(str(css.get("gap","0"))) or 0
        ix,iy = x+pl, y+pt
        iw,ih = max(w-pl-pr,0), max(h-pt-pb,0)
        slots = node.get("Slots") or {}
        if is_grid:
            raw   = css.get("grid-template-areas","")
            order = re.findall(r'"([^"]+)"',raw) or list(slots.keys())
            kids  = []
            for sn in order:
                for i,ch in enumerate(slots.get(sn) or []):
                    if isinstance(ch,dict): kids.append((ch,f"{path}.{sn}[{i}]"))
        else:
            kids = [(ch,f"{path}.Default[{i}]")
                    for i,ch in enumerate(slots.get("Default") or []) if isinstance(ch,dict)]
        if not kids: return result
        n = len(kids)
        avail = iw if is_row else ih
        sizes = self._flex_sizes_af([k for k,_ in kids], avail-gap*max(n-1,0), is_row, is_grid)
        cursor = 0.0
        for (child,cp), size in zip(kids, sizes):
            if is_row: cx2,cy2,cw2,ch2 = ix+cursor, iy, size, ih
            else:      cx2,cy2,cw2,ch2 = ix, iy+cursor, iw, size
            result.extend(self._compute_layout(child,cx2,cy2,max(cw2,0),max(ch2,0),cp,_depth+1))
            cursor += size+gap
        return result

    def _flex_sizes_af(self, children, available, is_row, is_grid):
        VREF = _AF_VW if is_row else _AF_VH
        specs = []
        for i,child in enumerate(children):
            ctype = child.get("Container","")
            css   = (child.get("Style") or {}).get("css") or {}
            style = child.get("Style") or {}
            if is_grid:
                specs.append(("fixed",_AF_AUTO_H.get(ctype,36)) if i==0 else ("flex",1.0))
                continue
            flex_s = str(css.get("flex") or style.get("flex","")).strip()
            parts  = flex_s.split()
            placed = False
            if parts:
                try:
                    grow = float(parts[0])
                    if len(parts)==1:
                        specs.append(("fixed",_AF_AUTO_H.get(ctype,40)) if grow==0 else ("flex",max(grow,0.1)))
                        placed=True
                    elif len(parts)>=3:
                        shrink=float(parts[1]); basis=parts[2]
                        if grow==0 and shrink==0:
                            px=_af_px_val(basis,VREF)
                            if px: specs.append(("fixed",px)); placed=True
                        elif basis in ("0","0px","0rem"):
                            specs.append(("flex",max(grow,0.1))); placed=True
                        elif basis=="auto":
                            specs.append(("flex",max(grow,0.1))); placed=True
                        elif grow>0:
                            specs.append(("flex",max(grow,0.1))); placed=True
                except (ValueError,IndexError): pass
            if placed: continue
            dim="width" if is_row else "height"
            done=False
            for k in (dim,"min"+dim[0].upper()+dim[1:]):
                v=css.get(k) or style.get(k)
                if v:
                    pv=_af_px_val(str(v),VREF)
                    if pv and str(v) not in ("100%","100vh","100vw"):
                        specs.append(("fixed",pv)); done=True; break
            if done: continue
            if not is_row and ctype in _AF_AUTO_H:
                specs.append(("fixed",_AF_AUTO_H[ctype])); continue
            specs.append(("flex",1.0))
        fixed_t = sum(v for k,v in specs if k=="fixed")
        flex_t  = sum(v for k,v in specs if k=="flex") or 1e-9
        flex_av = max(available-fixed_t, len(specs)*4)
        result  = [max(v if k=="fixed" else v/flex_t*flex_av,2) for k,v in specs]
        total   = sum(result)
        if total>1 and abs(total-available)>0.5:
            f=available/total; result=[r*f for r in result]
        return result

    def _draw_rounded_rect(self, c, x, y, w, h, r, fill, outline, width=1, dash=None):
        """Draw a rectangle with simulated rounded corners on the tkinter canvas."""
        r = max(0.0, min(float(r), w/2-1, h/2-1))
        kw_rect = {"fill": fill, "outline": outline, "width": width}
        if dash: kw_rect["dash"] = dash
        if r < 2:
            c.create_rectangle(x, y, x+w, y+h, **kw_rect); return
        # Fill body (three overlapping rects cover all interior pixels)
        c.create_rectangle(x+r, y,   x+w-r, y+h,   fill=fill, outline="")
        c.create_rectangle(x,   y+r, x+w,   y+h-r, fill=fill, outline="")
        # Corner arc fills
        for ax, ay, st in [(x, y, 90), (x+w-2*r, y, 0), (x, y+h-2*r, 180), (x+w-2*r, y+h-2*r, 270)]:
            c.create_arc(ax, ay, ax+2*r, ay+2*r, start=st, extent=90, fill=fill, outline="", style="pieslice")
        if not outline: return
        # Border straight segments
        kw_ln = {"fill": outline, "width": width}
        if dash: kw_ln["dash"] = dash
        c.create_line(x+r,   y,     x+w-r, y,     **kw_ln)
        c.create_line(x+r,   y+h,   x+w-r, y+h,   **kw_ln)
        c.create_line(x,     y+r,   x,     y+h-r, **kw_ln)
        c.create_line(x+w,   y+r,   x+w,   y+h-r, **kw_ln)
        # Border corner arcs
        kw_arc = {"outline": outline, "width": width, "style": "arc"}
        if dash: kw_arc["dash"] = dash
        for ax, ay, st in [(x, y, 90), (x+w-2*r, y, 0), (x, y+h-2*r, 180), (x+w-2*r, y+h-2*r, 270)]:
            c.create_arc(ax, ay, ax+2*r, ay+2*r, start=st, extent=90, **kw_arc)

    def _draw_wireframe(self, c, node, x, y, w, h, path):
        ctype    = node.get("Container","")
        etype    = node.get("Element","")
        selected = (node is self._selected_preview_node)
        locked   = _af_is_locked(node)
        css      = (node.get("Style") or {}).get("css") or {}
        style    = node.get("Style") or {}

        # ── base colors from type palette ──────────────────────────────────────
        fill, outline = _AF_SCHEMATIC_COLORS.get(ctype or "element", _AF_SCHEMATIC_COLORS["default"])

        # CSS background overrides palette fill (skip gradients/url)
        css_bg = css.get("background") or css.get("backgroundColor") or style.get("background")
        if css_bg:
            res = _af_resolve_var(str(css_bg))
            if res and not any(res.lstrip().startswith(p) for p in ("linear","radial","url","none")):
                fill = res

        # CSS border: parse "2px solid #aaa" → outline color + width
        outline_w = 1
        css_bdr = css.get("border") or style.get("border")
        if css_bdr:
            for part in str(css_bdr).split():
                if part.startswith("#") or part.startswith("rgb"):
                    outline = _af_resolve_var(part)
                elif part.endswith("px"):
                    try: outline_w = max(1, round(float(part[:-2])))
                    except ValueError: pass

        # boxShadow — simulate with a slightly larger muted offset rect below
        box_shadow = css.get("boxShadow") or style.get("boxShadow")
        if box_shadow and box_shadow not in ("none",""):
            c.create_rectangle(x+3, y+3, x+w+3, y+h+3, fill="#b0b0b0", outline="")

        # Selection / lock overrides
        if selected:
            outline = "#ef4444" if ctype == "flex" else "#f59e0b"
            outline_w = 3 if ctype == "flex" else 2
        elif locked:
            outline = "#f38ba8"

        # borderRadius → scale to canvas pixels
        br_raw = css.get("borderRadius") or style.get("borderRadius")
        br_px  = 0.0
        if br_raw and br_raw not in ("0","0px",""):
            br_px = (_af_px_val(str(br_raw)) or 0) * min(getattr(self,"_sx",1), getattr(self,"_sy",1))
            br_px = max(0.0, min(br_px, 10.0))

        # dash for flex containers
        dash = (8,3) if (selected and ctype=="flex") else (6,3) if ctype=="flex" else None

        # Draw shape
        self._draw_rounded_rect(c, x, y, w, h, br_px, fill, outline, outline_w, dash)
        self._click_zones.append((x, y, x+w, y+h, node, path))

        # Draw padding inset indicator for all containers (before type-specific content)
        _pad_raw = css.get("padding") or style.get("padding","")
        if _pad_raw and _pad_raw not in ("0","0px",""):
            _pad_sc = (_af_px_val(str(_pad_raw).split()[0]) or 0) * min(getattr(self,"_sx",1), getattr(self,"_sy",1))
            _pad_sc = max(2.0, min(float(_pad_sc), min(w,h)/4))
            c.create_rectangle(x+_pad_sc, y+_pad_sc, x+w-_pad_sc, y+h-_pad_sc,
                               fill="", outline="#94a3b8", width=1, dash=(3,3))

        if   ctype=="header-action":    self._wf_header_action(c,node,x,y,w,h)
        elif ctype=="header":           self._wf_header(c,node,x,y,w,h)
        elif ctype=="table":            self._wf_table(c,node,x,y,w,h)
        elif ctype=="chart":            self._wf_chart(c,node,x,y,w,h)
        elif ctype=="search":           self._wf_search(c,node,x,y,w,h)
        elif ctype=="segment-panel":    self._wf_segment(c,node,x,y,w,h)
        elif ctype=="footer-container": self._wf_footer(c,node,x,y,w,h)
        elif not ctype and etype:       self._wf_element(c,node,x,y,w,h)
        else:                           self._wf_label(c,node,x,y,w,h)

    def _wf_label(self, c, node, x, y, w, h):
        ctype = node.get("Container", node.get("Element", "?"))
        cfg   = node.get("Config") or {}
        title = cfg.get("title") or cfg.get("LabelKey") or ""
        label = ctype + (f' "{title}"' if title else "")
        css   = (node.get("Style") or {}).get("css") or {}
        style = node.get("Style") or {}

        def _g(prop): return css.get(prop) or style.get(prop) or ""

        fd  = _g("flexDirection") or "column"
        ai  = _g("alignItems")
        jc  = _g("justifyContent")
        flx = _g("flex")
        gap_v = _g("gap")
        ov  = _g("overflow") or _g("overflowY")
        mh  = _g("minHeight")
        mw  = _g("minWidth")
        wd  = _g("width")
        ht  = _g("height")
        br  = _g("borderRadius")
        bsh = _g("boxShadow")
        bg  = _g("background") or _g("backgroundColor")
        pad = _g("padding")
        bdr = _g("border")

        is_row = fd in ("row", "row-reverse")
        fs_m = max(int(min(w / 10, h / 2, 9)), 6)
        fs_s = max(int(min(w / 14, 7)), 5)
        fs_xs = max(fs_s - 1, 5)

        # ── overflow:hidden clip marks ─────────────────────────────────────────────
        if ov == "hidden" and w > 10 and h > 10:
            cl = 6
            for cx2, cy2, dx, dy in [(x, y, cl, 0), (x, y, 0, cl),
                                      (x+w, y, -cl, 0), (x+w, y, 0, cl),
                                      (x, y+h, cl, 0), (x, y+h, 0, -cl),
                                      (x+w, y+h, -cl, 0), (x+w, y+h, 0, -cl)]:
                c.create_line(cx2, cy2, cx2+dx, cy2+dy, fill="#ef4444", width=2)

        # ── padding inset indicator ────────────────────────────────────────────────
        if pad and pad not in ("0", "0px", ""):
            pad_px = (_af_px_val(str(pad).split()[0]) or 0) * min(getattr(self,"_sx",1), getattr(self,"_sy",1))
            pad_px = max(2.0, min(pad_px, min(w, h) / 4))
            c.create_rectangle(x+pad_px, y+pad_px, x+w-pad_px, y+h-pad_px,
                                fill="", outline="#94a3b8", width=1, dash=(3, 3))

        # ── flex direction arrows ──────────────────────────────────────────────────
        if ctype in ("flex", "grid", "sidebar", "card") and w > 20 and h > 14:
            arrow_clr = "#3b82f6"
            if is_row:
                # Horizontal arrows across the top
                ax, ay = x + 4, y + 6
                for i in range(min(3, int(w / 14))):
                    ox = ax + i * 10
                    if ox + 8 < x + w - 4:
                        c.create_line(ox, ay, ox+6, ay, fill=arrow_clr, width=1, arrow=tk.LAST, arrowshape=(4,5,2))
            else:
                # Vertical arrows down the left side
                ax, ay = x + 6, y + 4
                for i in range(min(3, int(h / 14))):
                    oy = ay + i * 10
                    if oy + 8 < y + h - 4:
                        c.create_line(ax, oy, ax, oy+6, fill=arrow_clr, width=1, arrow=tk.LAST, arrowshape=(4,5,2))

        # ── alignItems cross-axis guide lines ──────────────────────────────────────
        if ai and w > 30 and h > 20:
            gi_clr = "#6d28d9"
            dash_p = (2, 3)
            if is_row:
                # cross axis is vertical — draw guide lines at the top and bottom
                if ai == "stretch":
                    c.create_line(x+w-8, y+3, x+w-8, y+h-3, fill=gi_clr, width=1, dash=dash_p)
                    c.create_line(x+w-5, y+3, x+w-5, y+h-3, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "flex-start":
                    c.create_line(x+w-7, y+3, x+w-7, y+h//3, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "center":
                    mid = y + h//2
                    c.create_line(x+w-7, mid-h//6, x+w-7, mid+h//6, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "flex-end":
                    c.create_line(x+w-7, y+2*h//3, x+w-7, y+h-3, fill=gi_clr, width=1, dash=dash_p)
            else:
                # cross axis is horizontal — guide at right
                if ai == "stretch":
                    c.create_line(x+3, y+h-7, x+w-3, y+h-7, fill=gi_clr, width=1, dash=dash_p)
                    c.create_line(x+3, y+h-4, x+w-3, y+h-4, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "flex-start":
                    c.create_line(x+3, y+h-6, x+w//3, y+h-6, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "center":
                    mid = x + w//2
                    c.create_line(mid-w//6, y+h-6, mid+w//6, y+h-6, fill=gi_clr, width=1, dash=dash_p)
                elif ai == "flex-end":
                    c.create_line(x+2*w//3, y+h-6, x+w-3, y+h-6, fill=gi_clr, width=1, dash=dash_p)

        # ── minHeight dimension line ───────────────────────────────────────────────
        if mh and mh not in ("0", "0px", "auto", "") and h > 20:
            mh_px = (_af_px_val(str(mh)) or 0) * getattr(self, "_sy", 1)
            mh_px = min(mh_px, h - 4)
            if mh_px > 4:
                my = y + mh_px
                c.create_line(x+2, my, x+w-2, my, fill="#f59e0b", width=1, dash=(4, 2))
                if w > 30:
                    c.create_text(x+w-2, my-2, text=f"min:{mh}", fill="#f59e0b",
                                  font=("Courier", fs_xs), anchor="se")

        # ── minWidth dimension line ────────────────────────────────────────────────
        if mw and mw not in ("0", "0px", "auto", "") and w > 20:
            mw_px = (_af_px_val(str(mw)) or 0) * getattr(self, "_sx", 1)
            mw_px = min(mw_px, w - 4)
            if mw_px > 4:
                mx = x + mw_px
                c.create_line(mx, y+2, mx, y+h-2, fill="#f59e0b", width=1, dash=(4, 2))

        # ── gap indicator ─────────────────────────────────────────────────────────
        # (shown as a small coloured annotation near the arrows)
        if gap_v and gap_v not in ("0", "0px", "") and w > 40 and h > 16:
            gap_y = y + 3 if is_row else y + h - 12
            gap_x = x + w - 4
            c.create_text(gap_x, gap_y, text=f"gap:{gap_v}", fill="#10b981",
                          font=("Courier", fs_xs), anchor="ne")

        # ── label + dims ─────────────────────────────────────────────────────────
        if h >= 14:
            c.create_text(x + w/2, y + min(10, h/2), text=label[:36], fill="#111827",
                          font=("TkDefaultFont", fs_m, "bold"),
                          width=max(w - 4, 4), anchor="n")

        # Build compact multi-line CSS summary (all non-empty props)
        summary_parts = []
        for prop, val in [("flex", flx), ("w", wd), ("h", ht),
                          ("minH", mh), ("minW", mw), ("fd", fd if fd != "column" else ""),
                          ("ai", ai), ("jc", jc), ("ov", ov)]:
            if val and val not in ("", "column"):
                summary_parts.append(f"{prop}:{val}")

        if summary_parts and h >= 26:
            line1 = "  ".join(summary_parts[:4])
            c.create_text(x + w/2, y + min(22, h/2 + 10), text=line1[:48],
                          fill="#1d4ed8", font=("Courier", fs_s),
                          width=max(w - 4, 4), anchor="n")
        if len(summary_parts) > 4 and h >= 38:
            line2 = "  ".join(summary_parts[4:8])
            c.create_text(x + w/2, y + min(34, h/2 + 22), text=line2[:48],
                          fill="#1d4ed8", font=("Courier", fs_xs),
                          width=max(w - 4, 4), anchor="n")

        # Visual CSS badges (decorative)
        badges = []
        if bsh and bsh not in ("none", ""):    badges.append("shadow")
        if br and br not in ("0", "0px", ""):  badges.append(f"r:{br}")
        if bg and bg not in ("", "transparent", "none"):
            badges.append("bg:var" if "var(" in str(bg) else "bg")
        if bdr:                                badges.append("bdr")
        if badges and h >= 50:
            c.create_text(x + w/2, y + min(46, h/2 + 34), text=" · ".join(badges),
                          fill="#6d28d9", font=("Courier", fs_xs),
                          width=max(w - 4, 4), anchor="n")

    def _wf_header_action(self, c, node, x, y, w, h):
        so  = node.get("Style") or {}
        css = so.get("css") or {}
        bg  = _af_resolve_var(css.get("background","#e8ecf0"))
        c.create_rectangle(x,y,x+w,y+h,fill=bg,outline="")
        ph = max(h*0.55,4); pw = min(w*0.3,180)
        px0=x+8; py0=y+(h-ph)/2; r=ph/2
        c.create_oval(px0,py0,px0+ph,py0+ph,fill="white",outline="#ccc")
        c.create_oval(px0+pw-ph,py0,px0+pw,py0+ph,fill="white",outline="#ccc")
        c.create_rectangle(px0+r,py0,px0+pw-r,py0+ph,fill="white",outline="")
        c.create_line(px0+r,py0,px0+pw-r,py0,fill="#ccc")
        c.create_line(px0+r,py0+ph,px0+pw-r,py0+ph,fill="#ccc")
        if ph>8: c.create_text(px0+14,py0+ph/2,text="Search…",fill="#bbb",
                                anchor="w",font=("TkDefaultFont",max(int(ph*0.6),6)))
        dw=min(w*0.2,120); dh=min(h*0.7,26)
        dx=x+w-dw-8; dy=y+(h-dh)/2
        c.create_rectangle(dx,dy,dx+dw,dy+dh,fill="white",outline="#ccc")
        if dh>8: c.create_text(dx+5,dy+dh/2,text="Filter ▾",fill="#666",
                                anchor="w",font=("TkDefaultFont",max(int(dh*0.5),6)))

    def _wf_header(self, c, node, x, y, w, h):
        css = (node.get("Style") or {}).get("css") or {}
        bg  = _af_resolve_var(css.get("background","#E8E8ED"))
        c.create_rectangle(x,y,x+w,y+h,fill=bg,outline="")
        for sv in (node.get("Slots") or {}).values():
            for child in (sv or []):
                if isinstance(child,dict) and child.get("Element")=="key-value":
                    lk = (child.get("Config") or {}).get("LabelKey","")
                    fw = "bold" if (child.get("Style") or {}).get("fontWeight")=="bold" else "normal"
                    fs = max(int(min(h*0.55,10)),7)
                    if h>=10 and lk:
                        c.create_text(x+10,y+h/2,text=lk[:40],fill="#4a4a4a",
                                      anchor="w",font=("TkDefaultFont",fs,fw))
                    return

    def _wf_table(self, c, node, x, y, w, h):
        cfg  = node.get("Config") or {}
        so   = node.get("Style") or {}
        title = cfg.get("title","Table"); cols = cfg.get("Columns") or []
        hbg  = _af_resolve_var(so.get("headerBackgroundColor","#f0f2f5"))
        even = _af_resolve_var(so.get("rowEvenBackgroundColor","#fff"))
        odd  = _af_resolve_var(so.get("rowOddBackgroundColor","#fafafa"))
        bdr  = _af_resolve_var(so.get("tableBorderColor","#e0e0e0"))
        TH=max(h*0.10,4); CH=max(h*0.09,4); RH=max(h*0.07,3); FTH=max(h*0.07,3)
        has_ftr = any(isinstance(s,dict) and s.get("Container")=="footer-container"
                      for s in (node.get("Slots") or {}).get("Default") or [])
        has_ag  = bool((node.get("Slots") or {}).get("AgenticActions"))
        c.create_rectangle(x,y,x+w,y+TH,fill=hbg,outline="")
        if TH>7:
            c.create_text(x+6,y+TH/2,text=title[:28],fill="#333",
                          anchor="w",font=("TkDefaultFont",max(int(TH*0.6),6),"bold"))
        if has_ag and TH>7:
            c.create_text(x+w-8,y+TH/2,text="⋮",fill="#888",
                          anchor="e",font=("TkDefaultFont",max(int(TH*0.7),6)))
        y1=y+TH
        c.create_rectangle(x,y1,x+w,y1+CH,fill=hbg,outline=bdr)
        if cols and w>20:
            cw2=w/len(cols)
            for j,col in enumerate(cols):
                lk=(col.get("Config") or {}).get("LabelKey","")
                cx2=x+j*cw2
                if j>0: c.create_line(cx2,y1,cx2,y1+CH,fill=bdr)
                if CH>6 and cw2>8:
                    c.create_text(cx2+4,y1+CH/2,text=lk[:10],fill="#555",
                                  anchor="w",font=("Courier",max(int(CH*0.55),5)))
        y2=y1+CH; ftr_y=(y+h-FTH) if has_ftr else (y+h)
        n_rows=max(int((ftr_y-y2)/max(RH,1)),0)
        for i in range(min(n_rows,6)):
            bg2=even if i%2==0 else odd
            c.create_rectangle(x,y2+i*RH,x+w,y2+(i+1)*RH,fill=bg2,outline=bdr)
        if has_ftr:
            c.create_rectangle(x,ftr_y,x+w,y+h,fill=hbg,outline=bdr)
            if FTH>7:
                c.create_text(x+w/2,ftr_y+FTH/2,text="1–25 of 243  ‹ 1 2 3 ›",
                              fill="#666",font=("Courier",max(int(FTH*0.55),5)))

    def _wf_chart(self, c, node, x, y, w, h):
        import math as _m
        cfg=node.get("Config") or {}; dm=cfg.get("dataMapping") or {}
        series=dm.get("seriesMappings") or []
        colors=[sm.get("staticOptions",{}).get("color","#888") for sm in series] or ["#90CAF9"]
        n_ser=len(colors); chart_h=h*0.85
        n_bars=max(min(int(w/14),14),4); bw=w/n_bars*0.55; bg_gap=w/n_bars*0.45
        for pct in (0.25,0.5,0.75):
            gy=y+chart_h*(1-pct)
            c.create_line(x,gy,x+w,gy,fill="#ddd",width=1,dash=(2,4))
        for i in range(n_bars):
            bx=x+bg_gap/2+i*(bw+bg_gap)
            tot=max(0.12,min(0.88,0.4+0.28*_m.sin(i*0.85+0.6)+0.15*_m.sin(i*0.3)))
            bar_tot=chart_h*tot; hs=[]; rem=float(bar_tot)
            for j in range(n_ser):
                hj=rem if j==n_ser-1 else max(2,bar_tot*(0.28/n_ser)+3*_m.sin(i*0.5+j))
                hj=min(hj,rem-(n_ser-j-1)*2); hs.append(hj); rem-=hj
            y_off=0.0
            for j in range(n_ser-1,-1,-1):
                by2=y+chart_h-y_off-hs[j]
                c.create_rectangle(bx,by2,bx+bw,by2+hs[j],fill=colors[j],outline="")
                y_off+=hs[j]
        legend_y=y+chart_h+(h-chart_h)*0.15; lx=x+4
        for sm,color in zip(series,colors):
            nm=sm.get("staticOptions",{}).get("name","")
            if lx+30>x+w: break
            bs=max(h*0.04,4)
            c.create_rectangle(lx,legend_y,lx+bs,legend_y+bs,fill=color,outline="")
            if bs>4:
                c.create_text(lx+bs+3,legend_y+bs/2,text=nm[:8],fill="#374151",
                              anchor="w",font=("Courier",max(int(bs*0.8),5)))
            lx+=len(nm[:8])*4.5+bs+8

    def _wf_search(self, c, node, x, y, w, h):
        cfg=node.get("Config") or {}
        ph=(((cfg.get("Filter") or {}).get("Placeholder") or {}).get("LabelKey") or
            (cfg.get("SearchProperty") or {}).get("placeholder","Search…"))
        r=min(h/2,w/2,14)
        c.create_oval(x,y,x+h,y+h,fill="white",outline="#ccc")
        c.create_oval(x+w-h,y,x+w,y+h,fill="white",outline="#ccc")
        c.create_rectangle(x+r,y,x+w-r,y+h,fill="white",outline="")
        c.create_line(x+r,y,x+w-r,y,fill="#ccc")
        c.create_line(x+r,y+h,x+w-r,y+h,fill="#ccc")
        if h>8: c.create_text(x+16,y+h/2,text=ph[:22],fill="#888",
                               anchor="w",font=("TkDefaultFont",max(int(h*0.5),6)))

    def _wf_segment(self, c, node, x, y, w, h):
        cfg  = node.get("Config") or {}
        lbl  = ((cfg.get("Filter") or {}).get("Placeholder") or {}).get("LabelKey","Select…")
        c.create_rectangle(x,y,x+w,y+h,fill="white",outline="#ccc")
        if h>7: c.create_text(x+6,y+h/2,text=f"{lbl} ▾",fill="#4a4a4a",
                               anchor="w",font=("TkDefaultFont",max(int(h*0.55),6)))

    def _wf_footer(self, c, node, x, y, w, h):
        c.create_rectangle(x,y,x+w,y+h,fill="#f9f9f9",outline="#e0e0e0")
        if h>7: c.create_text(x+w/2,y+h/2,text="1–25 of 243  ‹ 1 2 3 ›",
                               fill="#777",font=("Courier",min(max(int(h*0.55),5),7)))

    def _wf_element(self, c, node, x, y, w, h):
        etype=node.get("Element",""); cfg=node.get("Config") or {}
        inp=str(node.get("Input","") or "")
        label=cfg.get("LabelKey") or inp or etype
        fw="bold" if (node.get("Style") or {}).get("fontWeight")=="bold" else "normal"
        fs=max(int(min(h*0.6,w/max(len(label),1)*1.2,9)),6)
        c.create_text(x+4,y+max(h/2,5),text=label[:30],fill="#111827",
                      anchor="w",font=("TkDefaultFont",fs,fw))

    # ═══════ canvas interaction ═══════════════════════════════════════════════

    def _on_canvas_press(self, event):
        R=9   # wider hit zone for handles
        sel=self._selected_preview_node
        if sel:
            box=next((z for z in self._click_zones if z[4] is sel),None)
            if box:
                x1,y1,x2,y2=box[:4]
                near_r = abs(event.x-x2)<=R
                near_b = abs(event.y-y2)<=R
                in_x   = x1<=event.x<=x2+R
                in_y   = y1<=event.y<=y2+R
                if near_r and near_b:   # corner — resize both
                    self._resize_state={"node":sel,"box":box[:4],"dir":"both",
                                        "start_x":event.x,"start_y":event.y}; return
                if near_b and in_x:     # bottom edge — resize height
                    self._resize_state={"node":sel,"box":box[:4],"dir":"v","start":event.y}; return
                if near_r and in_y:     # right edge — resize width
                    self._resize_state={"node":sel,"box":box[:4],"dir":"h","start":event.x}; return
        self._resize_state=None
        for x1,y1,x2,y2,node,path in reversed(self._click_zones):
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                self._selected_preview_node=node
                for tid,ref in self.tree_id_map.items():
                    if ref.node is node:
                        self.tree.see(tid); self.tree.selection_set(tid); return
                break

    def _on_canvas_hover(self, event):
        R=9
        sel=self._selected_preview_node
        if sel:
            box=next((z for z in self._click_zones if z[4] is sel),None)
            if box:
                x1,y1,x2,y2=box[:4]
                near_r = abs(event.x-x2)<=R
                near_b = abs(event.y-y2)<=R
                in_x   = x1<=event.x<=x2+R
                in_y   = y1<=event.y<=y2+R
                if near_r and near_b:
                    self._layout_canvas.config(cursor="sizing")
                    self._hide_canvas_tooltip(); return
                if near_b and in_x:
                    self._layout_canvas.config(cursor="sb_v_double_arrow")
                    self._hide_canvas_tooltip(); return
                if near_r and in_y:
                    self._layout_canvas.config(cursor="sb_h_double_arrow")
                    self._hide_canvas_tooltip(); return
        for x1,y1,x2,y2,node,path in reversed(self._click_zones):
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                self._layout_canvas.config(cursor="hand2")
                self._show_canvas_tooltip(event,node,path); return
        self._layout_canvas.config(cursor="")
        self._hide_canvas_tooltip()

    def _show_canvas_tooltip(self, event, node, path):
        if self._canvas_tooltip_path==path:
            if self._canvas_tooltip:
                try: self._canvas_tooltip.wm_geometry(f"+{event.x_root+14}+{event.y_root+10}")
                except tk.TclError: pass
            return
        self._hide_canvas_tooltip()
        self._canvas_tooltip_path=path
        ctype=node.get("Container") or node.get("Element","?")
        cfg=node.get("Config") or {}; css=(node.get("Style") or {}).get("css") or {}
        title=cfg.get("title") or cfg.get("LabelKey") or cfg.get("Name") or ""
        dims="  ".join(f"{k}:{css[k]}" for k in ("flex","width","height") if css.get(k))
        lines=[f"▸ {ctype}"+(f'  "{title}"' if title else "")]
        if dims: lines.append(dims)
        init=node.get("Init")
        if isinstance(init,dict) and init.get("DataSourcePath"):
            lines.append(f"data: {init['DataSourcePath']}")
        lines.append(f"path: …{path[-45:]}" if len(path)>48 else f"path: {path}")
        tip=tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{event.x_root+14}+{event.y_root+10}")
        tip.attributes("-topmost",True)
        outer=tk.Frame(tip,bg="#1E293B",highlightbackground="#475569",highlightthickness=1)
        outer.pack()
        tk.Label(outer,text="\n".join(lines),bg="#1E293B",fg="#F1F5F9",
                 font=("Helvetica",9),justify="left",padx=10,pady=6).pack()
        self._canvas_tooltip=tip

    def _hide_canvas_tooltip(self):
        self._canvas_tooltip_path=None
        if self._canvas_tooltip:
            try: self._canvas_tooltip.destroy()
            except tk.TclError: pass
            self._canvas_tooltip=None

    # ── resize helpers ────────────────────────────────────────────────────────

    def _parent_canvas_box(self, node):
        """Return (x1,y1,x2,y2) of the smallest enclosing zone that is not node."""
        box = next((z for z in self._click_zones if z[4] is node), None)
        if not box: return None
        bx1,by1,bx2,by2 = box[:4]
        best = None
        for zx1,zy1,zx2,zy2,zn,_ in self._click_zones:
            if zn is node: continue
            if zx1<=bx1 and zy1<=by1 and zx2>=bx2 and zy2>=by2:
                area = (zx2-zx1)*(zy2-zy1)
                if best is None or area < best[0]:
                    best = (area, zx1, zy1, zx2, zy2)
        return (best[1], best[2], best[3], best[4]) if best else None

    def _apply_smart_resize(self, node, new_canvas_w, new_canvas_h, direction):
        """Compute and write smart CSS values from a drag resize."""
        css   = _af_get_css(node)
        style = node.get("Style") or {}

        virt_w = round(new_canvas_w / self._sx)
        virt_h = round(new_canvas_h / self._sy)
        parent = self._parent_canvas_box(node)

        if direction in ("h", "both"):
            if parent:
                parent_virt_w = round((parent[2]-parent[0]) / self._sx)
                ratio = virt_w / max(parent_virt_w, 1)
                if ratio >= 0.88:
                    # Almost full width → let it grow
                    css["flex"] = "1 1 auto"
                    css.pop("width", None)
                    style.pop("width", None)
                elif ratio >= 0.45:
                    # Mid range → grow+shrink with explicit basis
                    css["flex"] = f"1 1 {virt_w}px"
                    css["width"] = f"{virt_w}px"
                    style.pop("width", None)
                else:
                    # Small fixed sidebar / panel
                    css["flex"] = f"0 0 {virt_w}px"
                    css["width"] = f"{virt_w}px"
                    style.pop("width", None)
            else:
                css["width"] = f"{virt_w}px"
                css["flex"]  = f"0 0 {virt_w}px"

        if direction in ("v", "both"):
            if parent:
                parent_virt_h = round((parent[3]-parent[1]) / self._sy)
                ratio = virt_h / max(parent_virt_h, 1)
                if ratio >= 0.88:
                    css["height"] = "100%"
                    css.pop("minHeight", None)
                elif ratio <= 0.05:
                    css["height"] = "auto"
                else:
                    css["height"] = f"{virt_h}px"
                style.pop("height", None)
            else:
                css["height"] = f"{virt_h}px"

    def _on_canvas_drag(self, event):
        rs = self._resize_state
        if not rs: return
        c = self._layout_canvas
        node = rs["node"]
        x1, y1, x2, y2 = rs["box"]
        direction = rs["dir"]

        # Compute new canvas dimensions
        if direction == "h":
            new_cw = max(event.x - x1, 20); new_ch = y2 - y1
        elif direction == "v":
            new_cw = x2 - x1; new_ch = max(event.y - y1, 20)
        else:   # both
            new_cw = max(event.x - x1, 20); new_ch = max(event.y - y1, 20)

        # Store current drag dimensions for release
        rs["new_cw"] = new_cw
        rs["new_ch"] = new_ch

        # Draw live resize overlay (no full redraw — smooth drag)
        c.delete("_resize_overlay")
        nx2 = x1 + new_cw
        ny2 = y1 + new_ch
        c.create_rectangle(x1, y1, nx2, ny2,
                            outline="#3b82f6", width=2, dash=(6,3),
                            tags="_resize_overlay")
        # Show virtual pixel dimensions in overlay
        vw = round(new_cw / self._sx)
        vh = round(new_ch / self._sy)
        if direction == "h":
            label = f"width: {vw}px"
        elif direction == "v":
            label = f"height: {vh}px"
        else:
            label = f"{vw}px × {vh}px"
        c.create_rectangle(nx2-len(label)*5-6, ny2-16, nx2-2, ny2-2,
                            fill="#1d4ed8", outline="", tags="_resize_overlay")
        c.create_text(nx2-4, ny2-9, text=label,
                      fill="white", font=("Courier",8), anchor="e",
                      tags="_resize_overlay")
        # Dimension lines
        if direction in ("h","both"):
            c.create_line(x1, ny2+6, nx2, ny2+6, fill="#3b82f6", width=1,
                          arrow=tk.BOTH, tags="_resize_overlay")
        if direction in ("v","both"):
            c.create_line(nx2+6, y1, nx2+6, ny2, fill="#3b82f6", width=1,
                          arrow=tk.BOTH, tags="_resize_overlay")

    def _on_canvas_release(self, event):
        rs = self._resize_state
        self._resize_state = None
        self._layout_canvas.delete("_resize_overlay")
        if not rs: return
        new_cw = rs.get("new_cw")
        new_ch = rs.get("new_ch")
        if new_cw is None and new_ch is None:
            return   # no drag happened, was just a click
        node = rs["node"]
        direction = rs["dir"]
        x1, y1, x2, y2 = rs["box"]
        if new_cw is None: new_cw = x2 - x1
        if new_ch is None: new_ch = y2 - y1
        # Apply smart CSS
        self._apply_smart_resize(node, new_cw, new_ch, direction)
        # Full redraw with new CSS
        self._reload_preview()
        # Sync CSS panel
        if self._selected_slot_ref:
            self._refresh_css_panel(self._selected_slot_ref)
        # Status
        css = (node.get("Style") or {}).get("css") or {}
        applied = "  ".join(f"{k}:{css[k]}" for k in ("flex","width","height") if css.get(k))
        self.status_var.set(f"Resized → {applied}")

    def _on_canvas_double(self, event):
        for x1,y1,x2,y2,node,path in reversed(self._click_zones):
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                if _af_is_locked(node):
                    ctype = node.get("Container", node.get("Element","node"))
                    if messagebox.askyesno(
                            "Locked Node",
                            f"'{ctype}' is locked (leaf component).\n\n"
                            "Locked nodes can't have children added to them.\n"
                            "Unlock to edit its layout slots freely.\n\n"
                            "Unlock this node?", parent=self):
                        self._toggle_node_lock(node)
                else:
                    self._open_edit_dialog(node)
                return

    def _on_tree_click_lock(self, event):
        """Click the 🔒 column in the tree to toggle lock instantly."""
        region = self.tree.identify_region(event.x, event.y)
        col    = self.tree.identify_column(event.x)
        if region == "cell" and col == "#3":   # "lk" column
            iid = self.tree.identify_row(event.y)
            if iid and iid in self.tree_id_map:
                self._toggle_node_lock(self.tree_id_map[iid].node)

    def _unlock_all(self):
        """Unlock every natively-locked node in the fragment."""
        if not self.fragment_root: return
        count = [0]
        def _walk(node):
            if not isinstance(node, dict): return
            if (node.get("Container") in _AF_LOCKED_CONTAINERS
                    or bool(node.get("Element"))) and not node.get("_unlocked"):
                node["_unlocked"] = True; count[0] += 1
            for v in node.values():
                if isinstance(v, dict):  _walk(v)
                elif isinstance(v, list):
                    for i in v: _walk(i)
        _walk(self.fragment_root)
        self._rebuild_tree(); self._reload_preview()
        self.status_var.set(f"Unlocked {count[0]} node(s)  —  🔒 Re-lock All to restore")

    def _relock_all(self):
        """Restore default locks on all natively-locked containers."""
        if not self.fragment_root: return
        count = [0]
        def _walk(node):
            if not isinstance(node, dict): return
            if node.pop("_unlocked", None): count[0] += 1
            for v in node.values():
                if isinstance(v, dict):  _walk(v)
                elif isinstance(v, list):
                    for i in v: _walk(i)
        _walk(self.fragment_root)
        self._rebuild_tree(); self._reload_preview()
        self.status_var.set(f"Re-locked {count[0]} node(s)")

    def _toggle_lock_selected(self):
        ref = self._selected_slot_ref
        if not ref: return
        self._toggle_node_lock(ref.node)

    def _toggle_node_lock(self, node):
        if node.get("_unlocked"):
            node.pop("_unlocked", None)
        else:
            node["_unlocked"] = True
        self._rebuild_tree()
        self._reload_preview()
        if self._selected_slot_ref:
            self._refresh_css_panel(self._selected_slot_ref)
        state = "unlocked" if node.get("_unlocked") else "locked"
        ctype = node.get("Container", node.get("Element", "node"))
        self.status_var.set(f"{ctype} is now {state}")

    def _on_canvas_right(self, event):
        for x1,y1,x2,y2,node,path in reversed(self._click_zones):
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                m=tk.Menu(self,tearoff=0,bg="#313244",fg=_AF_C_FG,
                          activebackground="#45475a",activeforeground=_AF_C_FG,
                          font=("TkDefaultFont",9))
                m.add_command(label="✏️  Edit",
                              command=lambda n=node: self._open_edit_dialog(n))
                m.add_separator()
                m.add_command(label="➕  Add Child",
                              command=lambda n=node,p=path: self._add_child_dialog(n,p))
                m.add_separator()
                if _af_is_locked(node):
                    m.add_command(label="🔓  Unlock this node",
                                  command=lambda n=node: self._toggle_node_lock(n))
                elif (node.get("Container") in _AF_LOCKED_CONTAINERS
                      or node.get("Element")):
                    m.add_command(label="🔒  Re-lock this node",
                                  command=lambda n=node: self._toggle_node_lock(n))
                m.add_separator()
                m.add_command(label="🗑  Delete",
                              command=lambda n=node,p=path: self._delete_node(n,p))
                try: m.tk_popup(event.x_root,event.y_root)
                finally: m.grab_release()
                return

    # ═══════ tree management ════════════════════════════════════════════════

    def _rebuild_tree(self, reselect_path=None):
        self.tree.delete(*self.tree.get_children())
        self.tree_id_map.clear()
        if not self.fragment_root: return
        frag=self.fragment_root.get("Fragment",self.fragment_root)
        self._add_tree_node("",frag,None,None,None,"Fragment",0)
        for tid in list(self.tree_id_map)[:14]:
            try: self.tree.item(tid,open=True)
            except tk.TclError: pass
        if reselect_path:
            for tid,ref in self.tree_id_map.items():
                if ref.path==reselect_path:
                    self.tree.see(tid); self.tree.selection_set(tid); break

    def _add_tree_node(self, ptid, node, pnode, pslot, idx, path, depth):
        if not isinstance(node,dict): return
        if "Container" not in node and "Element" not in node: return
        locked=_af_is_locked(node); is_el=bool(node.get("Element"))
        tag="element" if is_el else ("locked" if locked else "layout")
        tid=self.tree.insert(ptid,tk.END,
            text=f"  {_af_node_label(node)}",
            values=(node.get("Container") or node.get("Element","?"), pslot or "","🔒" if locked else ""),
            open=(depth<2),tags=(tag,))
        self.tree_id_map[tid]=_AFNodeRef(node=node,parent=pnode,parent_slot=pslot,
                                         index=idx,path=path,depth=depth,locked=locked)
        for sn,items in (node.get("Slots") or {}).items():
            if isinstance(items,list):
                for i,child in enumerate(items):
                    if isinstance(child,dict):
                        self._add_tree_node(tid,child,node,sn,i,f"{path}.{sn}[{i}]",depth+1)

    def _on_tree_select(self, event=None):
        sel=self.tree.selection()
        if not sel: return
        ref=self.tree_id_map.get(sel[0])
        if not ref: return
        self._selected_slot_ref=ref
        self._selected_preview_node=ref.node
        self.breadcrumb_var.set(ref.path)
        self._refresh_slot_panel(ref)
        self._refresh_css_panel(ref)
        self._refresh_info(ref)
        self._reload_preview()

    def _refresh_info(self, ref: _AFNodeRef):
        node=ref.node
        lines=[f"Path: {ref.path}",
               f"Type: {node.get('Container') or node.get('Element','?')}",
               f"Locked: {'YES' if ref.locked else 'no'}"]
        if node.get("UID"): lines.append(f"UID: {node['UID']}")
        css=(node.get("Style") or {}).get("css") or {}
        lines.append("css: "+(", ".join(css.keys()) if css else "(none)"))
        for sn,sv in (node.get("Slots") or {}).items():
            lines.append(f"Slots.{sn}: {len(sv) if isinstance(sv,list) else '?'}")
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0",tk.END)
        self.info_text.insert("1.0","\n".join(lines))
        self.info_text.config(state=tk.DISABLED)

    def _refresh_slot_panel(self, ref: _AFNodeRef):
        node=ref.node
        names=[k for k,v in (node.get("Slots") or {}).items() if isinstance(v,list)]
        self.slot_choice["values"]=names
        if names:
            pick="Default" if "Default" in names else names[0]
            self.slot_choice.set(pick)
            self._populate_slot_list(node,pick)
            self.slot_path_var.set(f"Slots.{pick}")
        else:
            self.slot_choice.set(""); self.slot_list.delete(0,tk.END)
            self.slot_path_var.set("no slots")

    def _on_slot_choice(self, event=None):
        if not self._selected_slot_ref: return
        slot=self.slot_choice.get()
        self._populate_slot_list(self._selected_slot_ref.node,slot)
        self.slot_path_var.set(f"Slots.{slot}")

    def _populate_slot_list(self, node, slot_name):
        self.slot_list.delete(0,tk.END)
        for i,child in enumerate((node.get("Slots") or {}).get(slot_name) or []):
            if isinstance(child,dict):
                icon="🔒" if _af_is_locked(child) else "↕ "
                css=(child.get("Style") or {}).get("css") or {}
                dim=css.get("flex") or css.get("height") or css.get("width") or ""
                suffix=f"  [{dim}]" if dim else ""
                self.slot_list.insert(tk.END,f"  {i}  {icon}  {_af_node_label(child)}{suffix}")

    def _on_slot_select(self, event=None):
        sel=self.slot_list.curselection()
        if not sel or not self._selected_slot_ref: return
        idx=sel[0]; node=self._selected_slot_ref.node; slot=self.slot_choice.get()
        items=(node.get("Slots") or {}).get(slot) or []
        if 0<=idx<len(items):
            child=items[idx]
            if isinstance(child,dict):
                for tid,ref in self.tree_id_map.items():
                    if ref.node is child:
                        self.tree.see(tid); self.tree.selection_set(tid); return

    def _on_slot_double(self, event=None): self._on_slot_select()
    def _move_up(self):   self._move_in_slot(-1)
    def _move_down(self): self._move_in_slot(1)

    def _move_in_slot(self, delta):
        if not self._selected_slot_ref: return
        node=self._selected_slot_ref.node; slot=self.slot_choice.get()
        sel=self.slot_list.curselection()
        if not sel: return
        idx,new_idx=sel[0],sel[0]+delta
        if _af_move_child(node,slot,idx,new_idx):
            cur=self._selected_slot_ref.path
            self._rebuild_tree(reselect_path=cur)
            self._populate_slot_list(node,slot)
            self.slot_list.selection_set(new_idx); self.slot_list.see(new_idx)
            self._reload_preview()

    # ═══════ CSS panel ═══════════════════════════════════════════════════════

    def _refresh_css_panel(self, ref: _AFNodeRef):
        style = ref.node.get("Style") or {}
        css   = style.get("css") or {}
        for prop, var in self.css_vars.items():
            val = css.get(prop, "")
            # Fall back to top-level Style key (e.g. Style.flex, Style.padding)
            if not val and prop in _AF_STYLE_TOP_KEYS:
                val = str(style.get(prop, ""))
            var.set(str(val))
        is_locked = _af_is_locked(ref.node)
        self.lock_warn_var.set("⚠  Locked node" if is_locked else "")
        try:
            native_lock = (ref.node.get("Container") in _AF_LOCKED_CONTAINERS
                           or bool(ref.node.get("Element")))
            if is_locked:
                self._unlock_btn.config(text="🔓 Unlock", bg="#7c3aed")
                self._unlock_btn.pack(side=tk.LEFT, padx=(6,0))
            elif native_lock:
                self._unlock_btn.config(text="🔒 Re-lock", bg="#374151")
                self._unlock_btn.pack(side=tk.LEFT, padx=(6,0))
            else:
                self._unlock_btn.pack_forget()
        except Exception:
            pass

    def _apply_css_prop(self, prop, refresh=False):
        if not self._selected_slot_ref: return
        val   = self.css_vars[prop].get().strip()
        node  = self._selected_slot_ref.node
        css   = _af_get_css(node)
        style = node.get("Style") or {}
        if val:
            changed = css.get(prop) != val
            if not changed and prop in _AF_STYLE_TOP_KEYS and prop in style:
                changed = True  # top-level value still exists; need to normalise
            if changed:
                css[prop] = val
                # Remove duplicate top-level key so both sources don't conflict
                if prop in _AF_STYLE_TOP_KEYS:
                    style.pop(prop, None)
                self.status_var.set(f"Set {prop}={val!r}")
                if refresh: self._reload_preview()
        else:
            changed = False
            if prop in css:
                del css[prop]; changed = True
            if prop in _AF_STYLE_TOP_KEYS and prop in style:
                style.pop(prop); changed = True
            if changed:
                self.status_var.set(f"Cleared {prop}")
                if refresh: self._reload_preview()

    def _apply_all_css(self):
        if not self._selected_slot_ref: return
        node  = self._selected_slot_ref.node
        css   = _af_get_css(node)
        style = node.get("Style") or {}
        changed = []
        for prop, var in self.css_vars.items():
            val = var.get().strip()
            if val:
                if css.get(prop) != val or (prop in _AF_STYLE_TOP_KEYS and prop in style):
                    css[prop] = val
                    if prop in _AF_STYLE_TOP_KEYS:
                        style.pop(prop, None)
                    changed.append(prop)
            else:
                if prop in css:
                    del css[prop]; changed.append(f"-{prop}")
                if prop in _AF_STYLE_TOP_KEYS and prop in style:
                    style.pop(prop); changed.append(f"-top.{prop}")
        self._reload_preview()
        self.status_var.set(f"Applied {len(changed)} CSS changes" if changed else "No changes")

    def _reset_node_css(self):
        if not self._selected_slot_ref: return
        if not messagebox.askyesno("Confirm Reset","Clear all Style.css on this node?",parent=self): return
        style = self._selected_slot_ref.node.get("Style", {})
        style.pop("css", None)
        for k in list(_AF_STYLE_TOP_KEYS):
            style.pop(k, None)
        for var in self.css_vars.values(): var.set("")
        self._reload_preview(); self.status_var.set("Node CSS reset")

    def _clean_css(self):
        if not self.fragment_root: return
        def _cl(node):
            if isinstance(node,dict):
                if "Style" in node and isinstance(node["Style"],dict):
                    css=node["Style"].get("css")
                    if isinstance(css,dict):
                        node["Style"]["css"]={k:v for k,v in css.items() if v not in ("",None)}
                        if not node["Style"]["css"]: node["Style"].pop("css",None)
                    if not node["Style"]: node.pop("Style",None)
                for v in node.values(): _cl(v)
            elif isinstance(node,list):
                for i in node: _cl(i)
        _cl(self.fragment_root); self._reload_preview(); self.status_var.set("Empty CSS cleaned")

    def _open_glean_chat(self):
        if not _GLEAN_REQUESTS_OK:
            messagebox.showerror(
                "Glean AI",
                "Missing dependencies.\nRun: pip install requests browser-cookie3\nthen restart the app.",
                parent=self)
            return
        # Collect current validation issues so Glean sees them in context
        issues = []
        try:
            self._validate_node(
                self.fragment_root.get("Fragment", {}), "Fragment", None, issues)
        except Exception:
            pass
        def _after_apply():
            self._rebuild_tree()
            self.status_var.set("Glean AI suggestions applied ✓")
        # Parent + store on root Designer so the window outlives AlignFix close/reopen
        _root = self._v5 if self._v5 else self
        win = getattr(_root, "_glean_chat_win_af", None)
        if win and win.winfo_exists():
            win.fragment_root       = self.fragment_root
            win._validation_issues  = issues
            win.deiconify()
            win.lift()
            return
        dlg = GleanChatDialog(_root, self.fragment_root,
                              on_apply_cb=_after_apply, validation_issues=issues)
        _root._glean_chat_win_af = dlg

    # ═══════ auto-tune ════════════════════════════════════════════════════════

    def _auto_tune(self):
        if not self.fragment_root:
            messagebox.showinfo("No Data","Load a fragment first.",parent=self); return
        changed: list = []
        self._tune_node_af(self.fragment_root.get("Fragment",{}), "Fragment", changed)
        self._rebuild_tree(); self._reload_preview()
        if changed:
            self.status_var.set(f"Auto-tuned {len(changed)} node(s)")
            win=tk.Toplevel(self); win.title("Auto-tune Report")
            win.geometry("640x400"); win.configure(bg=_AF_C_BG)
            txt=scrolledtext.ScrolledText(win,bg="#313244",fg=_AF_C_FG,
                                           font=("Courier",9),relief=tk.FLAT,
                                           highlightthickness=0)
            txt.pack(fill=tk.BOTH,expand=True,padx=8,pady=8)
            txt.insert("1.0","\n".join(changed)); txt.config(state=tk.DISABLED)
        else:
            self.status_var.set("Auto-tune: layout already optimal")

    def _tune_node_af(self, node, path, changed):
        if not isinstance(node,dict): return
        ctype=node.get("Container",""); slots=node.get("Slots") or {}
        css=(node.get("Style") or {}).get("css") or {}
        if ctype=="flex":
            fd=css.get("flexDirection","column"); is_row=fd in ("row","row-reverse")
            children=slots.get("Default") or []
            for child in children:
                if not isinstance(child,dict): continue
                cc=(child.get("Style") or {}).get("css") or {}
                cs=child.get("Style") or {}; ct=child.get("Container","")
                ex=str(cc.get("flex") or cs.get("flex","")).strip()
                if is_row:
                    if not ex:
                        has_w=bool(cc.get("width") or cs.get("width") or ex.startswith("0 0"))
                        tgt="0 0 auto" if (ct in _AF_AUTO_H or has_w) else "1 1 0"
                        cc["flex"]=tgt; child.setdefault("Style",{})["css"]=cc
                        changed.append(f"SET flex:{tgt:<12}  at {path} → {_af_node_label(child)}")
                else:
                    tgt=("0 0 auto" if ct in _AF_AUTO_H or
                         bool(cc.get("height") or cs.get("height") or ex.startswith("0 0"))
                         else "1")
                    if ex!=tgt:
                        cc["flex"]=tgt; child.setdefault("Style",{})["css"]=cc
                        changed.append(f"SET flex:{tgt:<12}  at {path} → {_af_node_label(child)}")
        for sn,items in slots.items():
            if isinstance(items,list):
                for i,child in enumerate(items):
                    self._tune_node_af(child,f"{path}.{sn}[{i}]",changed)

    # ═══════ quick fix + validate ════════════════════════════════════════════

    def _apply_quick_fix(self, props: dict):
        """Write a preset dict of CSS props to the selected node and refresh."""
        if not self._selected_slot_ref:
            self.status_var.set("Select a node first"); return
        node  = self._selected_slot_ref.node
        css   = _af_get_css(node)
        style = node.get("Style") or {}
        for prop, val in props.items():
            css[prop] = val
            if prop in _AF_STYLE_TOP_KEYS:
                style.pop(prop, None)
        self._refresh_css_panel(self._selected_slot_ref)
        self._reload_preview()
        self.status_var.set(f"Applied preset: {', '.join(f'{k}:{v}' for k,v in props.items())}")

    def _jump_to_issue(self, node, prop):
        """Select node in tree + scroll CSS editor to the offending property."""
        # 1. Navigate tree
        for tid, ref in self.tree_id_map.items():
            if ref.node is node:
                self.tree.item(tid, open=True)
                self.tree.see(tid)
                self.tree.selection_set(tid)
                self._on_tree_select()
                break
        # 2. Scroll CSS canvas to the property row and flash it
        if prop and prop in _AF_LAYOUT_CSS_PROPS and hasattr(self, '_css_canvas'):
            idx   = _AF_LAYOUT_CSS_PROPS.index(prop)
            total = max(len(_AF_LAYOUT_CSS_PROPS) - 1, 1)
            self._css_canvas.yview_moveto(max(0.0, (idx - 2) / total))
        entry = (self.css_entries or {}).get(prop)
        if entry and entry.winfo_exists():
            orig = entry.cget("foreground") if True else "black"
            try:
                style_obj = ttk.Style()
                entry.config(foreground="#ef4444")
                self.after(900, lambda: entry.config(foreground="black") if entry.winfo_exists() else None)
            except Exception:
                pass

    def _run_validate(self):
        if not self.fragment_root:
            self._warn_var.set("Nothing loaded")
            self._warn_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            return
        issues = []   # each item: (node, path, prop, message)
        self._validate_node(self.fragment_root.get("Fragment", {}), "Fragment", None, issues)
        if not issues:
            self._warn_var.set("")
            self._warn_lbl.pack_forget()
            self.status_var.set("✓ Validate: no layout issues found")
            return

        # Show count in bar
        self._warn_var.set(f"⚠  {len(issues)} issue(s) — see report window")
        self._warn_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.status_var.set(f"Validate: {len(issues)} issue(s)")

        # Build clickable report window
        win = tk.Toplevel(self)
        win.title("Layout Validation — click an issue to navigate")
        win.geometry("860x480")
        win.configure(bg=_AF_C_BG)

        hdr = tk.Frame(win, bg="#1a1b2e", pady=4)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"  {len(issues)} issue(s) found — click any row to jump to the node and CSS field",
                 bg="#1a1b2e", fg="#fbbf24", font=("TkDefaultFont", 9)).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕ Close", bg="#7f1d1d", fg="white", relief=tk.FLAT,
                  padx=6, command=win.destroy).pack(side=tk.RIGHT, padx=4)

        # Scrollable issue list
        outer = tk.Frame(win, bg=_AF_C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(outer, orient=tk.VERTICAL)
        lbox = tk.Listbox(outer, yscrollcommand=sb.set,
                          bg="#1e1e2e", fg="#cdd6f4", selectbackground="#45475a",
                          selectforeground="#fbbf24", font=("Courier", 9),
                          activestyle="none", relief=tk.FLAT, bd=0,
                          highlightthickness=0)
        sb.config(command=lbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        _issue_data = []
        for node, path, prop, msg in issues:
            short_path = path.replace("Fragment.", "").replace("Default", "Def")
            prop_tag = f"  [{prop}]  " if prop else "  "
            display = f"⚠  {short_path}{prop_tag}{msg}"
            lbox.insert(tk.END, display)
            _issue_data.append((node, prop))

        # Detail panel below
        detail_frame = tk.Frame(win, bg="#313244", height=80)
        detail_frame.pack(fill=tk.X, padx=6, pady=(0,4))
        detail_frame.pack_propagate(False)
        detail_var = tk.StringVar(value="← Select an issue above to see details and navigate")
        detail_lbl = tk.Label(detail_frame, textvariable=detail_var,
                              bg="#313244", fg="#a6adc8", font=("TkDefaultFont", 9),
                              justify=tk.LEFT, anchor=tk.NW, wraplength=820, padx=8, pady=6)
        detail_lbl.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(win, bg=_AF_C_BG)
        btn_row.pack(fill=tk.X, padx=6, pady=(0,6))
        jump_btn = tk.Button(btn_row, text="→ Go to Node & CSS Field",
                             bg="#1d4ed8", fg="white", relief=tk.FLAT,
                             padx=10, pady=4, cursor="hand2",
                             font=("TkDefaultFont", 9),
                             state=tk.DISABLED, command=lambda: None)
        jump_btn.pack(side=tk.LEFT, padx=2)
        fix_btn  = tk.Button(btn_row, text="⚡ Apply Suggested Fix",
                             bg="#065F46", fg="white", relief=tk.FLAT,
                             padx=10, pady=4, cursor="hand2",
                             font=("TkDefaultFont", 9),
                             state=tk.DISABLED, command=lambda: None)
        fix_btn.pack(side=tk.LEFT, padx=2)

        _cur = [None]   # [0] = (node, prop, fix_props)

        # Build per-issue suggested fixes
        _FIXES = {
            "height": {"height": "100%"},
            "alignItems": None,   # context-dependent, handled below
            "minHeight": {"minHeight": "0"},
        }

        def _on_select(evt=None):
            sel = lbox.curselection()
            if not sel: return
            idx2 = sel[0]
            node2, prop2 = _issue_data[idx2]
            _, _, _, msg2 = issues[idx2]
            detail_var.set(msg2)
            fix_props = _FIXES.get(prop2) if prop2 else None
            _cur[0] = (node2, prop2, fix_props)
            jump_btn.config(state=tk.NORMAL,
                            command=lambda n=node2, p=prop2: self._jump_to_issue(n, p))
            if fix_props:
                fix_btn.config(state=tk.NORMAL,
                               command=lambda n=node2, fp=fix_props: _apply_fix(n, fp))
            else:
                fix_btn.config(state=tk.DISABLED, command=lambda: None)

        def _apply_fix(node2, fix_props):
            """Apply the suggested fix directly from the validation window."""
            css2 = _af_get_css(node2)
            sty2 = node2.get("Style") or {}
            for p2, v2 in fix_props.items():
                css2[p2] = v2
                if p2 in _AF_STYLE_TOP_KEYS:
                    sty2.pop(p2, None)
            self._reload_preview()
            self.status_var.set(f"Fixed: {fix_props}")
            # re-run validate so the issue disappears if resolved
            issues.clear()
            self._validate_node(self.fragment_root.get("Fragment", {}), "Fragment", None, issues)
            lbox.delete(0, tk.END)
            _issue_data.clear()
            for nd, pth, pr, mg in issues:
                sp = pth.replace("Fragment.", "").replace("Default", "Def")
                pt = f"  [{pr}]  " if pr else "  "
                lbox.insert(tk.END, f"⚠  {sp}{pt}{mg}")
                _issue_data.append((nd, pr))
            if not issues:
                detail_var.set("✓ All issues resolved!")
                jump_btn.config(state=tk.DISABLED)
                fix_btn.config(state=tk.DISABLED)
                self._warn_var.set("")
                self._warn_lbl.pack_forget()

        def _on_double(evt=None):
            sel = lbox.curselection()
            if not sel: return
            node2, prop2 = _issue_data[sel[0]]
            self._jump_to_issue(node2, prop2)

        lbox.bind("<<ListboxSelect>>", _on_select)
        lbox.bind("<Double-Button-1>",  _on_double)
        # Color alternate rows
        for i in range(lbox.size()):
            lbox.itemconfig(i, bg="#1e1e2e" if i % 2 == 0 else "#252537")

    def _validate_node(self, node, path, parent_node, issues):
        """Recursively collect layout issues as (node, path, prop, message) tuples."""
        if not isinstance(node, dict): return
        css   = (node.get("Style") or {}).get("css") or {}
        style = node.get("Style") or {}
        ctype = node.get("Container", "")

        def _get(prop):
            return css.get(prop) or style.get(prop) or ""

        # ── Warning 1: fixed px height on child when parent has padding ───────────
        height_val = _get("height")
        if height_val and str(height_val).endswith("px") and parent_node is not None:
            pcss   = (parent_node.get("Style") or {}).get("css") or {}
            pstyle = parent_node.get("Style") or {}
            pad    = pcss.get("padding") or pstyle.get("padding", "")
            if pad and pad not in ("0", "0px", ""):
                try:
                    if float(str(height_val)[:-2]) > 50:
                        issues.append((
                            node, path, "height",
                            f"height:{height_val} is a fixed pixel height but the parent has "
                            f"padding:{pad}. Fixed heights overflow padded parents. "
                            f"Change to height:100% so the child fills the padded inner area."
                        ))
                except ValueError:
                    pass

        # ── Warning 2: alignItems on a leaf or non-flex container ─────────────────
        ai = _get("alignItems")
        if ai and ai not in ("", "normal"):
            slot_children = [c for sl in (node.get("Slots") or {}).values()
                             if isinstance(sl, list) for c in sl if isinstance(c, dict)]
            fd = _get("flexDirection")
            if not slot_children:
                issues.append((
                    node, path, "alignItems",
                    f"alignItems:{ai} is set on ({ctype}) but this node has NO children — it has no effect. "
                    f"alignItems controls how a container's OWN children align on the cross axis. "
                    f"To control how THIS node aligns in its parent, use alignSelf instead."
                ))
            elif not fd and ctype not in ("flex", "grid", "sidebar", "card"):
                issues.append((
                    node, path, "alignItems",
                    f"alignItems:{ai} on ({ctype}) has no effect — node is not a flex/grid container. "
                    f"Add flexDirection:row or flexDirection:column to make it flex, "
                    f"or remove alignItems and set alignSelf on THIS node to align it inside its parent."
                ))

        # ── Warning 3: flex-row children missing minHeight: 0 ────────────────────
        fd = _get("flexDirection")
        if ctype == "flex" and fd in ("row", "row-reverse"):
            slot_kids = (node.get("Slots") or {}).get("Default") or []
            for child in slot_kids:
                if not isinstance(child, dict): continue
                ccss  = (child.get("Style") or {}).get("css") or {}
                cstyle = (child.get("Style") or {})
                mh     = ccss.get("minHeight") or cstyle.get("minHeight", "")
                child_has_kids = any(
                    isinstance(c2, dict)
                    for sl in (child.get("Slots") or {}).values()
                    if isinstance(sl, list)
                    for c2 in sl
                )
                if child_has_kids and mh not in ("0", "0px") and not _af_is_locked(child):
                    ct2 = child.get("Container", "")
                    issues.append((
                        child,
                        f"{path}.Default[child:{ct2}]",
                        "minHeight",
                        f"({ct2}) child of flex-row is missing minHeight:0. "
                        f"Without it the flex item cannot shrink below its content height, "
                        f"so inner scrollbars never activate. Add minHeight:0 to fix."
                    ))

        # ── Recurse into all slots ────────────────────────────────────────────────
        for sn, items in (node.get("Slots") or {}).items():
            if isinstance(items, list):
                for i, child in enumerate(items):
                    self._validate_node(child, f"{path}.{sn}[{i}]", node, issues)

    # ═══════ edit dialogs (mirror V6) ════════════════════════════════════════

    def _open_edit_dialog(self, node):
        ctype=node.get("Container","")
        if   ctype=="table":         self._edit_table_dlg(node)
        elif ctype=="chart":         self._edit_chart_dlg(node)
        elif ctype in ("flex","grid","sidebar","card"): self._edit_container_dlg(node)
        elif ctype=="segment-panel": self._edit_segment_dlg(node)
        elif ctype=="search":        self._edit_search_dlg(node)
        else: self.status_var.set(f"Edit CSS for {ctype} in the right panel →")

    def _edit_container_dlg(self, node):
        css=_af_get_css(node)
        win=tk.Toplevel(self); win.title(f"Edit {node.get('Container','')}"); win.geometry("420x320"); win.configure(bg=_AF_C_BG)
        rows=[("flexDirection",["column","row","row-reverse","column-reverse"]),
              ("gap",None),("padding",None),("flex",None),("height",None),("width",None),
              ("overflow",["hidden","auto","visible"])]
        vars_={}
        for prop,choices in rows:
            r=tk.Frame(win,bg=_AF_C_BG); r.pack(fill=tk.X,padx=10,pady=3)
            tk.Label(r,text=prop+":",width=16,anchor=tk.E,bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
            v=tk.StringVar(value=str(css.get(prop,"")))
            vars_[prop]=v
            if choices: ttk.Combobox(r,textvariable=v,values=choices,width=18).pack(side=tk.LEFT,padx=4)
            else: ttk.Entry(r,textvariable=v,width=20).pack(side=tk.LEFT,padx=4)
        def _apply():
            for prop,v in vars_.items():
                val=v.get().strip()
                if val: css[prop]=val
                elif prop in css: del css[prop]
            self._rebuild_tree(); self._reload_preview()
            if self._selected_slot_ref: self._refresh_css_panel(self._selected_slot_ref)
            win.destroy()
        self._tbtn(win,"Apply ✓",_apply,"#065F46").pack(pady=10)

    def _edit_table_dlg(self, node):
        cfg=node.get("Config") or {}
        win=tk.Toplevel(self); win.title("Edit Table"); win.geometry("500x460"); win.configure(bg=_AF_C_BG); win.resizable(True,True)
        r0=tk.Frame(win,bg=_AF_C_BG); r0.pack(fill=tk.X,padx=10,pady=(10,4))
        tk.Label(r0,text="Title:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        title_var=tk.StringVar(value=cfg.get("title",""))
        ttk.Entry(r0,textvariable=title_var,width=28).pack(side=tk.LEFT,padx=6)
        tk.Label(r0,text="Page size:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        pg_var=tk.StringVar(value=str(cfg.get("pageSize",25)))
        ttk.Entry(r0,textvariable=pg_var,width=6).pack(side=tk.LEFT,padx=4)
        tk.Label(win,text="Columns:",bg=_AF_C_BG,fg=_AF_C_ACC).pack(anchor=tk.W,padx=10)
        cf=tk.Frame(win,bg=_AF_C_BG); cf.pack(fill=tk.BOTH,expand=True,padx=10,pady=4)
        col_list=tk.Listbox(cf,bg="#313244",fg=_AF_C_FG,selectbackground="#45475a",font=("Courier",10),relief=tk.FLAT,highlightthickness=0)
        csb=ttk.Scrollbar(cf,command=col_list.yview); col_list.configure(yscrollcommand=csb.set)
        csb.pack(side=tk.RIGHT,fill=tk.Y); col_list.pack(fill=tk.BOTH,expand=True)
        for col in cfg.get("Columns",[]):
            lk=(col.get("Config") or {}).get("LabelKey","")
            col_list.insert(tk.END,f"  {lk}")
        br=tk.Frame(win,bg=_AF_C_BG); br.pack(fill=tk.X,padx=10,pady=2)
        new_col_var=tk.StringVar()
        ttk.Entry(br,textvariable=new_col_var,width=18).pack(side=tk.LEFT)
        def _add_col():
            lk=new_col_var.get().strip()
            if lk: col_list.insert(tk.END,f"  {lk}"); new_col_var.set("")
        def _del_col():
            s=col_list.curselection()
            if s: col_list.delete(s[0])
        self._tbtn(br,"Add ➕",_add_col,"#065F46").pack(side=tk.LEFT,padx=2)
        self._tbtn(br,"Del 🗑",_del_col,"#7f1d1d").pack(side=tk.LEFT,padx=2)
        init=node.get("Init") or {}
        ds_lf=ttk.LabelFrame(win,text="Data Source",padding=6,style="AF.TLabelframe")
        ds_lf.pack(fill=tk.X,padx=10,pady=(4,2))
        ds_row=tk.Frame(ds_lf,bg=_AF_C_BG); ds_row.pack(fill=tk.X)
        tk.Label(ds_row,text="DataSourcePath:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        ds_var=tk.StringVar(value=init.get("DataSourcePath",""))
        _v5_pool = getattr(self._v5, '_var_pool', {}) if self._v5 else {}
        _pool_keys_af = sorted(set(list(_v5_pool.keys()) +
                                    [c.ds for c in (self._v5.cards.values()
                                                     if self._v5 else []) if c.ds]))
        if _pool_keys_af:
            ds_cb2 = ttk.Combobox(ds_row, textvariable=ds_var,
                                   values=_pool_keys_af, width=26)
            ds_cb2.pack(side=tk.LEFT, padx=6)
            Tooltip(ds_cb2, "DataSourcePath — choose from Variable Pool\nor type a new key.")
        else:
            ttk.Entry(ds_row, textvariable=ds_var, width=28).pack(side=tk.LEFT, padx=6)
        def _apply():
            cfg["title"]=title_var.get().strip()
            try: cfg["pageSize"]=int(pg_var.get())
            except: pass
            old_map={(c.get("Config") or {}).get("LabelKey",""):c for c in cfg.get("Columns",[])}
            new_cols=[]
            for i in range(col_list.size()):
                lk=col_list.get(i).strip()
                if lk in old_map: new_cols.append(old_map[lk])
                else: new_cols.append({"Config":{"LabelKey":lk,"Sort":{"Sortable":True,"SortBy":lk}},"Slots":{"Default":[{"Element":"key-value","Input":lk,"Config":{"Link":None}}]}})
            cfg["Columns"]=new_cols
            ds=ds_var.get().strip()
            if ds: node["Init"]={"Type":"value-array","DataSourcePath":ds}
            self._rebuild_tree(); self._reload_preview(); win.destroy()
        self._tbtn(win,"Apply ✓",_apply,"#065F46").pack(pady=8)

    def _edit_chart_dlg(self, node):
        cfg=node.get("Config") or {}; dm=cfg.get("dataMapping") or {}
        win=tk.Toplevel(self); win.title("Edit Chart"); win.geometry("540x460"); win.configure(bg=_AF_C_BG)
        init=node.get("Init") or {}
        r0=ttk.LabelFrame(win,text="Data Source",padding=6,style="AF.TLabelframe"); r0.pack(fill=tk.X,padx=10,pady=(10,4))
        rr=tk.Frame(r0,bg=_AF_C_BG); rr.pack(fill=tk.X)
        tk.Label(rr,text="DataSourcePath:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        ds_var=tk.StringVar(value=init.get("DataSourcePath",""))
        _v5p2 = getattr(self._v5,'_var_pool',{}) if self._v5 else {}
        _pk2  = sorted(set(list(_v5p2.keys()) +
                            [c.ds for c in (self._v5.cards.values()
                                            if self._v5 else []) if c.ds]))
        if _pk2:
            cbc = ttk.Combobox(rr, textvariable=ds_var, values=_pk2, width=28)
            cbc.pack(side=tk.LEFT, padx=6)
            Tooltip(cbc, "Choose from Variable Pool or type a new key.")
        else:
            ttk.Entry(rr,textvariable=ds_var,width=30).pack(side=tk.LEFT,padx=6)
        tk.Label(win,text="Series (Name | Color | Y-field | X-field):",bg=_AF_C_BG,fg=_AF_C_ACC).pack(anchor=tk.W,padx=10)
        sf=tk.Frame(win,bg=_AF_C_BG); sf.pack(fill=tk.BOTH,expand=True,padx=10,pady=4)
        s_list=tk.Listbox(sf,bg="#313244",fg=_AF_C_FG,selectbackground="#45475a",font=("Courier",9),relief=tk.FLAT,highlightthickness=0)
        ssb=ttk.Scrollbar(sf,command=s_list.yview); s_list.configure(yscrollcommand=ssb.set)
        ssb.pack(side=tk.RIGHT,fill=tk.Y); s_list.pack(fill=tk.BOTH,expand=True)
        for sm in dm.get("seriesMappings",[]):
            so=sm.get("staticOptions") or {}; nm=so.get("name",""); cl=so.get("color","#888")
            fm=sm.get("fieldMappings") or {}
            yf=next((k for k,v in fm.items() if v=="y"),""); xf=next((k for k,v in fm.items() if v=="name"),"")
            s_list.insert(tk.END,f"  {nm} | {cl} | {yf} | {xf}")
        br=tk.Frame(win,bg=_AF_C_BG); br.pack(fill=tk.X,padx=10,pady=2)
        sn_v=tk.StringVar(); sc_v=tk.StringVar(value="#90CAF9"); sy_v=tk.StringVar(); sx_v=tk.StringVar()
        for lbl,var in [("Name:",sn_v),("Color:",sc_v),("Y-field:",sy_v),("X-field:",sx_v)]:
            tk.Label(br,text=lbl,bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
            ttk.Entry(br,textvariable=var,width=8).pack(side=tk.LEFT,padx=1)
        def _add_s():
            nm=sn_v.get().strip()
            if nm: s_list.insert(tk.END,f"  {nm} | {sc_v.get().strip()} | {sy_v.get().strip()} | {sx_v.get().strip()}")
        def _del_s():
            s=s_list.curselection()
            if s: s_list.delete(s[0])
        self._tbtn(br,"Add ➕",_add_s,"#065F46").pack(side=tk.LEFT,padx=4)
        self._tbtn(br,"Del",   _del_s,"#7f1d1d").pack(side=tk.LEFT,padx=2)
        def _apply():
            ds=ds_var.get().strip()
            if ds: node["Init"]={"Type":"value-array","DataSourcePath":ds}
            new_series=[]
            for i in range(s_list.size()):
                parts=[p.strip() for p in s_list.get(i).strip().split("|")]
                while len(parts)<4: parts.append("")
                nm,cl,yf,xf=parts[0],parts[1],parts[2],parts[3]
                fm={}
                if xf: fm[xf]="name"
                if yf: fm[yf]="y"
                new_series.append({"fieldMappings":fm,"seriesType":"column","staticOptions":{"name":nm,"color":cl}})
            cfg.setdefault("dataMapping",{})["seriesMappings"]=new_series
            self._rebuild_tree(); self._reload_preview(); win.destroy()
        self._tbtn(win,"Apply ✓",_apply,"#065F46").pack(pady=8)

    def _edit_segment_dlg(self, node):
        cfg=node.get("Config") or {}; fcfg=cfg.get("Filter") or {}
        win=tk.Toplevel(self); win.title("Edit Segment Panel"); win.geometry("420x380"); win.configure(bg=_AF_C_BG)
        r0=tk.Frame(win,bg=_AF_C_BG); r0.pack(fill=tk.X,padx=10,pady=(10,4))
        tk.Label(r0,text="Label:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        lbl_var=tk.StringVar(value=(fcfg.get("Placeholder") or {}).get("LabelKey",""))
        ttk.Entry(r0,textvariable=lbl_var,width=24).pack(side=tk.LEFT,padx=6)
        tk.Label(win,text="Options (Label | Value):",bg=_AF_C_BG,fg=_AF_C_ACC).pack(anchor=tk.W,padx=10)
        of=tk.Frame(win,bg=_AF_C_BG); of.pack(fill=tk.BOTH,expand=True,padx=10)
        opt_list=tk.Listbox(of,bg="#313244",fg=_AF_C_FG,selectbackground="#45475a",font=("Courier",10),relief=tk.FLAT,highlightthickness=0)
        osb=ttk.Scrollbar(of,command=opt_list.yview); opt_list.configure(yscrollcommand=osb.set)
        osb.pack(side=tk.RIGHT,fill=tk.Y); opt_list.pack(fill=tk.BOTH,expand=True)
        key_k=fcfg.get("EntityKey","AttributeKey"); val_k=fcfg.get("EntityValue","AttributeValue")
        for item in fcfg.get("StaticList",[]):
            opt_list.insert(tk.END,f"  {item.get(key_k,'')} | {item.get(val_k,'')}")
        br=tk.Frame(win,bg=_AF_C_BG); br.pack(fill=tk.X,padx=10,pady=4)
        nk=tk.StringVar(); nv=tk.StringVar()
        ttk.Entry(br,textvariable=nk,width=14).pack(side=tk.LEFT,padx=2)
        tk.Label(br,text="|",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        ttk.Entry(br,textvariable=nv,width=14).pack(side=tk.LEFT,padx=2)
        def _add():
            k=nk.get().strip(); v=nv.get().strip()
            if k: opt_list.insert(tk.END,f"  {k} | {v or k}")
        def _del():
            s=opt_list.curselection()
            if s: opt_list.delete(s[0])
        self._tbtn(br,"Add ➕",_add,"#065F46").pack(side=tk.LEFT,padx=4)
        self._tbtn(br,"Del",   _del,"#7f1d1d").pack(side=tk.LEFT,padx=2)
        def _apply():
            fcfg.setdefault("Placeholder",{})["LabelKey"]=lbl_var.get().strip()
            new_list=[]
            for i in range(opt_list.size()):
                parts=[p.strip() for p in opt_list.get(i).strip().split("|")]
                k=parts[0]; v=parts[1] if len(parts)>1 else parts[0]
                new_list.append({key_k:k,"UID":str(uuid.uuid4())[:8],val_k:v})
            fcfg["StaticList"]=new_list
            if "Filter" not in cfg: cfg["Filter"]={}
            cfg["Filter"].update(fcfg)
            self._rebuild_tree(); self._reload_preview(); win.destroy()
        self._tbtn(win,"Apply ✓",_apply,"#065F46").pack(pady=8)

    def _edit_search_dlg(self, node):
        cfg=node.get("Config") or {}
        win=tk.Toplevel(self); win.title("Edit Search"); win.geometry("400x200"); win.configure(bg=_AF_C_BG)
        placeholder=((cfg.get("Filter") or {}).get("Placeholder") or {}).get("LabelKey","")
        vars_={"Name":tk.StringVar(value=cfg.get("Name","")),
               "_placeholder":tk.StringVar(value=placeholder),
               "SectionName":tk.StringVar(value=cfg.get("SectionName",""))}
        for label,key in [("Name","Name"),("Placeholder","_placeholder"),("SectionName","SectionName")]:
            r=tk.Frame(win,bg=_AF_C_BG); r.pack(fill=tk.X,padx=10,pady=4)
            tk.Label(r,text=label+":",width=20,anchor=tk.E,bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
            ttk.Entry(r,textvariable=vars_[key],width=26).pack(side=tk.LEFT,padx=4)
        def _apply():
            cfg["Name"]=vars_["Name"].get().strip(); cfg["SectionName"]=vars_["SectionName"].get().strip()
            cfg.setdefault("Filter",{}).setdefault("Placeholder",{})["LabelKey"]=vars_["_placeholder"].get().strip()
            cfg.setdefault("SearchProperty",{})["placeholder"]=vars_["_placeholder"].get().strip()
            self._rebuild_tree(); self._reload_preview(); win.destroy()
        self._tbtn(win,"Apply ✓",_apply,"#065F46").pack(pady=10)

    # ═══════ add / delete ════════════════════════════════════════════════════

    def _add_child_dialog(self, parent_node=None, parent_path=None):
        if parent_node is None:
            ref=self._selected_slot_ref
            if not ref:
                messagebox.showinfo("No Selection","Select a container first.",parent=self); return
            parent_node=ref.node; parent_path=ref.path
        slots=parent_node.get("Slots") or {}
        slot_names=[k for k,v in slots.items() if isinstance(v,list)]
        if not slot_names:
            messagebox.showinfo("Cannot Add","Selected node has no Slots arrays.\nChoose a flex/grid/header-action container.",parent=self); return
        win=tk.Toplevel(self); win.title("Add Container"); win.geometry("420x240"); win.configure(bg=_AF_C_BG)
        r0=tk.Frame(win,bg=_AF_C_BG); r0.pack(fill=tk.X,padx=10,pady=(10,4))
        tk.Label(r0,text="Type:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        type_var=tk.StringVar(value="flex-col")
        ttk.Combobox(r0,textvariable=type_var,values=list(_AF_NEW_NODES.keys()),
                     state="readonly",width=20).pack(side=tk.LEFT,padx=6)
        r1=tk.Frame(win,bg=_AF_C_BG); r1.pack(fill=tk.X,padx=10,pady=4)
        tk.Label(r1,text="Title / Label:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        title_var=tk.StringVar()
        ttk.Entry(r1,textvariable=title_var,width=24).pack(side=tk.LEFT,padx=6)
        r2=tk.Frame(win,bg=_AF_C_BG); r2.pack(fill=tk.X,padx=10,pady=4)
        tk.Label(r2,text="Add to Slot:",bg=_AF_C_BG,fg=_AF_C_FG).pack(side=tk.LEFT)
        slot_var=tk.StringVar(value="Default" if "Default" in slot_names else slot_names[0])
        ttk.Combobox(r2,textvariable=slot_var,values=slot_names,state="readonly",width=14).pack(side=tk.LEFT,padx=6)
        def _ok():
            tpl=_AF_NEW_NODES.get(type_var.get())
            if not tpl: messagebox.showerror("Unknown Type",f"No template for {type_var.get()}",parent=win); return
            new_node=copy.deepcopy(tpl)
            t=title_var.get().strip()
            if t: new_node.setdefault("Config",{})["title"]=t
            slot=slot_var.get()
            parent_node.setdefault("Slots",{}).setdefault(slot,[]).append(new_node)
            self._rebuild_tree(reselect_path=parent_path); self._reload_preview(); win.destroy()
        self._tbtn(win,"Add ✓",_ok,"#065F46").pack(pady=14)

    def _delete_selected_node(self):
        ref=self._selected_slot_ref
        if not ref: messagebox.showinfo("No Selection","Select a node first.",parent=self); return
        if ref.parent is None: messagebox.showwarning("Cannot Delete","Cannot delete the Fragment root.",parent=self); return
        label=_af_node_label(ref.node)
        if not messagebox.askyesno("Confirm Delete",f"Delete {label!r} from Slots.{ref.parent_slot}?\nThis cannot be undone.",parent=self): return
        items=ref.parent.get("Slots",{}).get(ref.parent_slot,[])
        try: items.remove(ref.node)
        except ValueError: pass
        self._selected_slot_ref=None; self._selected_preview_node=None
        self._rebuild_tree(); self._reload_preview(); self.status_var.set(f"Deleted {label}")

    def _delete_node(self, node, path):
        ref=next((r for r in self.tree_id_map.values() if r.node is node),None)
        if ref and ref.parent:
            items=ref.parent.get("Slots",{}).get(ref.parent_slot,[])
            try: items.remove(node)
            except ValueError: pass
        elif not ref:
            messagebox.showwarning("Not Found","Node not in tree map.",parent=self); return
        self._selected_slot_ref=None; self._selected_preview_node=None
        self._rebuild_tree(); self._reload_preview(); self.status_var.set(f"Deleted {_af_node_label(node)}")

    # ═══════ JSON I/O ════════════════════════════════════════════════════════

    def _paste_json(self):
        win=tk.Toplevel(self); win.title("Paste Fragment JSON"); win.geometry("860x600"); win.configure(bg=_AF_C_BG)
        tk.Label(win,text="Paste JSON below:",bg=_AF_C_BG,fg=_AF_C_FG).pack(anchor=tk.W,padx=8,pady=(8,2))
        txt=scrolledtext.ScrolledText(win,bg="#313244",fg=_AF_C_FG,font=("Courier",10),
                                       insertbackground="white",relief=tk.FLAT,
                                       highlightthickness=1,highlightbackground="#45475a")
        txt.pack(fill=tk.BOTH,expand=True,padx=8,pady=4)
        try:
            clip=self.clipboard_get()
            if clip.strip().startswith("{"): txt.insert("1.0",clip)
        except tk.TclError: pass
        def _ok():
            try:
                raw=txt.get("1.0",tk.END)
                raw=re.sub(r'\{:[^}]+\}', lambda m: f'"{m.group(0)}"', raw)
                data=json.loads(raw)
                if "Fragment" not in data:
                    raise ValueError("JSON must have a top-level 'Fragment' key.")
                self.fragment_root=data; self.orig_snapshot=copy.deepcopy(data)
                self._rebuild_tree(); self._reload_preview(); win.destroy()
                self.status_var.set("Fragment loaded")
            except Exception as exc:
                messagebox.showerror("Parse Error",str(exc),parent=win)
        self._tbtn(win,"Load  →",_ok,"#065F46").pack(pady=6)

    def _clean_internal_keys(self, obj):
        if isinstance(obj, dict):
            for key in ("_unlocked", "_cid"):
                obj.pop(key, None)
            for v in obj.values():
                self._clean_internal_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                self._clean_internal_keys(item)

    def _export_json(self):
        path=filedialog.asksaveasfilename(title="Export",defaultextension=".json",
                                           filetypes=[("JSON","*.json"),("All","*.*")])
        if path:
            export=copy.deepcopy(self.fragment_root)
            self._clean_internal_keys(export)
            with open(path,"w",encoding="utf-8") as f:
                json.dump(export,f,indent=2)
            self.status_var.set(f"Exported → {path}")

    def _copy_json(self):
        if not self.fragment_root: return
        export=copy.deepcopy(self.fragment_root)
        self._clean_internal_keys(export)
        self.clipboard_clear()
        self.clipboard_append(json.dumps(export,indent=2))
        self.status_var.set("JSON copied to clipboard")

    def _show_diff(self):
        if not self.fragment_root or not self.orig_snapshot:
            messagebox.showinfo("No Data","Nothing loaded.",parent=self); return
        diffs: list=[]
        _af_diff_trees(self.orig_snapshot,self.fragment_root,"root",diffs)
        win=tk.Toplevel(self); win.title("Diff vs original"); win.geometry("960x560"); win.configure(bg=_AF_C_BG)
        tk.Label(win,text=f"{len(diffs)} difference(s)." if diffs else "No differences.",
                 bg=_AF_C_BG,fg="#a6e3a1" if not diffs else "#f38ba8").pack(anchor=tk.W,padx=8,pady=(8,2))
        txt=scrolledtext.ScrolledText(win,bg="#313244",fg=_AF_C_FG,font=("Courier",10),
                                       relief=tk.FLAT,highlightthickness=1,highlightbackground="#45475a")
        txt.pack(fill=tk.BOTH,expand=True,padx=8,pady=(0,8))
        txt.insert("1.0","\n".join(diffs) if diffs else "✓  No changes.")
        txt.config(state=tk.DISABLED)


# ───────────────────────────────────────────────────────────────
#  MAIN APP
# ───────────────────────────────────────────────────────────────
class Designer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Manhattan UI Builder - Pro")
        self.geometry("1600x900")
        self.minsize(1200,800)
        self.configure(bg=BG)
        self.cards = {}; self.filters = []; self._sel = None; self._clipboard = None
        self._sel_set = set(); self._bg_canvas = None; self._rb_start = None; self._rb_rect_id = None
        self._dir_bar = None
        self._vp_w = tk.IntVar(value=1920); self._vp_h = tk.IntVar(value=1080)
        self._vp_sb = tk.IntVar(value=0)
        self._canvas_zoom = 1.0
        self.filter_pos = tk.StringVar(value="left")
        self.wrap_flyout = tk.BooleanVar(value=False)
        self.segment_dirs = {}
        self.header_action_meta   = {}
        self.flyout_card_meta     = {}
        self.sidebar_meta         = {}
        self.main_content_meta    = {}
        self.root_fragment_config = {}
        # ── Variable pool from imported Action JSON ───────────────────
        self._var_pool: dict = {}          # {DataSourcePath: backendVar}
        self._var_pool_source: str = ""    # label of where pool came from
        self.filter_orig_node     = None   # original filter-panel element (passthrough)
        self.fragment_init_orig   = {}     # original Fragment.Init (preserves DefaultValues)
        self.sidebar_right_slot   = []     # Right slot of sidebar (details flyout stack)
        self._filters_modified    = False
        self._loading_fragment    = False
        # ── Strict round-trip import mode ────────────────────────────
        self.strict_roundtrip_import  = tk.BooleanVar(value=True)
        self.imported_fragment_root   = None   # deepcopy of Fragment node at import time (for debug check)
        # ── Debug mode state ──────────────────────────────────────────
        self.debug_mode         = tk.BooleanVar(value=False)
        self._debug_log         = []          # list of {time, action, detail}
        self._debug_imported_json = None      # raw JSON string at import time
        self._debug_session_start = None      # datetime of debug session start
        self._debug_btn         = None        # toolbar button reference
        self.layout_prefs = {
            "padding": "0px", "gap": "0px", "bg": "",
            "jc": "", "height": "", "sb_collapsible": True,
            "chart_wrap": "wrap", "content_layout": "flex-row", "grid_columns": "1fr 1fr",
            "opt_width": False, "opt_flex": False,
            "opt_minheight": False, "opt_boxsizing": False,
        }
        self._build_ui()
        self._load_defaults()
        self.after(3000, self._check_for_updates)

    def _build_ui(self):
        # ── Top navigation bar (redesigned with sections) ─────────────────
        bar = tk.Frame(self, bg="#0F172A", height=58)
        bar.pack(fill="x"); bar.pack_propagate(False)

        # Logo block
        logo_f = tk.Frame(bar, bg="#2563EB", padx=14, pady=0)
        logo_f.pack(side="left", fill="y")
        tk.Label(logo_f, text="⬡", bg="#2563EB", fg="white",
                 font=("Helvetica",14,"bold")).pack(side="left",padx=(0,6),pady=14)
        tk.Label(logo_f, text="Fragment UI Designer", bg="#2563EB", fg="white",
                 font=("Helvetica",10,"bold")).pack(side="left")

        # Fragment name + Draft badge
        name_f = tk.Frame(bar, bg="#0F172A"); name_f.pack(side="left", padx=12)
        self._frag_name_var = tk.StringVar(value="My Dashboard Fragment")
        tk.Entry(name_f, textvariable=self._frag_name_var, bg="#0F172A",
                 fg="white", insertbackground="white", relief="flat",
                 font=("Helvetica",11,"bold"), width=22).pack(side="left")
        tk.Label(name_f, text="Draft", bg="#374151", fg="#CBD5E1",
                 font=("Helvetica",8,"bold"), padx=8, pady=2).pack(side="left",padx=8)

        # ── Section helper ──────────────────────────────────────────────────
        def _section(label_text):
            """Create a labeled section group on the RIGHT side of the bar."""
            tk.Frame(bar, bg="#334155", width=1).pack(side="right", fill="y", padx=0, pady=10)
            grp = tk.Frame(bar, bg="#0F172A")
            grp.pack(side="right", padx=4, fill="y")
            tk.Label(grp, text=label_text, bg="#0F172A", fg="#475569",
                     font=("Helvetica",7,"bold")).pack(side="top", pady=(4,0))
            btn_row = tk.Frame(grp, bg="#0F172A")
            btn_row.pack(side="top", fill="x", pady=(2,4))
            return btn_row

        def _sbtn(parent, text, bg, fg, cmd, tip=""):
            def _hov(c, d=22):
                try:
                    c = c.lstrip('#')
                    r,g,b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
                    return f"#{max(0,min(255,r+d)):02x}{max(0,min(255,g+d)):02x}{max(0,min(255,b+d)):02x}"
                except Exception:
                    return c
            hover = _hov(bg)
            b = tk.Label(parent, text=text, bg=bg, fg=fg,
                         relief="flat", font=("Helvetica",8,"bold"),
                         padx=8, pady=4, cursor="hand2")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e, w=b: w.config(bg=hover))
            b.bind("<Leave>",    lambda e, w=b: w.config(bg=bg))
            b.pack(side="left", padx=2)
            if tip: Tooltip(b, tip)
            return b

        # ── Section: MORE (rightmost) ───────────────────────────────────
        more_row = _section("MORE")
        self._adv_menu_btn = _sbtn(more_row, "⋮", "#0F172A", "#94A3B8", self._save_menu, "Advanced tools")
        self._pool_btn = _sbtn(more_row, "🗃 Vars (0)", "#1E293B", "#94A3B8",
                               self._import_action_json_dialog,
                               "Import Action JSON to populate the DataSourcePath variable pool.")

        # ── Section: AI ─────────────────────────────────────────────────
        ai_row = _section("AI")
        _sbtn(ai_row, "✨ Glean", "#4C1D95", "#C4B5FD",
              self._open_glean_chat_standalone,
              "Open Glean AI advisor — chat about your fragment and get reviewable suggestions.")

        # ── Section: LAYOUT ─────────────────────────────────────────────
        layout_row = _section("LAYOUT")
        _sbtn(layout_row, "🔧 Align Fix", "#1E293B", "#94A3B8",
              self._show_preview, "Open the V6 layout schematic / CSS editor")
        _sbtn(layout_row, "⚙ Settings", "#1E293B", "#94A3B8",
              self._edit_css, "Layout settings: padding, gap, grid columns, etc.")
        _sbtn(layout_row, "📦 Segments", "#1E293B", "#94A3B8",
              self._manage_segments, "Manage fragment segments")

        # ── Section: VIEW ───────────────────────────────────────────────
        view_row = _section("VIEW")
        _sbtn(view_row, "👁 Preview", "#1E293B", "#94A3B8",
              self._html_preview, "Open live browser preview of the fragment")

        # ── Section: FILE ───────────────────────────────────────────────
        file_row = _section("FILE")
        _sbtn(file_row, "📥 Import", "#1E293B", "#94A3B8",
              self._import_dialog, "Import a Fragment JSON file")
        _sbtn(file_row, "📤 Export", "#1E293B", "#94A3B8",
              self._generate_fragment, "Export the fragment JSON to clipboard/file")
        _sbtn(file_row, "💾 Save", "#2563EB", "white",
              lambda: (self.clipboard_clear(),
                       self.clipboard_append(json.dumps(self._build_fragment(), indent=2))),
              "Copy Fragment JSON to clipboard")

        # ── Info / tips banner ──────────────────────────────────────────
        self._tips_visible = True
        self._tips_bar = tk.Frame(self, bg="#EFF6FF", pady=0)
        self._tips_bar.pack(fill="x")
        tk.Label(self._tips_bar,
                 text="ⓘ  Canvas Tips:  Drag to move  •  Drag edges to resize  •  Double-click to edit",
                 bg="#EFF6FF", fg="#1D4ED8", font=("Helvetica",9)
                 ).pack(side="left", padx=12, pady=4)
        tk.Button(self._tips_bar, text="Got it", bg="#DBEAFE", fg="#1D4ED8",
                  relief="flat", font=("Helvetica",8,"bold"), padx=8, pady=2,
                  cursor="hand2", command=self._dismiss_tips
                  ).pack(side="left", padx=4, pady=3)
        tk.Button(self._tips_bar, text="✕", bg="#EFF6FF", fg="#93C5FD",
                  relief="flat", font=("Helvetica",10), padx=6,
                  cursor="hand2", command=self._dismiss_tips
                  ).pack(side="right", padx=8)

        # ── Body: left | center | right ─────────────────────────────────
        body = tk.Frame(self, bg="#F1F5F9"); body.pack(fill="both", expand=True)
        self._toolbox(body)
        self._workspace(body)
        self._properties_panel(body)

    def _dismiss_tips(self):
        if self._tips_visible:
            self._tips_bar.pack_forget(); self._tips_visible = False

    def _save_menu(self):
        m = tk.Menu(self, tearoff=0, bg="white", fg="#111827",
                    activebackground="#EFF6FF", font=("Helvetica",9))
        m.add_command(label="▶ Fragment JSON",       command=self._generate_fragment)
        m.add_command(label="⚡ Action JSON",         command=self._generate_action)
        m.add_separator()
        m.add_command(label="📥 Import JSON",          command=self._import_dialog)
        m.add_separator()
        m.add_command(label="🔧 Align Fix (Layout)",  command=self._show_preview)
        m.add_command(label="📦 Segments",             command=self._manage_segments)
        m.add_command(label="⚙️ Layout Settings",      command=self._edit_css)
        m.add_separator()
        m.add_command(label="↔ Reflow",                command=self._do_import_layout)
        m.add_command(label="📋 Paste",                command=self._paste_comp)
        m.add_command(label="⎘ Copy",                  command=self._copy_comp)
        m.add_command(label="🗂 → Tab",                command=self._assign_to_tab_dialog)
        m.add_separator()
        m.add_command(label="🗑 Clear All",             command=self._clear)
        m.add_command(label="🔄 Check Updates",        command=self._manual_update_check)
        m.add_separator()
        lbl = f"🐛 Debug {'ON ✓' if self.debug_mode.get() else 'OFF'}"
        m.add_command(label=lbl, command=self._toggle_debug)
        try:
            x = self._adv_menu_btn.winfo_rootx()
            y = self._adv_menu_btn.winfo_rooty() + self._adv_menu_btn.winfo_height()
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def _show_advanced_menu(self): self._save_menu()

    def _toggle_toolbox(self):
        if self._toolbox_visible:
            self._toolbox_outer.pack_forget()
        else:
            self._toolbox_outer.pack(
                side="left", fill="y",
                before=self._workspace_frame if hasattr(self,"_workspace_frame") else None)
        self._toolbox_visible = not self._toolbox_visible

    def _toggle_filter_panel(self):
        if self._filter_visible:
            self._flist_wrap.pack_forget()
            self._filter_toggle_btn.config(text="▶  🔍  Filters")
        else:
            self._flist_wrap.pack(fill="x")
            self._filter_toggle_btn.config(text="▼  🔍  Filters")
        self._filter_visible = not self._filter_visible

    # ── LEFT PANEL: Component Library ──────────────────────────────────
    def _toolbox(self, parent):
        outer = tk.Frame(parent, bg="white", width=230,
                          highlightbackground="#1E293B", highlightthickness=1)
        outer.pack(side="left", fill="y"); outer.pack_propagate(False)
        self._toolbox_outer  = outer
        self._toolbox_visible = True

        # Components / Data tabs
        tabs_f = tk.Frame(outer, bg="white"); tabs_f.pack(fill="x")
        self._tb_tab_var = tk.StringVar(value="Components")
        self._tb_comp_btn = tk.Button(tabs_f, text="Components", relief="flat",
            cursor="hand2", font=("Helvetica",9,"bold"), pady=8,
            command=lambda: self._switch_tb_tab("Components"))
        self._tb_comp_btn.pack(side="left", fill="x", expand=True)
        self._tb_data_btn = tk.Button(tabs_f, text="Data", relief="flat",
            cursor="hand2", font=("Helvetica",9), pady=8,
            command=lambda: self._switch_tb_tab("Data"))
        self._tb_data_btn.pack(side="left", fill="x", expand=True)
        tk.Frame(outer, bg="#2563EB", height=2).pack(fill="x")
        self._refresh_tb_tabs()

        # Search
        sf = tk.Frame(outer, bg="#F8FAFC", padx=8, pady=6); sf.pack(fill="x")
        se_f = tk.Frame(sf, bg="white", highlightbackground="#1E293B",
                         highlightthickness=1); se_f.pack(fill="x")
        tk.Label(se_f, text="🔍", bg="white", fg="#374151",
                 font=("Helvetica",9)).pack(side="left", padx=(8,2))
        self._tb_search = tk.StringVar()
        ttk.Entry(se_f, textvariable=self._tb_search,
                  font=("Helvetica",9)).pack(side="left",fill="x",expand=True,padx=(0,8),pady=4)

        # Scrollable list
        tc = tk.Canvas(outer, bg="white", highlightthickness=0)
        tsb = ttk.Scrollbar(outer, orient="vertical", command=tc.yview)
        tsb.pack(side="right", fill="y"); tc.pack(side="left",fill="both",expand=True)
        tc.configure(yscrollcommand=tsb.set)
        tb = tk.Frame(tc, bg="white")
        tb_win = tc.create_window((0,0), window=tb, anchor="nw")
        tb.bind("<Configure>", lambda e: tc.configure(scrollregion=tc.bbox("all")))
        tc.bind("<Configure>", lambda e: tc.itemconfig(tb_win, width=e.width))
        def _tbw(e): tc.yview_scroll(_wheel_scroll_units(e), "units")
        tc.bind("<MouseWheel>", _tbw); tb.bind("<MouseWheel>", _tbw)

        all_items = []  # (frame, kind, label_lower)

        def _section(label, expanded=True):
            sec_f = tk.Frame(tb, bg="white"); sec_f.pack(fill="x")
            all_items.append((sec_f,"sec",""))
            con_f = tk.Frame(tb, bg="white"); con_f.pack(fill="x")
            all_items.append((con_f,"content",""))
            _exp = [expanded]
            def _tog():
                _exp[0]=not _exp[0]
                tb2.config(text=f"{'▾' if _exp[0] else '▸'}  {label}")
                (con_f.pack(fill="x") if _exp[0] else con_f.pack_forget())
                tc.configure(scrollregion=tc.bbox("all"))
            hdr=tk.Frame(sec_f,bg="white"); hdr.pack(fill="x")
            tb2=tk.Button(hdr,text=f"{'▾' if expanded else '▸'}  {label}",
                bg="white",fg="#111827",relief="flat",font=("Helvetica",8,"bold"),
                anchor="w",padx=12,pady=5,cursor="hand2",command=_tog)
            tb2.pack(fill="x")
            tk.Frame(sec_f,bg="#F1F5F9",height=1).pack(fill="x")
            if not expanded: con_f.pack_forget()
            return con_f

        def _cbtn(p, ico, lbl, cmd, tip="", ref=""):
            row=tk.Frame(p,bg="white"); row.pack(fill="x")
            all_items.append((row,"btn",lbl.lower()))
            b=tk.Button(row,text=f"{ico}  {lbl}",bg="white",fg="#111827",
                relief="flat",anchor="w",font=("Helvetica",9),padx=14,pady=5,
                cursor="hand2",command=cmd)
            b.pack(side="left",fill="x",expand=True)
            b.bind("<Enter>",lambda e: b.config(bg="#EFF6FF",fg="#1D4ED8"))
            b.bind("<Leave>",lambda e: b.config(bg="white",fg="#111827"))
            b.bind("<MouseWheel>",_tbw); row.bind("<MouseWheel>",_tbw)
            if tip: Tooltip(b, tip)
            if ref and ref in RIVER_ELEM_DEFS:
                ib=tk.Button(row,text="ⓘ",bg="white",fg="#CBD5E1",relief="flat",
                    font=("Helvetica",9),padx=4,pady=4,cursor="hand2",
                    command=lambda c=ref: self._show_element_ref(c))
                ib.pack(side="right",padx=4)
                ib.bind("<Enter>",lambda e: ib.config(fg="#2563EB"))
                ib.bind("<Leave>",lambda e: ib.config(fg="#CBD5E1"))
                ib.bind("<MouseWheel>",_tbw)

        # FAVORITES
        fv=_section("FAVORITES",True)
        _cbtn(fv,"📊","KPI Card",    lambda:self.add_comp("metrics"), "KPI / Metric tile")
        _cbtn(fv,"🥧","Pie Chart",   lambda:self.add_comp("pie"),     "Pie or donut chart")
        _cbtn(fv,"📊","Bar Chart",   lambda:self.add_comp("bar"),     "Bar chart")
        _cbtn(fv,"📋","Data Table",  lambda:self.add_comp("table"),   "Paginated data table")
        _cbtn(fv,"📅","Date Range",  lambda:self.add_filter("date"),  "Date range filter")

        # VISUALIZATIONS
        vs=_section("VISUALIZATIONS",True)
        for ct,ico,lbl in [
            ("metrics","📊","KPI Card"),("bar","📊","Bar Chart"),
            ("column","📉","Column Chart"),("line","📈","Line Chart"),
            ("spline","〜","Spline Chart"),("area","▲","Area Chart"),
            ("areaspline","∿","Area Spline"),("pie","🥧","Pie / Donut"),
            ("scatter","⁘","Scatter"),("sunburst","☀","Sunburst"),
            ("waterfall","⬇","Waterfall"),("table","📋","Data Table")]:
            _cbtn(vs,ico,lbl,lambda c=ct:self.add_comp(c),TOOLTIPS.get(ct,""))

        # INPUTS
        ip=_section("INPUTS",False)
        for ft,ico,lbl,tip in [
            ("date","📅","Date Range","Calendar date-range picker"),
            ("dropdown","🔽","Dropdown","Single-select dropdown filter"),
            ("multiselect","☑️","Multi Select","Multi-select filter"),
            ("singleselect","🔘","Single Select","Single-select filter"),
            ("textbox","✏️","Text Input","Free-text search field")]:
            _cbtn(ip,ico,lbl,lambda f=ft:self.add_filter(f),tip)
        for ct,ico,lbl in [
            ("search","🔍","Search"),("segment-panel","📑","Segment Panel"),
            ("input","✏️","Input Field"),("combobox","🔽","Combobox"),
            ("toggle-button","🔄","Toggle Button"),("date-select","📅","Date Select")]:
            _cbtn(ip,ico,lbl,lambda c=ct:self.add_river_elem(c),TOOLTIPS.get(ct,""),ct)

        # LAYOUT
        la=_section("LAYOUT",False)
        _cbtn(la,"⬛","Row",    lambda:self.add_river_elem("flex"),"Horizontal flex row")
        _cbtn(la,"▬","Column", lambda:self.add_river_elem("flex"),"Vertical flex column")
        _cbtn(la,"⊟","Grid",   lambda:self.add_river_elem("grid"),"CSS grid container")
        for ct,ico,lbl in [("tab-group","📂","Tab Group"),
                            ("card","🃏","Card"),("accordion","▸","Accordion"),
                            ("carousel","🎠","Carousel")]:
            _cbtn(la,ico,lbl,lambda c=ct:self.add_river_elem(c),TOOLTIPS.get(ct,""),ct)

        # DISPLAY
        dp=_section("DISPLAY",False)
        for ct,ico,lbl in [("text","🔤","Text"),("key-value","🔑","Key Value"),
                            ("pill","🏷️","Pill"),("progress-bar","▰","Progress Bar"),
                            ("banner","📢","Banner"),("icon","✦","Icon"),
                            ("message","💬","Message")]:
            _cbtn(dp,ico,lbl,lambda c=ct:self.add_river_elem(c),TOOLTIPS.get(ct,""),ct)

        # ACTIONS
        ac=_section("ACTIONS",False)
        for ct,ico,lbl in [("button","🔘","Button"),("action-button","⚡","Action Button"),
                            ("link","🔗","Link"),("related-link","↗","Related Link")]:
            _cbtn(ac,ico,lbl,lambda c=ct:self.add_river_elem(c),TOOLTIPS.get(ct,""),ct)

        # + Custom Component
        cust_f=tk.Frame(outer,bg="white",highlightbackground="#1E293B",highlightthickness=1)
        cust_f.pack(fill="x",side="bottom")
        tk.Button(cust_f,text="＋  Custom Component",bg="white",fg="#111827",relief="flat",
                  font=("Helvetica",9),padx=14,pady=8,cursor="hand2",
                  command=lambda:None).pack(fill="x")
        tk.Label(cust_f,text="Create your own reusable component",bg="white",fg="#374151",
                 font=("Helvetica",7),pady=2).pack()

        # Search filter
        def _on_search(*_):
            q=self._tb_search.get().lower().strip()
            for frame,itype,lbl in all_items:
                if itype in("sec","content"): frame.pack(fill="x")
                elif itype=="btn":
                    if not q or q in lbl: frame.pack(fill="x")
                    else: frame.pack_forget()
            tc.configure(scrollregion=tc.bbox("all"))
        self._tb_search.trace_add("write",_on_search)

    def _switch_tb_tab(self, tab):
        self._tb_tab_var.set(tab); self._refresh_tb_tabs()

    def _refresh_tb_tabs(self):
        tab=self._tb_tab_var.get()
        for b,n in [(self._tb_comp_btn,"Components"),(self._tb_data_btn,"Data")]:
            try:
                if n==tab: b.config(bg="white",fg="#2563EB",font=("Helvetica",9,"bold"),relief="flat")
                else:      b.config(bg="#F8FAFC",fg="#111827",font=("Helvetica",9),relief="flat")
            except Exception: pass

    # ── CENTER PANEL: Canvas ───────────────────────────────────────────
    def _workspace(self, parent):
        self._workspace_frame = tk.Frame(parent, bg="#F1F5F9")
        self._workspace_frame.pack(side="left", fill="both", expand=True)
        mid = self._workspace_frame

        # Canvas toolbar
        ctb = tk.Frame(mid, bg="white",
                        highlightbackground="#1E293B", highlightthickness=1)
        ctb.pack(fill="x")

        # Screen size
        tk.Label(ctb,text="Screen",bg="white",fg="#111827",
                 font=("Helvetica",8)).pack(side="left",padx=(12,4))
        self._screen_var = tk.StringVar(value="Desktop (1920)")
        _sm = {"Desktop (1920)":(1920,1080,0),"Desktop (1280)":(1280,800,0),
               "Tablet (768)":(768,1024,0),"Mobile (390)":(390,844,0)}
        sc=ttk.Combobox(ctb,textvariable=self._screen_var,
                         values=list(_sm.keys()),state="readonly",
                         width=14,font=("Helvetica",9))
        sc.pack(side="left",padx=2,pady=6)
        def _on_screen(*_):
            s=self._screen_var.get()
            if s in _sm:
                w,h,sb=_sm[s]
                try: self._vp_w.set(w);self._vp_h.set(h);self._vp_sb.set(sb);self._draw_grid()
                except Exception: pass
        sc.bind("<<ComboboxSelected>>",_on_screen)

        # Device icons
        tk.Frame(ctb,bg="#1E293B",width=1).pack(side="left",fill="y",padx=8,pady=4)
        for ico,tip,val in [("🖥","Desktop","Desktop (1920)"),
                             ("📱","Tablet","Tablet (768)"),
                             ("📲","Mobile","Mobile (390)")]:
            b=tk.Button(ctb,text=ico,bg="white",fg="#111827",relief="flat",
                font=("Helvetica",11),padx=6,cursor="hand2",
                command=lambda v=val:(self._screen_var.set(v),_on_screen()))
            b.pack(side="left",padx=1,pady=6); Tooltip(b,tip)

        # Zoom
        tk.Frame(ctb,bg="#1E293B",width=1).pack(side="left",fill="y",padx=8,pady=4)
        tk.Button(ctb,text="−",bg="white",fg="#111827",relief="flat",
                  font=("Helvetica",11,"bold"),padx=6,cursor="hand2",
                  command=lambda:self._zoom_apply(round(self._canvas_zoom-0.25,2))
                  ).pack(side="left")
        self._zoom_label=tk.Label(ctb,text="100%",bg="white",fg="#111827",
                                   font=("Helvetica",9,"bold"),width=5)
        self._zoom_label.pack(side="left")
        tk.Button(ctb,text="+",bg="white",fg="#111827",relief="flat",
                  font=("Helvetica",11,"bold"),padx=6,cursor="hand2",
                  command=lambda:self._zoom_apply(round(self._canvas_zoom+0.25,2))
                  ).pack(side="left")

        # View Options
        tk.Frame(ctb,bg="#1E293B",width=1).pack(side="left",fill="y",padx=8,pady=4)
        self._vo_btn=tk.Button(ctb,text="⚙ View Options  ▾",bg="white",fg="#111827",
            relief="flat",font=("Helvetica",9),padx=10,cursor="hand2",
            command=self._show_view_options)
        self._vo_btn.pack(side="left",pady=6)

        # Show Grid + Snap toggles (right side)
        tk.Frame(ctb,bg="#1E293B",width=1).pack(side="right",fill="y",padx=8,pady=4)
        self._snap_var=tk.BooleanVar(value=True)
        tk.Label(ctb,text="Snap to Grid",bg="white",fg="#111827",
                 font=("Helvetica",8)).pack(side="right",padx=(0,4))
        tk.Checkbutton(ctb,variable=self._snap_var,bg="white",
                        activebackground="white").pack(side="right")
        tk.Frame(ctb,bg="#1E293B",width=1).pack(side="right",fill="y",padx=8,pady=4)
        self._show_grid_var=tk.BooleanVar(value=False)
        tk.Label(ctb,text="Show Grid",bg="white",fg="#111827",
                 font=("Helvetica",8)).pack(side="right",padx=(0,4))
        tk.Checkbutton(ctb,variable=self._show_grid_var,bg="white",
                        activebackground="white",command=self._draw_grid
                        ).pack(side="right")

        # Filter panel (collapsible, tucked away)
        fpw=tk.Frame(mid,bg="white",
                      highlightbackground="#1E293B",highlightthickness=1)
        fpw.pack(fill="x",padx=12,pady=(4,0))
        self._filter_visible=False
        fp_hdr=tk.Frame(fpw,bg="white"); fp_hdr.pack(fill="x")
        self._filter_toggle_btn=tk.Button(fp_hdr,text="▶  🔍  Filters",
            bg="white",fg="#111827",relief="flat",font=("Helvetica",8,"bold"),
            anchor="w",padx=10,pady=4,cursor="hand2",command=self._toggle_filter_panel)
        self._filter_toggle_btn.pack(side="left",fill="x",expand=True)
        Tooltip(self._filter_toggle_btn,
            "Add filter attributes shown in the filter panel.\n"
            "Each row = one filter input (date, dropdown, text, etc.).\n"
            "These become the filter-panel element in the exported fragment.")
        self._flist_wrap=tk.Frame(fpw,bg="white")
        self._flist=tk.Frame(self._flist_wrap,bg="white")
        self._flist.pack(fill="x",padx=8,pady=(4,6))

        # Canvas
        wrap=tk.Frame(mid,bg="white",
                       highlightbackground="#1E293B",highlightthickness=1)
        wrap.pack(fill="both",expand=True,padx=12,pady=(4,0))
        self._canvas_wrap=wrap
        self._cv=tk.Canvas(wrap,bg="#F0F4F8",highlightthickness=0)
        sy=ttk.Scrollbar(wrap,orient="vertical",  command=self._cv.yview)
        sx=ttk.Scrollbar(wrap,orient="horizontal",command=self._cv.xview)
        self._cv.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        sy.pack(side="right",fill="y"); sx.pack(side="bottom",fill="x")
        self._cv.pack(fill="both",expand=True)
        self._cf=tk.Frame(self._cv,bg="#F0F4F8")
        self._cfw=self._cv.create_window((0,0),window=self._cf,anchor="nw")
        self._cf.bind("<Configure>",
                       lambda e:self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Button-1>",lambda e:self._deselect())
        def _cvw(e):
            if e.delta==0: return "break"
            s=_wheel_scroll_units(e)
            if s==0: return "break"
            (self._cv.xview_scroll(s,"units") if e.state&0x1
             else self._cv.yview_scroll(s,"units"))
            return "break"
        for w in (self._cv,self._cf,self._canvas_wrap):
            w.bind("<Enter>",lambda e:self.bind_all("<MouseWheel>",_cvw))
            w.bind("<Leave>",lambda e:self.unbind_all("<MouseWheel>"))

        # Bottom breadcrumb + status bar
        bb=tk.Frame(mid,bg="#F8FAFC",
                     highlightbackground="#1E293B",highlightthickness=1)
        bb.pack(fill="x",padx=12,pady=(2,4))
        self._breadcrumb_var=tk.StringVar(value="Fragment")
        tk.Label(bb,textvariable=self._breadcrumb_var,bg="#F8FAFC",fg="#111827",
                 font=("Helvetica",8)).pack(side="left",padx=10,pady=3)
        self._err_var=tk.StringVar(value="")
        self._warn_var=tk.StringVar(value="")
        tk.Label(bb,textvariable=self._err_var,bg="#F8FAFC",fg="#16A34A",
                 font=("Helvetica",8,"bold")).pack(side="right",padx=8)
        tk.Label(bb,textvariable=self._warn_var,bg="#F8FAFC",fg="#D97706",
                 font=("Helvetica",8,"bold")).pack(side="right",padx=4)

        self.after(200,self._draw_grid)

    def _show_view_options(self):
        m=tk.Menu(self,tearoff=0,bg="white",fg="#111827",
                   activebackground="#EFF6FF",font=("Helvetica",9))
        m.add_checkbutton(label="Show Grid",     variable=self._show_grid_var,
                           command=self._draw_grid)
        m.add_checkbutton(label="Snap to Grid",  variable=self._snap_var)
        m.add_separator()
        m.add_command(label="↔ Reflow Layout",   command=self._do_import_layout)
        m.add_command(label="⚙️ Layout Settings", command=self._edit_css)
        m.add_command(label="📦 Segments",        command=self._manage_segments)
        m.add_separator()
        m.add_command(label="Viewport 1920×1080",
            command=lambda:(self._vp_w.set(1920),self._vp_h.set(1080),self._draw_grid()))
        m.add_command(label="Viewport 1280×800",
            command=lambda:(self._vp_w.set(1280),self._vp_h.set(800),self._draw_grid()))
        try:
            x=self._vo_btn.winfo_rootx()
            y=self._vo_btn.winfo_rooty()+self._vo_btn.winfo_height()
            m.tk_popup(x,y)
        except Exception:
            m.tk_popup(self.winfo_pointerx(),self.winfo_pointery())
        finally:
            m.grab_release()

    # ── RIGHT PANEL: Properties ─────────────────────────────────────────
    def _properties_panel(self, parent):
        rp=tk.Frame(parent,bg="#F8FAFC",width=300,
                     highlightbackground="#E2E8F0",highlightthickness=1)
        rp.pack(side="right",fill="y"); rp.pack_propagate(False)
        self._rp_frame=rp

        # Tabs
        tabs_f=tk.Frame(rp,bg="white"); tabs_f.pack(fill="x")
        self._rp_tab_var=tk.StringVar(value="Properties")
        self._rp_tab_btns={}
        for t in ("Properties","Events","Styles"):
            b=tk.Button(tabs_f,text=t,relief="flat",cursor="hand2",
                font=("Helvetica",9),pady=8,
                command=lambda tv=t:self._switch_rp_tab(tv))
            b.pack(side="left",fill="x",expand=True)
            self._rp_tab_btns[t]=b
        tk.Frame(rp,bg="#2563EB",height=2).pack(fill="x")
        self._refresh_rp_tabs()

        # Selected component header
        sel_hdr=tk.Frame(rp,bg="#F8FAFC",
                          highlightbackground="#E2E8F0",highlightthickness=1)
        sel_hdr.pack(fill="x")
        tk.Label(sel_hdr,text="Selected Component",bg="#F8FAFC",fg="#374151",
                 font=("Helvetica",8,"bold")).pack(anchor="w",padx=12,pady=(6,0))
        self._rp_comp_name=tk.Label(sel_hdr,text="—",bg="#F8FAFC",fg="#111827",
                                     font=("Helvetica",11,"bold"))
        self._rp_comp_name.pack(anchor="w",padx=12,pady=(2,6))

        # Basic / Advanced toggle
        mf=tk.Frame(rp,bg="white"); mf.pack(fill="x",padx=12,pady=(6,2))
        self._rp_mode_var=tk.StringVar(value="Basic")
        self._rp_mode_btns=[]
        for mv in ("Basic","Advanced"):
            b=tk.Button(mf,text=mv,bg="#E5E7EB",fg="#374151",relief="flat",
                cursor="hand2",font=("Helvetica",9,"bold"),padx=14,pady=4,
                command=lambda m=mv:self._switch_rp_mode(m))
            b.pack(side="left",padx=(0,2)); self._rp_mode_btns.append(b)
        self._switch_rp_mode("Basic")

        # Scrollable body
        pc=tk.Canvas(rp,bg="white",highlightthickness=0)
        psb=ttk.Scrollbar(rp,orient="vertical",command=pc.yview)
        pc.configure(yscrollcommand=psb.set)
        psb.pack(side="right",fill="y"); pc.pack(side="left",fill="both",expand=True)
        pc.bind("<MouseWheel>",
                lambda e:pc.yview_scroll(_wheel_scroll_units(e),"units"))
        self._rp_body=tk.Frame(pc,bg="white")
        rp_win=pc.create_window((0,0),window=self._rp_body,anchor="nw")
        self._rp_body.bind("<Configure>",
                            lambda e:pc.configure(scrollregion=pc.bbox("all")))
        pc.bind("<Configure>",lambda e:pc.itemconfig(rp_win,width=e.width))
        self._rp_canvas=pc
        self._rp_current_card=None
        # Empty state
        tk.Label(self._rp_body,
                  text="Select a component\non the canvas\nto edit its properties.",
                  bg="white",fg="#374151",font=("Helvetica",10),
                  justify="center",pady=40).pack()

    def _switch_rp_tab(self,tab):
        self._rp_tab_var.set(tab); self._refresh_rp_tabs()
        card = getattr(self, '_rp_current_card', None)
        if card: self._update_properties_panel(card)

    def _switch_rp_mode(self,mode):
        self._rp_mode_var.set(mode)
        try:
            for b in self._rp_mode_btns:
                if b["text"]==mode:
                    b.config(bg="#374151", fg="black")   # active: dark grey, black text
                else:
                    b.config(bg="#E5E7EB", fg="#374151")  # inactive: light grey, dark text
        except Exception: pass
        card = getattr(self, '_rp_current_card', None)
        if card: self._update_properties_panel(card)

    def _refresh_rp_tabs(self):
        tab=self._rp_tab_var.get()
        for t,b in self._rp_tab_btns.items():
            try:
                if t==tab: b.config(bg="white",fg="#2563EB",font=("Helvetica",9,"bold"))
                else:      b.config(bg="#F8FAFC",fg="#111827",font=("Helvetica",9))
            except Exception: pass

    def _update_properties_panel(self, card):
        self._rp_current_card=card
        ico=COMP_COLORS.get(card.ctype,("#374151","◻"))[1]
        try: self._rp_comp_name.config(text=f"{ico}  {card.title or card.ctype}")
        except Exception: pass
        try:
            seg=f" › {card.segment}" if card.segment else ""
            self._breadcrumb_var.set(f"Fragment  ›  {card.ctype}{seg}  ({card.cid})")
        except Exception: pass
        for w in self._rp_body.winfo_children(): w.destroy()
        tab=self._rp_tab_var.get(); mode=self._rp_mode_var.get()
        if tab=="Properties":   self._build_props_section(card,mode)
        elif tab=="Events":     self._build_events_section(card)
        elif tab=="Styles":     self._build_styles_section(card)
        try: self._rp_canvas.configure(scrollregion=self._rp_canvas.bbox("all"))
        except Exception: pass

    def _sec_hdr(self,parent,label):
        f=tk.Frame(parent,bg="white"); f.pack(fill="x",pady=(8,0))
        tk.Label(f,text=label,bg="#F8FAFC",fg="#111827",
                 font=("Helvetica",9,"bold"),padx=12,pady=4,anchor="w").pack(fill="x")
        tk.Frame(f,bg="#1E293B",height=1).pack(fill="x")

    def _prop_row(self,parent,label,var,choices=None,tip=""):
        f=tk.Frame(parent,bg="white"); f.pack(fill="x",padx=12,pady=2)
        tk.Label(f,text=label,bg="white",fg="#111827",
                 font=("Helvetica",8),anchor="w").pack(anchor="w")
        if choices:
            w=ttk.Combobox(f,textvariable=var,values=choices,
                            state="readonly",font=("Helvetica",9))
        else:
            w=ttk.Entry(f,textvariable=var,font=("Helvetica",9))
        w.pack(fill="x",pady=(1,0))
        if tip: Tooltip(w,tip)
        return w

    def _build_props_section(self,card,mode):
        self._sec_hdr(self._rp_body,"Component Details")
        title_var=tk.StringVar(value=card.title)
        self._prop_row(self._rp_body,"Title",title_var)
        ds_var = tk.StringVar(value=card.ds)
        bv_var = tk.StringVar(value=card.bvar)
        _pool_keys  = self._get_pool_ds_keys()
        _bvar_map   = self._get_pool_bvar_map()
        if card.ctype in CHART_TYPES or card.ctype == "table":
            # Data Source — Combobox fed from variable pool
            ds_f = tk.Frame(self._rp_body, bg="white")
            ds_f.pack(fill="x", padx=12, pady=2)
            tk.Label(ds_f, text="Data Source", bg="white", fg="#111827",
                     font=("Helvetica",8), anchor="w").pack(anchor="w")
            ds_row = tk.Frame(ds_f, bg="white"); ds_row.pack(fill="x")
            pool_tip = ("DataSourcePath — must match a key in the Action JSON dataMap.\n"
                        "Import Action JSON via  🗃 Variable Pool  in the toolbar\n"
                        "to populate these choices automatically.")
            ds_cb = ttk.Combobox(ds_row, textvariable=ds_var,
                                  values=_pool_keys or [card.ds],
                                  font=("Helvetica",9))
            ds_cb.pack(side="left", fill="x", expand=True)
            Tooltip(ds_cb, pool_tip)
            pool_count = len(self._var_pool)
            pool_lbl_text = f"  🗃 {pool_count} in pool" if pool_count else "  (load 🗃 pool)"
            pool_lbl_color = "#16A34A" if pool_count else "#9CA3AF"
            tk.Label(ds_row, text=pool_lbl_text, bg="white", fg=pool_lbl_color,
                     font=("Helvetica",7), cursor="hand2"
                     ).pack(side="left", padx=2)

            def _on_ds_select(event=None, _dv=ds_var, _bv=bv_var, _m=_bvar_map):
                ds = _dv.get().strip()
                if ds in _m and not _bv.get():
                    _bv.set(_m[ds])
                elif ds and not _bv.get():
                    _bv.set(f"object::{ds}Js.result")

            ds_cb.bind("<<ComboboxSelected>>", _on_ds_select)
            ds_var.trace_add("write", lambda *_: _on_ds_select())

            # Backend Variable — Combobox fed from pool values
            bv_f = tk.Frame(self._rp_body, bg="white")
            bv_f.pack(fill="x", padx=12, pady=2)
            tk.Label(bv_f, text="Backend Variable", bg="white", fg="#111827",
                     font=("Helvetica",8), anchor="w").pack(anchor="w")
            bv_cb = ttk.Combobox(bv_f, textvariable=bv_var,
                                   values=sorted(set(_bvar_map.values())) or [card.bvar],
                                   font=("Helvetica",9))
            bv_cb.pack(fill="x")
            Tooltip(bv_cb, "EFW output variable that supplies data to this component.\n"
                            "Format: object::{Key}Js.result\n"
                            "Auto-filled when you select a Data Source from the pool.")

        self._sec_hdr(self._rp_body,"Size & Layout")
        w_var=tk.StringVar(value=card.css_width)
        h_var=tk.StringVar(value=card.css_height)
        wr=tk.Frame(self._rp_body,bg="white"); wr.pack(fill="x",padx=12,pady=2)
        wf=tk.Frame(wr,bg="white"); wf.pack(side="left",fill="x",expand=True,padx=(0,4))
        hf=tk.Frame(wr,bg="white"); hf.pack(side="left",fill="x",expand=True)
        tk.Label(wf,text="Width",bg="white",fg="#111827",font=("Helvetica",8)).pack(anchor="w")
        tk.Label(hf,text="Height",bg="white",fg="#111827",font=("Helvetica",8)).pack(anchor="w")
        ttk.Combobox(wf,textvariable=w_var,
            values=["auto","100%","50%","calc(50% - 16px)","380px","480px","600px","800px"],
            font=("Helvetica",9)).pack(fill="x")
        ttk.Combobox(hf,textvariable=h_var,
            values=["auto","300px","400px","500px","600px","100%"],
            font=("Helvetica",9)).pack(fill="x")
        Tooltip(wr,"Width/Height in CSS units.\n'auto'=content-based, '100%'=fill, or fixed px.")

        sg_var=tk.StringVar(value=card.segment or "Default")
        dir_var=tk.StringVar(value=(self.segment_dirs.get(card.segment,{})
                                    .get("direction","row")).title())
        gap_var=tk.StringVar(value=self.segment_dirs.get(card.segment,{})
                                    .get("gap","16px"))
        sr=tk.Frame(self._rp_body,bg="white"); sr.pack(fill="x",padx=12,pady=2)
        sf_=tk.Frame(sr,bg="white"); sf_.pack(side="left",fill="x",expand=True,padx=(0,4))
        df_=tk.Frame(sr,bg="white"); df_.pack(side="left",fill="x",expand=True,padx=(0,4))
        gf_=tk.Frame(sr,bg="white"); gf_.pack(side="left",fill="x",expand=True)
        for f_,l_ in [(sf_,"Segment"),(df_,"Direction"),(gf_,"Gap")]:
            tk.Label(f_,text=l_,bg="white",fg="#111827",font=("Helvetica",8)).pack(anchor="w")
        segs=["Default"]+list(self.segment_dirs.keys())
        ttk.Combobox(sf_,textvariable=sg_var,values=segs,font=("Helvetica",9),width=8).pack(fill="x")
        ttk.Combobox(df_,textvariable=dir_var,values=["Row","Column"],
                      state="readonly",font=("Helvetica",9),width=6).pack(fill="x")
        ttk.Combobox(gf_,textvariable=gap_var,
                      values=["0","4px","8px","12px","16px","24px"],
                      font=("Helvetica",9),width=5).pack(fill="x")
        Tooltip(sr,"Segment: layout group.\nDirection: row or column.\n"
                   "Gap: spacing between siblings.\n"
                   "Tip: '1fr 1fr' in Layout Settings = two equal columns.")

        def _apply():
            card.title=title_var.get().strip()
            card.css_width=w_var.get().strip(); card.css_height=h_var.get().strip()
            ns=sg_var.get().strip()
            card.segment="" if ns=="Default" else ns
            if ns and ns!="Default":
                self.segment_dirs.setdefault(ns,{}).update(
                    {"direction":dir_var.get().lower(),"gap":gap_var.get().strip()})
            if card.ctype in CHART_TYPES:
                card.ds=ds_var.get().strip(); card.bvar=bv_var.get().strip()
            # Mark card as config-edited so export reflects these changes
            card._config_edited = True
            try: card._preview()
            except Exception: pass
            self.after(80,self._draw_grid)
            self._update_properties_panel(card)

        tk.Button(self._rp_body,text="Apply Changes",bg=BTN_OK_BG, fg=BTN_OK_FG,
                  relief="flat",font=("Helvetica",9,"bold"),padx=12,pady=6,
                  cursor="hand2",command=_apply).pack(fill="x",padx=12,pady=(8,4))

        if mode=="Advanced":
            tk.Button(self._rp_body,text="✏️  Open Full Edit Dialog",bg="#F1F5F9",
                      fg="#111827",relief="flat",font=("Helvetica",9),padx=12,pady=5,
                      cursor="hand2",command=lambda:card._edit()
                      ).pack(fill="x",padx=12,pady=2)

        self._sec_hdr(self._rp_body,"Live Preview")
        pf=tk.Frame(self._rp_body,bg="#F8FAFC"); pf.pack(fill="x",padx=12,pady=(4,8))
        try:
            pc=CompCard(pf,"rp_prev",card.ctype,card.title,card.ds,card.bvar,self,
                width=256,height=130,css_width=card.css_width,css_height=card.css_height)
            pc.pack(padx=4,pady=4); self.update_idletasks(); pc._preview()
        except Exception:
            tk.Label(pf,text="(preview not available)",bg="#F8FAFC",fg="#374151",
                     font=("Helvetica",8),pady=14).pack()
        tk.Label(self._rp_body,text="Changes you make are applied in real-time.",
                 bg="white",fg="#374151",font=("Helvetica",7),pady=4).pack()

    def _build_events_section(self,card):
        self._sec_hdr(self._rp_body,"Events & Interactions")
        tk.Button(self._rp_body,text="✏️  Edit Events / Links",bg="#F1F5F9",fg="#111827",
                  relief="flat",font=("Helvetica",9),padx=12,pady=6,cursor="hand2",
                  command=lambda:card._edit()).pack(fill="x",padx=12,pady=8)
        tk.Label(self._rp_body,
                  text="Configure OnClick, event listeners\nand navigation links\nin the full edit dialog.",
                  bg="white",fg="#374151",font=("Helvetica",9),justify="left",pady=4
                  ).pack(anchor="w",padx=12)

    def _build_styles_section(self,card):
        self._sec_hdr(self._rp_body,"CSS Overrides")
        css=getattr(card,"extra_css",{}) or {}
        self._style_vars = {}
        for prop in ["flex","width","height","minHeight","overflow",
                     "background","backgroundColor","color","border","borderColor","borderRadius","padding",
                     "gap","alignItems","justifyContent","boxShadow"]:
            var=tk.StringVar(value=css.get(prop,""))
            self._style_vars[prop] = var
            self._prop_row(self._rp_body,prop,var,
                            tip=f"CSS property: {prop}")
        
        # Table-specific color properties
        if card.ctype == "table":
            self._sec_hdr(self._rp_body,"Table Colors")
            table_style = getattr(card, 'table_style', {}) or {}
            self._table_style_vars = {}
            for prop in ["textColor","rowEvenBackgroundColor","rowOddBackgroundColor",
                         "headerBackgroundColor","tableBorderColor","hoverBackgroundColor"]:
                var=tk.StringVar(value=table_style.get(prop,""))
                self._table_style_vars[prop] = var
                self._prop_row(self._rp_body,prop,var,
                                tip=f"Table Style property: {prop}")
        
        # Apply button for styles
        def _apply_styles():
            # Save CSS properties
            if not hasattr(card, 'extra_css'):
                card.extra_css = {}
            for prop, var in self._style_vars.items():
                val = var.get().strip()
                if val:
                    card.extra_css[prop] = val
                elif prop in card.extra_css:
                    del card.extra_css[prop]
            # Save table-specific color properties
            if card.ctype == "table" and hasattr(self, '_table_style_vars'):
                if not hasattr(card, 'table_style'):
                    card.table_style = {}
                for prop, var in self._table_style_vars.items():
                    val = var.get().strip()
                    if val:
                        card.table_style[prop] = val
                    elif prop in card.table_style:
                        del card.table_style[prop]
            # Mark card as edited
            card._config_edited = True
            try: card._preview()
            except Exception: pass
            self.after(80,self._draw_grid)
            self._update_properties_panel(card)
        
        tk.Button(self._rp_body,text="Apply Style Changes",bg=BTN_OK_BG, fg=BTN_OK_FG,
                  relief="flat",font=("Helvetica",9,"bold"),padx=12,pady=6,
                  cursor="hand2",command=_apply_styles).pack(fill="x",padx=12,pady=(8,4))

    def _build_skeleton_fragment(self):
        """
        Build a minimal fragment JSON from the current V5 canvas cards/segments,
        suitable for V6-style layout computation.
        Returns (fragment_root_dict, cid_to_node_map).
        cid_to_node_map maps card.cid → the fragment node dict for that card.
        """
        cid_map: dict = {}
        gap = self.layout_prefs.get("gap", "16px")

        cards_sorted = sorted(
            [c for c in self.cards.values() if not getattr(c, '_tg_parent', None)],
            key=lambda c: (c.winfo_y(), c.winfo_x()))

        seg_card_groups: dict = {}
        for c in cards_sorted:
            if c.segment:
                seg_card_groups.setdefault(c.segment, []).append(c)

        seen_segs: set = set()
        output_blocks: list = []
        cur_row: list = []
        row_anchor_y = None
        ROW_THRESHOLD = 200

        def _flush():
            if cur_row:
                output_blocks.append(("row", list(cur_row)))
                cur_row.clear()

        for card in cards_sorted:
            if card.segment:
                if card.segment not in seen_segs:
                    _flush(); seen_segs.add(card.segment)
                    output_blocks.append(("seg", card.segment))
            else:
                y = card.winfo_y()
                if not cur_row:
                    cur_row.append(card); row_anchor_y = y
                elif y - row_anchor_y < ROW_THRESHOLD:
                    cur_row.append(card)
                else:
                    _flush(); cur_row.append(card); row_anchor_y = y
        _flush()

        def _card_node(card):
            ctype_map = {
                "table": "table", "chart": "chart", "search": "search",
                "segment-panel": "segment-panel", "metrics": "table",
                "filter-panel": "flex", "header-action": "header-action",
            }
            ct   = ctype_map.get(card.ctype, "flex")
            node = {"Container": ct, "_cid": card.cid}
            # Build CSS from card's configured sizes
            css = {}
            extra = getattr(card, 'extra_css', {}) or {}
            for k, v in extra.items():
                if v: css[k] = v
            cw = getattr(card, 'css_width', 'auto')
            ch = getattr(card, 'css_height', 'auto')
            if cw and cw not in ('auto', '100%', ''):
                css.setdefault('width', cw)
            if ch and ch not in ('auto', ''):
                css.setdefault('height', ch)
            # Locked types: add flex:0 0 auto so they don't stretch
            if ct in _AF_LOCKED_CONTAINERS and 'flex' not in css:
                if 'height' in css: css['flex'] = '0 0 auto'
            if css:
                node['Style'] = {'css': css}
            if card.title:
                node['Config'] = {'title': card.title}
            node['Slots'] = {}
            cid_map[card.cid] = node
            return node

        layout_slots: list = []
        for block_type, block_data in output_blocks:
            if block_type == "seg":
                sn  = block_data
                cfg = self.segment_dirs.get(sn, {"direction": "row", "gap": "0px"})
                sc  = [c for c in seg_card_groups.get(sn, [])
                       if c.ctype != "filter-panel"]
                if not sc: continue
                seg_nodes = [_card_node(c) for c in sc]
                dirn  = cfg.get("direction", "row")
                sgap  = cfg.get("gap", "0px")
                scss  = {"flexDirection": dirn, "gap": sgap}
                if cfg.get("expand_fill"):
                    scss.update({"flex": "1", "minHeight": "0",
                                 "overflow": "hidden"})
                    if dirn == "row":
                        sh = cfg.get("segment_height", "")
                        if sh: scss["height"] = sh
                else:
                    sh = cfg.get("segment_height", "")
                    if sh: scss["height"] = sh
                ct = cfg.get("container_type", "flex")
                if ct not in ("flex", "grid", "header-action"): ct = "flex"
                seg_node = {"Container": ct, "Style": {"css": scss},
                            "Slots": {"Default": seg_nodes}}
                layout_slots.append(seg_node)
            else:  # "row"
                row_nodes = [_card_node(c) for c in block_data]
                if len(row_nodes) == 1:
                    layout_slots.append(row_nodes[0])
                else:
                    layout_slots.append({
                        "Container": "flex",
                        "Style": {"css": {"flexDirection": "row", "gap": gap,
                                          "flex": "0 0 auto"}},
                        "Slots": {"Default": row_nodes},
                    })

        fragment = {
            "Fragment": {
                "Container": "flex",
                "Style": {"css": {"flexDirection": "column", "gap": gap,
                                  "height": "100%", "overflow": "hidden"}},
                "Slots": {"Default": layout_slots},
            }
        }
        return fragment, cid_map

    # ── V6-style schematic box renderer (for _draw_grid background) ───────────
    def _draw_schematic_on_bg(self, bg, node, x, y, w, h, selected_cid=None):
        """Draw one schematic box on the background canvas (matches V6 style)."""
        ctype = node.get("Container", "")
        cid   = node.get("_cid", "")
        fill, border = _AF_SCHEMATIC_COLORS.get(ctype or "default",
                                                  _AF_SCHEMATIC_COLORS["default"])
        is_flex   = (ctype == "flex")
        is_sel    = (cid and cid == selected_cid)
        if is_sel and is_flex:
            bg.create_rectangle(x, y, x+w, y+h, fill=fill,
                                 outline="#ef4444", width=3, dash=(8,3))
        elif is_sel:
            bg.create_rectangle(x, y, x+w, y+h, fill=fill,
                                 outline="#f59e0b", width=2)
        elif is_flex:
            bg.create_rectangle(x, y, x+w, y+h, fill=fill,
                                 outline=border, width=1, dash=(6,3))
        elif ctype in _AF_LOCKED_CONTAINERS:
            bg.create_rectangle(x, y, x+w, y+h, fill=fill,
                                 outline=border, width=1)
        else:
            bg.create_rectangle(x, y, x+w, y+h, fill=fill,
                                 outline=border, width=1)
        # Label inside the box
        cfg   = node.get("Config") or {}
        title = cfg.get("title") or cfg.get("LabelKey") or ""
        label = ctype + (f' "{title}"' if title else "")
        css   = (node.get("Style") or {}).get("css") or {}
        dims  = "  ".join(f"{k}:{css[k]}" for k in ("flex","width","height")
                          if css.get(k))
        if h >= 14:
            bg.create_text(x + w/2, y + min(10, h/2), text=label[:36],
                           fill="#111827",
                           font=("TkDefaultFont", max(int(min(w/12, h/2, 9)), 6), "bold"),
                           width=max(w-4, 4), anchor="n")
        if dims and h >= 26:
            bg.create_text(x + w/2, y + min(22, h/2+10), text=dims[:42],
                           fill="#1d4ed8",
                           font=("Courier", max(int(min(w/16, 7)), 5)),
                           width=max(w-4, 4), anchor="n")

    # ── main canvas draw ───────────────────────────────────────────────────────
    def _draw_grid(self):
        z    = getattr(self, '_canvas_zoom', 1.0)
        W, H = int(3000 * z), int(2000 * z)
        self._cf.config(width=W, height=H)
        self._cv.configure(scrollregion=(0, 0, W, H))
        if self._bg_canvas:
            try: self._bg_canvas.destroy()
            except: pass
        bg = tk.Canvas(self._cf, width=W, height=H,
                        bg="#F0F4F8", highlightthickness=0)
        bg.place(x=0, y=0)

        # ── Screen boundary values ─────────────────────────────────────
        try:
            vw    = max(200, self._vp_w.get())
            vh    = max(100, self._vp_h.get())
            sb_pct = max(0, min(50, self._vp_sb.get()))
        except Exception:
            vw, vh, sb_pct = 1920, 1080, 0

        svw      = int(vw * z);    svh    = int(vh * z)
        nav_h    = int(50 * z)
        sb_w     = int(vw * sb_pct / 100 * z)
        content_x = sb_w
        content_y = nav_h
        content_cw = svw - sb_w          # canvas pixels wide for content area
        content_ch = svh - nav_h         # canvas pixels tall for content area

        # ── Tint outside-screen area ───────────────────────────────────
        if svw < W:
            bg.create_rectangle(svw, 0, W, H, fill="#CBD5E1", outline="", stipple="gray25")
        if svh < H:
            bg.create_rectangle(0, svh, W, H, fill="#CBD5E1", outline="", stipple="gray25")

        # ── Navbar strip ───────────────────────────────────────────────
        bg.create_rectangle(0, 0, svw, nav_h, fill="#E0E7FF", outline="", stipple="gray25")
        bg.create_line(0, nav_h, svw, nav_h, fill="#6366F1", width=1, dash=(8,4))
        bg.create_text(8, nav_h//2, text="↕ Navbar ~50px",
                        anchor="w", fill="#6366F1", font=("Helvetica", 8))

        # ── Sidebar strip ─────────────────────────────────────────────
        if sb_pct > 0:
            bg.create_rectangle(0, nav_h, sb_w, svh,
                                  fill="#FEF3C7", outline="", stipple="gray25")
            bg.create_line(sb_w, nav_h, sb_w, svh,
                            fill="#D97706", width=2, dash=(10,5))
            bg.create_text(sb_w//2, nav_h+14,
                            text=f"Sidebar {sb_pct}vw",
                            fill="#92400E", font=("Helvetica", 8, "bold"))

        # ── V6-style fragment schematic on the content area ────────────
        sel_cid = (self._sel.cid if self._sel else None)
        if self.cards:
            try:
                frag, cid_map = self._build_skeleton_fragment()
                frag_root     = frag.get("Fragment", {})
                # Virtual space = content area in logical px
                virt_w = vw - int(vw * sb_pct / 100)
                virt_h = vh - 50
                items  = _af_compute_layout_tree(
                    frag_root, 0, 0, virt_w, virt_h, "Fragment")
                sx = content_cw / max(virt_w, 1)
                sy = content_ch / max(virt_h, 1)
                for node, vx, vy, nvw, nvh, _path in items:
                    cx2 = content_x + vx * sx
                    cy2 = content_y + vy * sy
                    cw2 = max(nvw * sx, 2)
                    ch2 = max(nvh * sy, 2)
                    self._draw_schematic_on_bg(bg, node, cx2, cy2, cw2, ch2, sel_cid)
                    # ── reposition the CompCard to match its schematic box ──
                    cid = node.get("_cid")
                    if cid and cid in self.cards:
                        card = self.cards[cid]
                        card.place(x=int(cx2), y=int(cy2))
                        new_w = max(60, int(cw2))
                        new_h = max(40, int(ch2))
                        card.configure(width=new_w, height=new_h)
                        try:
                            card.dim_label.config(
                                text=f"{card.css_width} × {card.css_height}")
                        except Exception:
                            pass
            except Exception as exc:
                # Fall back to light grid if schematic fails
                self._draw_blueprint_grid(bg, W, H, z)

        else:
            # No cards: draw a helpful blueprint hint
            self._draw_blueprint_grid(bg, W, H, z)

        # ── Screen edge markers ────────────────────────────────────────
        bg.create_rectangle(content_x, nav_h, svw, svh,
                              fill="", outline="#16A34A", width=2)
        bg.create_text(content_x + content_cw//2, nav_h + 12,
                        text=f"Content  {virt_w if self.cards else vw}×{vh-50}px",
                        fill="#15803D", font=("Helvetica", 8, "bold"))
        bg.create_line(svw, 0, svw, H, fill="#EF4444", width=2, dash=(12,6))
        bg.create_line(0, svh, W, svh, fill="#EF4444", width=2, dash=(12,6))
        bg.create_rectangle(svw-84, 2, svw-2, 18, fill="#FEE2E2", outline="#EF4444")
        bg.create_text(svw-43, 10, text=f"Screen {vw}px",
                        fill="#DC2626", font=("Helvetica", 7, "bold"))

        bg.tk.call('lower', bg._w)
        self._bg_canvas = bg
        bg.bind("<ButtonPress-1>",   self._rb_press)
        bg.bind("<B1-Motion>",       self._rb_drag)
        bg.bind("<ButtonRelease-1>", self._rb_release)
        self.after(50, self._draw_gap_overlay)
        # Push live preview update (debounced 400 ms so rapid drags don't flood)
        self._schedule_live_preview_push()

    def _schedule_live_preview_push(self):
        """Debounce: push new HTML to the live preview server 400 ms after last canvas change."""
        if not getattr(self, '_live_preview_server', None): return
        if hasattr(self, '_live_preview_push_job'):
            try: self.after_cancel(self._live_preview_push_job)
            except Exception: pass
        self._live_preview_push_job = self.after(400, self._push_live_preview)

    def _push_live_preview(self):
        """Generate fresh HTML from current fragment and push to the live server."""
        srv = getattr(self, '_live_preview_server', None)
        if not srv: return
        try:
            frag = self._build_fragment()
            html = self._build_preview_html(json.dumps(frag, indent=2))
            html = self._inject_live_reload_script(html, srv)
            srv.update(html)
        except Exception:
            pass   # silent — canvas might be mid-edit

    @staticmethod
    def _inject_live_reload_script(html, srv):
        """Inject a 400 ms polling script into the HTML so the browser auto-reloads."""
        script = (
            "<script>\n"
            "(function(){\n"
            "  var lv=null;\n"
            "  function poll(){\n"
            "    fetch('/version').then(function(r){return r.text();}).then(function(v){\n"
            "      if(lv===null){lv=v;}else if(v!==lv){lv=v;location.reload();}\n"
            "    }).catch(function(){});\n"
            "  }\n"
            "  setInterval(poll,400);\n"
            "})();\n"
            "</script>\n"
        )
        return html.replace("</body>", script + "</body>", 1) if "</body>" in html else html + script

    def _draw_blueprint_grid(self, bg, W, H, z):
        """Fallback: subtle grid lines when no cards are present."""
        step = max(1, int(GX * z))
        for x in range(0, W, step):
            bg.create_line(x, 0, x, H, fill="#1E293B", width=1)
        for y in range(0, H, step):
            bg.create_line(0, y, W, y, fill="#1E293B", width=1)
        for x_log in range(0, int(W/z)+1, 100):
            x_sc = int(x_log * z)
            if x_sc >= W: break
            bg.create_text(x_sc+4, 4, text=f"{x_log}px",
                            anchor="nw", fill="#94A3B8", font=("Helvetica", 8))
        for y_log in range(100, int(H/z)+1, 100):
            y_sc = int(y_log * z)
            if y_sc >= H: break
            bg.create_text(4, y_sc+4, text=f"{y_log}px",
                            anchor="nw", fill="#94A3B8", font=("Helvetica", 8))

    def _zoom_apply(self, new_zoom):
        new_zoom = max(0.25, min(3.0, new_zoom))
        old_zoom = self._canvas_zoom
        if abs(new_zoom - old_zoom) < 0.01:
            return
        ratio = new_zoom / old_zoom
        self._canvas_zoom = new_zoom
        self.update_idletasks()
        for card in self.cards.values():
            cx = int(card.winfo_x() * ratio)
            cy = int(card.winfo_y() * ratio)
            cw = max(80, int((card.winfo_width() or 400) * ratio))
            ch = max(60, int((card.winfo_height() or 300) * ratio))
            card.place(x=cx, y=cy)
            card.configure(width=cw, height=ch)
        self._draw_grid()   # sizes canvas frame + scrollregion + boundary overlay
        try:
            self._zoom_label.config(text=f"{int(new_zoom * 100)}%")
        except Exception:
            pass

    def _draw_gap_overlay(self):
        """Draw coloured gap bands + px labels between cards in each segment
        (blue) and between layout blocks (amber)."""
        if not self._bg_canvas:
            return
        self.update_idletasks()   # ensure all widget positions are current
        self._bg_canvas.delete("gap_overlay")
        # ── Intra-segment gaps (blue) ─────────────────────────────────────
        for seg, cfg in self.segment_dirs.items():
            direction = cfg.get("direction", "row")
            sc = [c for c in self.cards.values() if c.segment == seg]
            if len(sc) < 2:
                continue
            sc = sorted(sc, key=lambda c: (c.winfo_x() if direction == "row" else c.winfo_y()))
            for i in range(len(sc) - 1):
                c1, c2 = sc[i], sc[i + 1]
                if direction == "row":
                    x1 = c1.winfo_x() + c1.winfo_width()
                    x2 = c2.winfo_x()
                    y1 = min(c1.winfo_y(), c2.winfo_y())
                    y2 = max(c1.winfo_y() + c1.winfo_height(),
                             c2.winfo_y() + c2.winfo_height())
                else:
                    x1 = min(c1.winfo_x(), c2.winfo_x())
                    x2 = max(c1.winfo_x() + c1.winfo_width(),
                             c2.winfo_x() + c2.winfo_width())
                    y1 = c1.winfo_y() + c1.winfo_height()
                    y2 = c2.winfo_y()
                if x2 > x1 and y2 > y1:
                    gap_px = (x2 - x1) if direction == "row" else (y2 - y1)
                    self._bg_canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#DBEAFE", outline="#93C5FD",
                        width=1, tags="gap_overlay")
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    self._bg_canvas.create_rectangle(
                        mx - 20, my - 8, mx + 20, my + 8,
                        fill="white", outline="#93C5FD", tags="gap_overlay")
                    self._bg_canvas.create_text(
                        mx, my, text=f"{gap_px}px", fill="#1D4ED8",
                        font=("Helvetica", 7, "bold"), tags="gap_overlay")

        # ── Layout padding band (amber edge band showing outer wrapper padding) ──
        lpad = self._parse_gap_px(self.layout_prefs.get("padding", "0px"))
        if lpad > 0 and self.cards:
            try:
                all_cx = [c.winfo_x() + max(1, c.winfo_width()) for c in self.cards.values()]
                x_right = max(all_cx) if all_cx else 800
                all_cy = [c.winfo_y() + max(1, c.winfo_height()) for c in self.cards.values()]
                y_bot   = max(all_cy) if all_cy else 600
                PFILL, PSTIP = "#FEF3C7", "gray12"
                # Top band
                self._bg_canvas.create_rectangle(
                    0, 0, x_right + lpad, lpad,
                    fill=PFILL, outline="#F59E0B", stipple=PSTIP, tags="gap_overlay")
                # Left band
                self._bg_canvas.create_rectangle(
                    0, 0, lpad, y_bot + lpad,
                    fill=PFILL, outline="#F59E0B", stipple=PSTIP, tags="gap_overlay")
                # Right band
                self._bg_canvas.create_rectangle(
                    x_right, 0, x_right + lpad, y_bot + lpad,
                    fill=PFILL, outline="#F59E0B", stipple=PSTIP, tags="gap_overlay")
                # Bottom band
                self._bg_canvas.create_rectangle(
                    0, y_bot, x_right + lpad, y_bot + lpad,
                    fill=PFILL, outline="#F59E0B", stipple=PSTIP, tags="gap_overlay")
                self._bg_canvas.create_text(
                    lpad // 2, lpad // 2, text=f"{lpad}px",
                    fill="#B45309", font=("Helvetica", 7, "bold"), tags="gap_overlay")
            except Exception:
                pass

        # ── Inter-block gaps (amber) ──────────────────────────────────
        blocks = self._get_layout_block_bounds()
        if len(blocks) >= 2 and self.cards:
            # x-span: from canvas left margin to rightmost card edge
            all_cx = [c.winfo_x() + max(1, c.winfo_width()) for c in self.cards.values()]
            x_right = max(all_cx) if all_cx else 800
            for i in range(len(blocks) - 1):
                y1_bot = blocks[i][1]
                y2_top = blocks[i + 1][0]
                if y2_top - y1_bot > 0:
                    gap_px = y2_top - y1_bot
                    x1, x2 = 16, max(x_right, 200)
                    self._bg_canvas.create_rectangle(
                        x1, y1_bot, x2, y2_top,
                        fill="#FEF3C7", outline="#F59E0B", width=1, tags="gap_overlay")
                    mx, my = (x1 + x2) // 2, (y1_bot + y2_top) // 2
                    self._bg_canvas.create_rectangle(
                        mx - 22, my - 8, mx + 22, my + 8,
                        fill="white", outline="#F59E0B", tags="gap_overlay")
                    self._bg_canvas.create_text(
                        mx, my, text=f"{gap_px}px", fill="#B45309",
                        font=("Helvetica", 7, "bold"), tags="gap_overlay")

    def _show_dir_bar(self, card):
        """Rebuild the Move Controls panel in self._dir_inner for the selected card."""
        if not hasattr(self, '_dir_inner'):
            return
        # Clear everything in the inner frame (including any placeholder)
        for w in self._dir_inner.winfo_children():
            w.destroy()
        self._dir_bar = None
        STEP = GX
        inner = self._dir_inner

        def _btn(parent, txt, cmd, col):
            b = tk.Button(parent, text=txt, bg=col, fg="black",
                          font=("Helvetica", 10, "bold"), width=3, height=1,
                          relief="flat", cursor="hand2", command=cmd,
                          activebackground="#1E293B", activeforeground="#0F172A")
            b.pack(side="left", padx=2)
            return b

        PAD_STEP = 4; H_STEP = 8; W_STEP = 16

        def _sec_hdr(text, bg, fg="#FFFFFF"):
            hf = tk.Frame(inner, bg=bg)
            hf.pack(fill="x", pady=(6, 2))
            tk.Label(hf, text=f"  {text}", bg=bg, fg=fg,
                     font=("Helvetica", 8, "bold"), pady=2).pack(side="left")

        def _pad_ctrl(parent, side_key, label, pad_dict, pad_bg, pad_fg, btn_bg, btn_fg):
            tk.Label(parent, text=f"{label}:", bg=CARD_BG, fg=pad_fg,
                     font=("Helvetica", 7, "bold")).pack(side="left", padx=(6,1))
            var = tk.IntVar(value=pad_dict[side_key])
            tk.Label(parent, textvariable=var, width=3, bg=pad_bg,
                     fg=pad_fg, font=("Courier", 8, "bold"),
                     relief="sunken", bd=1).pack(side="left", padx=1)
            def _sub(k=side_key, v=var):
                pad_dict[k] = max(0, pad_dict[k] - PAD_STEP); v.set(pad_dict[k])
                self._draw_pad_overlay(card)
            def _add(k=side_key, v=var):
                pad_dict[k] += PAD_STEP; v.set(pad_dict[k])
                self._draw_pad_overlay(card)
            tk.Button(parent, text="−", bg=btn_bg, fg=btn_fg,
                      relief="flat", font=("Helvetica", 9, "bold"),
                      width=2, cursor="hand2", command=_sub).pack(side="left", padx=1)
            tk.Button(parent, text="+", bg=btn_bg, fg=btn_fg,
                      relief="flat", font=("Helvetica", 9, "bold"),
                      width=2, cursor="hand2", command=_add).pack(side="left", padx=1)

        # ── Title row ────────────────────────────────────────────
        tr = tk.Frame(inner, bg=CARD_BG)
        tr.pack(fill="x", pady=(0, 2))
        seg_info = f"   ●  {card.segment}" if card.segment else "   (no segment)"
        tk.Label(tr, text=f"📦  {card.title or card.ctype}{seg_info}",
                 bg=CARD_BG, fg=DARK, font=("Helvetica", 8, "bold")).pack(side="left")
        if card.segment:
            gap_now = self.segment_dirs.get(card.segment, {}).get("gap", "0px")
            self._gap_label = tk.Label(tr, text=f"  gap:{gap_now}",
                                       bg=CARD_BG, fg="#2563EB", font=("Helvetica", 8, "bold"))
            self._gap_label.pack(side="left", padx=6)
        else:
            self._gap_label = None

        # ══════════════════════════════════════════════════════════
        # SEGMENT section  (only when card belongs to a segment)
        # ══════════════════════════════════════════════════════════
        if card.segment:
            _sec_hdr("SEGMENT", "#334155")

            # — Move arrows (whole segment) —
            smf = tk.Frame(inner, bg=CARD_BG)
            smf.pack(fill="x", pady=(0, 2))
            sf = tk.Frame(smf, bg="#F1F5F9", relief="groove", bd=1)
            sf.pack(side="left")
            tk.Label(sf, text=" Move ", bg="#CBD5E1", fg="black",
                     font=("Helvetica", 7, "bold")).pack(side="left")
            _btn(sf, "◄", lambda: self._move_seg(card, -STEP, 0), "#475569")
            _btn(sf, "▲", lambda: self._move_seg(card,  0, -STEP), "#475569")
            _btn(sf, "▼", lambda: self._move_seg(card,  0,  STEP), "#475569")
            _btn(sf, "►", lambda: self._move_seg(card,  STEP, 0), "#475569")
            tk.Label(smf, text="  moves all cards in segment", bg=CARD_BG,
                     fg="#94A3B8", font=("Helvetica", 7)).pack(side="left")

            # — Segment size (applies to all cards in segment) —
            sszf = tk.Frame(inner, bg=CARD_BG)
            sszf.pack(fill="x", pady=(2, 0))
            tk.Label(sszf, text=" Size ", bg="#CBD5E1", fg="black",
                     font=("Helvetica", 7, "bold")).pack(side="left")
            # show the current card's dims as reference
            _sh = card.winfo_height() or int(getattr(card,'css_height','400px').replace('px',''))
            _sw = card.winfo_width()  or (int(card.css_width.replace('px','')) if 'px' in getattr(card,'css_width','') else 400)
            self._seg_size_h_label = tk.Label(sszf, text=f"H:{_sh}px",
                bg=CARD_BG, fg="#334155", font=("Helvetica", 8, "bold"), width=7)
            self._seg_size_h_label.pack(side="left", padx=(6,0))
            def _adj_seg_height(delta, _card=card):
                for _c in self.cards.values():
                    if _c.segment == _card.segment:
                        nv = max(80, _c.winfo_height() + delta)
                        _c.configure(height=nv); _c.css_height = f"{nv}px"
                        try: _c.dim_label.config(text=f"Scale: {_c.css_width} x {_c.css_height}")
                        except: pass
                        _c.after(80, _c._preview)
                nv_ref = max(80, _card.winfo_height())
                try:
                    if self._seg_size_h_label.winfo_exists():
                        self._seg_size_h_label.config(text=f"H:{nv_ref}px")
                    if self._size_h_label.winfo_exists():
                        self._size_h_label.config(text=f"H:{nv_ref}px")
                except: pass
                self._draw_pad_overlay(_card); self._draw_gap_overlay()
            tk.Button(sszf, text="−", bg="#CBD5E1", fg="black", font=("Helvetica", 8, "bold"),
                      relief="flat", command=lambda: _adj_seg_height(-H_STEP)).pack(side="left", padx=(0,1))
            tk.Button(sszf, text="+", bg="#CBD5E1", fg="black", font=("Helvetica", 8, "bold"),
                      relief="flat", command=lambda: _adj_seg_height(H_STEP)).pack(side="left")
            tk.Label(sszf, text="  ", bg=CARD_BG).pack(side="left")
            self._seg_size_w_label = tk.Label(sszf, text=f"W:{_sw}px",
                bg=CARD_BG, fg="#334155", font=("Helvetica", 8, "bold"), width=7)
            self._seg_size_w_label.pack(side="left")
            def _adj_seg_width(delta, _card=card):
                for _c in self.cards.values():
                    if _c.segment == _card.segment:
                        nv = max(80, _c.winfo_width() + delta)
                        _c.configure(width=nv); _c.css_width = f"{nv}px"
                        try: _c.dim_label.config(text=f"Scale: {_c.css_width} x {_c.css_height}")
                        except: pass
                        _c.after(80, _c._preview)
                nv_ref = max(80, _card.winfo_width())
                try:
                    if self._seg_size_w_label.winfo_exists():
                        self._seg_size_w_label.config(text=f"W:{nv_ref}px")
                    if self._size_w_label.winfo_exists():
                        self._size_w_label.config(text=f"W:{nv_ref}px")
                except: pass
                self._draw_pad_overlay(_card); self._draw_gap_overlay()
            tk.Button(sszf, text="−", bg="#CBD5E1", fg="black", font=("Helvetica", 8, "bold"),
                      relief="flat", command=lambda: _adj_seg_width(-W_STEP)).pack(side="left", padx=(0,1))
            tk.Button(sszf, text="+", bg="#CBD5E1", fg="black", font=("Helvetica", 8, "bold"),
                      relief="flat", command=lambda: _adj_seg_width(W_STEP)).pack(side="left")
            tk.Label(sszf, text="  all cards", bg=CARD_BG,
                     fg="#94A3B8", font=("Helvetica", 7)).pack(side="left")

            # — Segment padding —
            seg_pad = self.segment_dirs.setdefault(
                card.segment, {}).setdefault(
                "padding", {"top": 0, "right": 0, "bottom": 0, "left": 0})
            spf = tk.Frame(inner, bg=CARD_BG)
            spf.pack(fill="x", pady=(2, 0))
            tk.Label(spf, text=" Padding ", bg="#D1FAE5", fg="black",
                     font=("Helvetica", 7, "bold")).pack(side="left")
            for sk, lbl in (("top","T"),("right","R"),("bottom","B"),("left","L")):
                _pad_ctrl(spf, sk, lbl, seg_pad, "#F0FDF4", "#064E3B", "#D1FAE5", "#065F46")
            self._draw_pad_overlay(card)

        # ══════════════════════════════════════════════════════════
        # CONTAINER section  (always shown)
        # ══════════════════════════════════════════════════════════
        _sec_hdr("CONTAINER", "#1E3A8A")

        # — Move arrows (this card only) —
        cmf = tk.Frame(inner, bg=CARD_BG)
        cmf.pack(fill="x", pady=(0, 2))
        cf2 = tk.Frame(cmf, bg="#EFF6FF", relief="groove", bd=1)
        cf2.pack(side="left")
        tk.Label(cf2, text=" Move ", bg="#DBEAFE", fg="black",
                 font=("Helvetica", 7, "bold")).pack(side="left")
        _btn(cf2, "◄", lambda: self._move_card(card, -STEP, 0), "#2563EB")
        _btn(cf2, "▲", lambda: self._move_card(card,  0, -STEP), "#2563EB")
        _btn(cf2, "▼", lambda: self._move_card(card,  0,  STEP), "#2563EB")
        _btn(cf2, "►", lambda: self._move_card(card,  STEP, 0), "#2563EB")
        tk.Label(cmf, text="  moves this card only", bg=CARD_BG,
                 fg="#94A3B8", font=("Helvetica", 7)).pack(side="left")

        # — Size H + W —
        szf = tk.Frame(inner, bg=CARD_BG)
        szf.pack(fill="x", pady=(2, 0))
        tk.Label(szf, text=" Size ", bg="#E5E7EB", fg="black",
                 font=("Helvetica", 7, "bold")).pack(side="left")
        cur_h = card.winfo_height() or int(getattr(card, 'css_height', '400px').replace('px',''))
        self._size_h_label = tk.Label(szf, text=f"H:{cur_h}px",
            bg=CARD_BG, fg="#374151", font=("Helvetica", 8, "bold"), width=7)
        self._size_h_label.pack(side="left", padx=(6,0))
        def _adj_height(delta, _card=card):
            nv = max(80, _card.winfo_height() + delta)
            _card.configure(height=nv); _card.css_height = f"{nv}px"
            try: _card.dim_label.config(text=f"Scale: {_card.css_width} x {_card.css_height}")
            except: pass
            _card.after(80, _card._preview)
            try:
                if self._size_h_label.winfo_exists(): self._size_h_label.config(text=f"H:{nv}px")
            except: pass
            self._draw_pad_overlay(_card); self._draw_gap_overlay()
        tk.Button(szf, text="−", bg="#E5E7EB", fg="black", font=("Helvetica", 8, "bold"),
                  relief="flat", command=lambda: _adj_height(-H_STEP)).pack(side="left", padx=(0,1))
        tk.Button(szf, text="+", bg="#E5E7EB", fg="black", font=("Helvetica", 8, "bold"),
                  relief="flat", command=lambda: _adj_height(H_STEP)).pack(side="left")
        tk.Label(szf, text="  ", bg=CARD_BG).pack(side="left")
        cur_w = card.winfo_width() or (int(card.css_width.replace('px','')) if 'px' in getattr(card,'css_width','') else 400)
        self._size_w_label = tk.Label(szf, text=f"W:{cur_w}px",
            bg=CARD_BG, fg="#374151", font=("Helvetica", 8, "bold"), width=7)
        self._size_w_label.pack(side="left")
        def _adj_width(delta, _card=card):
            nv = max(80, _card.winfo_width() + delta)
            _card.configure(width=nv); _card.css_width = f"{nv}px"
            try: _card.dim_label.config(text=f"Scale: {_card.css_width} x {_card.css_height}")
            except: pass
            _card.after(80, _card._preview)
            try:
                if self._size_w_label.winfo_exists(): self._size_w_label.config(text=f"W:{nv}px")
            except: pass
            self._draw_pad_overlay(_card); self._draw_gap_overlay()
        tk.Button(szf, text="−", bg="#E5E7EB", fg="black", font=("Helvetica", 8, "bold"),
                  relief="flat", command=lambda: _adj_width(-W_STEP)).pack(side="left", padx=(0,1))
        tk.Button(szf, text="+", bg="#E5E7EB", fg="black", font=("Helvetica", 8, "bold"),
                  relief="flat", command=lambda: _adj_width(W_STEP)).pack(side="left")

        # — Card padding —
        cpf = tk.Frame(inner, bg=CARD_BG)
        cpf.pack(fill="x", pady=(2, 0))
        tk.Label(cpf, text=" Padding ", bg="#DBEAFE", fg="black",
                 font=("Helvetica", 7, "bold")).pack(side="left")
        for sk, lbl in (("top","T"),("right","R"),("bottom","B"),("left","L")):
            _pad_ctrl(cpf, sk, lbl, card.card_padding, "#EFF6FF", "#1E3A8A", "#DBEAFE", "#1E40AF")

        self._dir_bar = cmf  # keep a ref so _hide_dir_bar can clean up

    def _hide_dir_bar(self):
        if not hasattr(self, '_dir_inner'):
            self._dir_bar = None; return
        for w in self._dir_inner.winfo_children():
            w.destroy()
        tk.Label(self._dir_inner,
                 text="Click a container on the canvas to enable move controls.",
                 bg=CARD_BG, fg="#94A3B8", font=("Helvetica", 8, "italic")
                 ).pack(anchor="w", pady=2)
        self._clear_pad_overlay()
        self._dir_bar = None

    def _draw_pad_overlay(self, card):
        """Draw padding overlays: green bands around the whole segment slot;
        blue bands inside the individual card boundary."""
        if not getattr(self, '_bg_canvas', None):
            return
        self._clear_pad_overlay()
        self.update_idletasks()
        cv = self._bg_canvas
        TAG = "pad_overlay"
        try:
            # ── SEG PAD overlay (green) ─────────────────────────────────────
            if card.segment:
                seg_cards = [c for c in self.cards.values() if c.segment == card.segment]
                if seg_cards:
                    bx1 = min(c.winfo_x() for c in seg_cards)
                    by1 = min(c.winfo_y() for c in seg_cards)
                    bx2 = max(c.winfo_x() + c.winfo_width()  for c in seg_cards)
                    by2 = max(c.winfo_y() + c.winfo_height() for c in seg_cards)
                    sp = self.segment_dirs.get(card.segment, {}).get(
                        "padding", {"top": 0, "right": 0, "bottom": 0, "left": 0})
                    sT, sR, sB, sL = sp["top"], sp["right"], sp["bottom"], sp["left"]
                    SFILL, SSTIP = "#22C55E", "gray25"
                    SFONT = ("Helvetica", 7, "bold")
                    # Filled bands only when padding > 0
                    if sT > 0:
                        cv.create_rectangle(bx1-sL, by1-sT, bx2+sR, by1,
                            fill=SFILL, outline="", stipple=SSTIP, tags=TAG)
                        cv.create_text((bx1+bx2)//2, by1-max(sT//2,6), text=f"{sT}px",
                            fill="#15803D", font=SFONT, tags=TAG)
                    if sB > 0:
                        cv.create_rectangle(bx1-sL, by2, bx2+sR, by2+sB,
                            fill=SFILL, outline="", stipple=SSTIP, tags=TAG)
                        cv.create_text((bx1+bx2)//2, by2+max(sB//2,6), text=f"{sB}px",
                            fill="#15803D", font=SFONT, tags=TAG)
                    if sL > 0:
                        cv.create_rectangle(bx1-sL, by1-sT, bx1, by2+sB,
                            fill=SFILL, outline="", stipple=SSTIP, tags=TAG)
                        cv.create_text(bx1-max(sL//2,6), (by1+by2)//2, text=f"{sL}px",
                            fill="#15803D", font=SFONT, tags=TAG)
                    if sR > 0:
                        cv.create_rectangle(bx2, by1-sT, bx2+sR, by2+sB,
                            fill=SFILL, outline="", stipple=SSTIP, tags=TAG)
                        cv.create_text(bx2+max(sR//2,6), (by1+by2)//2, text=f"{sR}px",
                            fill="#15803D", font=SFONT, tags=TAG)
                    # Always draw the segment slot boundary (dashed green outline)
                    cv.create_rectangle(bx1-sL, by1-sT, bx2+sR, by2+sB,
                        outline="#16A34A", fill="", dash=(5, 3), width=2, tags=TAG)
                    # Label: segment name
                    cv.create_text(bx1-sL+4, by1-sT-1, text=f" {card.segment} ",
                        anchor="sw", fill="#15803D",
                        font=("Helvetica", 7, "bold"), tags=TAG)

            # ── CRD PAD overlay (blue bands inside this card) ─────────────
            cp = card.card_padding
            cT, cR, cB, cL = cp["top"], cp["right"], cp["bottom"], cp["left"]
            if True:  # always draw card boundary
                cx, cy = card.winfo_x(), card.winfo_y()
                cw, ch = max(1, card.winfo_width()), max(1, card.winfo_height())
                CFILL, CSTIP = "#93C5FD", "gray25"
                CFONT = ("Helvetica", 7, "bold")
                if cT > 0:
                    cv.create_rectangle(cx, cy, cx+cw, cy+cT,
                        fill=CFILL, outline="", stipple=CSTIP, tags=TAG)
                    cv.create_text(cx+cw//2, cy+max(cT//2,6), text=f"{cT}px",
                        fill="#1D4ED8", font=CFONT, tags=TAG)
                if cB > 0:
                    cv.create_rectangle(cx, cy+ch-cB, cx+cw, cy+ch,
                        fill=CFILL, outline="", stipple=CSTIP, tags=TAG)
                    cv.create_text(cx+cw//2, cy+ch-max(cB//2,6), text=f"{cB}px",
                        fill="#1D4ED8", font=CFONT, tags=TAG)
                if cL > 0:
                    cv.create_rectangle(cx, cy, cx+cL, cy+ch,
                        fill=CFILL, outline="", stipple=CSTIP, tags=TAG)
                    cv.create_text(cx+max(cL//2,6), cy+ch//2, text=f"{cL}px",
                        fill="#1D4ED8", font=CFONT, tags=TAG)
                if cR > 0:
                    cv.create_rectangle(cx+cw-cR, cy, cx+cw, cy+ch,
                        fill=CFILL, outline="", stipple=CSTIP, tags=TAG)
                    cv.create_text(cx+cw-max(cR//2,6), cy+ch//2, text=f"{cR}px",
                        fill="#1D4ED8", font=CFONT, tags=TAG)
                # Always draw card outer boundary (blue dashed)
                cv.create_rectangle(cx, cy, cx+cw, cy+ch,
                    outline="#1D4ED8", fill="", dash=(5, 3), width=1, tags=TAG)
                # Content-area inner rectangle (shrinks as padding grows)
                ix, iy = cx+cL, cy+cT
                iw, ih = cw-cL-cR, ch-cT-cB
                if iw > 4 and ih > 4:
                    cv.create_rectangle(ix, iy, ix+iw, iy+ih,
                        outline="#1D4ED8", fill="", dash=(4, 2), width=2, tags=TAG)
        except Exception:
            pass

    def _clear_pad_overlay(self):
        if getattr(self, '_bg_canvas', None):
            try: self._bg_canvas.delete("pad_overlay")
            except: pass

    def _reposition_dir_bar(self, card):
        pass  # bar is fixed in the Move Controls panel — no repositioning needed

    @staticmethod
    def _parse_css_padding_dict(padding_str):
        """Parse a CSS shorthand padding string into {top,right,bottom,left} px dict."""
        if not padding_str:
            return {"top": 0, "right": 0, "bottom": 0, "left": 0}
        def _px(s):
            try:
                s = s.strip()
                if   s.endswith("rem"): return max(0, int(float(s[:-3]) * 16))
                elif s.endswith("px"):  return max(0, int(float(s[:-2])))
                elif s.endswith("em"):  return max(0, int(float(s[:-2]) * 16))
                else:                   return max(0, int(float(s)))
            except: return 0
        parts = str(padding_str).strip().split()
        pv = [_px(p) for p in parts]
        if   len(pv) == 1: T = R = B = L = pv[0]
        elif len(pv) == 2: T = B = pv[0]; R = L = pv[1]
        elif len(pv) == 3: T = pv[0]; R = L = pv[1]; B = pv[2]
        else:              T, R, B, L = pv[0], pv[1], pv[2], pv[3]
        return {"top": T, "right": R, "bottom": B, "left": L}

    @staticmethod
    def _parse_gap_px(gap_str):
        """Parse a CSS gap string to integer pixels."""
        try:
            s = str(gap_str).strip()
            if   s.endswith("rem"): return max(0, int(float(s[:-3]) * 16))
            elif s.endswith("px"):  return max(0, int(float(s[:-2])))
            elif s.endswith("vw"):  return max(0, int(float(s[:-2]) * 19.2))  # assume 1920px base
            else:                   return max(0, int(float(s)))
        except:
            return 0

    @staticmethod
    def _card_px_size(card):
        """Return (w, h) logical pixel size — css_width/css_height take priority over winfo."""
        VP_W, VP_H = 1920, 1080
        def _parse(css_val, fallback_winfo, default, vp_ref):
            s = str(css_val).strip()
            if not s or s in ("auto", "fit-content", ""):
                pass
            elif s.endswith("px"):
                try: return max(1, int(float(s[:-2])))
                except: pass
            elif s.endswith("rem"):
                try: return max(1, int(float(s[:-3]) * 16))
                except: pass
            elif s.endswith("vw"):
                try: return max(1, int(float(s[:-2]) / 100 * VP_W))
                except: pass
            elif s.endswith("vh"):
                try: return max(1, int(float(s[:-2]) / 100 * VP_H))
                except: pass
            elif s.endswith("%"):
                try: return max(1, int(float(s[:-1]) / 100 * vp_ref))
                except: pass
            elif s.startswith("calc("):
                # Best-effort: extract the first number
                import re as _re
                m = _re.search(r'[\d.]+', s)
                if m:
                    try: return max(1, int(float(m.group())))
                    except: pass
            v = fallback_winfo
            return max(1, v) if v > 1 else default
        cw = _parse(card.css_width,  card.winfo_width(),  450, VP_W)
        ch = _parse(card.css_height, card.winfo_height(), 300, VP_H)
        return cw, ch

    def _get_layout_block_bounds(self):
        """Return list of (y_top, y_bottom, label) for each layout block, sorted by y."""
        if not self.cards:
            return []
        self.update_idletasks()
        seen_segs = set()
        blocks = []
        for c in sorted(self.cards.values(), key=lambda c: (c.winfo_y(), c.winfo_x())):
            if c.segment:
                if c.segment not in seen_segs:
                    seen_segs.add(c.segment)
                    sc = [x for x in self.cards.values() if x.segment == c.segment]
                    y1 = min(x.winfo_y() for x in sc)
                    y2 = max(x.winfo_y() + max(1, x.winfo_height()) for x in sc)
                    blocks.append((y1, y2, c.segment))
            else:
                y1 = c.winfo_y()
                y2 = y1 + max(1, c.winfo_height())
                blocks.append((y1, y2, c.cid))
        return sorted(blocks, key=lambda b: b[0])

    def _recalc_layout_gap(self):
        """Measure vertical gaps between layout blocks for display only — does NOT overwrite layout_prefs['gap']."""
        blocks = self._get_layout_block_bounds()
        if len(blocks) < 2:
            return
        gaps = [max(0, blocks[i+1][0] - blocks[i][1]) for i in range(len(blocks)-1)]
        if gaps:
            raw     = int(sum(gaps) / len(gaps))
            snapped = round(raw / GX) * GX
            lbl = getattr(self, '_layout_gap_label', None)
            try:
                if lbl and lbl.winfo_exists():
                    lbl.config(text=f"  canvas gap: {snapped}px  (export uses Layout Settings)")
            except Exception:
                pass

    @staticmethod
    def _card_has_explicit_width(card):
        """Return True if the card has an explicit pixel/rem/vw width (not calc/% flex)."""
        css_w = getattr(card, 'css_width', '')
        if not css_w or css_w in ('auto', 'calc(50% - 16px)'):
            return False
        if css_w.endswith('%') or css_w.startswith('calc('):
            return False
        return True

    def _do_import_layout(self):
        """Full-page re-flow after import: place segment blocks and single cards
        in insertion order, top-to-bottom, honouring each segment's direction and gap."""
        self.update_idletasks()
        # Outer-wrapper padding drives the canvas margin and left/top offset of blocks
        MARGIN   = max(0, self._parse_gap_px(self.layout_prefs.get("padding", "16px")))
        # Use the stored outer-wrapper gap (imported from JSON or set in Layout Settings)
        ROW_GAP  = max(8, self._parse_gap_px(self.layout_prefs.get("gap", "24px")))

        # Build ordered block list preserving insertion order
        seen_segs = set()
        blocks = []   # each entry: ('seg', seg_name) | ('single', card)
        for c in self.cards.values():
            if c.segment:
                if c.segment not in seen_segs:
                    seen_segs.add(c.segment)
                    blocks.append(('seg', c.segment))
            else:
                blocks.append(('single', c))

        y_cur = MARGIN
        for kind, payload in blocks:
            if kind == 'single':
                c = payload
                cw, ch = self._card_px_size(c)
                c.place(x=MARGIN, y=y_cur)
                y_cur += ch + ROW_GAP

            else:  # segment block
                seg  = payload
                cfg  = self.segment_dirs.get(seg, {})
                dirn = cfg.get("direction", "row")
                gap  = self._parse_gap_px(cfg.get("gap", "0px"))
                sc   = [c for c in self.cards.values() if c.segment == seg]
                if not sc:
                    continue

                if dirn == "row":
                    # header-action elements may wrap during initial import placement,
                    # corrupting x positions. Use dict insertion order (= import order) instead.
                    if cfg.get("container_type") == "header-action":
                        _cid_order = {cid: i for i, cid in enumerate(self.cards.keys())}
                        sc = sorted(sc, key=lambda c: _cid_order.get(c.cid, 0))
                    else:
                        sc = sorted(sc, key=lambda c: c.winfo_x())
                    row_h = max(self._card_px_size(c)[1] for c in sc)
                    # Detect flex-grow cards (no explicit width, flex CSS)
                    flex_sc = [c for c in sc
                               if "flex" in getattr(c, 'orig_style_css', {})
                               or not self._card_has_explicit_width(c)]
                    # Equal-width redistribution: only when all cards have flex/auto width.
                    _do_redistribute = (
                        len(flex_sc) == len(sc)
                        and len(sc) > 1
                        and not any(self._card_has_explicit_width(c) for c in sc)
                    )
                    if _do_redistribute:
                        # Distribute viewport width equally (use _cv = visible scrollable area)
                        canvas_w = max(600, self._cv.winfo_width() or 1200)
                        avail_w  = canvas_w - MARGIN * 2
                        each_w   = max(80, (avail_w - gap * (len(sc) - 1)) // len(sc))
                        cx = MARGIN
                        for c in sc:
                            c.configure(width=each_w)
                            # Only write the px value if the element didn't have an
                            # explicit "auto" — preserves JSON-specified auto width.
                            if c.css_width != "auto":
                                c.css_width = f"{each_w}px"
                                c._style_edited = True  # new width should appear in export
                            try:
                                c.dim_label.config(
                                    text=f"Scale: {c.css_width} x {c.css_height}")
                            except Exception:
                                pass
                            c.place(x=cx, y=y_cur)
                            c.after(100, c._preview)
                            cx += each_w + gap
                    else:
                        cx = MARGIN
                        for c in sc:
                            cw, _ = self._card_px_size(c)
                            c.place(x=cx, y=y_cur)
                            cx += cw + gap
                    y_cur += row_h + ROW_GAP

                else:  # column
                    sc = sorted(sc, key=lambda c: c.winfo_y())
                    col_w = max(self._card_px_size(c)[0] for c in sc)
                    for c in sc:
                        _, ch = self._card_px_size(c)
                        c.place(x=MARGIN, y=y_cur)
                        y_cur += ch + gap
                    y_cur += ROW_GAP

        self.update_idletasks()
        self._recalc_layout_gap()   # store measured inter-block gap back into layout_prefs
        self._draw_gap_overlay()

    def _relayout_segments(self):
        """Adjust positions within each segment to match stored gap — keeps block origins."""
        self.update_idletasks()
        for seg, cfg in self.segment_dirs.items():
            dirn    = cfg.get("direction", "row")
            gap_px  = self._parse_gap_px(cfg.get("gap", "0px"))
            sc = [c for c in self.cards.values() if c.segment == seg]
            if len(sc) < 2:
                continue
            if dirn == "row":
                sc = sorted(sc, key=lambda c: c.winfo_x())
                cx, cy = sc[0].winfo_x(), sc[0].winfo_y()
                for c in sc:
                    cw, _ = self._card_px_size(c)
                    c.place(x=cx, y=cy)
                    cx += cw + gap_px
            else:
                sc = sorted(sc, key=lambda c: c.winfo_y())
                cx, cy = sc[0].winfo_x(), sc[0].winfo_y()
                for c in sc:
                    _, ch = self._card_px_size(c)
                    c.place(x=cx, y=cy)
                    cy += ch + gap_px
        self.update_idletasks()
        self._draw_gap_overlay()

    def _move_seg(self, card, dx, dy):
        """Move every card in the segment by (dx, dy) — keeps relative spacing."""
        for c in self.cards.values():
            if c.segment == card.segment:
                c.place(x=max(0, c.winfo_x() + dx), y=max(0, c.winfo_y() + dy))
                c._sync_dimensions()
        self._reposition_dir_bar(card)
        self._recalc_layout_gap()   # update inter-block gap in layout_prefs
        self._draw_gap_overlay()

    def _move_card(self, card, dx, dy):
        """Move a single card within its segment — gap adjusts automatically."""
        card.place(x=max(0, card.winfo_x() + dx), y=max(0, card.winfo_y() + dy))
        self.update_idletasks()
        card._sync_dimensions()
        if card.segment:
            self._recalc_seg_gap(card.segment)
            self._draw_gap_overlay()
        self._reposition_dir_bar(card)

    def _recalc_seg_gap(self, seg):
        """Measure actual pixel spacing between segment cards and store in segment_dirs."""
        seg_cfg = self.segment_dirs.get(seg)
        if not seg_cfg: return
        direction = seg_cfg.get("direction", "row")
        sc = [c for c in self.cards.values() if c.segment == seg]
        if len(sc) < 2: return
        self.update_idletasks()   # flush pending geometry changes before measuring
        if direction == "row":
            sc = sorted(sc, key=lambda c: c.winfo_x())
            gaps = [max(0, sc[i+1].winfo_x() - (sc[i].winfo_x() + sc[i].winfo_width()))
                    for i in range(len(sc)-1)]
        else:
            sc = sorted(sc, key=lambda c: c.winfo_y())
            gaps = [max(0, sc[i+1].winfo_y() - (sc[i].winfo_y() + sc[i].winfo_height()))
                    for i in range(len(sc)-1)]
        if gaps:
            raw = int(sum(gaps) / len(gaps))
            # Snap to nearest 16px grid step for clean values
            snapped = round(raw / GX) * GX
            seg_cfg["gap"] = f"{snapped}px"
            # Update live gap label in Move Controls if visible
            lbl = getattr(self, '_gap_label', None)
            try:
                if lbl and lbl.winfo_exists():
                    lbl.config(text=f"  gap: {seg_cfg['gap']}")
            except Exception:
                pass

    def _content_x_offset(self):
        """Return the canvas x-pixel where the content area starts (after sidebar)."""
        try:
            return max(0, int(self._vp_w.get() * self._vp_sb.get() / 100))
        except:
            return 0

    def _find_slot(self, cw, ch):
        """Find the first free top-left slot that doesn't overlap any existing card."""
        self.update_idletasks()
        placed = [(c.winfo_x(), c.winfo_y(),
                   c.winfo_reqwidth()  or cw,
                   c.winfo_reqheight() or ch) for c in self.cards.values()]
        cx_off = self._content_x_offset()
        try:
            max_x = max(cx_off + 600, self._vp_w.get())
        except:
            max_x = 1920
        y = GY
        while y < 8000:
            x = max(GX, cx_off)
            while x + cw <= max_x:
                free = all(
                    not (x < cx+cw2+GX//2 and x+cw+GX//2 > cx and
                         y < cy+ch2+GY//2 and y+ch+GY//2 > cy)
                    for cx, cy, cw2, ch2 in placed
                )
                if free:
                    return x, y
                x += cw + GX
            y += ch + GY
        return GX, GY

    def _scroll_to(self, x, y):
        """Scroll the canvas viewport so the given coordinate is visible."""
        def _do():
            cw = self._cf.winfo_width()
            ch = self._cf.winfo_height()
            if cw > 10 and ch > 10:
                self._cv.xview_moveto(max(0.0, (x - 30) / cw))
                self._cv.yview_moveto(max(0.0, (y - 30) / ch))
        self.after(80, _do)

    def _refresh_jump_combo(self):
        if not hasattr(self, '_jump_combo'): return
        vals = []; self._jump_cids = []
        for cid, card in self.cards.items():
            lbl = f"{card.title or card.ctype}  [{card.ctype}]"
            if card.segment: lbl += f"  · {card.segment}"
            vals.append(lbl); self._jump_cids.append(cid)
        self._jump_combo['values'] = vals

    def _jump_to_card(self):
        if not hasattr(self, '_jump_cids'): return
        idx = self._jump_combo.current()
        if idx < 0 or idx >= len(self._jump_cids): return
        card = self.cards.get(self._jump_cids[idx])
        if card:
            self._sel_card(card)
            self._scroll_to(card.winfo_x(), card.winfo_y())
        self._jump_var.set("")

    def add_comp(self, ctype):
        cid = str(uuid.uuid4())[:8]
        title = COMP_DEFS[ctype]["label"]
        ds    = COMP_DEFS[ctype]["dataSourcePath"]
        bvar  = COMP_DEFS[ctype]["backendVar"]
        cw = 800 if ctype in ("table", "metrics") else CARD_W
        ch = CARD_H
        x, y = self._find_slot(cw, ch)
        css_w = "100%" if ctype in ("table", "metrics") else "calc(50% - 16px)"
        card = CompCard(self._cf, cid, ctype, title, ds, bvar, self, css_width=css_w)
        card.place(x=x, y=y)
        card.bind("<Button-1>", lambda e, c=card: self._sel_card(c, e))
        self.cards[cid] = card
        self._scroll_to(x, y)
        self._debug_log_event("CARD_ADD", f"Added {ctype} card '{title}' (cid={cid})")
        self.after(80, self._draw_grid)

    def add_river_elem(self, ctype):
        cid  = str(uuid.uuid4())[:8]
        rdef = RIVER_ELEM_DEFS[ctype]
        cw, ch = 260, 160
        x, y = self._find_slot(cw, ch)
        card = CompCard(self._cf, cid, ctype, rdef["label"], "", "", self,
                        width=cw, height=ch, css_width="auto")
        card.place(x=x, y=y)
        card.bind("<Button-1>", lambda e, c=card: self._sel_card(c, e))
        self.cards[cid] = card
        self._scroll_to(x, y)
        self._debug_log_event("ELEM_ADD", f"Added river element '{ctype}' (cid={cid})")

    def remove_comp(self, cid):
        if cid in self.cards:
            card = self.cards[cid]
            self._debug_log_event("CARD_REMOVE", f"Removed {card.ctype} card '{card.title}' (cid={cid})")
            if self._sel and self._sel.cid==cid: self._sel=None
            self._sel_set.discard(cid)
            card.destroy(); del self.cards[cid]
            self.after(80, self._draw_grid)

    def _sel_card(self, card, event=None):
        ctrl = event and bool(event.state & 0x4)
        if ctrl:
            if card.cid in self._sel_set:
                self._sel_set.discard(card.cid); card.set_selected(False)
                self._sel = self.cards.get(next(iter(self._sel_set))) if self._sel_set else None
            else:
                self._sel_set.add(card.cid); self._sel = card; card.set_selected(True)
        else:
            self._deselect(); self._sel = card; self._sel_set = {card.cid}; card.set_selected(True)
        if self._sel:
            self._show_dir_bar(self._sel)
            self._draw_pad_overlay(self._sel)
            try: self._update_properties_panel(self._sel)
            except Exception: pass
        if self._sel and self._sel.segment:
            self._draw_gap_overlay()

    def _deselect(self):
        for cid in list(self._sel_set):
            if cid in self.cards: self.cards[cid].set_selected(False)
        if self._sel and self._sel.cid not in self._sel_set: self._sel.set_selected(False)
        self._sel = None; self._sel_set = set()
        self._hide_dir_bar()
        # Clear right panel
        try:
            self._rp_current_card = None
            self._rp_comp_name.config(text="—")
            self._breadcrumb_var.set("Fragment")
            for w in self._rp_body.winfo_children(): w.destroy()
            tk.Label(self._rp_body,
                      text="Select a component\non the canvas\nto edit its properties.",
                      bg="white", fg="#9CA3AF",
                      font=("Helvetica",10), justify="center", pady=40).pack()
        except Exception: pass

    def add_filter(self, ftype, label=None, key=None, placeholder=None, static_list="", entity_key="", entity_value=""):
        fid = str(uuid.uuid4())[:8]
        _lbl_defaults = {"date": "Date Range", "dropdown": "Group By", "multiselect": "Multi-Select Field", "singleselect": "Single-Select Field"}
        lbl = label if label else _lbl_defaults.get(ftype, "Text Field")
        _key_defaults = {"date": "DATE_RANGE", "dropdown": "GROUP_BY", "multiselect": "MULTI_SELECT", "singleselect": "SINGLE_SELECT"}
        k = key if key else _key_defaults.get(ftype, "TEXT_FIELD")

        if placeholder is None:
            _ph_defaults = {"date": "Select Date", "dropdown": "Select Option", "multiselect": f"Select {lbl}", "singleselect": f"Select {lbl}"}
            ph = _ph_defaults.get(ftype, f"Enter {lbl}")
        else:
            ph = placeholder

        row = FilterRow(self._flist, fid, ftype, self, ph, static_list, entity_key, entity_value)
        row.lv.set(lbl); row.kv.set(k); row.pack(fill="x", pady=3)
        self.filters.append(row)
        if not getattr(self, '_loading_fragment', False):
            self._filters_modified = True
            self._debug_log_event("FILTER_ADD", f"Added {ftype} filter '{lbl}' key='{k}'")

    def remove_filter(self, fid):
        row = next((f for f in self.filters if f.fid==fid), None)
        if row:
            if self.debug_mode.get():
                _ftype = getattr(row, 'ftype', '?')
                _lbl = row.lv.get() if hasattr(row, 'lv') else '?'
                _key = row.kv.get() if hasattr(row, 'kv') else '?'
                self._debug_log_event("FILTER_REMOVE", f"Removed {_ftype} filter '{_lbl}' key='{_key}'")
            self.filters.remove(row); row.destroy()
            if not getattr(self, '_loading_fragment', False):
                self._filters_modified = True

    def _copy_comp(self):
        target_cids = self._sel_set if self._sel_set else ({self._sel.cid} if self._sel else set())
        if not target_cids:
            messagebox.showinfo("Copy", "Select a component first — click a card, or drag on the canvas background to select multiple.", parent=self); return
        self._clipboard = []
        for cid in target_cids:
            c = self.cards[cid]
            self._clipboard.append({
                "ctype": c.ctype, "title": c.title, "ds": c.ds, "bvar": c.bvar,
                "css_width": c.css_width, "css_height": c.css_height,
                "extra_css": copy.deepcopy(getattr(c, 'extra_css', {})),
                "has_footer": getattr(c,"has_footer",False),
                "has_checkboxes": getattr(c,"has_checkboxes",True),
                "has_multiselect": getattr(c,"has_multiselect",True),
                "has_agentic": getattr(c,"has_agentic",True),
                "agent_id": getattr(c,"agent_id","ext-mhetroubleshoot"),
                "agent_args": list(getattr(c,"agent_args",[])),
                "agent_question": getattr(c, "agent_question", ""),
                "columns": copy.deepcopy(c.columns), "series": copy.deepcopy(c.series),
                "metrics": copy.deepcopy(c.metrics),
                "elem_config": copy.deepcopy(c.elem_config), "elem_input": c.elem_input,
                "elem_style": copy.deepcopy(c.elem_style),
                "segment": c.segment, "uid": "", "events": copy.deepcopy(c.events),
                "w": c.winfo_width(), "h": c.winfo_height(),
                "has_insights": getattr(c, "has_insights", False),
                "insights_field": getattr(c, "insights_field", "TicketsList"),
                "insights_agent_id": getattr(c, "insights_agent_id", ""),
            })
        n = len(self._clipboard)
        messagebox.showinfo("Copied", f"Copied {n} component{'s' if n>1 else ''} — click Paste to duplicate.", parent=self)

    def _paste_comp(self):
        if not self._clipboard:
            messagebox.showinfo("Paste", "Nothing copied yet. Select a component and click Copy first.", parent=self); return
        self._deselect()
        pasted = []
        for cb in self._clipboard:
            ctype = cb["ctype"]
            cid = str(uuid.uuid4())[:8]
            cw = cb["w"] or (800 if ctype in ("table","metrics") else 260 if ctype in RIVER_TYPES else CARD_W)
            ch = cb["h"] or (CARD_H if ctype not in RIVER_TYPES else 160)
            x, y = self._find_slot(cw, ch)
            card = CompCard(self._cf, cid, ctype, cb["title"], cb["ds"], cb["bvar"], self,
                            copy.deepcopy(cb["columns"]), copy.deepcopy(cb["series"]),
                            cw, ch, cb["has_footer"], cb["css_width"], cb["css_height"],
                            cb["has_checkboxes"], cb["has_agentic"], cb["agent_id"],
                            elem_config=copy.deepcopy(cb["elem_config"]),
                            elem_input=cb["elem_input"],
                            elem_style=copy.deepcopy(cb["elem_style"]),
                            has_multiselect=cb["has_multiselect"],
                            segment=cb["segment"], uid=cb["uid"],
                            events=copy.deepcopy(cb["events"]),
                            has_insights=cb.get("has_insights", False),
                            insights_field=cb.get("insights_field", "TicketsList"),
                            insights_agent_id=cb.get("insights_agent_id", ""))
            if ctype == "metrics" and cb.get("metrics"):
                card.metrics = copy.deepcopy(cb["metrics"])
            if ctype == "table":
                card.agent_question = cb.get("agent_question", "")
            card.extra_css = copy.deepcopy(cb.get("extra_css", {}))
            card.place(x=x, y=y)
            card.bind("<Button-1>", lambda e, cd=card: self._sel_card(cd, e))
            self.cards[cid] = card
            self._sel_set.add(cid)
            card.set_selected(True)
            pasted.append((cid, card, x, y))
        if pasted:
            self._sel = pasted[-1][1]
            self._scroll_to(pasted[-1][2], pasted[-1][3])

    def _assign_to_tab_dialog(self):
        """Open the card-first 'Assign to Tab Slot' dialog."""
        AssignToTabDialog(self)

    def _rb_press(self, e):
        if not (e.state & 0x4): self._deselect()
        self._rb_start = (e.x, e.y); self._rb_rect_id = None

    def _rb_drag(self, e):
        if self._rb_start is None: return
        x0, y0 = self._rb_start
        if self._rb_rect_id:
            self._bg_canvas.coords(self._rb_rect_id, x0, y0, e.x, e.y)
        else:
            self._rb_rect_id = self._bg_canvas.create_rectangle(
                x0, y0, e.x, e.y, outline="#3B82F6", fill="", dash=(5,3), width=2)

    def _rb_release(self, e):
        if self._rb_start is None: return
        x0, y0 = self._rb_start
        rx1, ry1 = min(x0, e.x), min(y0, e.y)
        rx2, ry2 = max(x0, e.x), max(y0, e.y)
        if self._rb_rect_id:
            self._bg_canvas.delete(self._rb_rect_id); self._rb_rect_id = None
        self._rb_start = None
        if rx2 - rx1 < 5 and ry2 - ry1 < 5: return
        new_sel = set()
        for cid, card in self.cards.items():
            cx2 = card.winfo_x(); cy2 = card.winfo_y()
            cw2 = card.winfo_width(); ch2 = card.winfo_height()
            if cx2 < rx2 and cx2+cw2 > rx1 and cy2 < ry2 and cy2+ch2 > ry1:
                new_sel.add(cid)
        if new_sel:
            self._sel_set = new_sel
            for cid in new_sel: self.cards[cid].set_selected(True)
            self._sel = self.cards[next(iter(new_sel))]

    def _load_defaults(self):
        self.add_comp("pie"); self.cards[list(self.cards.keys())[-1]].place(x=16, y=16)
        self.add_comp("column"); self.cards[list(self.cards.keys())[-1]].place(x=482, y=16)
        self.add_comp("table"); self.cards[list(self.cards.keys())[-1]].place(x=16, y=432)
        self.add_filter("date", label="Date Range", key="DATE_RANGE", placeholder="Select Date Range")
        self.add_filter("textbox", label="Time", key="TIME_RANGE", placeholder="e.g. 00:00-06:00")
        self.add_filter("textbox", label="Message Type", key="MESSAGE_TYPE", placeholder="Enter Message Type")

    # ── VERSION / UPDATE CHECK ────────────────────────────────────────────────────
    @staticmethod
    def _sp_ssl_ctx():
        """SSL context for SharePoint requests.
        Python.org macOS builds don't ship with system CA certs, so Microsoft's
        certificate chain can't be verified.  We skip verification here — the URL
        is a hardcoded Microsoft domain so the risk is acceptable for an internal tool."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        return ctx

    def _check_for_updates(self):
        threading.Thread(target=self._fetch_version, daemon=True).start()

    def _manual_update_check(self):
        """Triggered by the toolbar button — runs the Confluence check and always shows a result."""
        if not CONFLUENCE_PAGE_ID:
            messagebox.showinfo("Version Check", "Confluence page ID is not configured.", parent=self)
            return
        def _run():
            try:
                body = self._fetch_confluence_body()
                if body is None:
                    self.after(0, lambda: messagebox.showerror(
                        "Version Check Failed",
                        "Could not reach the Confluence page.\n"
                        "Check your network connection and that the API token is valid.",
                        parent=self))
                    return
                best_ver, best_win, best_mac = self._parse_version_blocks(body)
                if not best_ver:
                    self.after(0, lambda: messagebox.showwarning(
                        "Version Check",
                        "Could not find LATEST_VERSION on the Confluence page.\n"
                        "Make sure the page contains a  LATEST_VERSION: x.y.z  line.",
                        parent=self))
                    return
                if self._ver_newer(best_ver, APP_VERSION):
                    dl = (best_mac if sys.platform == "darwin" and best_mac else best_win)
                    self.after(0, lambda v=best_ver, u=dl: self._show_update_dialog(v, u))
                else:
                    self.after(0, lambda v=best_ver: messagebox.showinfo(
                        "Up to Date",
                        f"You are running the latest version  ({APP_VERSION}).\n"
                        f"Latest on Confluence: {v}",
                        parent=self))
            except Exception as exc:
                self.after(0, lambda e=str(exc): messagebox.showerror(
                    "Version Check Failed", f"Unexpected error:\n{e}", parent=self))
        threading.Thread(target=_run, daemon=True).start()

    def _fetch_confluence_body(self):
        """Fetch the storage-format body of the Confluence version page. Returns None on error."""
        try:
            url = (f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{CONFLUENCE_PAGE_ID}"
                   f"?expand=body.storage")
            req = urllib.request.Request(url)
            if CONFLUENCE_EMAIL and CONFLUENCE_TOKEN:
                creds = base64.b64encode(
                    f"{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}".encode()).decode()
                req.add_header("Authorization", f"Basic {creds}")
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", f"FragDesigner/{APP_VERSION}")
            with urllib.request.urlopen(req, timeout=10, context=self._sp_ssl_ctx()) as resp:
                data = json.loads(resp.read().decode())
            return data.get("body", {}).get("storage", {}).get("value", "")
        except Exception:
            return None

    @staticmethod
    def _parse_version_blocks(body):
        """Scan body text for all LATEST_VERSION blocks and return (best_ver, win_url, mac_url)."""
        blocks = re.split(r'(?=LATEST_VERSION:)', body)
        best_ver = None
        best_win = ""
        best_mac = ""
        for block in blocks:
            v_m = re.search(r"LATEST_VERSION:\s*([\d.]+)", block)
            if not v_m:
                continue
            ver = v_m.group(1).strip()
            if best_ver is None or Designer._ver_newer(ver, best_ver):
                best_ver = ver
                w = re.search(r"DOWNLOAD_URL_WIN:\s*(https?://\S+)", block)
                m = re.search(r"DOWNLOAD_URL_MAC:\s*(https?://\S+)", block)
                best_win = w.group(1) if w else ""
                best_mac = m.group(1) if m else ""
        return best_ver, best_win, best_mac

    def _fetch_version(self):
        """Background auto-check on startup — silent on failure."""
        try:
            body = self._fetch_confluence_body()
            if not body:
                return
            best_ver, best_win, best_mac = self._parse_version_blocks(body)
            if not best_ver:
                return
            if self._ver_newer(best_ver, APP_VERSION):
                dl = (best_mac if sys.platform == "darwin" and best_mac else best_win)
                self.after(0, lambda v=best_ver, u=dl: self._show_update_dialog(v, u))
        except Exception:
            pass  # silent — version check must never crash the app

    @staticmethod
    def _ver_newer(a, b):
        """Return True if version string a is strictly newer than b.
        Zero-pads shorter strings so '2.0' > '1.0.0' works correctly."""
        try:
            pa = [int(x) for x in a.strip().split(".")]
            pb = [int(x) for x in b.strip().split(".")]
            n  = max(len(pa), len(pb))
            pa += [0] * (n - len(pa))
            pb += [0] * (n - len(pb))
            return pa > pb
        except Exception:
            return False

    def _show_update_dialog(self, latest_ver, download_url):
        dlg = tk.Toplevel(self)
        dlg.title("Update Available")
        dlg.configure(bg="#0F172A")
        dlg.resizable(False, False)
        dlg.grab_set()
        tk.Label(dlg, text="🆕  New Version Available",
                 bg="#0F172A", fg="#FCD34D", font=("Helvetica", 13, "bold")).pack(pady=(18, 4))
        tk.Label(dlg,
                 text=f"FragDesigner {latest_ver} is available  (you have {APP_VERSION})",
                 bg="#0F172A", fg="#CBD5E1", font=("Helvetica", 10)).pack(pady=(0, 12))
        btn_row = tk.Frame(dlg, bg="#0F172A")
        btn_row.pack(pady=(0, 16))
        if download_url:
            import webbrowser
            tk.Button(btn_row, text="⬇  Download", bg="#0F766E", fg="#F0FDFA",
                      font=("Helvetica", 10, "bold"), padx=14, pady=6, relief="flat",
                      cursor="hand2",
                      command=lambda: (webbrowser.open(download_url), dlg.destroy())
                      ).pack(side="left", padx=6)
        tk.Button(btn_row, text="Later", bg="#334155", fg="#CBD5E1",
                  font=("Helvetica", 10), padx=14, pady=6, relief="flat",
                  cursor="hand2", command=dlg.destroy).pack(side="left", padx=6)
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    # ── USER FRIENDLY LAYOUT SETTINGS ────────────────────────────────────────────
    def _edit_css(self):
        w = tk.Toplevel(self)
        w.title("Dashboard Layout Settings")
        w.geometry("500x420")
        w.configure(bg=BG)
        w.grab_set()

        tk.Label(w, text="Dashboard Layout Settings", bg=BG, fg=DARK, font=("Helvetica", 12, "bold")).pack(pady=10, padx=16, anchor="w")

        f = tk.Frame(w, bg=BG)
        f.pack(fill="both", expand=True, padx=20)
        f.columnconfigure(1, weight=1)

        tk.Label(f, text="Chart Alignment:", bg=BG).grid(row=0, column=0, sticky="w", pady=8)
        wrap_var = tk.StringVar(value=self.layout_prefs.get("chart_wrap", "wrap"))
        ttk.Combobox(f, textvariable=wrap_var,
                     values=["wrap (Scale by Percent)", "nowrap (Scroll Horizontally)"],
                     state="readonly").grid(row=0, column=1, sticky="ew", pady=8)

        tk.Frame(f, bg=BORDER, height=1).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,4))
        tk.Label(f, text="— Content (River elements) Layout —", bg=BG, fg=MUTED,
                 font=("Helvetica",8)).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0,4))

        tk.Label(f, text="Layout Type:", bg=BG).grid(row=3, column=0, sticky="w", pady=8)
        layout_vals = ["flex – row (side by side)",
                       "flex – column (stacked)",
                       "grid (CSS grid)",
                       "stack (vertical stack)"]
        cl_map = {"flex-row": layout_vals[0], "flex-col": layout_vals[1],
                  "grid": layout_vals[2], "stack": layout_vals[3]}
        cl_var = tk.StringVar(value=cl_map.get(self.layout_prefs.get("content_layout","flex-row"), layout_vals[0]))
        cl_cb = ttk.Combobox(f, textvariable=cl_var, values=layout_vals, state="readonly")
        cl_cb.grid(row=3, column=1, sticky="ew", pady=8)

        tk.Label(f, text="Grid Columns (CSS):", bg=BG).grid(row=4, column=0, sticky="w", pady=8)
        gc_var = tk.StringVar(value=self.layout_prefs.get("grid_columns", "1fr 1fr"))
        gc_entry = tk.Entry(f, textvariable=gc_var)
        gc_entry.grid(row=4, column=1, sticky="ew", pady=8)
        tk.Label(f, text="e.g. 1fr 1fr  or  repeat(3,1fr)", bg=BG, fg=MUTED,
                 font=("Helvetica",8)).grid(row=5, column=1, sticky="w")

        tk.Label(f, text="Grid Row Height:", bg=BG).grid(row=6, column=0, sticky="w", pady=8)
        gar_var = tk.StringVar(value=self.layout_prefs.get("grid_auto_rows", ""))
        tk.Entry(f, textvariable=gar_var).grid(row=6, column=1, sticky="ew", pady=8)
        tk.Label(f, text="e.g. minmax(200px, auto)  or  300px  (blank = auto)", bg=BG, fg=MUTED,
                 font=("Helvetica",8)).grid(row=7, column=1, sticky="w")

        tk.Frame(f, bg=BORDER, height=1).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8,4))
        tk.Label(f, text="ℹ  Gap, Padding, Background & extra CSS are set in the 👁 Preview window.",
                 bg=BG, fg="#2563EB", font=("Helvetica",8,"bold")
                 ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0,4))

        def save():
            self.layout_prefs["chart_wrap"] = "nowrap" if "nowrap" in wrap_var.get() else "wrap"
            self.layout_prefs["grid_columns"] = gc_var.get()
            self.layout_prefs["grid_auto_rows"] = gar_var.get().strip()
            chosen = cl_var.get()
            self.layout_prefs["content_layout"] = (
                "flex-col" if "column" in chosen else
                "grid"     if "grid"   in chosen else
                "stack"    if "stack"  in chosen else "flex-row")
            w.destroy()

        btns = tk.Frame(w, bg=BG)
        btns.pack(pady=10)
        tk.Button(btns, text="💾 Save Settings", bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica", 10, "bold"), padx=16, pady=6, cursor="hand2", command=save).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", bg=BORDER, fg=DARK, font=("Helvetica", 10), padx=16, pady=6, cursor="hand2", command=w.destroy).pack(side="left", padx=6)

    # ── SEGMENT MANAGER ──────────────────────────────────────────────
    def _manage_segments(self):
        w = tk.Toplevel(self); w.title("Segment Manager"); w.geometry("760x520"); w.configure(bg=BG); w.grab_set()
        tk.Label(w, text="Segments — group components into named flex containers", bg=BG, fg=DARK, font=("Helvetica",12,"bold")).pack(pady=10, padx=16, anchor="w")
        tk.Label(w, text="Assign a Segment to each component via its ✎ Edit dialog. Configure direction & gap here.", bg=BG, fg=MUTED, font=("Helvetica",9)).pack(padx=16, anchor="w")

        cols = ("Segment Name","Direction","Gap (intra-row)","Section Name","Listeners","Flyout","Fill","# Comps")
        tree = ttk.Treeview(w, columns=cols, show="headings", height=10)
        for c,width in zip(cols,[140,65,55,140,108,58,38,52]):
            tree.heading(c, text=c); tree.column(c, width=width)
        tree.pack(fill="both", expand=True, padx=16, pady=10)

        def _refresh():
            tree.delete(*tree.get_children())
            seg_counts = {}
            for card in self.cards.values():
                if card.segment: seg_counts[card.segment] = seg_counts.get(card.segment, 0) + 1
            all_segs = sorted(set(list(self.segment_dirs.keys()) + list(seg_counts.keys())))
            for sn in all_segs:
                cfg = self.segment_dirs.get(sn, {"direction":"row","gap":"0rem","section_name":sn})
                _ls = cfg.get("events", {}).get("Listeners", {})
                _lbl = ("OnHide+OnShow" if ("OnHideContainer" in _ls and "OnShowContainer" in _ls)
                        else "OnHide" if "OnHideContainer" in _ls
                        else "OnShow" if "OnShowContainer" in _ls else "—")
                _flyout_cfg = cfg.get("flyout", {})
                _flyout_lbl = f"⇄ {_flyout_cfg.get('toggle_evt','?')}" if _flyout_cfg.get("enabled") else "—"
                _fill_lbl = "✓" if cfg.get("expand_fill") else "—"
                tree.insert("", "end", values=(sn, cfg.get("direction","row"), cfg.get("gap","0rem"), cfg.get("section_name",sn), _lbl, _flyout_lbl, _fill_lbl, seg_counts.get(sn,0)))

        def _add():
            name = simpledialog.askstring("New Segment", "Segment name (used as label on cards):", parent=w)
            if not name or not name.strip(): return
            name = name.strip()
            self.segment_dirs.setdefault(name, {"direction":"row","gap":"0rem","section_name":name})
            _refresh()

        def _edit_sel():
            sel = tree.selection()
            if not sel: messagebox.showwarning("Select", "Select a segment first.", parent=w); return
            vals = tree.item(sel[0], "values")
            sn = vals[0]; cfg = self.segment_dirs.get(sn, {"direction":"row","gap":"0rem","section_name":sn})
            ed = tk.Toplevel(w); ed.title(f'Edit Segment — {sn}'); ed.geometry("560x700"); ed.configure(bg=BG)
            w.grab_release(); ed.grab_set()
            ed.columnconfigure(1, weight=1)
            evs = {}
            # ── Layout fields ──────────────────────────────────────────
            for row,(lbl,key,opts) in enumerate([
                ("Section Name (SectionName in JSON)","section_name",None),
                ("Direction","direction",["row","column"]),
                ("Gap — between items inside this row","gap",["0rem","0.5rem","1rem","1.5rem","2rem"]),
            ]):
                tk.Label(ed,text=lbl+":",bg=BG,fg=DARK,font=("Helvetica",10)).grid(row=row,column=0,sticky="w",padx=14,pady=7)
                v = tk.StringVar(value=cfg.get(key,key)); evs[key]=v
                if opts: ttk.Combobox(ed,textvariable=v,values=opts,width=24,state="readonly").grid(row=row,column=1,sticky="w",padx=10,pady=7)
                else: tk.Entry(ed,textvariable=v,width=28,font=("Helvetica",10)).grid(row=row,column=1,sticky="ew",padx=10,pady=7)
            # ── Listener events divider ────────────────────────────────
            tk.Frame(ed, bg=BORDER, height=1).grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(8,0))
            tk.Label(ed, text="Container Event Listeners", bg=BG, fg=DARK,
                     font=("Helvetica",10,"bold")).grid(row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(6,0))
            tk.Label(ed, text="Emitted by header-action triggers to show/hide this segment container.",
                     bg=BG, fg=MUTED, font=("Helvetica",8), wraplength=440
                     ).grid(row=5, column=0, columnspan=2, sticky="w", padx=14, pady=(0,4))
            # Pre-populate from existing events
            _ls = cfg.get("events", {}).get("Listeners", {})
            _hide = _ls.get("OnHideContainer", [{}])[0] if _ls.get("OnHideContainer") else {}
            _show = _ls.get("OnShowContainer", [{}])[0] if _ls.get("OnShowContainer") else {}
            for row_off, grp_lbl, entry_dict, k_src, k_evt in [
                (0, "OnHideContainer", _hide, "hide_src", "hide_evt"),
                (2, "OnShowContainer", _show, "show_src", "show_evt"),
            ]:
                base = 6 + row_off
                tk.Label(ed, text=f"{grp_lbl}  →  SourceContainerId:", bg=BG, fg=DARK,
                         font=("Helvetica",9)).grid(row=base,   column=0, sticky="w", padx=14, pady=4)
                tk.Label(ed, text=f"{grp_lbl}  →  EventId:",          bg=BG, fg=DARK,
                         font=("Helvetica",9)).grid(row=base+1, column=0, sticky="w", padx=14, pady=4)
                evs[k_src] = tk.StringVar(value=entry_dict.get("SourceContainerId", ""))
                evs[k_evt] = tk.StringVar(value=entry_dict.get("EventId", ""))
                _cid_opts = ["header-action-fragment"] + sorted(
                    {d.get("section_name", s) for s, d in self.segment_dirs.items()
                     if d.get("section_name", s)} - {"header-action-fragment"})
                _evt_opts = ["toggle-filter","show-chart","hide-chart","show-metrics",
                             "hide-metrics","view-switch","show-table","hide-table"]
                ttk.Combobox(ed, textvariable=evs[k_src], values=_cid_opts, width=32
                             ).grid(row=base,   column=1, sticky="ew", padx=10, pady=4)
                ttk.Combobox(ed, textvariable=evs[k_evt], values=_evt_opts, width=32
                             ).grid(row=base+1, column=1, sticky="ew", padx=10, pady=4)
            # ── Flyout Card section ────────────────────────────────────
            tk.Frame(ed, bg=BORDER, height=1).grid(row=10, column=0, columnspan=2, sticky="ew", padx=14, pady=(8,0))
            tk.Label(ed, text="Flyout Card  (ToggleFlyout)", bg=BG, fg=DARK,
                     font=("Helvetica",10,"bold")).grid(row=11, column=0, columnspan=2, sticky="w", padx=14, pady=(6,0))
            tk.Label(ed, text="Wraps this segment in a flyout-card drawer. Buttons emit a toggle event to show/hide.",
                     bg=BG, fg=MUTED, font=("Helvetica",8), wraplength=440
                     ).grid(row=12, column=0, columnspan=2, sticky="w", padx=14, pady=(0,4))
            _flyout_cfg = cfg.get("flyout", {})
            evs["flyout_enabled"] = tk.BooleanVar(value=bool(_flyout_cfg.get("enabled", False)))
            tk.Checkbutton(ed, text="Wrap as flyout-card", variable=evs["flyout_enabled"],
                           bg=BG, fg=DARK, font=("Helvetica",10),
                           activebackground=BG).grid(row=13, column=0, columnspan=2, sticky="w", padx=14, pady=4)
            for row_off, row_lbl, fc_key, fc_default in [
                (0, "ToggleFlyout  →  SourceContainerId:", "flyout_src", _flyout_cfg.get("toggle_src","")),
                (1, "ToggleFlyout  →  EventId:",           "flyout_evt", _flyout_cfg.get("toggle_evt","")),
                (2, "closeButtonPosition:",                "flyout_close", _flyout_cfg.get("close_pos","none")),
            ]:
                base = 14 + row_off
                tk.Label(ed, text=row_lbl, bg=BG, fg=DARK,
                         font=("Helvetica",9)).grid(row=base, column=0, sticky="w", padx=14, pady=4)
                evs[fc_key] = tk.StringVar(value=fc_default)
                if fc_key == "flyout_close":
                    ttk.Combobox(ed, textvariable=evs[fc_key],
                                 values=["none","left","right"],
                                 width=14, state="readonly"
                                 ).grid(row=base, column=1, sticky="w", padx=10, pady=4)
                else:
                    _fc_opts = (["header-action-fragment"] +
                                sorted({d.get("section_name",s) for s, d in self.segment_dirs.items()
                                        if d.get("section_name",s)} - {"header-action-fragment"})
                                if fc_key == "flyout_src" else
                                ["toggle-chart","toggle-table","toggle-metrics","toggle-filter",
                                 "show-chart","hide-chart","toggle-chart"])
                    ttk.Combobox(ed, textvariable=evs[fc_key], values=_fc_opts,
                                 width=32).grid(row=base, column=1, sticky="ew", padx=10, pady=4)

            # ── Expand to fill section ──────────────────────────
            tk.Frame(ed, bg=BORDER, height=1).grid(row=17, column=0, columnspan=2, sticky="ew", padx=14, pady=(8,0))
            tk.Label(ed, text="Expand to Fill", bg=BG, fg=DARK,
                     font=("Helvetica",10,"bold")).grid(row=18, column=0, columnspan=2, sticky="w", padx=14, pady=(6,0))
            tk.Label(ed, text="Sets flex:1 + minHeight:0 on this segment so it stretches to fill remaining space "
                              "(e.g. table expands full-height when the chart flyout collapses).",
                     bg=BG, fg=MUTED, font=("Helvetica",8), wraplength=440
                     ).grid(row=19, column=0, columnspan=2, sticky="w", padx=14, pady=(0,4))
            evs["expand_fill"] = tk.BooleanVar(value=bool(cfg.get("expand_fill", False)))
            tk.Checkbutton(ed, text="Expand segment to fill remaining space  (flex: 1)",
                           variable=evs["expand_fill"],
                           bg=BG, fg=DARK, font=("Helvetica",10),
                           activebackground=BG).grid(row=20, column=0, columnspan=2, sticky="w", padx=14, pady=4)

            def _save_edit():
                # Preserve all existing keys (container_type, config, style, events…)
                existing = dict(self.segment_dirs.get(sn, {}))
                existing["direction"]    = evs["direction"].get()
                existing["gap"]          = evs["gap"].get()
                existing["section_name"] = evs["section_name"].get()
                # Rebuild Listeners block
                new_listeners = {}
                hide_src = evs["hide_src"].get().strip()
                hide_evt = evs["hide_evt"].get().strip()
                show_src = evs["show_src"].get().strip()
                show_evt = evs["show_evt"].get().strip()
                if hide_src or hide_evt:
                    new_listeners["OnHideContainer"] = [{"SourceContainerId": hide_src, "EventId": hide_evt}]
                if show_src or show_evt:
                    new_listeners["OnShowContainer"] = [{"SourceContainerId": show_src, "EventId": show_evt}]
                if new_listeners:
                    existing.setdefault("events", {})["Listeners"] = new_listeners
                elif "events" in existing:
                    existing["events"].pop("Listeners", None)
                # Save flyout settings
                if evs["flyout_enabled"].get():
                    existing["flyout"] = {
                        "enabled":    True,
                        "toggle_src": evs["flyout_src"].get().strip(),
                        "toggle_evt": evs["flyout_evt"].get().strip(),
                        "close_pos":  evs["flyout_close"].get().strip() or "none",
                    }
                else:
                    existing.pop("flyout", None)
                # Save expand-to-fill
                if evs["expand_fill"].get():
                    existing["expand_fill"] = True
                else:
                    existing.pop("expand_fill", None)
                self.segment_dirs[sn] = existing
                # Rebuild segment card labels to reflect flyout badge change
                for _c in self.cards.values():
                    if _c.segment == sn:
                        try: _c.rebuild()
                        except Exception: pass
                ed.destroy(); w.grab_set(); _refresh()
            tk.Button(ed,text="Save",bg=BTN_OK_BG, fg=BTN_OK_FG,font=("Helvetica",10,"bold"),padx=14,pady=5,cursor="hand2",command=_save_edit).grid(row=21,column=0,padx=14,pady=14,sticky="w")
            tk.Button(ed,text="Cancel",bg=BORDER,fg=DARK,font=("Helvetica",10),padx=14,pady=5,cursor="hand2",command=lambda: (ed.destroy(), w.grab_set())).grid(row=21,column=1,pady=14)

        def _del_sel():
            sel = tree.selection()
            if not sel: return
            sn = tree.item(sel[0], "values")[0]
            if not messagebox.askyesno("Delete", f"Remove segment '{sn}'? Cards will be unassigned.", parent=w): return
            self.segment_dirs.pop(sn, None)
            for card in self.cards.values():
                if card.segment == sn: card.segment = ""; card.rebuild()
            _refresh()

        bf = tk.Frame(w, bg=BG); bf.pack(pady=6)
        tk.Button(bf,text="+ Add Segment",  bg=BTN_OK_BG,   fg=BTN_OK_FG,  font=("Helvetica",10,"bold"),padx=12,pady=5,cursor="hand2",command=_add).pack(side="left",padx=6)
        tk.Button(bf,text="✎ Edit Selected",bg=BTN_OK_BG,   fg=BTN_OK_FG,  font=("Helvetica",10),padx=12,pady=5,cursor="hand2",command=_edit_sel).pack(side="left",padx=6)
        tk.Button(bf,text="✕ Delete",       bg=BTN_DEL_BG,  fg=BTN_DEL_FG, font=("Helvetica",10),padx=12,pady=5,cursor="hand2",command=_del_sel).pack(side="left",padx=6)
        tk.Button(bf,text="Close",          bg=BORDER,  fg=DARK,   font=("Helvetica",10),padx=12,pady=5,cursor="hand2",command=w.destroy).pack(side="left",padx=6)
        _refresh()

    # ── WYSIWYG PREVIEW ──────────────────────────────────────────────
    def _show_preview(self):
        """Launch the V6 layout designer as the Align Fix dialog."""
        if hasattr(self, '_align_fix_win'):
            try:
                if self._align_fix_win.winfo_exists():
                    self._align_fix_win.deiconify()
                    self._align_fix_win.lift()
                    return
            except Exception:
                pass
        try:
            if getattr(self, 'imported_fragment_root', None):
                # Use original imported JSON so AlignFix sees the true structure.
                # Edits in AlignFix will only touch the nodes the user unlocks,
                # and _apply_v5 writes them back to imported_fragment_root.
                frag = {"Fragment": copy.deepcopy(self.imported_fragment_root)}
            else:
                frag = self._build_fragment()
        except Exception as exc:
            messagebox.showerror("Build Error",
                f"Could not build fragment JSON:\n{exc}\n\n"
                "Add at least one component first.", parent=self)
            return
        self._align_fix_win = AlignFixDialog(self, frag, v5_designer=self)
        # Stop preview server only when the dialog window itself is destroyed
        _af_win_ref = self._align_fix_win
        def _on_af_destroy(e):
            if e.widget is not _af_win_ref: return   # ignore child-widget destroy events
            try:
                if hasattr(_af_win_ref, '_preview_server') and _af_win_ref._preview_server:
                    _af_win_ref._preview_server.stop()
            except Exception: pass
        self._align_fix_win.bind("<Destroy>", _on_af_destroy)

    def _open_glean_chat_standalone(self):
        if not _GLEAN_REQUESTS_OK:
            messagebox.showerror(
                "Glean AI",
                "Missing dependencies.\nRun: pip install requests browser-cookie3\nthen restart the app.")
            return
        frag = self._build_fragment()
        fragment_root = frag.get("Fragment", frag)
        # Reuse existing window if still open — update fragment then show
        win = getattr(self, "_glean_chat_win", None)
        if win and win.winfo_exists():
            win.fragment_root = fragment_root
            win.deiconify()
            win.lift()
            return
        dlg = GleanChatDialog(self, fragment_root,
                              on_apply_cb=lambda: messagebox.showinfo(
                                  "Glean AI", "Suggestions applied. Re-export to see changes."))
        self._glean_chat_win = dlg

    # ── JSON IMPORT ──────────────────────────────────────────────────
    def _import_dialog(self):
        w = tk.Toplevel(self); w.title("Import Fragment JSON"); w.geometry("860x660"); w.configure(bg=BG)
        tk.Label(w, text="Paste your Manhattan Active Fragment JSON below:",
                 bg=BG, fg=DARK, font=("Helvetica", 12, "bold")).pack(pady=10, padx=16, anchor="w")
        txt = scrolledtext.ScrolledText(w, font=("Courier", 9), bg=CARD_BG, fg=DARK, wrap="none")
        txt.pack(fill="both", expand=True, padx=16, pady=4)

        # ── Standard import ───────────────────────────────────────────
        tk.Frame(w, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(6, 0))
        row1 = tk.Frame(w, bg=BG); row1.pack(fill="x", padx=16, pady=4)
        tk.Label(row1, text="Import as canvas layout (replaces current canvas):",
                 bg=BG, fg=DARK, font=("Helvetica", 9, "bold")).pack(side="left")
        tk.Button(row1, text="📥 Import to Canvas", bg=BTN_OK_BG, fg=BTN_OK_FG,
                  font=("Helvetica", 10, "bold"), padx=14, pady=4, relief="flat",
                  cursor="hand2",
                  command=lambda: self._confirm_and_import(txt.get("1.0", "end-1c"), w)
                  ).pack(side="left", padx=8)

        def _preview_pasted_json():
            import tempfile, webbrowser as _wb
            raw = txt.get("1.0", "end-1c").strip()
            if not raw:
                messagebox.showwarning("Empty", "Paste your JSON first.", parent=w); return
            try:
                cleaned = _clean_json_str(raw)
                cleaned = re.sub(r'\{:[^}]+\}', lambda m: f'"{m.group(0)}"', cleaned)
                data = json.loads(cleaned)
            except Exception as e:
                messagebox.showerror("JSON Error", str(e), parent=w); return
            frag_json_str = json.dumps(data, indent=2)
            html = self._build_preview_html(frag_json_str)
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html); tmp = f.name
                _wb.open(f'file://{tmp}')
            except Exception as e:
                messagebox.showerror("Preview Error", str(e), parent=w)

        tk.Button(row1, text="🌐 HTML Preview", bg="#0F766E", fg="white",
                  font=("Helvetica", 10, "bold"), padx=14, pady=4, relief="flat",
                  cursor="hand2", command=_preview_pasted_json).pack(side="left", padx=4)
        tk.Button(row1, text="Cancel", bg=BORDER, fg=DARK,
                  font=("Helvetica", 10), padx=14, pady=4, relief="flat",
                  cursor="hand2", command=w.destroy).pack(side="left")

        # ── Import into tab slot ──────────────────────────────────────
        tk.Frame(w, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(4, 0))
        row2 = tk.Frame(w, bg="#F0F9FF"); row2.pack(fill="x", padx=16, pady=4)
        tk.Label(row2, text="OR: assign this JSON directly into a Tab Group slot  →",
                 bg="#F0F9FF", fg="#0369A1", font=("Helvetica", 9, "bold")).pack(side="left", padx=(0,8))

        tg_cards = [c for c in self.cards.values() if c.ctype == "tab-group"]
        if not tg_cards:
            tk.Label(row2, text="(No Tab Group on canvas — drop one first)",
                     bg="#F0F9FF", fg="#DC2626", font=("Helvetica", 9)).pack(side="left")
        else:
            tg_var  = tk.StringVar()
            tg_combo = ttk.Combobox(row2, textvariable=tg_var, state="readonly",
                                    values=[f"📂 {c.title or 'Tab Group'}" for c in tg_cards],
                                    width=20, font=("Helvetica", 9))
            tg_combo.current(0); tg_combo.pack(side="left", padx=4)

            slot_var  = tk.StringVar()
            slot_combo = ttk.Combobox(row2, textvariable=slot_var, state="readonly",
                                      width=22, font=("Helvetica", 9))
            slot_combo.pack(side="left", padx=4)

            def _refresh_slots(*_):
                idx = tg_combo.current()
                if 0 <= idx < len(tg_cards):
                    slots = list((tg_cards[idx].orig_full_node or {}).get("Slots", {}).keys())
                    slot_combo["values"] = slots
                    if slots: slot_combo.current(0)

            tg_combo.bind("<<ComboboxSelected>>", _refresh_slots)
            _refresh_slots()

            def _import_into_slot():
                raw = txt.get("1.0", "end-1c").strip()
                if not raw:
                    messagebox.showwarning("Empty", "Paste your JSON first.", parent=w); return
                slot_name = slot_var.get().strip()
                if not slot_name:
                    messagebox.showwarning("No slot", "Select a target slot.", parent=w); return
                idx = tg_combo.current()
                if idx < 0 or idx >= len(tg_cards):
                    messagebox.showwarning("No tab group", "Select a tab group.", parent=w); return
                try:
                    cleaned = _clean_json_str(raw)
                    cleaned = re.sub(r'\{:[^}]+\}', lambda m: f'"{m.group(0)}"', cleaned)
                    data = json.loads(cleaned)
                except Exception as e:
                    messagebox.showerror("JSON Error", str(e), parent=w); return

                # Accept both {"Fragment":{...}} and a bare node
                node = data.get("Fragment", data)
                tab_card = tg_cards[idx]
                slot = tab_card.orig_full_node.setdefault("Slots", {})
                existing = slot.get(slot_name, [])
                if not isinstance(existing, list):
                    existing = [existing] if existing else []
                slot[slot_name] = existing + [node]
                tab_card.rebuild()
                messagebox.showinfo("Done",
                    f"JSON assigned to slot '{slot_name}'.\n"
                    "Click ⬡ on the tab group to expand and inspect.", parent=w)
                w.destroy()

            tk.Button(row2, text="📥 Import into Slot", bg=BTN_OK_BG, fg=BTN_OK_FG,
                      font=("Helvetica", 9, "bold"), padx=12, pady=4, relief="flat",
                      cursor="hand2", command=_import_into_slot).pack(side="left", padx=6)

    def _confirm_and_import(self, raw_str, window):
        if len(self.cards) > 0:
            if not messagebox.askyesno("Import", "Importing will clear your current layout. Proceed?",
                                       parent=window): return
        self._process_import(raw_str, window)

    def _process_import(self, raw_str, window):
        try:
            raw_str = _clean_json_str(raw_str)
            def _wrap_placeholder(m, s=raw_str):
                # Only wrap when the placeholder is in a JSON value position
                # (nearest non-whitespace char before it is :, [, or ,)
                # This avoids wrapping {: } patterns already inside quoted strings.
                j = m.start() - 1
                while j >= 0 and s[j] in (' ', '\t', '\n', '\r'):
                    j -= 1
                before_nonws = s[j] if j >= 0 else ''
                if before_nonws in (':', '[', ','):
                    return f'"{m.group(0)}"'
                return m.group(0)
            raw_str = re.sub(r'\{:[^}]+\}', _wrap_placeholder, raw_str)
            try:
                data = json.loads(raw_str)
            except json.JSONDecodeError as first_err:
                if "Extra data" in str(first_err) or "extra data" in str(first_err).lower():
                    try:
                        data, _ = json.JSONDecoder().raw_decode(raw_str.lstrip())
                    except json.JSONDecodeError:
                        raise first_err
                else:
                    raise first_err
            
            if "type" in data and data["type"] == "renderUI": 
                messagebox.showerror("Error", "Please paste the Fragment JSON, not the Action JSON.", parent=window); return
            if "Fragment" not in data: 
                messagebox.showerror("Error", "Invalid Manhattan Active Fragment JSON.", parent=window); return

            for cid in list(self.cards.keys()): self.remove_comp(cid)
            for f in list(self.filters): self.remove_filter(f.fid)
            self.segment_dirs       = {}
            self.header_action_meta = {}
            self.flyout_card_meta   = {}
            self.root_fragment_config = {}
            self.passthrough_nodes  = []
            self.filter_orig_node        = None
            self.fragment_init_orig      = {}
            self.sidebar_right_slot      = []
            self._filters_modified       = False
            self._loading_fragment       = True
            self.imported_fragment_root  = None

            def find_attrs(node):
                # Collect filter Attributes only from the top-level fragment structure.
                # Skip contents of tab-group Slots — each slot has its own filter-panel
                # and those are shown dynamically per-slot via _extract_fp_attrs.
                attrs = []
                if isinstance(node, dict):
                    if "Attributes" in node and isinstance(node["Attributes"], list):
                        attrs.extend(node["Attributes"])
                    for k, v in list(node.items()):
                        if k == "Slots" and node.get("Container") == "tab-group":
                            continue   # skip slot contents — not master-level filters
                        attrs.extend(find_attrs(v))
                elif isinstance(node, list):
                    for i in node: attrs.extend(find_attrs(i))
                return attrs

            def _css_to_pixels(value, reference=1200):
                if isinstance(value, (int, float)):
                    return int(value)
                if not isinstance(value, str):
                    return None
                v = value.strip()
                if v.endswith("px"):
                    try:
                        return int(float(v[:-2].strip()))
                    except ValueError:
                        return None
                if v.endswith("rem"):
                    try:
                        return int(float(v[:-3].strip()) * 16)
                    except ValueError:
                        return None
                if v.endswith("vw"):
                    try:
                        return int(float(v[:-2].strip()) * 19.2)  # 1920px viewport base
                    except ValueError:
                        return None
                if v.endswith("%"):
                    try:
                        return int(reference * float(v[:-1].strip()) / 100)
                    except ValueError:
                        return None
                if v.startswith("calc(") and v.endswith(")"):
                    expr = v[5:-1].replace(" ", "")
                    m = re.match(r"([0-9.]+)%([+-][0-9]+)px$", expr)
                    if m:
                        try:
                            return int(reference * float(m.group(1)) / 100 + int(m.group(2)))
                        except ValueError:
                            return None
                    m = re.match(r"([0-9.]+)%$", expr)
                    if m:
                        try:
                            return int(reference * float(m.group(1)) / 100)
                        except ValueError:
                            return None
                return None

            def _kpi_cards_from_defaults(items):
                """Return card-with-Init children whose Default slot has key-value elements."""
                return [
                    item for item in items
                    if isinstance(item, dict)
                    and item.get("Container") == "card"
                    and "Init" in item
                    and any(
                        isinstance(e, dict) and e.get("Element") == "key-value"
                        for e in item.get("Slots", {}).get("Default", [])
                    )
                ]

            def _parse_metrics_tiles(card_children):
                """Extract metrics spec list from card-Init KPI tiles."""
                result = []
                for child in card_children:
                    kvs = [e for e in child.get("Slots", {}).get("Default", [])
                           if isinstance(e, dict) and e.get("Element") == "key-value"]
                    label = ""; field = ""; unit = ""
                    for kv in kvs:
                        cfg = kv.get("Config", {})
                        if cfg.get("LabelKey") and not label:
                            label = cfg["LabelKey"]
                    for kv in reversed(kvs):
                        inp = kv.get("Input", "")
                        if inp and " | " not in inp:
                            field = inp
                            unit = kv.get("Config", {}).get("postValueSeparator", "").strip()
                            break
                    if label or field:
                        result.append({"label": label, "field": field, "unit": unit})
                return result

            def find_comps(node, comps_list):
                if isinstance(node, dict):
                    container = node.get("Container")
                    # ── Our generated chart/metrics: grid with header slot ──────
                    if container == "grid" and "header" in node.get("Slots", {}):
                        comps_list.append(node)
                        return  # stop recursion — inner chart containers are handled by the else branch
                    # ── Native chart container (reference JSON format) ──────────
                    elif container == "chart" and "Init" in node:
                        comps_list.append({"_is_native_chart": True, "_node": node})
                        return  # stop recursion into chart internals
                    # ── Table ──────────────────────────────────────────────────
                    elif container == "table":
                        # Detect footer-container in Default slot inline (no recursion needed)
                        for _tc in node.get("Slots", {}).get("Default", []):
                            if isinstance(_tc, dict) and _tc.get("Container") == "footer-container":
                                node["_has_footer"] = True
                                break
                        comps_list.append(node)
                        return
                    # ── header-action: emit meta + tagged button elements ────
                    elif container == "header-action":
                        ha_section = node.get("Config", {}).get("SectionName", "header-action")
                        comps_list.append({"_is_header_action_meta": True,
                                           "_section": ha_section,
                                           "_config":  node.get("Config", {}),
                                           "_events":  node.get("Events", {}),
                                           "_style":   node.get("Style",  {})})
                        for _slot in ("Left", "Right", "Default"):
                            for _elem in node.get("Slots", {}).get(_slot, []):
                                _ekey = _elem.get("Element") or _elem.get("Container", "")
                                if isinstance(_elem, dict) and _ekey in RIVER_TYPES:
                                    comps_list.append({"_is_river_elem": True, "_node": _elem,
                                                       "_segment": ha_section, "_ha_section": ha_section,
                                                       "_ha_slot": _slot})
                        return
                    # ── Content flyout-card (chart/table section wrapped as drawer) ─
                    elif container == "flyout-card":
                        _fc_cfg    = node.get("Config", {})
                        _fc_events = node.get("Events", {})
                        _tgl_entry = _fc_events.get("Listeners", {}).get("ToggleFlyout", [{}])[0]
                        _fc_meta   = {
                            "enabled":    True,
                            "toggle_src": _tgl_entry.get("SourceContainerId", ""),
                            "toggle_evt": _tgl_entry.get("EventId", ""),
                            "close_pos":  _fc_cfg.get("closeButtonPosition", "none"),
                        }
                        inner_comps = []
                        for _inner in node.get("Slots", {}).get("Default", []):
                            find_comps(_inner, inner_comps)
                        if inner_comps:
                            for _ic in inner_comps:
                                if isinstance(_ic, dict):
                                    _ic["_flyout_meta"] = _fc_meta
                            comps_list.extend(inner_comps)
                            return
                        # If nothing useful inside (e.g. filter panel), just recurse normally
                        for k, v in list(node.items()):
                            find_comps(v, comps_list)
                        return

                    # ── Tab-group: emit as single river element card ───────────────
                    elif container == "tab-group":
                        comps_list.append({"_is_river_elem": True, "_node": node})
                        return

                    # ── Segment-panel: emit as river element card ──────────────
                    elif container == "segment-panel":
                        comps_list.append({"_is_river_elem": True, "_node": node})
                        return

                    # ── flyout-layout: transparent wrapper ──────────────────────
                    elif container == "flyout-layout":
                        for slot_items in node.get("Slots", {}).values():
                            if isinstance(slot_items, list):
                                for ch in slot_items:
                                    find_comps(ch, comps_list)
                        return

                    # ── list / carousel: extract as river element card ──────────
                    elif container in ("list", "carousel"):
                        comps_list.append({"_is_river_elem": True, "_node": node})
                        return

                    # ── Footer annotation ──────────────────────────────────────
                    elif container == "footer-container":
                        if comps_list and comps_list[-1].get("Container") == "table":
                            comps_list[-1]["_has_footer"] = True
                    # ── Flex/grid grouping card-Init KPI tiles → metrics panel ─
                    elif container in ("flex", "grid") and "Init" not in node:
                        kpi = _kpi_cards_from_defaults(node.get("Slots", {}).get("Default", []))
                        if kpi:
                            _mn_css = node.get("Style", {}).get("css", {})
                            comps_list.append({"_is_metrics_group": True, "_cards": kpi,
                                               "_style": node.get("Style", {}),
                                               "_segment":   node.get("Config", {}).get("SectionName", ""),
                                               "_seg_dir":   _mn_css.get("flexDirection", "row"),
                                               "_seg_gap":   _mn_css.get("gap", "0rem"),
                                               "_seg_pad":   _mn_css.get("padding", ""),
                                               "_seg_events": node.get("Events", {})})
                            return  # stop recursion; tiles already captured
                        # ── Named segment flex: tag children with segment info ──
                        section_name = node.get("Config", {}).get("SectionName", "")
                        if section_name:
                            children = node.get("Slots", {}).get("Default", [])
                            has_comps = any(isinstance(ch, dict) and ch.get("Container") in ("chart","table","grid","segment-panel","tab-group","list","carousel") for ch in children)
                            if has_comps:
                                _ncss      = node.get("Style", {}).get("css", {})
                                seg_dir    = _ncss.get("flexDirection", "row")
                                seg_gap    = _ncss.get("gap", "0rem")
                                seg_pad    = _ncss.get("padding", "")
                                seg_events = node.get("Events", {})
                                seg_flex   = _ncss.get("flex", "")
                                inner_comps = []
                                for ch in children:
                                    find_comps(ch, inner_comps)
                                for ic in inner_comps:
                                    if isinstance(ic, dict):
                                        ic["_segment"]      = section_name
                                        ic["_seg_dir"]      = seg_dir
                                        ic["_seg_gap"]      = seg_gap
                                        ic["_seg_pad"]      = seg_pad
                                        ic["_seg_events"]   = seg_events
                                        ic["_seg_flex"]     = seg_flex
                                        ic["_seg_css_full"] = dict(_ncss)
                                comps_list.extend(inner_comps)
                                return
                    # Known structural containers: recurse into children.
                    # Everything else is an unsupported element: preserve verbatim.
                    _RECURSE_CONTAINERS = {
                        None, "flex", "grid", "footer-container",
                        "sidebar", "card", "header", "stack"
                    }
                    if container in _RECURSE_CONTAINERS:
                        for k, v in list(node.items()):
                            find_comps(v, comps_list)
                    else:
                        comps_list.append({"_is_passthrough": True, "_node": node})
                elif isinstance(node, list):
                    for item in node:
                        find_comps(item, comps_list)

            root_node = data["Fragment"]
            self.root_fragment_config = root_node.get("Config", {})
            self.fragment_init_orig   = root_node.get("Init", {})

            if root_node.get("Container") == "flyout-card":
                self.wrap_flyout.set(True)
                inner_node = root_node.get("Slots", {}).get("Default", [{}])[0]
            else:
                self.wrap_flyout.set(False)
                inner_node = root_node
            
            root_container = inner_node.get("Container")
            root_slots = inner_node.get("Slots", {})

            # ── Unwrap flex/grid shell that wraps a sidebar ─────────────
            if root_container in ("flex", "grid"):
                for _item in root_slots.get("Default", []):
                    if isinstance(_item, dict) and _item.get("Container") == "sidebar":
                        inner_node = _item
                        root_container = "sidebar"
                        root_slots = inner_node.get("Slots", {})
                        break

            # ── Detect flex-row with flyout-card sibling (no sidebar) ────
            _flex_row_fc = None
            if root_container in ("flex", "grid"):
                _css_dir = (inner_node.get("Style") or {}).get("css", {}).get("flexDirection", "")
                _defs_fr = root_slots.get("Default", [])
                if _css_dir == "row" and len(_defs_fr) >= 2:
                    if isinstance(_defs_fr[0], dict) and _defs_fr[0].get("Container") == "flyout-card":
                        _flex_row_fc = ("left", _defs_fr[0], _defs_fr[1])
                    elif isinstance(_defs_fr[-1], dict) and _defs_fr[-1].get("Container") == "flyout-card":
                        _flex_row_fc = ("right", _defs_fr[-1], _defs_fr[0])

            filter_node = None; main_node = None

            if root_container == "sidebar":
                self.sidebar_meta = {"config": inner_node.get("Config", {}),
                                     "style":  inner_node.get("Style",  {})}
                if "Left" in root_slots and len(root_slots["Left"]) > 0:
                    self.filter_pos.set("left"); filter_node = root_slots["Left"][0]
                    if isinstance(filter_node, dict) and filter_node.get("Container") == "flyout-card":
                        self.flyout_card_meta = {"config": filter_node.get("Config", {}),
                                                 "events": filter_node.get("Events", {}),
                                                 "style":  filter_node.get("Style",  {})}
                elif "Right" in root_slots and len(root_slots["Right"]) > 0:
                    self.filter_pos.set("right"); filter_node = root_slots["Right"][0]
                    if isinstance(filter_node, dict) and filter_node.get("Container") == "flyout-card":
                        self.flyout_card_meta = {"config": filter_node.get("Config", {}),
                                                 "events": filter_node.get("Events", {}),
                                                 "style":  filter_node.get("Style",  {})}
                main_node = root_slots.get("Default", [{}])[0]
            elif _flex_row_fc:
                _fc_side, _fc_node, _main_node_fr = _flex_row_fc
                self.filter_pos.set(f"flex-{_fc_side}")
                filter_node = _fc_node
                self.flyout_card_meta = {"config": _fc_node.get("Config", {}),
                                         "events": _fc_node.get("Events", {}),
                                         "style":  _fc_node.get("Style",  {})}
                main_node = _main_node_fr
            else:
                self.filter_pos.set("top")
                defs = root_slots.get("Default", [])
                if defs and "filter-panel" in str(defs[0]): filter_node = defs[0]; main_node = defs[1] if len(defs)>1 else None
                elif defs: main_node = defs[0]

            # Store Right sidebar slot (details flyout / stack) for passthrough on export
            if root_container == "sidebar":
                _r_slot = root_slots.get("Right", [])
                if self.filter_pos.get() == "left" and _r_slot:
                    self.sidebar_right_slot = _r_slot

            # Extract actual filter-panel element node for verbatim passthrough
            if filter_node is not None:
                _fp_elem = None
                if isinstance(filter_node, dict):
                    if filter_node.get("Container") == "flyout-card":
                        _fp_defs = filter_node.get("Slots", {}).get("Default", [])
                        _fp_elem = _fp_defs[0] if _fp_defs else None
                    elif filter_node.get("Element") == "filter-panel":
                        _fp_elem = filter_node
                self.filter_orig_node = _fp_elem

            if main_node and isinstance(main_node, dict):
                # When main_node is a wrapper flex (header-action + content), the real
                # content node is the non-header-action child with a Config.SectionName.
                # Using it as the reference preserves justifyContent, height, SectionName, etc.
                _ref_node = main_node
                if main_node.get("Container") in ("flex", "grid") and not main_node.get("Config", {}).get("SectionName"):
                    for _ch in main_node.get("Slots", {}).get("Default", []):
                        if (isinstance(_ch, dict)
                                and _ch.get("Container") in ("flex", "grid")
                                and _ch.get("Config", {}).get("SectionName")):
                            _ref_node = _ch
                            break
                self.main_content_meta = {"config": _ref_node.get("Config", {}),
                                          "style":  _ref_node.get("Style",  {}),
                                          "events": _ref_node.get("Events", {})}
                if "Style" in _ref_node and "css" in _ref_node["Style"]:
                    css = _ref_node["Style"]["css"]
                    self.layout_prefs["padding"] = css.get("padding", "")
                    self.layout_prefs["gap"] = css.get("gap", "0")
                    self.layout_prefs["bg"] = css.get("background", css.get("backgroundColor","transparent"))
                    self.layout_prefs["jc"] = css.get("justifyContent", "")
                    self.layout_prefs["height"] = css.get("height", "")

            all_attrs = find_attrs(data)
            seen_keys = set()
            for a in all_attrs: 
                inp = a.get("Input", "")
                if inp in seen_keys: continue
                seen_keys.add(inp)
                
                ftype = "textbox"
                f_node = a.get("Filter", {})
                f_type_str = (f_node.get("Type") or f_node.get("type") or "").lower()
                if f_type_str == "multiselect":
                    ftype = "multiselect"
                elif f_type_str == "singleselect":
                    ftype = "singleselect"
                elif f_type_str in ("select", "dropdown", "combobox"):
                    ftype = "dropdown"
                elif "date" in f_type_str:
                    ftype = "date"

                ph = f_node.get("Placeholder", {}).get("LabelKey", "")
                sl = f_node.get("StaticList", "")
                ek = f_node.get("EntityKey", "")
                ev = f_node.get("EntityValue", "")
                if isinstance(sl, list):
                    sl = json.dumps(sl)

                self.add_filter(ftype, a.get("LabelKey", ""), inp, ph, sl, ek, ev)

            self._loading_fragment = False
            self._filters_modified = False

            extracted_comps = []
            find_comps(data, extracted_comps)
            
            current_y = 16
            current_x = 16
            row_max_h = 0
            
            def _parse_series(sm):
                series = []
                for s in sm:
                    fm = s.get("fieldMappings", {})
                    x_field = next((k for k, v in fm.items() if v == "name"), None)
                    fm_inverted = x_field is None
                    if x_field is None: x_field = fm.get("name", "")
                    y_field = next((k for k, v in fm.items() if v == "y"), None)
                    if y_field is None: y_field = fm.get("y", "")
                    opts = s.get("staticOptions", {})
                    color = opts.get("color", "colorByPoint" if opts.get("colorByPoint") else "")
                    series.append({"name": opts.get("name","Series"), "x_field": x_field,
                                   "y_field": y_field, "color": color, "fm_inverted": fm_inverted})
                return series

            def _col_field_and_link(col_node):
                """Return (field, link_or_None) for a column node.
                Handles simple key-value and complex flex+link patterns."""
                def _first_kv(node):
                    if isinstance(node, dict):
                        if node.get("Element") == "key-value":
                            return node.get("Input", "")
                        for v in node.values():
                            r = _first_kv(v)
                            if r: return r
                    elif isinstance(node, list):
                        for item in node:
                            r = _first_kv(item)
                            if r: return r
                    return ""
                def _find_link(node):
                    if isinstance(node, dict):
                        if node.get("Element") == "link":
                            ll = node.get("Config",{}).get("LegacyLink",{})
                            if ll.get("MenuId"):
                                rc = ll.get("RelationshipConfig",[{}])[0]
                                ref_keys = []
                                for rk in rc.get("ReferenceKeys",[]):
                                    if "FromAttribute" in rk:
                                        ref_keys.append({"type":"field","from_attr":rk["FromAttribute"],"to_attr":rk.get("ToAttribute","")})
                                    else:
                                        ref_keys.append({"type":"filter","to_attr":rk.get("ToAttribute",""),"from_values":rk.get("FromValues",[])})
                                id_field = ref_keys[0]["from_attr"] if ref_keys and ref_keys[0]["type"]=="field" else ""
                                return {"menu_id":ll.get("MenuId",""),"rel_name":rc.get("RelationshipName",""),
                                        "from_entity":rc.get("FromEntity","outputTable"),"to_entity":rc.get("ToEntity",""),
                                        "label_key":ll.get("LabelKey",""),"id_field":id_field,"ref_keys":ref_keys}
                            # Event-click link (EventId-based tab navigation)
                            _ec_clicks = node.get("Events", {}).get("Triggers", {}).get("OnClick", [])
                            if _ec_clicks:
                                _ec0 = _ec_clicks[0]
                                _payload = _ec0.get("Payload", {})
                                return {
                                    "event_type":     "event_click",
                                    "event_id":       _ec0.get("EventId", ""),
                                    "container_id":   _ec0.get("ContainerId", ""),
                                    "filter_section": _payload.get("filterSection", ""),
                                    "filter_id":      _payload.get("filterId", ""),
                                    "input_expr":     _ec0.get("Input", ""),
                                }
                        for v in node.values():
                            r = _find_link(v)
                            if r: return r
                    elif isinstance(node, list):
                        for item in node:
                            r = _find_link(item)
                            if r: return r
                    return None
                slots = col_node.get("Slots", {})
                field = _first_kv(slots) or slots.get("Default",[{}])[0].get("Input","Unknown")
                link  = _find_link(slots)
                # Detect Events.Triggers.OnClick on a key-value slot element (no link wrapper)
                col_events = None
                for _sn in slots.values() if isinstance(slots, dict) else []:
                    _sl = _sn if isinstance(_sn, list) else [_sn]
                    for _se in _sl:
                        if isinstance(_se, dict) and _se.get("Element") == "key-value":
                            _kv_clicks = _se.get("Events", {}).get("Triggers", {}).get("OnClick", [])
                            if _kv_clicks:
                                _kvc0 = _kv_clicks[0]
                                _kvp = _kvc0.get("Payload", {})
                                col_events = {
                                    "event_id":       _kvc0.get("EventId", ""),
                                    "container_id":   _kvc0.get("ContainerId", ""),
                                    "filter_section": _kvp.get("filterSection", ""),
                                    "filter_id":      _kvp.get("filterId", ""),
                                    "input_expr":     _kvc0.get("Input", ""),
                                }
                return field, link, col_events

            def _extract_table_cols(tbl_node):
                cols = []
                for col_node in tbl_node.get("Config",{}).get("Columns",[]):
                    if _is_insights_col(col_node)[0]:
                        continue
                    fv, lv, ev = _col_field_and_link(col_node)
                    tv = col_node.get("Config",{}).get("LabelKey","Unknown")
                    cols.append({"field": fv, "title": tv, "link": lv, "events": ev})
                return cols

            IMPORT_BASE_WIDTH = 1200
            for c in extracted_comps:
                try:
                    w = 450; h = 400; css_w = "calc(50% - 16px)"; css_h = "400px"
                    cols = series = metrics_import = None
                    has_footer = has_checkboxes = has_agentic = False
                    has_multiselect = True
                    agent_id = "ext-mhetroubleshoot"
                    agent_args = []
                    agent_question = ""
                    _ins_found = False; _ins_field = "TicketsList"; _ins_agent = ""
                    seg_name = c.get("_segment", "")
                    seg_dir  = c.get("_seg_dir", "row")
                    seg_gap  = c.get("_seg_gap", "0rem")
                    seg_pad  = c.get("_seg_pad", "")
                    elem_config_import = elem_input_import = elem_style_import = None
                    uid_import = ""; events_import = {}

                    # ── Unsupported element: store verbatim for round-trip ────────
                    if c.get("_is_passthrough"):
                        self.passthrough_nodes.append({
                            "node": c["_node"],
                            "segment": c.get("_segment", "")
                        })
                        continue

                    if c.get("_is_header_action_meta"):
                        sn = c["_section"]
                        self.header_action_meta = {"config": c["_config"], "events": c["_events"], "style": c["_style"]}
                        self.segment_dirs[sn] = {"direction": "row", "gap": "0rem", "section_name": sn,
                                                  "container_type": "header-action",
                                                  "config": c["_config"], "events": c["_events"], "style": c["_style"]}
                        continue

                    # ── Imported river element (button, action, etc.) ──────────
                    if c.get("_is_river_elem"):
                        en = c["_node"]
                        ctype = en.get("Element") or en.get("Container", "button")
                        if ctype not in RIVER_TYPES: raise ValueError(f"Unknown river type: {ctype}")
                        title = en.get("Config", {}).get("LabelKey", ctype)
                        ds = ""
                        uid_import    = en.get("UID", "")
                        events_import = en.get("Events", {})
                        elem_config_import = {k: v for k, v in en.get("Config", {}).items()}
                        elem_input_import  = en.get("Input", "")
                        elem_style_import  = en.get("Style", {})
                        # Segment-panel: flatten filter config into elem_config for the editor
                        if ctype == "segment-panel":
                            _sp_cfg = en.get("Config", {})
                            _sp_filter = _sp_cfg.get("Filter", {})
                            if _sp_filter or _sp_cfg.get("EnableFilter"):
                                # Filter mode — flatten StaticList into Segments (preserve UID)
                                _sl = _sp_filter.get("StaticList", [])
                                elem_config_import["Segments"] = [
                                    {"AttributeKey":   s.get("AttributeKey", ""),
                                     "UID":            s.get("UID", ""),
                                     "AttributeValue": s.get("AttributeValue", "")}
                                    for s in _sl
                                ]
                                elem_config_import["__filter_type"]       = _sp_filter.get("Type", "Singleselect")
                                elem_config_import["__placeholder_label"] = (_sp_filter.get("Placeholder") or {}).get("LabelKey", "")
                                elem_config_import["__entity_key"]        = _sp_filter.get("EntityKey", "")
                                elem_config_import["__entity_value"]      = _sp_filter.get("EntityValue", "")
                                elem_config_import.pop("Filter", None)
                            else:
                                # Simple chip mode — normalise LabelKey/Id → AttributeKey/AttributeValue
                                _segs = _sp_cfg.get("Segments", [])
                                elem_config_import["Segments"] = [
                                    {"AttributeKey":   s.get("LabelKey",   s.get("AttributeKey", "")),
                                     "UID":            s.get("UID", ""),
                                     "AttributeValue": s.get("Id",         s.get("AttributeValue", ""))}
                                    for s in _segs
                                ]
                        # Tab-group: extract OnOpenTab listener into elem_config helper vars
                        if ctype == "tab-group":
                            _tg_onoentab = en.get("Events", {}).get("Listeners", {}).get("OnOpenTab", [])
                            if _tg_onoentab:
                                _ot0 = _tg_onoentab[0] if isinstance(_tg_onoentab, list) else _tg_onoentab
                                elem_config_import["__onoentab_source"] = _ot0.get("SourceContainerId", "")
                                elem_config_import["__onoentab_event"]  = _ot0.get("EventId", "")
                        seg_name = c.get("_ha_section") or c.get("_segment", "")
                        w = 260; h = 100; css_w = "auto"; css_h = "auto"
                        # Extract explicit width/height from the element's Style
                        _esty = elem_style_import or {}
                        _esty_css = _esty.get("css", {}) if isinstance(_esty.get("css"), dict) else {}
                        _rw = _esty_css.get("width", "") or _esty.get("width", "")
                        _rh = _esty_css.get("height", "") or _esty.get("height", "")
                        if _rw:
                            _rpx = _css_to_pixels(_rw, IMPORT_BASE_WIDTH)
                            css_w = _rw
                            if _rpx: w = _rpx
                        if _rh:
                            _rpx = _css_to_pixels(_rh)
                            css_h = _rh
                            if _rpx: h = _rpx

                    # ── Native chart container (direct Container:"chart") ──────
                    elif c.get("_is_native_chart"):
                        n = c["_node"]
                        sm = n.get("Config",{}).get("dataMapping",{}).get("seriesMappings",[])
                        ctype = (n.get("Config",{}).get("highchartsOptions",{})
                                  .get("chart",{}).get("type") or
                                 (sm[0].get("seriesType","column") if sm else "column"))
                        ds    = n.get("Init",{}).get("DataSourcePath","")
                        title = (n.get("Config",{}).get("chartMetadata",{}).get("name","") or ds or "Chart")
                        series = _parse_series(sm)
                        chart_width = n.get("Config",{}).get("chartMetadata",{}).get("chartWidth", "")
                        if chart_width:
                            width_px = _css_to_pixels(chart_width, IMPORT_BASE_WIDTH)
                            if width_px:
                                w = width_px
                                css_w = chart_width
                        h_raw = (n.get("Style",{}).get("height","") or
                                 n.get("Style",{}).get("css",{}).get("height","400px"))
                        try:
                            h = max(200, _css_to_pixels(h_raw) or int(str(h_raw).replace("px","")))
                        except:
                            h = 400
                        css_h = f"{h}px"
                        uid_import = n.get("UID", "")

                    # ── Card-Init KPI group (flex/grid with card children) ─────
                    elif c.get("_is_metrics_group"):
                        ctype = "metrics"
                        cards_c = c["_cards"]
                        ds = cards_c[0].get("Init",{}).get("DataSourcePath","") if cards_c else ""
                        title = "Metrics Panel"
                        metrics_import = _parse_metrics_tiles(cards_c)
                        w = IMPORT_BASE_WIDTH; h = 200; css_w = "100%"; css_h = "200px"
                        # Extract tile-level padding from first card's Style.css
                        if cards_c:
                            _tile_pad = cards_c[0].get("Style", {}).get("css", {}).get("padding", "")
                            if _tile_pad:
                                card_padding_import = self._parse_css_padding_dict(_tile_pad)

                    # ── Table ────────────────────────────────────────────────
                    elif c.get("Container") == "table":
                        ctype = "table"
                        uid_import = c.get("UID", "")
                        title = c.get("Config",{}).get("title","Data Table")
                        ds    = c.get("Init",{}).get("DataSourcePath","")
                        has_footer     = c.get("_has_footer", False)
                        has_checkboxes  = c.get("Config",{}).get("SelectionConfig",{}).get("ShowSelection", False)
                        has_multiselect = c.get("Config",{}).get("SelectionConfig",{}).get("SupportMultiSelect", True)
                        has_agentic    = "AgenticActions" in c.get("Slots", {})
                        if has_agentic:
                            try:
                                _ag_cfg  = (c["Slots"]["AgenticActions"][0]["Slots"]["Menu"][0]
                                            ["Emitters"]["click"]["actions"][0]["config"])
                                agent_id       = _ag_cfg.get("agentId", agent_id)
                                agent_args     = _ag_cfg.get("actionArguments", [])
                                agent_question = _ag_cfg.get("question", "")
                            except: pass
                        cols = _extract_table_cols(c)
                        _ins_found, _ins_field, _ins_agent = _detect_table_insights(c)
                        w = IMPORT_BASE_WIDTH; css_w = "100%"

                    # ── Our generated grid+header format (chart, metrics, or table) ───
                    else:
                        try:
                            title = (c["Slots"]["header"][0]["Slots"]["Left"][0]
                                     .get("Config",{}).get("LabelKey","Chart"))
                        except: title = "Chart"
                        content_flex = c.get("Slots",{}).get("content",[{}])[0]

                        if content_flex.get("Container") == "table":
                            # ── Table placed directly in content slot ─────────
                            tbl = content_flex
                            ctype = "table"
                            ds    = tbl.get("Init",{}).get("DataSourcePath","")
                            has_checkboxes  = tbl.get("Config",{}).get("SelectionConfig",{}).get("ShowSelection", False)
                            has_multiselect = tbl.get("Config",{}).get("SelectionConfig",{}).get("SupportMultiSelect", True)
                            has_agentic     = "AgenticActions" in tbl.get("Slots", {})
                            cols = _extract_table_cols(tbl)
                            _ins_found, _ins_field, _ins_agent = _detect_table_insights(tbl)
                            w = IMPORT_BASE_WIDTH; css_w = "100%"
                        else:
                            content_items = content_flex.get("Slots",{}).get("Default",[])
                            first_item = content_items[0] if content_items else {}

                            if first_item.get("Container") == "card" and "Init" in first_item:
                                # ── Our generated metrics format ──────────────────
                                ctype = "metrics"
                                ds = first_item.get("Init",{}).get("DataSourcePath","")
                                metrics_import = _parse_metrics_tiles(content_items)
                                w = IMPORT_BASE_WIDTH; h = 200; css_w = "100%"; css_h = "200px"
                            else:
                                # ── Our generated chart format ────────────────────
                                chart_node = first_item
                                ds = chart_node.get("Init",{}).get("DataSourcePath","")
                                sm = (chart_node.get("Config",{}).get("dataMapping",{})
                                      .get("seriesMappings",[]))
                                ctype = sm[0].get("seriesType","column") if sm else "column"
                                series = _parse_series(sm)
                                chart_width = chart_node.get("Config",{}).get("chartMetadata",{}).get("chartWidth", "")
                                if chart_width:
                                    width_px = _css_to_pixels(chart_width, IMPORT_BASE_WIDTH)
                                    if width_px:
                                        w = width_px
                                        css_w = chart_width

                    # ── Recover pixel dimensions + card-level padding from Style ──
                    card_padding_import = None
                    orig_style_css_import = {}
                    if c.get("Container"):
                        try:
                            _style_top = c.get("Style", {})
                            _card_css = _style_top.get("css", {}) if isinstance(_style_top.get("css"), dict) else {}
                            orig_style_css_import = dict(_card_css)  # full CSS for round-trip
                            # css.width takes priority, then top-level Style.width
                            _w_raw = _card_css.get("width", "") or _style_top.get("width", "")
                            _h_raw = _card_css.get("height", "") or _style_top.get("height", "")
                            if _w_raw:
                                css_w = _w_raw
                                width_px = _css_to_pixels(css_w, IMPORT_BASE_WIDTH)
                                if width_px: w = width_px
                            if _h_raw:
                                css_h = _h_raw
                                height_px = _css_to_pixels(css_h)
                                if height_px: h = height_px
                            _pad_raw = _card_css.get("padding", "") or _style_top.get("padding", "")
                            if _pad_raw:
                                card_padding_import = self._parse_css_padding_dict(_pad_raw)
                        except: pass

                    if current_x + w > 1400:
                        current_x = 16; current_y += row_max_h + 24; row_max_h = 0
                    row_max_h = max(row_max_h, h)

                    bvar = f"object::{ds}Js.result"
                    cid  = str(uuid.uuid4())[:8]
                    if seg_name:
                        seg_events_for_dir = c.get("_seg_events", {})
                        seg_flex_import    = c.get("_seg_flex", "")
                        _sd_entry = {
                            "direction": seg_dir, "gap": seg_gap,
                            "section_name": seg_name,
                            "events": seg_events_for_dir,
                            "padding": self._parse_css_padding_dict(seg_pad)}
                        if "1" in str(seg_flex_import):  # flex:1 or flex:"1 1 0" → expand_fill
                            _sd_entry["expand_fill"] = True
                        # preserve non-derived segment CSS for round-trip
                        _seg_css_full = c.get("_seg_css_full", {})
                        _SEG_KNOWN = {'flexDirection','gap','padding','flex','backgroundColor','width','boxSizing','minHeight','height','overflowX'}
                        _seg_extra = {k: v for k, v in _seg_css_full.items() if k not in _SEG_KNOWN}
                        if _seg_extra:
                            _sd_entry['extra_css'] = _seg_extra
                        self.segment_dirs.setdefault(seg_name, _sd_entry)
                    card = CompCard(self._cf, cid, ctype, title, ds, bvar, self,
                                    cols, series, w, h, has_footer, css_w, css_h,
                                    has_checkboxes, has_agentic, agent_id, agent_args,
                                    elem_config=elem_config_import,
                                    elem_input=elem_input_import,
                                    elem_style=elem_style_import,
                                    has_multiselect=has_multiselect, segment=seg_name,
                                    uid=uid_import, events=events_import,
                                    has_insights=_ins_found, insights_field=_ins_field,
                                    insights_agent_id=_ins_agent)
                    if ctype == "metrics" and metrics_import is not None:
                        card.metrics = metrics_import
                    if ctype == "table":
                        card.agent_question = agent_question
                    if card_padding_import is not None:
                        card.card_padding = card_padding_import
                    if orig_style_css_import:
                        card.orig_style_css = orig_style_css_import
                        _CONT_KNOWN = {'width','height','padding','paddingTop','paddingRight','paddingBottom','paddingLeft'}
                        card.extra_css = {k: v for k, v in orig_style_css_import.items() if k not in _CONT_KNOWN}
                    if c.get("_flyout_meta") and card.segment:
                        self.segment_dirs.setdefault(card.segment, {})["flyout"] = c["_flyout_meta"]
                    if c.get("_is_native_chart"):
                        card.orig_chart_node = c["_node"]
                        _hc2 = c["_node"].get("Config", {}).get("highchartsOptions", {})
                        card.hc_adv = _extract_hc_adv(_hc2)
                        _po2 = _hc2.get("plotOptions", {})
                        card.chart_stacking = bool(
                            _po2.get("series", {}).get("stacking")
                            or _po2.get("bar", {}).get("stacking")
                            or _po2.get("column", {}).get("stacking")
                        )
                    # Preserve original JSON for round-trip on unmodified elements.
                    # Used by _comp_json() to restore extra Config/Style properties.
                    _c_cont = c.get("Container")
                    _c_inner = c.get("_node", {}).get("Container", "") if c.get("_is_river_elem") else ""
                    if _c_cont == "table" or (_c_cont == "grid" and "header" in c.get("Slots", {})):
                        card.orig_full_node = c
                        try:
                            _inner_pi = c["Slots"]["content"][0]["Slots"]["Default"][0]
                            _po_pi = _inner_pi.get("Config", {}).get("highchartsOptions", {}).get("plotOptions", {})
                            card.chart_stacking = bool(
                                _po_pi.get("series", {}).get("stacking")
                                or _po_pi.get("bar", {}).get("stacking")
                                or _po_pi.get("column", {}).get("stacking")
                            )
                        except: pass
                    elif _c_cont == "tab-group":
                        card.orig_full_node = c
                        card._build()  # Rebuild to show marry/unmarry buttons
                    elif _c_inner == "tab-group":
                        card.orig_full_node = c["_node"]
                        card._build()  # Rebuild to show marry/unmarry buttons
                    if c.get("_is_river_elem") and c.get("_ha_slot"):
                        card._ha_slot = c["_ha_slot"]
                    card.place(x=current_x, y=current_y)
                    card.bind("<Button-1>", lambda e, cd=card: self._sel_card(cd, e))
                    self.cards[cid] = card
                    current_x += w + 16
                except Exception as ex:
                    print("Skipped component during import:", ex)
                    
            # ── Debug: record successful import ──────────────────────
            if self.debug_mode.get():
                self._debug_imported_json = raw_str
                n_cards   = len(self.cards)
                n_filters = len(self.filters)
                root_c = data.get("Fragment", {}).get("Container", "?")
                self._debug_log_event("IMPORT",
                    f"Imported fragment — Container:{root_c}, "
                    f"{n_cards} card(s), {n_filters} filter(s)")
            # Save original fragment tree for round-trip integrity check (debug mode).
            self.imported_fragment_root = copy.deepcopy(data.get("Fragment", data))
            window.destroy(); messagebox.showinfo("Success", "Fragment imported successfully!")
            if not self.strict_roundtrip_import.get():
                self.after(500, self._do_import_layout)

        except json.JSONDecodeError as e:
            snippet = raw_str[max(0,e.pos-80):e.pos+80] if hasattr(e,'pos') else ""
            messagebox.showerror("JSON Parse Error", f"{e}\n\nAround:\n...{snippet}...", parent=window)
        except Exception as e: messagebox.showerror("Error", f"Error during import:\n{e}", parent=window)

    # ── JSON GENERATION ──────────────────────────────────────────────
    def _metrics_kv_tiles(self, card):
        """Return list of card-container KV tiles in original fragment format (no grid wrapper)."""
        tiles = []
        for m in (card.metrics or []):
            field = m.get("field", "")
            label = m.get("label", "Metric")
            unit  = m.get("unit", "")
            val_elem = {"Element": "key-value", "Input": field,
                        "Style": {"valueWeight": "bold", "font-size": "28rem", "color": "#111111"}}
            if unit:
                val_elem["Config"] = {"postValueSeparator": f" {unit}"}
            tiles.append({
                "Container": "card",
                "Init": {"Type": "value-array", "DataSourcePath": card.ds},
                "Config": {"key": f"metric-{field.lower().replace('_','-')}", "direction": "column"},
                "Style": {
                    "flex": 1, "selectColor": "#2196f3", "display": "flex",
                    "css": {
                        "background": "#f5f5f5", "border-radius": "12rem",
                        "border": "1px solid #e0e0e0", "padding": "16rem",
                        "boxShadow": "0 2rem 4rem rgba(0,0,0,0.05)",
                        "flexDirection": "column", "alignItems": "center", "justifyContent": "center"
                    }
                },
                "Slots": {"Default": [
                    {"Element": "key-value", "Input": f"DUMMY_{field}",
                     "Config": {"LabelKey": label},
                     "Style": {"valueWeight": "bold", "font-size": "14rem", "color": "#555555"}},
                    val_elem
                ]}
            })
        return tiles

    def _river_elem_json(self, card):
        # Tab-group: return the full original node with filter-position wrapping applied.
        # Filter-panel nodes in slot JSON carry Config.Position so we can reconstruct
        # the correct sidebar / flyout-card / top structure at export time.
        if card.ctype == "tab-group":
            orig = getattr(card, "orig_full_node", None)
            if orig:
                result = copy.deepcopy(orig)

                def _wrap_slot_fp(slot_items):
                    """Given [fp_node?, ...content], restructure based on fp_node.Config.Position."""
                    if not isinstance(slot_items, list):
                        return slot_items
                    fp = None
                    content = []
                    for _it in slot_items:
                        if isinstance(_it, dict) and (
                                _it.get("Element") == "filter-panel"
                                or _it.get("Container") == "filter-panel"):
                            if fp is None:
                                fp = _it
                        else:
                            content.append(_it)
                    if fp is None:
                        return slot_items  # no filter — leave unchanged

                    pos = fp.get("Config", {}).get("Position", "top") or "top"

                    # Strip Position from the exported element (it's a layout concern)
                    clean_fp = copy.deepcopy(fp)
                    clean_fp.setdefault("Config", {}).pop("Position", None)

                    if pos == "none":
                        return content

                    if pos == "top":
                        return [clean_fp] + content

                    # left / right → sidebar + flyout-card wrapper
                    fm = getattr(self, 'flyout_card_meta', {}) or {}
                    flyout = {
                        "Container": "flyout-card",
                        "Config":    fm.get("config") or {"closeButtonPosition": "right"},
                        "Style":     fm.get("style")  or {"padding": "0px", "width": "23vw"},
                        "Slots":     {"Default": [clean_fp]},
                    }
                    if fm.get("events"):
                        flyout["Events"] = fm["events"]

                    # Wrap content in a flex column (the content node)
                    if (len(content) == 1 and isinstance(content[0], dict)
                            and content[0].get("Container") == "flex"):
                        content_node = content[0]
                    else:
                        content_node = {
                            "Container": "flex",
                            "Style": {"css": {"flexDirection": "column",
                                              "flex": "1", "minHeight": "0"}},
                            "Slots": {"Default": content},
                        }

                    _sb_meta = getattr(self, 'sidebar_meta', {}) or {}
                    sb_cfg = _sb_meta.get("config") or {}
                    sb_sty = _sb_meta.get("style") or {}
                    if pos == "left":
                        return [{"Container": "sidebar",
                                 **({"Config": sb_cfg} if sb_cfg else {}),
                                 **({"Style": sb_sty} if sb_sty else {}),
                                 "Slots": {"Left": [flyout], "Default": [content_node]}}]
                    else:  # right
                        return [{"Container": "sidebar",
                                 **({"Config": sb_cfg} if sb_cfg else {}),
                                 **({"Style": sb_sty} if sb_sty else {}),
                                 "Slots": {"Default": [content_node], "Right": [flyout]}}]

                for _sname in list(result.get("Slots", {}).keys()):
                    result["Slots"][_sname] = _wrap_slot_fp(result["Slots"][_sname])

                # Merge schema cfg fields (preserveContent, SelectedTabName, Personalizable)
                _ec = getattr(card, 'elem_config', {}) or {}
                _schema_cfg_keys = {"preserveContent", "SelectedTabName", "Personalizable"}
                _cfg_updates = {k: v for k, v in _ec.items()
                                if k in _schema_cfg_keys and v not in ("", None)}
                if _cfg_updates:
                    result.setdefault("Config", {}).update(_cfg_updates)

                # OnOpenTab listener from helper schema vars
                _onoentab_source = _ec.get("__onoentab_source", "").strip()
                _onoentab_event  = _ec.get("__onoentab_event", "").strip()
                if _onoentab_source or _onoentab_event:
                    _ev = result.setdefault("Events", {})
                    _ev.setdefault("Listeners", {})["OnOpenTab"] = [{
                        "SourceContainerId": _onoentab_source,
                        "EventId": _onoentab_event,
                    }]
                elif getattr(card, 'events', {}):
                    for _ek, _ev2 in card.events.items():
                        result.setdefault("Events", {})[_ek] = _ev2

                return result

        rdef = RIVER_ELEM_DEFS[card.ctype]
        out = {}
        if getattr(card, "uid", ""):
            out["UID"] = card.uid
        if rdef["is_container"]:
            out["Container"] = card.ctype
        else:
            out["Element"] = card.ctype

        if card.ctype == "carousel":
            # Carousel must iterate over a bound array — always needs Input: "map(*)"
            out["Input"] = "map(*)"
            _cfg = {k: v for k, v in (card.elem_config or {}).items() if k != "_married_cards"}
            # Inject dataSourcePath from the card's ds field
            if card.ds:
                _cfg["dataSourcePath"] = card.ds
            # Clean Fragment: strip Init from all descendant nodes (they read from array
            # item context instead), then add Input: "map(*)" to the Fragment root so
            # each slide receives its own item.
            if "Fragment" in _cfg:
                frag = _clean_carousel_fragment(_cfg["Fragment"])
                frag["Input"] = "map(*)"
                _cfg["Fragment"] = frag
            if _cfg:
                out["Config"] = _cfg
            style_out = dict(card.elem_style) if card.elem_style else {}
            css = {**getattr(card, 'extra_css', {}), "width": card.css_width}
            if card.css_height and card.css_height not in ("auto", ""):
                css["height"] = card.css_height
            _cpad = self._card_padding_css(card)
            if _cpad:
                css["padding"] = _cpad
            if any(v not in ("auto", "") for v in css.values()):
                style_out["css"] = css
            if style_out:
                out["Style"] = style_out
            if getattr(card, "events", {}):
                out["Events"] = card.events
            out["Slots"] = {}  # carousel uses Config.Fragment, not Slots
            return out

        # Segment-panel: filter mode uses Container + nested Filter.StaticList
        if card.ctype == "segment-panel":
            _sec = getattr(card, 'elem_config', {}) or {}
            _enable_filter    = _sec.get("EnableFilter", False)
            _filter_type      = _sec.get("__filter_type", "Singleselect") or "Singleselect"
            _placeholder_lbl  = _sec.get("__placeholder_label", "")
            _entity_key       = _sec.get("__entity_key", "")
            _entity_value     = _sec.get("__entity_value", "")
            _segments         = _sec.get("Segments", [])
            _cfg_sp = {}
            if _enable_filter:
                # Filter mode: Container (not Element), nested Filter.StaticList
                del out["Element"]
                out["Container"] = "segment-panel"
                out["Input"]     = card.elem_input or "map(*)"
                _cfg_sp["EnableSegmentPanel"] = _sec.get("EnableSegmentPanel", False)
                if _sec.get("Type"):        _cfg_sp["Type"]        = _sec["Type"]
                _cfg_sp["EnableFilter"] = True
                # Build Filter block
                _filter_block = {"Type": _filter_type}
                if _placeholder_lbl:
                    _filter_block["Placeholder"] = {"LabelKey": _placeholder_lbl}
                if _entity_key:   _filter_block["EntityKey"]   = _entity_key
                if _entity_value: _filter_block["EntityValue"] = _entity_value
                _static_list = []
                for s in _segments:
                    _item = {"AttributeKey": s.get("AttributeKey", s.get("LabelKey", ""))}
                    if s.get("UID"): _item["UID"] = s["UID"]
                    _item["AttributeValue"] = s.get("AttributeValue", s.get("Id", ""))
                    _static_list.append(_item)
                _filter_block["StaticList"] = _static_list
                _cfg_sp["Filter"] = _filter_block
                if _sec.get("SectionName"): _cfg_sp["SectionName"] = _sec["SectionName"]
                if _sec.get("Name"):        _cfg_sp["Name"]        = _sec["Name"]
            else:
                # Simple chip mode: Element, Segments with LabelKey/Id
                _cfg_sp["EnableSegmentPanel"] = _sec.get("EnableSegmentPanel", True)
                _cfg_sp["EnableFilter"] = False
                _cfg_sp["Segments"] = [
                    {"LabelKey": s.get("AttributeKey", s.get("LabelKey", "")),
                     "Id":       s.get("AttributeValue", s.get("Id", ""))}
                    for s in _segments
                ]
                if _sec.get("Name"):        _cfg_sp["Name"]        = _sec["Name"]
                if _sec.get("SectionName"): _cfg_sp["SectionName"] = _sec["SectionName"]
            # Style
            _sp_css = dict(getattr(card, 'extra_css', {}))
            if card.css_width and card.css_width not in ("auto", ""):
                _sp_css["width"] = card.css_width
            if card.css_height and card.css_height not in ("auto", ""):
                _sp_css["height"] = card.css_height
            _sp_sty = dict(card.elem_style) if card.elem_style else {}
            if _sp_css: _sp_sty["css"] = _sp_css
            if _cfg_sp: out["Config"] = _cfg_sp
            if _sp_sty: out["Style"] = _sp_sty
            if getattr(card, "events", {}): out["Events"] = card.events
            out["Slots"] = {}
            return out

        if card.elem_input:
            out["Input"] = card.elem_input
        if card.elem_config:
            _cfg = {k: v for k, v in card.elem_config.items() if k != "_married_cards"}
            if _cfg:
                out["Config"] = _cfg
        css = dict(getattr(card, 'extra_css', {}))
        if card.css_width and card.css_width not in ("auto", ""):
            css["width"] = card.css_width
        if card.css_height and card.css_height not in ("auto",""):
            css["height"] = card.css_height
        _cpad = self._card_padding_css(card)
        if _cpad:
            css["padding"] = _cpad
        style_out = dict(card.elem_style) if card.elem_style else {}
        if css:
            style_out["css"] = css
        if style_out:  # omit Style entirely when empty
            out["Style"] = style_out
        if getattr(card, "events", {}):
            out["Events"] = card.events
        if rdef["is_container"]:
            out["Slots"] = {"Default": []}
        return out

    def _comp_json(self, card):
        if card.ctype in RIVER_TYPES:
            return self._river_elem_json(card)

        if card.ctype == "metrics":
            # ── Each KPI tile = card container with its OWN Init ──────────────
            # This follows the UIRiver card-with-own-Init pattern where child
            # key-value elements can do direct field access (Input: "FIELD_NAME").
            kv_tiles = []
            for m in (card.metrics or []):
                field = m.get("field", "")
                label = m.get("label", "Metric")
                unit  = m.get("unit", "")
                val_elem = {
                    "Element": "key-value",
                    "Input": field,
                    "Style": {"valueWeight": "bold", "css": {"fontSize": "22px", "color": "#111111"}}
                }
                if unit:
                    val_elem["Config"] = {"postValueSeparator": f" {unit}"}
                kv_tiles.append({
                    "Container": "card",
                    "Init": {"Type": "value-array", "DataSourcePath": card.ds},
                    "Style": {
                        "flex": 1,
                        "css": {
                            "background": "#f5f5f5",
                            "borderRadius": "8px",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "padding": "12px 16px",
                            "minWidth": "120px",
                            "boxSizing": "border-box"
                        }
                    },
                    "Slots": {"Default": [
                        {
                            "Element": "key-value",
                            "Config": {"LabelKey": label},
                            "Style": {"css": {"fontSize": "13px", "color": "#555555"}}
                        },
                        val_elem
                    ]}
                })
            _style_css = {
                "flex": "1 1 0",
                "minWidth": "280px",
                "background": "white",
                "border": "2px solid #E8E8ED",
                "borderRadius": "4px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.12)",
                "gridTemplateAreas": '"header" "content"',
                "gridTemplateRows": "auto 1fr",
                "boxSizing": "border-box"
            }
            if card.css_width and card.css_width not in ("auto", ""):
                _style_css["width"] = card.css_width
            if card.css_height and card.css_height not in ("auto", ""):
                _style_css["height"] = card.css_height
            _cpad = self._card_padding_css(card)
            if _cpad:
                _style_css["padding"] = _cpad
            _style_css.update(getattr(card, 'extra_css', {}))
            return {
                "Container": "grid",
                "Style": {"css": _style_css},
                "Slots": {
                    "header": [{"Container": "header",
                        "Style": {"css": {"background": "#E8E8ED", "gridArea": "header", "paddingLeft": "1.5rem"}},
                        "Slots": {"Left": [{"Element": "key-value", "Input": "", "Config": {
                            "LabelKey": card.title, "keyValueSeparator": "",
                            "postValueSeparator": "", "preKeySeparator": ""},
                            "Style": {"color": "#4a4a4a", "fontSize": 16, "fontWeight": "bold"}}]}}],
                    "content": [{"Container": "flex",
                        "Style": {"css": {"height": "100%", "overflow": "hidden",
                                          "flexDirection": "row", "flexWrap": "wrap",
                                          "gap": "16px", "padding": "16px",
                                          "alignItems": "stretch", "boxSizing": "border-box"}},
                        "Slots": {"Default": kv_tiles}}]
                }
            }

        if card.ctype == "table":
            # Imported table (orig_full_node set) → passthrough with CSS-only patch.
            # Preserves all original Columns (complex flex/link/conditions), Slots
            # (footer-container, AgenticActions exactly as authored), Events, UID, and
            # every Config attribute (FilterConfig, ShowFilter, etc.).  Only CSS layout
            # properties changed by Align Fix are patched.
            # Internal designer metadata keys are stripped from the output.
            #
            # Fast-path: if user never edited this card, return orig_full_node verbatim.
            _orig_node = getattr(card, 'orig_full_node', None)
            if (_orig_node is not None
                    and not getattr(card, '_config_edited', False)
                    and not getattr(card, '_style_edited', False)
                    and not getattr(card, '_slots_edited', False)
                    and not getattr(card, '_structure_edited', False)):
                _out = copy.deepcopy(_orig_node)
                _strip_internal_meta(_out)
                return _out
            if getattr(card, 'orig_full_node', None):
                _of = copy.deepcopy(card.orig_full_node)
                # Only patch CSS when user explicitly resized/reflowed (_style_edited).
                # Importing always sets css_width="100%" / css_height="300px" as canvas
                # defaults — blindly writing those would corrupt flex/absolute layouts.
                if getattr(card, '_style_edited', False):
                    _css = _of.setdefault("Style", {}).setdefault("css", {})
                    if card.css_height:
                        _css["height"] = card.css_height
                    elif not card.css_height:
                        _css.pop("height", None)
                    if card.css_width:
                        _css["width"] = card.css_width
                _ec = getattr(card, 'extra_css', {})
                if _ec:
                    _of.setdefault("Style", {}).setdefault("css", {}).update(_ec)
                # Apply table-specific color properties
                _table_style = getattr(card, 'table_style', {})
                if _table_style:
                    _of_style = _of.setdefault("Style", {})
                    for prop, val in _table_style.items():
                        if val:
                            _of_style[prop] = val
                _strip_internal_meta(_of)
                # Apply current dialog settings (checkboxes, multiselect, agentic, footer)
                if getattr(card, 'has_checkboxes', True):
                    _of.setdefault("Config", {})["SelectionConfig"] = {
                        "ShowSelection": True,
                        "SupportMultiSelect": getattr(card, 'has_multiselect', True)
                    }
                else:
                    # Preserve SelectionConfig structure when original had it (ShowSelection:false),
                    # rather than omitting it entirely which changes component behavior
                    _orig_sel = (card.orig_full_node or {}).get("Config", {}).get("SelectionConfig")
                    if _orig_sel is not None:
                        _of.setdefault("Config", {})["SelectionConfig"] = {
                            "ShowSelection": False,
                            "SupportMultiSelect": getattr(card, 'has_multiselect', False)
                        }
                    else:
                        _of.get("Config", {}).pop("SelectionConfig", None)
                _of_slots = _of.setdefault("Slots", {})
                if not getattr(card, 'has_agentic', True):
                    _of_slots.pop("AgenticActions", None)
                else:
                    # Always update AgenticActions configuration when card is edited
                    # This ensures agent_question and actionArguments changes are reflected
                    _of_slots["AgenticActions"] = [
                        {
                            "Element": "agentic-actions",
                            "Slots": {"Menu": [{
                                "Element": "menu-item",
                                "Config": {"LabelKey": "Troubleshoot with AI"},
                                "Emitters": {"click": {"actions": [{
                                    "type": "agentic",
                                    "config": {
                                        "agentId": getattr(card, 'agent_id', 'ext-mhetroubleshoot'),
                                        "question": getattr(card, 'agent_question', '') or "Analyze and troubleshoot failures for this message type",
                                        "actionArguments": list(getattr(card, 'agent_args', []))
                                    }
                                }]}}
                            }]}
                        }
                    ]
                _of_default = _of_slots.get("Default", [])
                _footer_idx = next((i for i, x in enumerate(_of_default)
                                    if isinstance(x, dict) and x.get("Container") == "footer-container"), None)
                if getattr(card, 'has_footer', False):
                    if _footer_idx is None:
                        _of_slots.setdefault("Default", []).append({
                            "Container": "footer-container",
                            "Slots": {"Footer": [{
                                "Container": "footer",
                                "Input": "map(*)",
                                "Config": {"PaginationConfig": {
                                    "Paginate": True,
                                    "Size": [10, 25, 50, 100],
                                    "Slot": "footer"
                                }}
                            }]}
                        })
                else:
                    if _footer_idx is not None:
                        _of_default.pop(_footer_idx)
                # Rebuild Config.Columns from current card.columns, preserving rich
                # original column nodes where they match, building simple nodes for new ones.
                _orig_cols = _of.get("Config", {}).get("Columns", [])
                _orig_col_map = {}   # LabelKey → original col node (non-insights)
                _orig_insights_col = None
                for _oc in _orig_cols:
                    if _is_insights_col(_oc)[0]:
                        _orig_insights_col = _oc
                    else:
                        _oc_lk = _oc.get("Config", {}).get("LabelKey", "")
                        if _oc_lk:
                            _orig_col_map[_oc_lk] = _oc
                _new_cols = []
                if getattr(card, 'has_insights', False):
                    if _orig_insights_col:
                        _new_cols.append(_orig_insights_col)
                    else:
                        _ins_f2 = getattr(card, 'insights_field', 'TicketsList') or 'TicketsList'
                        _ins_a2 = getattr(card, 'insights_agent_id', '') or 'obe-ticketDetailFlyout'
                        _new_cols.append({
                            "UID": f"Column{_ins_f2}",
                            "Config": {"LabelKey": "Insights"},
                            "Slots": {"Default": [
                                {"Input": "Dummy", "Config": {}, "Element": "key-value", "Style": {}},
                                {"Element": "action-button",
                                 "Conditions": [{"Condition": f"{_ins_f2} == null", "Visible": False}],
                                 "Input": f"map({{{_ins_f2}: {_ins_f2}}})",
                                 "Config": {"LabelKey": "", "src": "assets/river/assets/icons/lightbulb-on.svg",
                                            "ActionConfig": {"Behavior": {"Flyout": {"AgentRef": {"AgentId": _ins_a2}}}}},
                                 "Style": {"css": {"border": "none", "background-color": "transparent",
                                                   "color": "var(--fixed-13)", "white-space": "nowrap",
                                                   "padding-left": 0, "justify-self": "end"}},
                                 "Events": {"Triggers": {"OnClick": [{"EventId": "push-details-flyout",
                                                                       "ContainerId": "details-button"}]}}}
                            ]}
                        })
                for _ci, _cc in enumerate(card.columns):
                    _cc_field = _cc.get('field', '')
                    if _cc_field in _orig_col_map:
                        _cn2 = _orig_col_map[_cc_field]
                        if _cc.get('title') and _cc['title'] != _cc_field:
                            _cn2.setdefault("Config", {})["LabelKey"] = _cc['title']
                        # Compare current link/events against originally imported state;
                        # rebuild Default slot only when user actually changed something.
                        _lk2x = _cc.get("link")
                        _ev2x = _cc.get("events")
                        _orig_pf2, _orig_lk2, _orig_ev2 = _parse_col_link_events(_cn2)
                        _si2 = _orig_pf2 or _cc_field
                        if _lk2x != _orig_lk2 or _ev2x != _orig_ev2:
                            if _lk2x and _lk2x.get("event_type") == "event_click":
                                _p2 = {}
                                if _lk2x.get("filter_section") or _lk2x.get("filter_id"):
                                    _p2 = {"filterSection": _lk2x.get("filter_section","Filters"),
                                           "filterId": _lk2x.get("filter_id",""),
                                           "filterValue": f"<{_si2}>"}
                                _e2 = {"EventId": _lk2x["event_id"], "ContainerId": _lk2x["container_id"]}
                                if _p2: _e2["Payload"] = _p2
                                if _lk2x.get("input_expr"): _e2["Input"] = _lk2x["input_expr"]
                                _cn2.setdefault("Slots",{})["Default"] = [{"Element":"link","Input":_si2,"Events":{"Triggers":{"OnClick":[_e2]}}}]
                            elif _lk2x and _lk2x.get("menu_id") and _lk2x.get("to_entity") and _lk2x.get("id_field"):
                                _rk2x = []
                                for _rk in _lk2x.get("ref_keys",[]):
                                    if _rk.get("type")=="field": _rk2x.append({"FromAttribute":_rk["from_attr"],"ToAttribute":_rk["to_attr"]})
                                    else: _rk2x.append({"ToAttribute":_rk["to_attr"],"FromValues":_rk.get("from_values",[])})
                                _cn2.setdefault("Slots",{})["Default"] = [{"Element":"link","Input":_si2,"Config":{"LegacyLink":{"MenuId":_lk2x["menu_id"],"RelationshipConfig":[{"RelationshipName":_lk2x["rel_name"],"FromEntity":_lk2x["from_entity"],"ToEntity":_lk2x["to_entity"],"ReferenceKeys":_rk2x}],"RelationshipName":_lk2x["rel_name"],"LabelKey":_lk2x.get("label_key",_cc['title'])}}}]
                            else:
                                _se2 = {"Element":"key-value","Input":_si2,"Config":{"AttributeType":"string"}}
                                if _ev2x and (_ev2x.get("event_id") or _ev2x.get("container_id")):
                                    _oe2 = {"EventId":_ev2x.get("event_id",""),"ContainerId":_ev2x.get("container_id","")}
                                    if _ev2x.get("filter_section") or _ev2x.get("filter_id"):
                                        _oe2["Payload"] = {"filterSection":_ev2x.get("filter_section","Filters"),"filterId":_ev2x.get("filter_id",""),"filterValue":f"<{_si2}>"}
                                    if _ev2x.get("input_expr"): _oe2["Input"] = _ev2x["input_expr"]
                                    _se2["Events"] = {"Triggers":{"OnClick":[_oe2]}}
                                _cn2.setdefault("Slots",{})["Default"] = [_se2]
                        _new_cols.append(_cn2)
                    else:
                        _lk2 = _cc.get("link")
                        if _lk2 and _lk2.get("event_type") == "event_click":
                            _oc2_payload = {}
                            if _lk2.get("filter_section") or _lk2.get("filter_id"):
                                _oc2_payload = {
                                    "filterSection": _lk2.get("filter_section", "Filters"),
                                    "filterId":      _lk2.get("filter_id", ""),
                                    "filterValue":   f"<{_cc_field}>",
                                }
                            _oc2_entry = {"EventId": _lk2["event_id"], "ContainerId": _lk2["container_id"]}
                            if _oc2_payload: _oc2_entry["Payload"] = _oc2_payload
                            if _lk2.get("input_expr"): _oc2_entry["Input"] = _lk2["input_expr"]
                            _new_cols.append({
                                "UID": f"Col_{_cc_field.replace(' ', '_')}_{_ci}",
                                "Config": {"LabelKey": _cc['title']},
                                "Slots": {"Default": [{
                                    "Element": "link",
                                    "Input": _cc_field,
                                    "Events": {"Triggers": {"OnClick": [_oc2_entry]}}
                                }]}
                            })
                        elif _lk2 and _lk2.get("menu_id") and _lk2.get("to_entity") and _lk2.get("id_field"):
                            _rk2_json = []
                            for _rk2 in _lk2.get("ref_keys", []):
                                if _rk2.get("type") == "field":
                                    _rk2_json.append({"FromAttribute": _rk2["from_attr"], "ToAttribute": _rk2["to_attr"]})
                                else:
                                    _rk2_json.append({"ToAttribute": _rk2["to_attr"], "FromValues": _rk2.get("from_values", [])})
                            _new_cols.append({
                                "UID": f"Column{_cc_field}",
                                "Config": {"Filter": {"Filterable": False}, "LabelKey": _cc['title'],
                                           "Sort": {"SortBy": _cc_field, "Sortable": True}},
                                "Slots": {"Default": [{"Element": "link", "Input": _cc_field,
                                                       "Config": {"LegacyLink": {
                                                           "MenuId": _lk2["menu_id"],
                                                           "RelationshipConfig": [{"RelationshipName": _lk2["rel_name"],
                                                               "FromEntity": _lk2["from_entity"], "ToEntity": _lk2["to_entity"],
                                                               "ReferenceKeys": _rk2_json}],
                                                           "RelationshipName": _lk2["rel_name"],
                                                           "LabelKey": _lk2.get("label_key", _cc['title'])}}}]}
                            })
                        else:
                            _cev2 = _cc.get("events")
                            _kv_slot2 = {"Element": "key-value", "Input": _cc_field, "Config": {"AttributeType": "string"}}
                            if _cev2 and (_cev2.get("event_id") or _cev2.get("container_id")):
                                _oc_ev2 = {"EventId": _cev2.get("event_id",""), "ContainerId": _cev2.get("container_id","")}
                                if _cev2.get("filter_section") or _cev2.get("filter_id"):
                                    _oc_ev2["Payload"] = {
                                        "filterSection": _cev2.get("filter_section","Filters"),
                                        "filterId":      _cev2.get("filter_id",""),
                                        "filterValue":   f"<{_cc_field}>",
                                    }
                                if _cev2.get("input_expr"): _oc_ev2["Input"] = _cev2["input_expr"]
                                _kv_slot2["Events"] = {"Triggers": {"OnClick": [_oc_ev2]}}
                            _new_cols.append({
                                "UID": f"Col_{_cc_field.replace(' ', '_')}_{_ci}",
                                "Config": {"LabelKey": _cc['title']},
                                "Slots": {"Default": [_kv_slot2]}
                            })
                _of_cfg = _of.setdefault("Config", {})
                if _new_cols:
                    _of_cfg["AutoGenerateColumns"] = False
                    _of_cfg["Columns"] = _new_cols
                else:
                    _of_cfg["AutoGenerateColumns"] = True
                    _of_cfg.pop("Columns", None)
                return _of

            # Fresh table (no orig_full_node) — build from card fields.
            columns_list = []
            if getattr(card, 'has_insights', False):
                _ins_f = getattr(card, 'insights_field', 'TicketsList') or 'TicketsList'
                _ins_a = getattr(card, 'insights_agent_id', '') or 'obe-ticketDetailFlyout'
                columns_list.append({
                    "UID": f"Column{_ins_f}",
                    "Config": {"LabelKey": "Insights"},
                    "Slots": {"Default": [
                        {"Input": "Dummy", "Config": {}, "Element": "key-value", "Style": {}},
                        {
                            "Element": "action-button",
                            "Conditions": [{"Condition": f"{_ins_f} == null", "Visible": False}],
                            "Input": f"map({{{_ins_f}: {_ins_f}}})",
                            "Config": {
                                "LabelKey": "",
                                "src": "assets/river/assets/icons/lightbulb-on.svg",
                                "ActionConfig": {"Behavior": {"Flyout": {"AgentRef": {"AgentId": _ins_a}}}}
                            },
                            "Style": {"css": {
                                "border": "none",
                                "background-color": "transparent",
                                "color": "var(--fixed-13)",
                                "white-space": "nowrap",
                                "padding-left": 0,
                                "justify-self": "end"
                            }},
                            "Events": {"Triggers": {"OnClick": [
                                {"EventId": "push-details-flyout", "ContainerId": "details-button"}
                            ]}}
                        }
                    ]}
                })
            for i, c in enumerate(card.columns):
                lk = c.get("link")
                if lk and lk.get("event_type") == "event_click":
                    _oc_payload = {}
                    if lk.get("filter_section") or lk.get("filter_id"):
                        _oc_payload = {
                            "filterSection": lk.get("filter_section", "Filters"),
                            "filterId":      lk.get("filter_id", ""),
                            "filterValue":   f"<{c['field']}>",
                        }
                    _oc_entry = {"EventId": lk["event_id"], "ContainerId": lk["container_id"]}
                    if _oc_payload: _oc_entry["Payload"] = _oc_payload
                    if lk.get("input_expr"): _oc_entry["Input"] = lk["input_expr"]
                    columns_list.append({
                        "UID": f"Col_{c['field'].replace(' ', '_')}_{i}",
                        "Config": {"LabelKey": c['title']},
                        "Slots": {"Default": [{
                            "Element": "link",
                            "Input": c["field"],
                            "Events": {"Triggers": {"OnClick": [_oc_entry]}}
                        }]}
                    })
                elif lk and lk.get("menu_id") and lk.get("to_entity") and lk.get("id_field"):
                    id_field = lk.get("id_field", "")
                    ref_keys_json = []
                    for rk in lk.get("ref_keys", []):
                        if rk.get("type") == "field":
                            ref_keys_json.append({"FromAttribute": rk["from_attr"], "ToAttribute": rk["to_attr"]})
                        else:
                            ref_keys_json.append({"ToAttribute": rk["to_attr"], "FromValues": rk.get("from_values", [])})
                    columns_list.append({
                        "UID": f"Column{c['field']}",
                        "Config": {
                            "Filter": {"Filterable": False},
                            "LabelKey": c["title"],
                            "Sort": {"SortBy": c["field"], "Sortable": True}
                        },
                        "Slots": {"Default": [{
                            "Element": "link",
                            "Input": c["field"],
                            "Config": {"LegacyLink": {
                                "MenuId": lk["menu_id"],
                                "RelationshipConfig": [{
                                    "RelationshipName": lk["rel_name"],
                                    "FromEntity": lk["from_entity"],
                                    "ToEntity": lk["to_entity"],
                                    "ReferenceKeys": ref_keys_json
                                }],
                                "RelationshipName": lk["rel_name"],
                                "LabelKey": lk.get("label_key", c["title"])
                            }}
                        }]}
                    })
                else:
                    _cev = c.get("events")
                    _slot_elem = {"Element": "key-value", "Input": c['field'], "Config": {"AttributeType": "string"}}
                    if _cev and (_cev.get("event_id") or _cev.get("container_id")):
                        _oc_ev = {"EventId": _cev.get("event_id",""), "ContainerId": _cev.get("container_id","")}
                        if _cev.get("filter_section") or _cev.get("filter_id"):
                            _oc_ev["Payload"] = {
                                "filterSection": _cev.get("filter_section","Filters"),
                                "filterId":      _cev.get("filter_id",""),
                                "filterValue":   f"<{c['field']}>",
                            }
                        if _cev.get("input_expr"): _oc_ev["Input"] = _cev["input_expr"]
                        _slot_elem["Events"] = {"Triggers": {"OnClick": [_oc_ev]}}
                    columns_list.append({
                        "UID": f"Col_{c['field'].replace(' ', '_')}_{i}",
                        "Config": {"LabelKey": c['title']},
                        "Slots": {"Default": [_slot_elem]}
                    })

            table_config = {
                "title": card.title,
                "pageSize": 10
            }
            
            if columns_list:
                table_config["AutoGenerateColumns"] = False
                table_config["Columns"] = columns_list
            else:
                table_config["AutoGenerateColumns"] = True
            
            if getattr(card, 'has_checkboxes', True):
                table_config["SelectionConfig"] = {
                    "ShowSelection": True,
                    "SupportMultiSelect": getattr(card, 'has_multiselect', True)
                }
                
            table_slots = {}
            if getattr(card, 'has_agentic', True):
                table_slots["AgenticActions"] = [
                    {
                        "Element": "agentic-actions",
                        "Slots": {
                            "Menu": [
                                {
                                    "Element": "menu-item",
                                    "Config": {
                                        "LabelKey": "Troubleshoot with AI"
                                    },
                                    "Emitters": {
                                        "click": {
                                            "actions": [
                                                {
                                                    "type": "agentic",
                                                    "config": {
                                                        "agentId": getattr(card, 'agent_id', 'ext-mhetroubleshoot'),
                                                        "question": getattr(card, 'agent_question', '') or "Analyze and troubleshoot failures for this message type",
                                                        "actionArguments": list(getattr(card, 'agent_args', []))
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            
            if getattr(card, 'has_footer', False):
                if "Default" not in table_slots:
                    table_slots["Default"] = []
                table_slots["Default"].append({
                    "Container": "footer-container",
                    "Slots": {
                        "Footer": [
                            {
                                "Container": "footer",
                                "Input": "map(*)",
                                "Config": {
                                    "PaginationConfig": {
                                        "Paginate": True,
                                        "Size": [10, 25, 50, 100],
                                        "Slot": "footer"
                                    }
                                }
                            }
                        ]
                    }
                })
                
            out = {
                "Container": "table",
                "UID": card.uid if getattr(card, 'uid', '') else f"Table_{card.cid}",
                "Init": { "Type": "value-array", "DataSourcePath": card.ds },
                "Config": table_config,
                "Style": {
                    "css": {
                        **{"width": card.css_width or "100%", "height": card.css_height,
                           "background": "white", "border": "2px solid #E8E8ED", "borderRadius": "4px",
                           "boxShadow": "0 2px 8px rgba(0,0,0,0.12)",
                           **({"padding": self._card_padding_css(card)} if self._card_padding_css(card) else {}),
                           "overflowX": "auto", "boxSizing": "border-box"},
                        **getattr(card, 'extra_css', {})
                    },
                    **{k: v for k, v in getattr(card, 'table_style', {}).items() if v}
                }
            }
            if table_slots:
                out["Slots"] = table_slots
            return out

        # ── Use original node as base when available (preserves extra Config/Style) ──
        # Fast-path: if user never edited this card, return orig_full_node verbatim.
        _orig_node = getattr(card, 'orig_full_node', None)
        if (_orig_node is not None
                and not getattr(card, '_config_edited', False)
                and not getattr(card, '_style_edited', False)
                and not getattr(card, '_slots_edited', False)
                and not getattr(card, '_structure_edited', False)):
            _out = copy.deepcopy(_orig_node)
            _strip_internal_meta(_out)
            return _out
        if getattr(card, 'orig_full_node', None):
            _of = copy.deepcopy(card.orig_full_node)
            # Patch outer wrapper CSS
            _of.setdefault("Style", {}).setdefault("css", {})["height"] = card.css_height
            if card.css_width and card.css_width not in ("auto", ""):
                _of["Style"]["css"]["width"] = card.css_width
            _cpad = self._card_padding_css(card)
            if _cpad:
                _of["Style"]["css"]["padding"] = _cpad
            # Patch title in header slot
            try:
                _of["Slots"]["header"][0]["Slots"]["Left"][0]["Config"]["LabelKey"] = card.title
            except: pass
            # Patch inner chart node (DataSource + series mappings)
            try:
                _ic = _of["Slots"]["content"][0]["Slots"]["Default"][0]
                _ic.setdefault("Init", {})["DataSourcePath"] = card.ds
                _sm = []
                for _s in card.series:
                    _fm = ({"name": _s["x_field"], "y": _s["y_field"]} if _s.get("fm_inverted")
                           else {_s["x_field"]: "name", _s["y_field"]: "y"})
                    _m = {"fieldMappings": _fm,
                          "seriesType": card.ctype, "sourceDataPath": card.ds,
                          "staticOptions": {"name": _s["name"]}}
                    if _s["color"] in ("colorByPoint", ""):
                        _m["staticOptions"]["colorByPoint"] = True
                    elif _s["color"]:
                        _m["staticOptions"]["color"] = _s["color"]
                    _sm.append(_m)
                _ic.setdefault("Config", {}).setdefault("dataMapping", {})["seriesMappings"] = _sm
                # Merge series names into existing highchartsOptions.series — preserve
                # all other per-series properties (color, zIndex, stacking, etc.)
                _hc = _ic["Config"].setdefault("highchartsOptions", {})
                _orig_hc_series = list(_hc.get("series", []))
                _merged_series = []
                for _i, _s in enumerate(card.series):
                    _base = dict(_orig_hc_series[_i]) if _i < len(_orig_hc_series) else {}
                    _base["name"] = _s["name"]
                    _merged_series.append(_base)
                _hc["series"] = _merged_series
                # Stacking: driven by card.chart_stacking (set from import and EditDialog)
                # Both orig_chart_node and orig_full_node inner chart are patched by
                # EditDialog._apply, so the deep copy already has the correct state.
                # Only set explicitly when True — never remove (orig already correct).
                if getattr(card, 'chart_stacking', False) and card.ctype in ("bar", "column"):
                    _po = _hc.setdefault("plotOptions", {})
                    for _pk in ("series", card.ctype):
                        _po.setdefault(_pk, {})["stacking"] = "normal"
            except: pass
            _strip_meta_keys(_of)
            return _of

        # ── Native chart: passthrough preserves all highchartsOptions verbatim ──
        if getattr(card, 'orig_chart_node', None):
            _cn = copy.deepcopy(card.orig_chart_node)
            _cn_css = _cn.setdefault("Style", {}).setdefault("css", {})
            if card.css_height and card.css_height not in ("auto", ""):
                _cn_css["height"] = card.css_height
            elif not card.css_height:
                _cn_css.pop("height", None)
            if card.css_width and card.css_width not in ("auto", ""):
                _cn_css["width"] = card.css_width
            return _cn

        tmpl = COMP_DEFS[card.ctype]
        hc = copy.deepcopy(tmpl["highchartsOptions"])

        sm = []
        for s in card.series:
            _fm = ({"name": s["x_field"], "y": s["y_field"]} if s.get("fm_inverted")
                   else {s["x_field"]: "name", s["y_field"]: "y"})
            mapping = {
                "fieldMappings": _fm,
                "seriesType": card.ctype,
                "sourceDataPath": card.ds,
                "staticOptions": {"name": s["name"]}
            }
            if s["color"] == "colorByPoint" or s["color"] == "": mapping["staticOptions"]["colorByPoint"] = True
            elif s["color"]: mapping["staticOptions"]["color"] = s["color"]
            sm.append(mapping)

        hc["series"] = [{"name": s["name"]} for s in card.series]

        # Apply Advanced tab overrides (zoom, margins, axes, plotOptions) from card.hc_adv.
        # Merged before stacking/legend so those always take final precedence.
        _hc_adv = getattr(card, 'hc_adv', {})
        if _hc_adv:
            for _ak, _av in _hc_adv.items():
                if isinstance(_av, dict) and isinstance(hc.get(_ak), dict):
                    _merge_target = hc[_ak]
                    for _sk, _sv2 in _av.items():
                        if isinstance(_sv2, dict) and isinstance(_merge_target.get(_sk), dict):
                            _merge_target[_sk].update(_sv2)
                        else:
                            _merge_target[_sk] = _sv2
                elif _av is not None:
                    hc[_ak] = _av

        # Apply stacking option for bar/column
        if getattr(card, 'chart_stacking', False) and card.ctype in ("bar", "column"):
            hc.setdefault("plotOptions", {}).setdefault("series", {})["stacking"] = "normal"
            hc["plotOptions"].setdefault(card.ctype, {})["stacking"] = "normal"
        elif card.ctype in ("bar", "column"):
            hc.get("plotOptions", {}).get("series", {}).pop("stacking", None)
            hc.get("plotOptions", {}).get(card.ctype, {}).pop("stacking", None)

        # Apply legend options
        hc["legend"] = {
            "enabled":       getattr(card, 'chart_legend_enabled', True),
            "layout":        getattr(card, 'chart_legend_layout',  "horizontal"),
            "verticalAlign": getattr(card, 'chart_legend_valign',  "bottom"),
            "align":         getattr(card, 'chart_legend_align',   "center"),
            "y":             getattr(card, 'chart_legend_y',       0),
        }

        # Merge orig_style_css if available (preserves flex, minWidth, etc.)
        # Always override height from current canvas size
        _base_gcss = {"flex": "1 1 0", "minWidth": "280px", "height": card.css_height, "background":"white","border":"2px solid #E8E8ED","borderRadius":"4px","boxShadow":"0 2px 8px rgba(0,0,0,0.12)","gridTemplateAreas":"\"header\" \"content\"","gridTemplateRows":"auto 1fr", "boxSizing": "border-box"}
        _orig = getattr(card, 'orig_style_css', {})
        _gcss = {**_base_gcss, **{k: v for k, v in _orig.items()
                                  if k not in ('height', 'padding', 'paddingTop', 'paddingRight',
                                               'paddingBottom', 'paddingLeft')},
                 "height": card.css_height}  # canvas height always wins
        if card.css_width and card.css_width not in ("auto", ""):
            _gcss["width"] = card.css_width  # Align Fix width always wins
        _cpad = self._card_padding_css(card)
        if _cpad: _gcss["padding"] = _cpad
        return {
            "Container":"grid",
            "Style":{"css": _gcss},
            "Slots":{
                "header":[{"Container":"header","Style":{"css":{"background":"#E8E8ED","gridArea":"header","paddingLeft":"1.5rem"}},"Slots":{"Left":[{"Element":"key-value","Input":"","Config":{"LabelKey":card.title,"keyValueSeparator":"","postValueSeparator":"","preKeySeparator":""},"Style":{"color":"#4a4a4a","fontSize":16,"fontWeight":"bold"}}]}}],
                "content":[{"Container":"flex","Style":{"css":{"height":"100%","overflow":"hidden"}},"Slots":{"Default":[{"Container":"chart","Init":{"Type":"value-array","DataSourcePath":card.ds},"Style":{"contentPadding":"0"},"Config":{"chartMetadata":{"applyAspectRatio":False,"aspectRatio":"16:9","chartWidth":"100%","detailsWidth":"0%","showChartHeader":False,"showChartTitle":False,"showHighchartsTitle":False,"showLegend":True},"dataMapping":{"seriesMappings":sm},"highchartsOptions":hc}}]}}]}}

    def _card_padding_css(self, card):
        """Return CSS padding shorthand from card.card_padding, or None if all zeros."""
        p = getattr(card, 'card_padding', {})
        vals = [p.get(k, 0) for k in ('top', 'right', 'bottom', 'left')]
        if not any(vals): return None
        if len(set(vals)) == 1: return f"{vals[0]}px"
        return f"{vals[0]}px {vals[1]}px {vals[2]}px {vals[3]}px"

    def _build_filter_element(self):
        """Build a filter-panel element from the current self.filters UI rows.
        Returns (element_dict, has_filters_bool)."""
        filter_attrs = []
        for f in self.filters:
            cfg = f.get_config()
            attr = {"UID": f"Filter_{cfg['key']}", "Input": cfg['key'], "AttributeType": "string", "LabelKey": cfg['label']}
            ph_lbl = cfg['placeholder'] or f"Enter {cfg['label']}"
            if cfg['type'] == "date":
                attr["Filter"] = {"Type": "Date-range", "Placeholder": {"LabelKey": ph_lbl}, "RangeSelect": True}
            elif cfg['type'] in ("multiselect", "singleselect"):
                filt = {
                    "Type": "Multiselect" if cfg['type'] == "multiselect" else "Singleselect",
                    "Placeholder": {"LabelKey": ph_lbl},
                }
                sl = cfg.get("static_list", "")
                if sl:
                    if sl.startswith("{:") or sl.startswith(":"):
                        filt["StaticList"] = sl
                    else:
                        try:
                            filt["StaticList"] = json.loads(sl)
                        except (json.JSONDecodeError, ValueError):
                            filt["StaticList"] = sl
                if cfg.get("entity_key"): filt["EntityKey"] = cfg["entity_key"]
                if cfg.get("entity_value"): filt["EntityValue"] = cfg["entity_value"]
                attr["Filter"] = filt
            elif cfg['type'] == "dropdown":
                attr["Filter"] = {"Type": "Select", "Placeholder": {"LabelKey": ph_lbl},
                                  "Options": [{"Id": "OPTION_1", "LabelKey": "Option 1"},
                                              {"Id": "OPTION_2", "LabelKey": "Option 2"}]}
            else:
                attr["Filter"] = {"Type": "Textbox", "Placeholder": {"LabelKey": ph_lbl}}
            filter_attrs.append(attr)
        has_filters = bool(filter_attrs)
        _filter_orig = getattr(self, 'filter_orig_node', None)
        _filter_mod  = getattr(self, '_filters_modified', False)
        if _filter_orig and not _filter_mod and has_filters:
            return copy.deepcopy(_filter_orig), has_filters
        return {
            "Element": "filter-panel",
            "Config": {
                "showFooter": True,
                "showApplyButton": True,
                "showClearButton": True,
                "Sections": [{"Type": "Object", "SectionName": "Filters", "Attributes": filter_attrs}]
            }
        }, has_filters

    def _build_fragment(self):
        # Exclude expanded slot cards (_tg_parent set) — they live inside their
        # parent tab-group's orig_full_node and must not appear as top-level items.
        # Tab-group parent cards themselves (ctype == "tab-group") are included.
        cards = sorted(
            [c for c in self.cards.values() 
             if not getattr(c, '_tg_parent', None) or c.ctype == "tab-group"],
            key=lambda c: (c.winfo_y(), c.winfo_x()))

        gap = self.layout_prefs["gap"]
        nowrap = "nowrap" in self.layout_prefs.get("chart_wrap", "wrap")
        cl = self.layout_prefs.get("content_layout", "flex-row")

        # ── Pre-group segmented cards ─────────────────────────────────────────
        ROW_THRESHOLD = 200
        seg_card_groups = {}  # seg_name -> [cards in visual order]
        for c in cards:
            if c.segment:
                seg_card_groups.setdefault(c.segment, []).append(c)

        # ── Build ordered output blocks (segments + non-segmented rows) ───────
        # Traverse cards in visual order; emit a segment block the first time a
        # segmented card is seen; collect non-segmented cards into rows.
        seen_segs = set()
        output_blocks = []   # list of ("seg", seg_name) | ("row", [cards])
        cur_row_cards = []
        row_anchor_y  = None

        def _flush_row():
            if cur_row_cards:
                output_blocks.append(("row", list(cur_row_cards)))
                cur_row_cards.clear()

        for card in cards:
            if card.segment:
                if card.segment not in seen_segs:
                    _flush_row()
                    seen_segs.add(card.segment)
                    output_blocks.append(("seg", card.segment))
                # individual segmented cards are handled by the seg block
            else:
                y = card.winfo_y()
                if not cur_row_cards:
                    cur_row_cards.append(card); row_anchor_y = y
                elif y - row_anchor_y < ROW_THRESHOLD:
                    cur_row_cards.append(card)
                else:
                    _flush_row()
                    cur_row_cards.append(card); row_anchor_y = y
        _flush_row()

        # ── Helper: build layout node for a list of non-segmented cards ───────
        def _row_node(row):
            row_json = [self._comp_json(c) for c in row if c.ctype != "filter-panel"]
            if not row_json:
                return None
            vis = [c for c in row if c.ctype != "filter-panel"]
            all_full_width = all(c.ctype in ("table", "metrics") for c in vis)
            has_charts     = any(c.ctype in CHART_TYPES and c.ctype != "metrics" for c in vis)
            has_river      = any(c.ctype in RIVER_TYPES and c.ctype != "filter-panel" for c in vis)
            if len(row_json) == 1:
                node = row_json[0]
                if vis and vis[0].ctype == "tab-group" and isinstance(node, dict):
                    node.setdefault("Style", {}).setdefault("css", {}).update(
                        {"flex": "1", "minHeight": "0"})
                return node
            elif all_full_width:
                return {"Container":"flex","Style":{"css":{"flexDirection":"column","gap":gap,"width":"100%","boxSizing":"border-box"}},"Slots":{"Default":row_json}}
            elif has_charts and not has_river:
                return {"Container":"flex","Style":{"css":{"flexDirection":"row","flexWrap":"nowrap" if nowrap else "wrap","gap":gap,"width":"100%","overflowX":"auto","boxSizing":"border-box"}},"Slots":{"Default":row_json}}
            elif has_river and not has_charts:
                if cl=="grid":
                    _gcss = {"gridTemplateColumns": self.layout_prefs.get("grid_columns","1fr 1fr"),
                             "gap": gap, "width": "100%", "boxSizing": "border-box",
                             "alignItems": "stretch"}
                    _gar = self.layout_prefs.get("grid_auto_rows", "")
                    if _gar: _gcss["gridAutoRows"] = _gar
                    w2 = {"Container":"grid","Style":{"css": _gcss}}
                    # Strip explicit heights from children so grid stretch works correctly;
                    # keep as minHeight so content doesn't collapse below its natural size.
                    for _rj in row_json:
                        if isinstance(_rj, dict):
                            _rj_css = _rj.setdefault("Style", {}).setdefault("css", {})
                            _rj_h = _rj_css.pop("height", None)
                            if _rj_h and _rj_h not in ("auto", "fit-content", ""):
                                _rj_css["minHeight"] = _rj_h
                elif cl=="flex-col": w2={"Container":"flex","Style":{"css":{"flexDirection":"column","gap":gap,"width":"100%","boxSizing":"border-box"}}}
                elif cl=="stack": w2={"Container":"stack","Style":{"css":{"gap":gap,"width":"100%","boxSizing":"border-box"}}}
                else: w2={"Container":"flex","Style":{"css":{"flexDirection":"row","flexWrap":"wrap","gap":gap,"width":"100%","alignItems":"flex-start","boxSizing":"border-box"}}}
                w2["Slots"]={"Default":row_json}; return w2
            else:
                return {"Container":"flex","Style":{"css":{"flexDirection":"row","flexWrap":"wrap","gap":gap,"width":"100%","alignItems":"flex-start","boxSizing":"border-box"}},"Slots":{"Default":row_json}}

        # ── Assemble layout_slots from output blocks ───────────────────────────
        layout_slots     = []
        header_action_node = None   # built separately — sits outside main_content
        for block_type, block_data in output_blocks:
            if block_type == "seg":
                sn = block_data
                cfg = self.segment_dirs.get(sn, {"direction":"row","gap":"0rem","section_name":sn})
                seg_cards = seg_card_groups.get(sn, [])
                _active_cards = [c for c in seg_cards if c.ctype != "filter-panel"]
                # All segment types respect the user's explicit Align Fix settings.
                # expand_fill, opt_flex, opt_minheight are honored unconditionally.
                seg_json  = []
                for _sc in seg_cards:
                    if _sc.ctype == "filter-panel": continue
                    elif _sc.ctype == "metrics":
                        seg_json.extend(self._metrics_kv_tiles(_sc))
                    elif _sc.ctype in CHART_TYPES and getattr(_sc, "orig_chart_node", None):
                        import copy as _copy
                        _cn = _copy.deepcopy(_sc.orig_chart_node)
                        # Strip css.height when expand_fill is off to avoid a circular
                        # reference (100% of unconstrained parent = 0 height).
                        if not cfg.get("expand_fill"):
                            _cn_css = _cn.get("Style", {}).get("css", {})
                            _cn_css.pop("height", None)
                        seg_json.append(_cn)
                    else:
                        seg_json.append(self._comp_json(_sc))
                # Re-inject unsupported passthrough nodes for this segment
                for _pt in getattr(self, 'passthrough_nodes', []):
                    if _pt["segment"] == sn:
                        seg_json.append(copy.deepcopy(_pt["node"]))
                if seg_json:
                    if cfg.get("container_type") == "header-action":
                        action_cards = []   # Left slot: buttons/links
                        right_cards  = []   # Right slot: segment-panel + tagged cards
                        content_cards = []
                        tg_cards = []       # tab-group — emitted as siblings after header-action
                        for _sc in _active_cards:
                            if _sc.ctype == "tab-group":
                                tg_cards.append(_sc)
                            elif _sc.ctype in ("button","button-icon","action-button","actions-popover","link") and getattr(_sc, '_ha_slot', '') != "Right":
                                _node = self._comp_json(_sc)
                                if isinstance(_node, dict):
                                    _node.pop("Style", None)
                                action_cards.append(_node)
                            elif getattr(_sc, '_ha_slot', '') == "Right" or _sc.ctype == "segment-panel":
                                right_cards.append(self._comp_json(_sc))
                            elif _sc.ctype == "metrics":
                                content_cards.extend(self._metrics_kv_tiles(_sc))
                            elif _sc.ctype in CHART_TYPES and getattr(_sc, "orig_chart_node", None):
                                import copy as _copy
                                _cn = _copy.deepcopy(_sc.orig_chart_node)
                                if not cfg.get("expand_fill"):
                                    _cn_css = _cn.get("Style", {}).get("css", {})
                                    _cn_css.pop("height", None)
                                content_cards.append(_cn)
                            else:
                                content_cards.append(self._comp_json(_sc))

                        ha_slots = {}
                        if action_cards: ha_slots["Left"] = action_cards
                        if right_cards:  ha_slots["Right"] = right_cards
                        if ha_slots:
                            node = {"Container": "header-action",
                                    "Config":  cfg.get("config", {"SectionName": sn}),
                                    "Style":   cfg.get("style",  {"css": {}}),
                                    "Slots":   ha_slots}
                            if cfg.get("events"): node["Events"] = cfg["events"]
                            header_action_node = node   # to be placed before inner_root

                        # Emit tab-group cards as siblings (after header-action) with stretch CSS
                        for _tg in tg_cards:
                            _tg_node = self._comp_json(_tg)
                            if isinstance(_tg_node, dict):
                                _tg_node.setdefault("Style", {}).setdefault("css", {}).update(
                                    {"flex": "1", "minHeight": "0"})
                            seg_json.append(_tg_node)

                        if content_cards:
                            _seg_dir = cfg.get("direction","row")
                            _seg_pad = cfg.get("padding", {})
                            _pad_str = (
                                f"{_seg_pad.get('top',0)}px {_seg_pad.get('right',0)}px "
                                f"{_seg_pad.get('bottom',0)}px {_seg_pad.get('left',0)}px"
                                if any(_seg_pad.get(k,0) for k in ('top','right','bottom','left')) else None)
                            _seg_css = {"flexDirection": _seg_dir}
                            if cfg.get("opt_width", True):
                                _seg_css["width"] = "100%"
                                if _seg_dir == "row":
                                    for _cj in content_cards:
                                        if isinstance(_cj, dict):
                                            _cj.setdefault("Style", {}).setdefault("css", {}).update(
                                                {"flex": "1", "minWidth": "0"})
                            if cfg.get("opt_boxsizing", True):
                                _seg_css["boxSizing"] = "border-box"
                            _seg_gap = cfg.get("gap", "0rem")
                            if _seg_gap not in ("0", "0px", "0rem", ""):
                                _seg_css["gap"] = _seg_gap
                            if _pad_str: _seg_css["padding"] = _pad_str
                            if _seg_dir == "row":
                                _seg_css["overflowX"] = "auto"
                            if cfg.get("expand_fill") or cfg.get("opt_flex"):
                                _seg_css["flex"] = "1"
                            if cfg.get("expand_fill") or cfg.get("opt_minheight"):
                                _seg_css["minHeight"] = "0"
                            if cfg.get("expand_fill"):
                                for _cj in content_cards:
                                    if isinstance(_cj, dict):
                                        _cj.setdefault("Style", {}).setdefault("css", {})["height"] = "100%"
                            _seg_bg = cfg.get("bg", "")
                            if _seg_bg not in ("", "transparent"):
                                _seg_css["backgroundColor"] = _seg_bg
                            _seg_css.update(cfg.get('extra_css', {}))
                            node = {"Container":"flex",
                                    "Config":{"SectionName": cfg.get("section_name", sn)},
                                    "Style":{"css": _seg_css},
                                    "Slots":{"Default": content_cards}}
                            if cfg.get("events"): node["Events"] = cfg["events"]
                            _flyout = cfg.get("flyout", {})
                            if _flyout.get("enabled"):
                                _tf_src   = _flyout.get("toggle_src", "header-action-fragment")
                                _tf_evt   = _flyout.get("toggle_evt", "")
                                _cl_pos   = _flyout.get("close_pos", "none")
                                _fc_node  = {
                                    "Container": "flyout-card",
                                    "Config": {
                                        "SectionName": cfg.get("section_name", sn),
                                        "closeButtonPosition": _cl_pos,
                                    },
                                    "Style": {"css": {"width": "100%", "overflow": "hidden"}},
                                    "Slots": {"Default": [node]},
                                }
                                if _tf_src or _tf_evt:
                                    _fc_node["Events"] = {"Listeners": {
                                        "ToggleFlyout": [{"SourceContainerId": _tf_src, "EventId": _tf_evt}]
                                    }}
                                node = _fc_node
                            layout_slots.append(node)
                    else:
                        _seg_dir = cfg.get("direction","row")
                        _seg_pad = cfg.get("padding", {})
                        _pad_str = (
                            f"{_seg_pad.get('top',0)}px {_seg_pad.get('right',0)}px "
                            f"{_seg_pad.get('bottom',0)}px {_seg_pad.get('left',0)}px"
                            if any(_seg_pad.get(k,0) for k in ('top','right','bottom','left')) else None)
                        _seg_css = {"flexDirection": _seg_dir}
                        # Per-segment optional CSS (set via Preview window; default True preserves legacy behaviour)
                        if cfg.get("opt_width", True):
                            _seg_css["width"] = "100%"
                            # In a row segment, make every child flex:1 so they spread equally
                            if _seg_dir == "row":
                                for _cj in seg_json:
                                    if isinstance(_cj, dict):
                                        _cj.setdefault("Style", {}).setdefault("css", {}).update(
                                            {"flex": "1", "minWidth": "0"})
                        if cfg.get("opt_boxsizing", True):
                            _seg_css["boxSizing"] = "border-box"
                        _seg_gap = cfg.get("gap", "0rem")
                        if _seg_gap not in ("0", "0px", "0rem", ""):
                            _seg_css["gap"] = _seg_gap
                        if _pad_str: _seg_css["padding"] = _pad_str
                        if _seg_dir == "row":
                            _seg_css["overflowX"] = "auto"
                        if cfg.get("expand_fill") or cfg.get("opt_flex"):
                            _seg_css["flex"] = "1"
                        if cfg.get("expand_fill") or cfg.get("opt_minheight"):
                            _seg_css["minHeight"] = "0"
                        if cfg.get("expand_fill"):
                            for _cj in seg_json:
                                if isinstance(_cj, dict):
                                    _cj.setdefault("Style", {}).setdefault("css", {})["height"] = "100%"
                        _seg_bg = cfg.get("bg", "")
                        if _seg_bg not in ("", "transparent"):
                            _seg_css["backgroundColor"] = _seg_bg
                        # merge any extra CSS set via Align Fix (user-defined or round-tripped)
                        _seg_css.update(cfg.get('extra_css', {}))
                        node = {"Container":"flex",
                                "Config":{"SectionName": cfg.get("section_name", sn)},
                                "Style":{"css": _seg_css},
                                "Slots":{"Default": seg_json}}
                        if cfg.get("events"): node["Events"] = cfg["events"]
                        # Wrap in flyout-card if enabled
                        _flyout = cfg.get("flyout", {})
                        if _flyout.get("enabled"):
                            _tf_src   = _flyout.get("toggle_src", "header-action-fragment")
                            _tf_evt   = _flyout.get("toggle_evt", "")
                            _cl_pos   = _flyout.get("close_pos", "none")
                            _fc_node  = {
                                "Container": "flyout-card",
                                "Config": {
                                    "SectionName": cfg.get("section_name", sn),
                                    "closeButtonPosition": _cl_pos,
                                },
                                "Style": {"css": {"width": "100%", "overflow": "hidden"}},
                                "Slots": {"Default": [node]},
                            }
                            if _tf_src or _tf_evt:
                                _fc_node["Events"] = {"Listeners": {
                                    "ToggleFlyout": [{"SourceContainerId": _tf_src, "EventId": _tf_evt}]
                                }}
                            node = _fc_node
                        layout_slots.append(node)
            else:
                node = _row_node(block_data)
                if node:
                    layout_slots.append(node)

        # Re-inject top-level (non-segmented) passthrough nodes
        for _pt in getattr(self, 'passthrough_nodes', []):
            if not _pt["segment"]:
                layout_slots.append(copy.deepcopy(_pt["node"]))

        filter_element, has_filters = self._build_filter_element()

        _mc_meta = self.main_content_meta
        # Always rebuild outer-flex CSS from live layout_prefs so designer changes
        # (gap, padding) are reflected in the export, even when meta was imported.
        _mc_css_base = dict((_mc_meta.get("style") or {}).get("css", {}))
        # Override the layout-controlled keys with current values
        _mc_css_base["flexDirection"] = "column"
        if self.layout_prefs.get("opt_width"):
            _mc_css_base["width"] = "100%"
        else:
            _mc_css_base.pop("width", None)
        # If any child segment uses flex:1 to fill remaining space, the parent
        # must also be flex:1 + minHeight:0 or the height chain is broken.
        _any_child_expand = any(
            (self.segment_dirs.get(sn, {}).get("expand_fill") or
             self.segment_dirs.get(sn, {}).get("opt_flex"))
            and seg_card_groups.get(sn)  # skip empty/phantom segments
            for sn in self.segment_dirs
        )
        if self.layout_prefs.get("opt_flex") or _any_child_expand:
            _mc_css_base["flex"] = "1"
        else:
            _mc_css_base.pop("flex", None)
        if self.layout_prefs.get("opt_minheight") or _any_child_expand:
            _mc_css_base["minHeight"] = "0"
        else:
            _mc_css_base.pop("minHeight", None)
        if self.layout_prefs.get("opt_boxsizing"):
            _mc_css_base["boxSizing"] = "border-box"
        else:
            _mc_css_base.pop("boxSizing", None)
        # Always write gap explicitly (even "0") so framework defaults are suppressed
        _mc_css_base["gap"] = gap if gap not in ("0px", "") else "0"
        if self.layout_prefs["padding"] not in ("0px", "0", ""):
            _mc_css_base["padding"]   = self.layout_prefs["padding"]
        else:
            _mc_css_base.pop("padding", None)
        if self.layout_prefs["bg"] not in ("transparent", ""):
            # Use backgroundColor (canonical camelCase); remove shorthand "background" to avoid duplication
            _mc_css_base.pop("background", None)
            _mc_css_base["backgroundColor"] = self.layout_prefs["bg"]
        else:
            _mc_css_base.pop("backgroundColor", None)
            _mc_css_base.pop("background", None)
        _mc_jc = self.layout_prefs.get("jc", "")
        if _mc_jc:
            _mc_css_base["justifyContent"] = _mc_jc
        else:
            _mc_css_base.pop("justifyContent", None)
        _mc_ht = self.layout_prefs.get("height", "")
        if _mc_ht:
            _mc_css_base["height"] = _mc_ht
        else:
            _mc_css_base.pop("height", None)
        _mc_style = {"css": _mc_css_base}
        main_content = {"Container": "flex", "Style": _mc_style, "Slots": {"Default": layout_slots}}
        if _mc_meta.get("config"): main_content["Config"] = _mc_meta["config"]
        if _mc_meta.get("events"): main_content["Events"] = _mc_meta["events"]

        # Build flyout-card wrapper merging any imported meta
        def _flyout_card(side_key):
            fm = self.flyout_card_meta
            node = {"Container": "flyout-card",
                    "Config": fm.get("config") or {"closeButtonPosition": "right"},
                    "Style":  fm.get("style")  or {"padding": "0px", "width": "23vw"},
                    "Slots":  {"Default": [filter_element]}}
            if fm.get("events"): node["Events"] = fm["events"]
            return node

        pos = self.filter_pos.get()
        _sb_right_passthrough = copy.deepcopy(getattr(self, 'sidebar_right_slot', []))
        if pos == "left":
            root_container = "sidebar"
            slots = {"Left": [_flyout_card("left")] if has_filters else [], "Default": [main_content]}
            if _sb_right_passthrough:
                slots["Right"] = _sb_right_passthrough
        elif pos == "right":
            root_container = "sidebar"
            slots = {"Default": [main_content], "Right": [_flyout_card("right")] if has_filters else []}
        elif pos == "flex-left":
            root_container = "flex"
            _fc_children = ([_flyout_card("left")] if has_filters else []) + [main_content]
            slots = {"Default": _fc_children}
        elif pos == "flex-right":
            root_container = "flex"
            _fc_children = [main_content] + ([_flyout_card("right")] if has_filters else [])
            slots = {"Default": _fc_children}
        elif pos == "none":
            root_container = "flex"
            slots = {"Default": [main_content]}
        else: # top
            root_container = "flex"
            slots = {"Default": [filter_element, main_content] if has_filters else [main_content]}

        _sb_meta = self.sidebar_meta
        _coll = self.layout_prefs.get("sb_collapsible", True)
        if root_container == "sidebar" and _sb_meta.get("config"):
            _sb_config = dict(_sb_meta["config"])
            for _side in ("Left", "Right"):
                if _side in _sb_config and isinstance(_sb_config[_side], dict):
                    _sb_config[_side] = dict(_sb_config[_side])
                    _sb_config[_side]["Collapsible"] = _coll
            _sb_style  = _sb_meta.get("style") or {"css": {"gap": "0"}}
        elif root_container == "sidebar":
            _sb_config = {"Left": {"Collapsible": _coll}, "Right": {"Collapsible": _coll}}
            _sb_style  = {"css": {"gap": "0"}}
        elif pos in ("flex-left", "flex-right"):
            _sb_config = {}
            _sb_style  = {"css": {"flexDirection": "row", "flex": "1", "minHeight": "0", "overflow": "hidden", "gap": "0"}}
        else:
            _sb_config = {}
            _sb_style  = {"css": {"gap": "0"}}
        inner_root = {
            "Container": root_container,
            "Config": _sb_config,
            "Style":  _sb_style,
            "Slots":  slots
        }

        frag_config  = self.root_fragment_config or {}
        _frag_init   = copy.deepcopy(
            getattr(self, 'fragment_init_orig', None)
            or {"Type": "agentic-api", "DefaultValues": {"Filters": "{:Filters}"}}
        )
        if pos == "none":
            _frag_init.get("DefaultValues", {}).pop("Filters", None)
            if not _frag_init.get("DefaultValues"):
                _frag_init.pop("DefaultValues", None)

        if self.wrap_flyout.get():
            frag_default = ([header_action_node] if header_action_node else []) + [inner_root]
            return {
                "Fragment": {
                    "Container": "flyout-card",
                    "Init": _frag_init,
                    "Config": { "closeButtonPosition": "left", "showCloseButton": True, "hideFlyoutCardByDefault": False },
                    "Style": { "width": "100vw", "padding": "0px" },
                    "Events": {
                        "Triggers": {
                            "CloseFlyout": [{ "EventId": "close-details-flyout", "ContainerId": "details-flyout" }]
                        }
                    },
                    "Slots": {"Default": frag_default}
                }
            }
        elif root_container == "sidebar":
            if header_action_node:
                # header-action belongs inside main_content (the sidebar's Default flex child),
                # not wrapped outside the sidebar at fragment level — that breaks the layout
                main_content["Slots"]["Default"].insert(0, header_action_node)
            sb_frag = {
                "Container": "sidebar",
                "Init":   _frag_init,
                "Style":  inner_root["Style"],
                "Config": inner_root.get("Config", {}),
                "Events": {},
                "Slots":  inner_root["Slots"]
            }
            return {"Fragment": sb_frag}
        elif pos in ("flex-left", "flex-right"):
            # Flat flex column: header-action (if any) + flex row (flyout-card + main content)
            frag_default = ([header_action_node] if header_action_node else []) + [inner_root]
            frag = {"Fragment": {
                    "Container": "flex",
                    "Init":      _frag_init,
                    "Style":     {"css": {"flexDirection": "column", "gap": "0", "flex": "1", "minHeight": "0"}},
                    "Slots":     {"Default": frag_default}
                }}
            if frag_config:
                frag["Fragment"]["Config"] = frag_config
            return frag
        else:
            frag_default = ([header_action_node] if header_action_node else []) + [inner_root]
            frag = {"Fragment": {
                    "Container": "flex",
                    "Init":      _frag_init,
                    "Style":     {"css": {"flexDirection": "column", "gap": "0"}},
                    "Slots":     {"Default": frag_default}
                }}
            if frag_config:
                frag["Fragment"]["Config"] = frag_config
            return frag

    # ── Variable Pool ─────────────────────────────────────────────────────────

    def _get_pool_ds_keys(self) -> list:
        """All DataSourcePath keys available: pool + existing cards."""
        pool_keys = list(self._var_pool.keys())
        card_keys = [c.ds for c in self.cards.values() if c.ds]
        return sorted(set(pool_keys + card_keys))

    def _get_pool_bvar_map(self) -> dict:
        """ds → bvar lookup: pool entries + existing cards."""
        m = {c.ds: c.bvar for c in self.cards.values() if c.ds and c.bvar}
        m.update(self._var_pool)          # pool takes precedence
        return m

    def _update_pool_btn(self):
        n = len(self._var_pool)
        try:
            fg = "#86EFAC" if n else "#94A3B8"
            self._pool_btn.config(
                text=f"🗃 Variable Pool ({n})",
                fg=fg)
        except Exception:
            pass

    def _parse_action_json(self, raw: str) -> dict:
        """
        Extract the dataMap dict from an Action JSON string.
        Handles several nesting formats:
          • {"dataMap": {...}}
          • {"type":"renderUI", "dataMap": {...}}
          • {"agentContentsAction": {"dataMap": {...}}}
          • An array of action objects — first renderUI wins.
          • Nested under "input" or "output"
        Returns {DataSourcePath: backendVar} or raises ValueError.
        """
        raw = re.sub(r'"\{:([^}]+)\}"', r'"{:\1}"', raw)  # normalize template vars
        data = json.loads(raw)

        def _find_datamap(obj):
            if isinstance(obj, dict):
                if "dataMap" in obj and isinstance(obj["dataMap"], dict):
                    return obj["dataMap"]
                for v in obj.values():
                    r = _find_datamap(v)
                    if r is not None: return r
            elif isinstance(obj, list):
                for item in obj:
                    r = _find_datamap(item)
                    if r is not None: return r
            return None

        dm = _find_datamap(data)
        if dm is None:
            raise ValueError(
                "No 'dataMap' key found.\n\n"
                "Expected format (renderUI action):\n"
                '{\n  "type": "renderUI",\n'
                '  "dataMap": {\n'
                '    "JournalData": "object::JournalDataJs.result",\n'
                '    "TimelineSummary": "object::TimelineJs.result"\n'
                '  }\n}'
            )
        return {k: v for k, v in dm.items() if k and isinstance(v, str)}

    def _import_action_json_dialog(self):
        win = tk.Toplevel(self)
        win.title("Import Action JSON — Variable Pool")
        win.geometry("860x620")
        win.configure(bg=BG)
        win.grab_set()

        # Header
        hdr = tk.Frame(win, bg="#0F172A", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🗃  Action JSON  →  Variable Pool",
                 bg="#0F172A", fg="white",
                 font=("Helvetica", 12, "bold")).pack(side="left", padx=16)
        n = len(self._var_pool)
        if n:
            tk.Label(hdr, text=f"  Pool has {n} variable(s) from: {self._var_pool_source}",
                     bg="#0F172A", fg="#86EFAC",
                     font=("Helvetica", 9)).pack(side="left")

        # Info banner
        info = tk.Frame(win, bg="#EFF6FF", pady=6)
        info.pack(fill="x")
        tk.Label(info,
                 text="ⓘ  Paste your renderUI Action JSON below.  The dataMap keys become available\n"
                      "    as dropdown choices in every Data Source / DataSourcePath field on this canvas.",
                 bg="#EFF6FF", fg="#1D4ED8",
                 font=("Helvetica", 9), justify="left").pack(anchor="w", padx=12)

        # Text area
        txt_f = tk.Frame(win, bg=BG)
        txt_f.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        txt = scrolledtext.ScrolledText(txt_f, font=("Courier", 10),
                                         bg=CARD_BG, fg=DARK, wrap="none",
                                         relief="flat",
                                         highlightthickness=1,
                                         highlightbackground=BORDER)
        txt.pack(fill="both", expand=True)
        # Pre-fill with existing pool source or example
        if self._var_pool:
            ex = json.dumps({"type": "renderUI", "name": "mheDashboardFragment",
                              "dataMap": self._var_pool}, indent=2)
            txt.insert("1.0", ex)
        else:
            ex = json.dumps({"type": "renderUI", "name": "mheDashboardFragment",
                              "dataMap": {
                                  "JournalData":       "object::JournalDataJs.result",
                                  "TimelineSummary":   "object::TimelineJs.result",
                                  "Filters":           "object::Filters",
                              }}, indent=2)
            txt.insert("1.0", ex)

        # Pool preview panel
        preview_f = tk.LabelFrame(win, text="Current Variable Pool",
                                    bg=BG, fg=DARK,
                                    font=("Helvetica", 9, "bold"),
                                    padx=8, pady=4)
        preview_f.pack(fill="x", padx=12, pady=(0, 4))
        self._pool_preview_txt = tk.Text(preview_f, height=5,
                                          bg=CARD_BG, fg=DARK,
                                          font=("Courier", 9), relief="flat",
                                          state=tk.DISABLED)
        self._pool_preview_txt.pack(fill="x")
        self._refresh_pool_preview()

        # Status
        status_var = tk.StringVar(value="")
        tk.Label(win, textvariable=status_var, bg=BG, fg="#16A34A",
                 font=("Helvetica", 9)).pack(anchor="w", padx=16)

        # Buttons
        btn_f = tk.Frame(win, bg=BG)
        btn_f.pack(pady=8)

        def _load():
            raw = txt.get("1.0", tk.END).strip()
            if not raw:
                messagebox.showwarning("Empty", "Paste an Action JSON first.", parent=win)
                return
            try:
                dm = self._parse_action_json(raw)
                self._var_pool = dm
                self._var_pool_source = f"{len(dm)} keys loaded"
                self._update_pool_btn()
                self._refresh_pool_preview()
                status_var.set(f"✓  Loaded {len(dm)} dataMap variable(s) into pool.")
                # Show list
                keys_str = "\n".join(f"  • {k}  →  {v}" for k, v in dm.items())
                messagebox.showinfo("Pool Updated",
                    f"Variable pool updated with {len(dm)} key(s):\n\n{keys_str}\n\n"
                    "These now appear as dropdowns in all Data Source fields.",
                    parent=win)
            except (json.JSONDecodeError, ValueError) as exc:
                messagebox.showerror("Parse Error", str(exc), parent=win)

        def _clear():
            if messagebox.askyesno("Clear Pool",
                                    "Remove all variables from the pool?", parent=win):
                self._var_pool = {}
                self._var_pool_source = ""
                self._update_pool_btn()
                self._refresh_pool_preview()
                status_var.set("Pool cleared.")

        tk.Button(btn_f, text="📥  Load into Pool", bg="#065F46", fg="black",
                  relief="flat", font=("Helvetica", 10, "bold"), padx=16, pady=6,
                  cursor="hand2", command=_load).pack(side="left", padx=6)
        tk.Button(btn_f, text="🗑 Clear Pool", bg="#7f1d1d", fg="black",
                  relief="flat", font=("Helvetica", 10), padx=14, pady=6,
                  cursor="hand2", command=_clear).pack(side="left", padx=6)
        tk.Button(btn_f, text="Close", bg=BORDER, fg=DARK,
                  relief="flat", font=("Helvetica", 10), padx=14, pady=6,
                  cursor="hand2", command=win.destroy).pack(side="left", padx=6)

    def _refresh_pool_preview(self):
        try:
            t = self._pool_preview_txt
            t.config(state=tk.NORMAL)
            t.delete("1.0", tk.END)
            if self._var_pool:
                for ds, bvar in self._var_pool.items():
                    t.insert(tk.END, f"{ds:<30}  →  {bvar}\n")
            else:
                t.insert(tk.END, "(empty — load an Action JSON to populate)")
            t.config(state=tk.DISABLED)
        except Exception:
            pass

    def _action_json(self):
        data_map = {c.ds: c.bvar for c in self.cards.values()}
        if self.filters and self.filter_pos.get() != "none": data_map["Filters"] = "object::Filters"
        
        if any(getattr(c, 'has_footer', False) for c in self.cards.values()):
            data_map["SearchAfterKey"] = "object::SearchAfterKeyJs.result"
            
        return {"type": "renderUI", "name": "mheDashboardFragment", "input": {}, "output": {}, "unsupportedOnUI": True, "inputJSON": "mheDashboardFragment", "dataMap": data_map, "description": "Render MHE Dashboard UI", "bundleNames": ["com-manh-cp-dcorder:labels", "com-manh-cp-dcorder:seeddata"], "outputVariableName": "response", "allowedPostFailure": True}

    def _show_json(self, title, raw_str, filename):
        try:
            with open(filename, "w") as f: f.write(raw_str)
        except Exception as e: print(f"Warning: Could not save backup file {filename}: {e}")
        w = tk.Toplevel(self); w.title(title); w.geometry("1000x750"); w.configure(bg=BG)
        w.lift(); w.attributes("-topmost", True); w.after(100, lambda: w.attributes("-topmost", False))
        txt = scrolledtext.ScrolledText(w, font=("Courier", 9), bg=SIDEBAR, fg="#F8FAFC", wrap="none"); txt.pack(fill="both", expand=True, padx=16, pady=8); txt.insert("1.0", raw_str)
        btns = tk.Frame(w, bg=BG); btns.pack(pady=8)
        tk.Button(btns, text="📋  Copy JSON", bg=BTN_OK_BG, fg=BTN_OK_FG, font=("Helvetica", 10, "bold"), padx=14, pady=6, cursor="hand2", command=lambda:[self.clipboard_clear(), self.clipboard_append(raw_str), messagebox.showinfo("Success", f"{title.split()[1]} copied to clipboard!", parent=w)]).pack(side="left", padx=6)
        tk.Button(btns, text="Close", bg=BORDER, fg=DARK, font=("Helvetica", 10), padx=14, pady=6, cursor="hand2", command=w.destroy).pack(side="left", padx=6)

    # ── HTML PREVIEW ─────────────────────────────────────────────────
    def _html_preview(self):
        """Open the preview in the browser. Uses a live HTTP server so the page
        auto-refreshes every 400 ms whenever the fragment changes."""
        import webbrowser

        # Start (or reuse) the live server
        if not _AF_HAS_HTTPSERVER:
            messagebox.showinfo("Preview", "socketserver not available.")
            return
        if not getattr(self, '_live_preview_server', None):
            srv = _AFPreviewServer()
            srv.start()
            self._live_preview_server = srv
        else:
            srv = self._live_preview_server

        # Build and push initial HTML
        try:
            frag = self._build_fragment()
        except Exception as e:
            messagebox.showerror("Preview Error",
                f"Could not build fragment:\n{e}\n\nAdd at least one component first.")
            return
        html = self._build_preview_html(json.dumps(frag, indent=2))
        html = self._inject_live_reload_script(html, srv)
        srv.update(html)

        # Open in browser — the page polls /version every 400 ms and auto-reloads
        webbrowser.open(srv.url)

    def _build_preview_html(self, frag_json_str):
        tpl = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fragment Preview</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F1F5F9;color:#1E293B;display:flex;flex-direction:column}
/* ── Manhattan chrome ── */
.m-screen{flex:1;min-height:0;display:flex;flex-direction:column}
.m-navbar{background:#1E293B;color:white;padding:0 20px;height:52px;min-height:52px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.m-navbar-title{font-size:15px;font-weight:600}
.m-navbar-logo{width:28px;height:28px;background:#2563EB;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:white}
.m-body{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden}
/* ── Header action bar (matches header-action.component.scss) ── */
.m-header-action{background:#F7F6F9;box-shadow:0 2px 8px rgba(0,0,0,0.12);height:50px;min-height:50px;display:flex;align-items:center;padding:0 16px;gap:8px;flex-shrink:0;z-index:10}
.m-header-action .left-actions{display:flex;align-items:center;gap:8px;flex:1;min-width:0}
.m-header-action .middle-actions{display:flex;align-items:center;gap:8px}
.m-header-action .right-actions{display:flex;align-items:center;gap:8px}
.m-header-action .m-btn{flex-shrink:0;flex-grow:0}
/* ── Sidebar layout ── */
.m-sidebar-wrap{flex:1;display:flex;flex-direction:row;overflow:hidden;min-height:0}
.m-sidebar-aside{flex-shrink:0;overflow-y:auto;background:#fff;border-right:1px solid #1E293B;display:flex;flex-direction:column}
.m-sidebar-content{flex:1;min-width:0;overflow:auto;display:flex;flex-direction:column}
/* ── Table fill ── */
.m-table-wrap{flex:1;min-width:0;min-height:0}
/* ── Flyout card ── */
.m-flyout{overflow:hidden;background:#fff;border-right:1px solid #1E293B;transition:width .25s ease;flex-shrink:0;display:flex;flex-direction:column}
.m-flyout-header{padding:12px 16px;border-bottom:1px solid #1E293B;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.m-flyout-header span{font-size:13px;font-weight:600;color:#1E293B}
.m-flyout-body{flex:1;overflow-y:auto}
/* ── Card ── */
.m-card{background:white;border:1px solid #1E293B;border-radius:8px;overflow:hidden;padding:16px}
/* ── Table ── */
.m-table-wrap{background:white;border:1px solid #1E293B;border-radius:8px;overflow:hidden;display:flex;flex-direction:column}
.m-table-scroll{flex:1;overflow:auto;min-height:0}
.m-table{width:100%;border-collapse:collapse;font-size:13px}
.m-table thead tr{background:#F8FAFC;border-bottom:2px solid #1E293B}
.m-table th{padding:10px 14px;text-align:left;font-size:12px;font-weight:600;color:#475569;white-space:nowrap;position:sticky;top:0;background:#F8FAFC}
.m-table th.sortable{cursor:pointer;user-select:none}
.m-table th.sortable:hover{background:#EFF6FF}
.m-table th .sort-icon{margin-left:4px;opacity:.4;font-size:10px}
.m-table th .filter-icon{margin-left:2px;opacity:.35;font-size:10px}
.m-table tbody tr{border-bottom:1px solid #F1F5F9}
.m-table tbody tr:hover{background:#F8FAFC}
.m-table td{padding:10px 14px;color:#374151;font-size:13px}
.m-table td.cb-cell{width:40px;padding:10px 10px}
.m-table th.cb-cell{width:40px;padding:10px 10px}
.m-table-footer{background:#F8FAFC;border-top:1px solid #1E293B;padding:8px 14px;display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#64748B;flex-shrink:0}
.m-pagination{display:flex;gap:4px;align-items:center}
.m-pagination button{padding:4px 9px;border:1px solid #CBD5E1;border-radius:4px;background:white;font-size:12px;cursor:pointer;color:#374151}
.m-pagination button:hover{background:#F1F5F9}
.m-pagination .active{background:#2563EB;color:white;border-color:#2563EB}
/* ── Chart ── */
.m-chart-wrap{background:white;border:1px solid #1E293B;border-radius:18px;overflow:hidden;width:100%;min-width:0;display:flex;flex-direction:column;box-shadow:0 2px 10px rgba(15,23,42,.05)}
.m-chart-header{background:#f8fafc;padding:12px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1E293B}
.m-chart-header-title{font-size:14px;font-weight:700;color:#0F172A}
.m-chart-body{padding:18px;display:flex;align-items:center;justify-content:center;flex:1;min-height:0;background:#fff}
/* ── Buttons (mawc-button) ── */
.m-btn{padding:6px 14px;border:none;border-radius:4px;font-size:13px;font-weight:500;cursor:pointer;display:inline-flex;align-items:center;gap:6px;white-space:nowrap;line-height:1.4}
.m-btn-primary{background:#2563EB;color:white}
.m-btn-secondary{background:#475569;color:white}
.m-btn-ghost{background:transparent;border:1px solid #CBD5E1;color:#374151}
.m-btn-stroked{background:transparent;border:1px solid #2563EB;color:#2563EB}
/* ── Actions popover ── */
.m-actions-popover{position:relative;display:inline-flex}
.m-actions-popover-trigger{padding:6px 10px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;cursor:pointer;background:white;display:flex;align-items:center;gap:4px;color:#374151}
.m-actions-popover-menu{position:absolute;top:100%;right:0;background:white;border:1px solid #1E293B;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.12);min-width:160px;z-index:100;display:none}
.m-actions-popover-menu.open{display:block}
.m-actions-popover-item{padding:8px 14px;font-size:13px;color:#374151;cursor:pointer;display:block}
.m-actions-popover-item:hover{background:#F1F5F9}
/* ── Filter panel (matches filter-panel.component) ── */
.m-filter-panel{display:flex;flex-direction:column;height:100%;background:#fff}
.m-filter-panel-top{padding:8px 12px;border-bottom:1px solid #1E293B;display:flex;align-items:center;justify-content:flex-end}
.m-filter-clearall{font-size:12px;color:#2563EB;cursor:pointer;background:none;border:none;padding:2px 6px}
.m-filter-body{flex:1;overflow-y:auto;padding:10px 12px}
.m-filter-section{margin-bottom:12px}
.m-filter-section-header{padding:6px 0;font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;justify-content:space-between;cursor:pointer;border-bottom:1px solid #F1F5F9;margin-bottom:8px}
.m-filter-section-body{padding:2px 0}
.m-filter-field{margin-bottom:10px}
.m-filter-label{font-size:12px;color:#374151;margin-bottom:4px;font-weight:500}
.m-filter-input{width:100%;padding:6px 10px;background:white;border:1px solid #CBD5E1;border-radius:4px;color:#1E293B;font-size:12px;outline:none;box-sizing:border-box}
.m-filter-input:focus{border-color:#2563EB;box-shadow:0 0 0 2px rgba(37,99,235,.1)}
.m-filter-actions{padding:10px 12px;border-top:1px solid #1E293B;display:flex;gap:8px}
.m-btn-apply{background:#2563EB;color:white;padding:8px 0;border:none;border-radius:4px;font-size:13px;font-weight:600;cursor:pointer;flex:1}
.m-btn-clear{background:transparent;border:1px solid #CBD5E1;color:#64748B;padding:8px 16px;border-radius:4px;font-size:13px;cursor:pointer}
/* ── Key-value element ── */
.m-kv-wrap{display:flex;gap:4px;align-items:baseline;flex-wrap:wrap}
.m-kv-label{font-size:12px;color:#64748B}
.m-kv-sep{font-size:12px;color:#94A3B8}
.m-kv-value{font-size:13px;color:#111827;font-weight:500}
/* ── Link element ── */
.m-link{color:#2563EB;text-decoration:none;font-size:13px}
.m-link:hover{text-decoration:underline}
/* ── Text element ── */
.m-text{font-size:13px;color:#374151}
/* ── Input element ── */
.m-input-wrap{display:flex;flex-direction:column;gap:3px}
.m-input-label{font-size:12px;color:#64748B;font-weight:500}
.m-input{padding:7px 10px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;color:#1E293B;background:white;width:100%;outline:none}
.m-input:focus{border-color:#2563EB;box-shadow:0 0 0 2px rgba(37,99,235,.1)}
/* ── Select element ── */
.m-select{padding:7px 10px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;color:#1E293B;background:white;min-width:140px;cursor:pointer;outline:none}
/* ── Combobox element ── */
.m-combobox{padding:7px 10px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;color:#1E293B;background:white;min-width:140px;cursor:pointer;outline:none}
/* ── Pill / badge ── */
.m-pill{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:#DBEAFE;color:#1D4ED8}
/* ── Progress bar ── */
.m-progress-wrap{display:flex;flex-direction:column;gap:4px;width:100%}
.m-progress-label{font-size:12px;color:#64748B;font-weight:500}
.m-progress-track{background:#1E293B;border-radius:9999px;height:10px;overflow:hidden;width:100%}
.m-progress-fill{background:#2563EB;height:100%;border-radius:9999px;transition:width .3s ease}
/* ── Value / value-unit ── */
.m-value{font-size:22px;font-weight:700;color:#111827}
.m-value-unit{display:inline-flex;align-items:baseline;gap:3px}.m-value-unit .num{font-size:22px;font-weight:700;color:#111827}.m-value-unit .unit{font-size:13px;color:#64748B}
/* ── Icon ── */
.m-icon{display:inline-flex;align-items:center;justify-content:center;font-size:20px;color:#374151;width:28px;height:28px}
/* ── Message ── */
.m-message{display:flex;align-items:flex-start;gap:8px;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:6px;padding:10px 14px;font-size:13px;color:#1E40AF}
/* ── Currency ── */
.m-currency{font-size:20px;font-weight:700;color:#16A34A}
/* ── Key-value detail ── */
.m-kvd-wrap{display:flex;flex-direction:column;gap:2px}.m-kvd-label{font-size:12px;color:#64748B;font-weight:500}.m-kvd-value{font-size:13px;color:#111827;font-weight:500}
/* ── Search ── */
.m-search-wrap{position:relative;display:inline-flex;align-items:center;width:100%;max-width:240px}
.m-search-input{padding:7px 10px 7px 32px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;width:100%;outline:none;background:white}
.m-search-icon{position:absolute;left:9px;color:#94A3B8;font-size:14px;pointer-events:none}
/* ── Toggle button ── */
.m-toggle-wrap{display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none}
.m-toggle-track{width:38px;height:20px;background:#CBD5E1;border-radius:10px;position:relative;transition:background .2s;flex-shrink:0}
.m-toggle-thumb{width:16px;height:16px;background:white;border-radius:50%;position:absolute;top:2px;left:2px;transition:left .2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
/* ── Numeric stepper ── */
.m-stepper{display:inline-flex;align-items:center;border:1px solid #CBD5E1;border-radius:4px;overflow:hidden}
.m-stepper button{background:#F1F5F9;border:none;padding:6px 10px;font-size:14px;cursor:pointer;color:#374151}
.m-stepper input{width:52px;text-align:center;border:none;border-left:1px solid #CBD5E1;border-right:1px solid #CBD5E1;padding:6px 4px;font-size:13px;outline:none}
/* ── Currency input ── */
.m-currinput{display:inline-flex;align-items:center;border:1px solid #CBD5E1;border-radius:4px;overflow:hidden}
.m-currinput .sym{background:#F1F5F9;padding:7px 10px;font-size:13px;color:#16A34A;font-weight:600;border-right:1px solid #CBD5E1}
.m-currinput input{border:none;padding:7px 10px;font-size:13px;outline:none;width:90px}
/* ── Date select ── */
.m-datesel{display:flex;flex-direction:column;gap:3px}.m-datesel label{font-size:12px;color:#64748B;font-weight:500}
.m-datesel input{padding:7px 10px;border:1px solid #CBD5E1;border-radius:4px;font-size:13px;outline:none;color:#1E293B}
/* ── Related link ── */
.m-related-link{display:inline-flex;align-items:center;gap:4px;color:#7C3AED;font-size:13px;text-decoration:none;cursor:pointer}
.m-related-link:hover{text-decoration:underline}
/* ── Button icon ── */
.m-btn-icon{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:#2563EB;border:none;cursor:pointer;color:white;font-size:16px}
/* ── Action button ── */
.m-action-btn{padding:7px 16px;background:#EA580C;color:white;border:none;border-radius:4px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
/* ── Quick filter ── */
.m-quick-filter{display:flex;flex-wrap:wrap;gap:6px}
.m-qf-chip{padding:4px 12px;border-radius:9999px;font-size:12px;cursor:pointer;border:1px solid #CBD5E1;background:white;color:#374151;font-weight:500}
.m-qf-chip.active{background:#2563EB;color:white;border-color:#2563EB}
/* ── Segment panel ── */
.m-segment-panel{display:flex;align-items:center;flex-shrink:0;border-bottom:2px solid #1E293B;margin-bottom:0;gap:4px;flex-wrap:wrap}
.m-seg-label{font-size:13px;color:#4a4a4a;padding:8px 8px 8px 0;white-space:nowrap;font-weight:500}
.m-seg-tab{padding:8px 16px;font-size:13px;cursor:pointer;color:#64748B;border-bottom:2px solid transparent;margin-bottom:-2px;font-weight:500;white-space:nowrap}
.m-seg-tab.active{color:#2563EB;border-bottom-color:#2563EB;background:#EFF6FF;border-radius:4px 4px 0 0}
/* ── Tab group ── */
.m-tab-group{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.m-tab-header{display:flex;border-bottom:2px solid #1E293B;background:#fff;flex-shrink:0}
.m-tab-item{padding:10px 18px;font-size:13px;cursor:pointer;color:#64748B;border-bottom:3px solid transparent;margin-bottom:-2px;white-space:nowrap;font-weight:500;transition:color .15s}
.m-tab-item.active{color:#2563EB;border-bottom-color:#2563EB;font-weight:600}
.m-tab-pane{display:none;flex:1;overflow:auto;min-height:0}.m-tab-pane.active{display:flex;flex-direction:column}
/* ── List ── */
.m-list{display:flex;flex-direction:column;gap:0}
.m-list-item{border-bottom:1px solid #F1F5F9;padding:8px 12px;display:flex;flex-direction:column;gap:4px}
.m-list-item:last-child{border-bottom:none}
.m-list-item:hover{background:#F8FAFC}
/* ── Carousel ── */
.m-carousel-wrap{display:flex;flex-direction:column;gap:8px;width:100%;overflow:hidden}
.m-carousel-track-wrap{overflow:hidden;position:relative}
.m-carousel-track{display:flex;gap:12px;transition:transform .3s ease}
.m-carousel-slide{flex-shrink:0;background:#F8FAFC;border:1px solid #1E293B;border-radius:8px;padding:12px;min-height:80px;display:flex;align-items:center;justify-content:center;color:#64748B;font-size:13px}
.m-carousel-controls{display:flex;align-items:center;justify-content:center;gap:8px}
.m-carousel-btn{width:30px;height:30px;border-radius:50%;background:white;border:1px solid #CBD5E1;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;color:#374151}
.m-carousel-btn:hover{background:#F1F5F9}
.m-carousel-dots{display:flex;gap:4px;align-items:center}
.m-carousel-dot{width:7px;height:7px;border-radius:50%;background:#CBD5E1;cursor:pointer}
.m-carousel-dot.active{background:#2563EB}
/* ── Accordion ── */
.m-accordion{display:flex;flex-direction:column;border:1px solid #1E293B;border-radius:6px;overflow:hidden}
.m-acc-item{border-bottom:1px solid #1E293B}.m-acc-item:last-child{border-bottom:none}
.m-acc-header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;cursor:pointer;background:#F8FAFC;font-size:13px;font-weight:600;color:#1E293B;user-select:none}
.m-acc-header:hover{background:#F1F5F9}
.m-acc-body{display:none;padding:12px 16px;background:#fff;font-size:13px;color:#374151}
.m-acc-item.open .m-acc-body{display:block}
/* ── Expandable ── */
.m-expandable{border:1px solid #1E293B;border-radius:6px;overflow:hidden}
.m-exp-header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;cursor:pointer;background:#F8FAFC;font-size:13px;font-weight:600;color:#1E293B;user-select:none}
.m-exp-body{padding:12px 16px;background:#fff;font-size:13px;color:#374151}
/* ── Section ── */
.m-section{display:flex;flex-direction:column;gap:8px}
.m-section-title{font-size:14px;font-weight:600;color:#1E293B;padding-bottom:6px;border-bottom:1px solid #1E293B}
/* ── Banner ── */
.m-banner{display:flex;align-items:center;gap:10px;padding:10px 16px;border-radius:6px;font-size:13px;border:1px solid transparent}
.m-banner-info{background:#EFF6FF;border-color:#BFDBFE;color:#1E40AF}
.m-banner-warning{background:#FFFBEB;border-color:#FDE68A;color:#92400E}
.m-banner-error{background:#FEF2F2;border-color:#FECACA;color:#991B1B}
.m-banner-success{background:#F0FDF4;border-color:#BBF7D0;color:#14532D}
/* ── Stack ── */
.m-stack-v{display:flex;flex-direction:column;gap:8px}
.m-stack-h{display:flex;flex-direction:row;gap:8px;flex-wrap:wrap}
/* ── Form ── */
.m-form{display:flex;flex-direction:column;gap:12px;padding:12px;background:#F0FDF4;border-radius:6px;border:1px solid #86EFAC}
/* ── Flyout layout ── */
.m-flyout-layout{display:flex;flex-direction:column;flex:1;min-height:0;gap:8px}
/* ── Header container ── */
.m-header-container{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:#F8FAFC;border-bottom:1px solid #1E293B}
/* ── Tab group ── */
.m-tab-bar{display:flex;border-bottom:2px solid #1E293B;gap:0;background:#F8FAFC}
.m-tab-btn{padding:8px 18px;background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:13px;color:#64748B;margin-bottom:-2px;transition:color .15s,border-color .15s}
.m-tab-btn.active,.m-tab-btn:hover{color:#2563EB;border-bottom-color:#2563EB}
.m-tab-content{flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column}
.m-tab-pane{flex-direction:column}
.m-tab-empty{padding:20px;color:#94A3B8;text-align:center;font-size:13px}
/* ── Accordion ── */
.m-accordion-item{border-bottom:1px solid #1E293B}
.m-accordion-item:last-child{border-bottom:none}
.m-accordion-header{width:100%;background:#F8FAFC;border:none;text-align:left;padding:10px 14px;font-size:13px;font-weight:600;cursor:pointer;display:flex;justify-content:space-between;align-items:center;color:#1E293B}
.m-accordion-header:hover{background:#F1F5F9}
.m-accordion-body{padding:10px 14px;font-size:13px;color:#374151;background:#fff}
.m-accordion-empty{padding:16px;color:#94A3B8;font-size:13px;text-align:center}
.m-acc-arrow{font-size:11px;color:#64748B}
/* ── Expandable ── */
.m-expandable-header{width:100%;background:#F8FAFC;border:none;border-bottom:1px solid #1E293B;text-align:left;padding:10px 14px;font-size:13px;font-weight:600;cursor:pointer;display:flex;justify-content:space-between;align-items:center;color:#1E293B}
.m-expandable-header:hover{background:#F1F5F9}
.m-expandable-body{padding:10px 14px;font-size:13px;color:#374151}
.m-exp-arrow{font-size:11px;color:#64748B}
/* ── List ── */
.m-list-row{border-bottom:1px solid #F1F5F9;padding:8px 12px}
.m-list-row:last-child{border-bottom:none}
.m-list-row:hover{background:#F8FAFC}
.m-list-row-placeholder{font-size:13px;color:#94A3B8}
/* ── Carousel ── */
.m-carousel{display:flex;align-items:center;gap:8px;position:relative;overflow:hidden}
.m-carousel-vertical{flex-direction:column}
.m-carousel-prev,.m-carousel-next{flex-shrink:0;width:30px;height:30px;border-radius:50%;background:#fff;border:1px solid #CBD5E1;cursor:pointer;font-size:20px;line-height:1;display:flex;align-items:center;justify-content:center;color:#374151;z-index:2}
.m-carousel-prev:hover,.m-carousel-next:hover{background:#F1F5F9}
.m-carousel-track-wrap{flex:1;overflow:hidden}
.m-carousel-track{display:flex;gap:12px;transition:transform .3s ease}
.m-carousel-slide{flex-shrink:0;background:#F8FAFC;border:1px solid #1E293B;border-radius:8px;padding:12px;min-height:80px;min-width:160px;display:flex;align-items:center;justify-content:center;color:#64748B;font-size:13px}
.m-carousel-dots{display:flex;gap:5px;justify-content:center;padding:4px 0}
.m-carousel-dot{width:8px;height:8px;border-radius:50%;background:#CBD5E1;cursor:pointer;border:none;padding:0}
.m-carousel-dot.active{background:#2563EB}
.m-carousel-placeholder{font-size:12px;color:#94A3B8;text-align:center}
/* ── Container outline markers ── */
/* inset box-shadow is drawn INSIDE the element, never clipped by parent overflow:hidden */
.show-containers [data-ct]{box-shadow:inset 0 0 0 2px rgba(220,38,38,0.75);position:relative;min-height:24px}
.show-containers [data-ct]::before{content:attr(data-ct);position:absolute;top:0;left:0;font-size:9px;line-height:1.3;background:rgba(220,38,38,0.92);color:#fff;padding:2px 7px 3px;border-radius:0 0 5px 0;z-index:9999;pointer-events:none;white-space:nowrap;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-weight:700;letter-spacing:0.03em}
/* ── Green layer: fill containers ── */
/* Light green tint + thick bottom band shows this container stretches to fill remaining height */
.show-containers [data-ct*="fill"]{background-color:rgba(34,197,94,0.10)!important;box-shadow:inset 0 0 0 2px rgba(220,38,38,0.75),inset 0 -4px 0 rgba(22,163,74,0.75)}
.show-containers [data-ct*="fill"]::after{content:'↕ FILL';position:absolute;bottom:4px;right:4px;font-size:9px;line-height:1.2;background:rgba(22,163,74,0.92);color:#fff;padding:2px 7px 3px;border-radius:3px;z-index:9999;pointer-events:none;font-weight:700;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;white-space:nowrap}
/* ── Green layer: width:100% containers ── */
/* Green left + right inset bands show this container spans the full available width */
.show-containers [data-ct*="w:100%"]{box-shadow:inset 0 0 0 2px rgba(220,38,38,0.75),inset 4px 0 0 rgba(34,197,94,0.65),inset -4px 0 0 rgba(34,197,94,0.65)}
/* ── Both fill + width:100% ── */
.show-containers [data-ct*="fill"][data-ct*="w:100%"]{background-color:rgba(34,197,94,0.10)!important;box-shadow:inset 0 0 0 2px rgba(220,38,38,0.75),inset 4px 0 0 rgba(34,197,94,0.65),inset -4px 0 0 rgba(34,197,94,0.65),inset 0 -4px 0 rgba(22,163,74,0.75)}
/* ── Preview toolbar ── */
#preview-toolbar{position:fixed;top:8px;right:14px;z-index:99999;display:flex;gap:6px;align-items:center;background:rgba(15,23,42,0.92);backdrop-filter:blur(6px);padding:5px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);box-shadow:0 4px 16px rgba(0,0,0,0.35)}
#preview-toolbar label{font-size:11px;color:#94A3B8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;cursor:pointer;display:flex;align-items:center;gap:5px;user-select:none}
#preview-toolbar label:hover{color:#1E293B}
.m-search-wrap{display:flex;align-items:center;min-width:0}
.m-search-base{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #CBD5E1;border-radius:999px;padding:0 10px;min-height:32px}
.m-search-icon{font-size:13px;color:#64748B;flex:0 0 auto}
.m-search-input{border:none;outline:none;background:transparent;color:#1E293B;font-size:12px;min-width:0;width:220px}
.m-search-input::placeholder{color:#94A3B8}
.m-search-suffix{display:inline-flex;align-items:center;justify-content:center}

.m-segment-wrap{display:flex;align-items:center;gap:8px}
.m-segment-label{font-size:12px;color:#475569;white-space:nowrap}
.m-segment-group{display:flex;align-items:center;gap:0;background:#fff;border:1px solid #CBD5E1;border-radius:4px;overflow:hidden}
.m-seg-pill{border:none;background:#fff;color:#4A4A4A;padding:7px 12px;font-size:12px;cursor:pointer;border-right:1px solid #E2E8F0}
.m-seg-pill:last-child{border-right:none}
.m-seg-pill.active{background:#E8F0FE;color:#1D4ED8;font-weight:600}

.m-kv{font-size:12px;color:#1E293B}
.m-cell-link{font-size:12px;color:#2563EB;text-decoration:none;font-weight:500}
.m-cell-link:hover{text-decoration:underline}

.m-agentic-actions{display:flex;align-items:center;justify-content:flex-end}
.m-agentic-btn{border:1px solid #C7D2FE;background:#EEF2FF;color:#4338CA;border-radius:6px;padding:6px 10px;font-size:12px;font-weight:600;cursor:pointer}

.m-table-card{display:flex;flex-direction:column;min-height:0;height:100%;background:#fff;border:1px solid #CBD5E1;border-radius:6px;overflow:hidden}
.m-table-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border-bottom:1px solid #E2E8F0;background:#fff}
.m-table-title{font-size:14px;font-weight:600;color:#1E293B}
.m-table-wrap{flex:1;min-height:0;overflow:auto}
.m-table{width:100%;border-collapse:collapse;font-size:12px}
.m-table th{background:#1E293B;color:#fff;font-weight:600;text-align:left;padding:10px 12px;position:sticky;top:0}
.m-table td{padding:9px 12px;border-bottom:1px solid #E2E8F0;color:#1E293B;white-space:nowrap}
.m-table tbody tr:nth-child(even){background:#F8FAFC}
.m-table tbody tr:hover{background:#EFF6FF}
.sort-icon,.filter-icon{margin-left:6px;color:#CBD5E1;font-size:10px}
.cb-cell{width:36px}

.m-chart-legend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;padding:6px 14px 0 14px;font-size:11px;color:#475569}
.m-chart-legend-item{display:flex;align-items:center;gap:6px}
.m-chart-legend-swatch{width:10px;height:10px;border-radius:2px;display:inline-block}
#toggle-containers{width:13px;height:13px;accent-color:#ef4444;cursor:pointer}
</style>
</head>
<body>
<div id="preview-toolbar">
  <label title="Toggle red outlines marking every flex/grid container boundary"><input type="checkbox" id="toggle-containers" checked> 🔴 Containers</label>
</div>
<div class="m-screen">
  <div class="m-navbar">
    <div class="m-navbar-logo">M</div>
    <span class="m-navbar-title">Manhattan Active Operations</span>
  </div>
  <div class="m-body" id="frag-root"></div>
</div>
<script>
const FRAG_DEF = "__FRAG_JSON__";

// ── CSS builder ─────────────────────────────────────────────────
// Manhattan Active CSS variable → preview fallback colours
const _MANH_VARS = {
  '--manh-footer-background-color': '#F8FAFC',
  '--manh-primary-color': '#2563EB',
  '--manh-secondary-color': '#7C3AED',
  '--manh-accent-color': '#F59E0B',
  '--manh-background-color': '#FFFFFF',
  '--manh-surface-color': '#F1F5F9',
  '--manh-border-color': '#1E293B',
  '--manh-text-color': '#1E293B',
  '--manh-text-secondary': '#64748B',
  '--manh-success-color': '#16A34A',
  '--manh-warning-color': '#D97706',
  '--manh-error-color': '#DC2626',
  '--manh-summary-bar-background-color': '#F1F5F9',
  '--manh-river-table-text-color': '#1E293B',
  '--manh-river-table-even-rows': '#F8FAFC',
  '--manh-river-table-odd-rows': '#FFFFFF',
  '--manh-river-table-header-row': '#1E293B',
  '--manh-river-table-border-color': '#CBD5E1',
  '--manh-river-hover-background': '#EFF6FF',
  '--mawc-color': '#4a4a4a',
};
function _resolveCssVars(s) {
  return String(s).replace(/var\\(([^)]+)\\)/g, (_, name) => {
    const key = name.trim().split(',')[0].trim();
    return _MANH_VARS[key] || '#1E293B';
  });
}

function _normCssKey(k) {
  return String(k).replace(/([A-Z])/g, '-$1').toLowerCase();
}

function _pushCssObj(parts, obj) {
  if (!obj || typeof obj !== 'object') return;
  Object.entries(obj).forEach(([k, v]) => {
    if (v == null || v === '') return;
    parts.push(_normCssKey(k) + ':' + _resolveCssVars(v));
  });
}

function buildCss(styleObj, extraBuckets) {
  if (!styleObj) return '';
  const parts = [];

  _pushCssObj(parts, styleObj.css);

  [
    'width','height','padding','margin','background','color','flex','flexDirection','gap','alignItems',
    'justifyContent','overflow','display','boxSizing','boxShadow','borderRadius','minWidth','minHeight',
    'maxWidth','maxHeight','backgroundColor','border','borderTop','borderRight','borderBottom','borderLeft',
    'flexShrink','flexGrow','flexWrap','position','zIndex','alignSelf','justifySelf','placeSelf'
  ].forEach(p => {
    if (styleObj[p] != null) parts.push(_normCssKey(p) + ':' + _resolveCssVars(styleObj[p]));
  });

  (extraBuckets || []).forEach(bucket => {
    const node = styleObj[bucket];
    if (!node || typeof node !== 'object') return;
    _pushCssObj(parts, node.css || node);
  });

  const dimRe = /((?:^|;)(?:width|height|min-width|min-height|max-width|max-height|gap|padding|margin|border-radius|font-size|flex-basis|top|left|right|bottom|line-height):\\s*)(\\d+(?:\\.\\d+)?)(?![0-9a-zA-Z%])/g;
  return parts
    .join(';')
    .replace(/(\\d+(?:\\.\\d+)?)rem\\b/g, '$1px')
    .replace(dimRe, '$1$2px');
}

// ── Slot renderer ─────────────────────────────────────────────────
function renderSlots(slots, order) {
  if (!slots) return '';
  const keys = order || Object.keys(slots);
  return keys.flatMap(k => (slots[k]||[]).map(renderItem)).join('');
}

// ── Dispatch ──────────────────────────────────────────────────────
function renderItem(item) {
  if (!item) return '';
  if (item.Container) return renderContainer(item);
  if (item.Element)   return renderElement(item);
  return '';
}

// ── Escape helper ─────────────────────────────────────────────────
function _esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _sampleValue(field, label, rowIdx) {
  const key = String(field || label || '').toLowerCase();
  if (key.includes('message id')) return 'MSG-' + String(104820 + rowIdx);
  if (key.includes('timestamp')) return '2026-06-05 10:' + String(10 + rowIdx).padStart(2, '0');
  if (key.includes('message type')) return ['OrderCreate','InventorySync','ASNUpdate','ShipmentStatus','InvoicePost','WaveRelease'][rowIdx % 6];
  if (key.includes('source')) return ['WMS','OMS','TMS','ERP'][rowIdx % 4];
  if (key.includes('destination')) return ['Queue-A','Queue-B','Queue-C','Partner API'][rowIdx % 4];
  if (key.includes('status')) return ['Completed','Failed','Completed','Completed','Failed','Completed'][rowIdx % 6];
  if (key.includes('failure %')) return ['1.2%','4.8%','0.6%','8.4%','2.1%','6.7%'][rowIdx % 6];
  if (key.includes('failed')) return [3, 12, 1, 19, 5, 11][rowIdx % 6];
  if (key.includes('completed')) return [248, 190, 301, 144, 220, 176][rowIdx % 6];
  if (key.includes('total')) return [251, 202, 302, 163, 225, 187][rowIdx % 6];
  if (key.includes('time')) return ['2.4s','7.8s','12.1s','24.6s','1.7s','9.3s'][rowIdx % 6];
  if (key.includes('error')) return rowIdx % 3 === 1 ? 'Timeout' : '—';
  if (key.includes('raw_in') || key.includes('parsed') || key.includes('enriched') || key.includes('transformed') || key.includes('queue')) {
    return ['0.2s','0.4s','0.6s','0.8s','1.1s','1.4s'][rowIdx % 6];
  }
  return rowIdx % 2 === 0 ? 'Value ' + (rowIdx + 1) : '—';
}

function renderKeyValue(e, rowIdx, labelOverride) {
  const cfg = e.Config || {};
  const css = buildCss(e.Style);
  const styleAttr = css ? ' style="' + css + '"' : '';
  const label = labelOverride || cfg.LabelKey || '';
  const val = _sampleValue(e.Input, label, rowIdx || 0);
  return '<span class="m-kv"' + styleAttr + '>' + _esc(val) + '</span>';
}

function renderLink(e, rowIdx, labelOverride) {
  const cfg = e.Config || {};
  const css = buildCss(e.Style);
  const styleAttr = css ? ' style="' + css + '"' : '';
  const label = labelOverride || cfg.LabelKey || '';
  const val = _sampleValue(e.Input, label, rowIdx || 0);
  return '<a href="#" class="m-cell-link"' + styleAttr + '>' + _esc(val) + '</a>';
}

function renderAgenticActions(e) {
  const menu = (((e.Slots || {}).Menu) || []);
  const first = menu[0] || {};
  const label = ((first.Config || {}).LabelKey) || 'Ask AI';
  return '<div class="m-agentic-actions"><button class="m-agentic-btn">✨ ' + _esc(label) + '</button></div>';
}

function renderSearch(c) {
  const cfg = c.Config || {};
  const searchProp = cfg.SearchProperty || {};
  const placeholder =
    searchProp.placeholder ||
    (((cfg.Filter || {}).Placeholder || {}).LabelKey) ||
    'Search';
  const wrapCss = buildCss(c.Style);
  const baseCss = buildCss(c.Style, ['baseCss']);
  const inputCss = buildCss(c.Style, ['inputCss']);
  const suffixCss = buildCss(c.Style, ['suffixCss']);
  return ''
    + '<div class="m-search-wrap" style="' + wrapCss + '">'
    +   '<div class="m-search-base" style="' + baseCss + '">'
    +     '<span class="m-search-icon">🔎</span>'
    +     '<input class="m-search-input" style="' + inputCss + '" placeholder="' + _esc(placeholder) + '" value="">'
    +     '<span class="m-search-suffix" style="' + suffixCss + '"></span>'
    +   '</div>'
    + '</div>';
}

function renderSegmentPanel(c) {
  const cfg = c.Config || {};
  const filter = cfg.Filter || {};
  const list = filter.StaticList || [];
  const label = ((filter.Placeholder || {}).LabelKey) || '';
  const segCss = buildCss(c.Style, ['segmentGroupCss']);
  const labelCss = buildCss(c.Style, ['labelKeyCss']);
  const pills = list.map((item, idx) => {
    const text = item.AttributeKey || item.LabelKey || item.AttributeValue || ('Option ' + (idx + 1));
    return '<button class="m-seg-pill ' + (idx === 1 ? 'active' : '') + '">' + _esc(text) + '</button>';
  }).join('');
  return ''
    + '<div class="m-segment-wrap">'
    +   '<div class="m-segment-label" style="' + labelCss + '">' + _esc(label) + '</div>'
    +   '<div class="m-segment-group" style="' + segCss + '">' + pills + '</div>'
    + '</div>';
}

// ── Element renderers ─────────────────────────────────────────────
function renderElement(e) {
  const cfg = e.Config || {};
  const css = buildCss(e.Style);
  const styleAttr = css ? ' style="'+css+'"' : '';
  const label = cfg.LabelKey || cfg.label || e.Input || e.Element || '';
  switch (e.Element) {
    case 'button': {
      // Manhattan puts variant in Style object (not Config); fall back to Config.Variant
      const variant = ((e.Style||{}).variant || cfg.Variant||'').toLowerCase();
      const cls = variant==='secondary'?'m-btn m-btn-secondary':variant==='ghost'?'m-btn m-btn-ghost':variant==='stroked'?'m-btn m-btn-stroked':'m-btn m-btn-primary';
      const prefix = cfg.PrefixIcon ? '<span style="font-size:14px">'+cfg.PrefixIcon+'</span>' : '';
      const suffix = cfg.SuffixIcon ? '<span style="font-size:14px">'+cfg.SuffixIcon+'</span>' : '';
      return '<button class="'+cls+'"'+styleAttr+'>'+prefix+label+suffix+'</button>';
    }
    case 'actions-popover': {
      const actions = cfg.Actions || cfg.actions || (cfg.ActionConfig||{}).Actions || (cfg.ActionConfig||{}).actions || [];
      const items = actions.map(a => '<div class="m-actions-popover-item">'+( a.LabelKey||a.label||(a.Config||{}).LabelKey||a.type||'Action')+'</div>').join('');
      const popId = 'pop_'+Math.random().toString(36).slice(2);
      return '<div class="m-actions-popover"'+styleAttr+'><button class="m-actions-popover-trigger" data-popid="'+popId+'">'+label+' &#9660;</button><div class="m-actions-popover-menu" id="'+popId+'">'+items+'</div></div>';
    }
    case 'key-value': {
      return renderKeyValue(e, 0, cfg.LabelKey || label);
    }
    case 'link': {
      return renderLink(e, 0, cfg.LabelKey || label);
    }
    case 'pill':
      return '<span class="m-pill"'+styleAttr+'>'+(e.Input||label)+'</span>';
    case 'text':
      return '<span class="m-text"'+styleAttr+'>'+(cfg.LabelKey||e.Input||label)+'</span>';
    case 'input': {
      const ph = (cfg.Placeholder||{}).LabelKey || '';
      const lbl = cfg.LabelKey||'';
      return '<div class="m-input-wrap"'+styleAttr+'>'+(lbl?'<label class="m-input-label">'+lbl+'</label>':'')+'<input class="m-input" placeholder="'+ph+'"></div>';
    }
    case 'select':
    case 'combobox': {
      const opts = (cfg.Options||[]).map(o=>'<option>'+( o.LabelKey||o.label||o)+'</option>').join('');
      const ph = (cfg.Placeholder||{}).LabelKey || (cfg.LabelKey||'');
      return '<select class="m-'+(e.Element===\'select\'?\'select\':\'combobox\')+'"'+styleAttr+'><option value="">'+ph+'</option>'+opts+'</select>';
    }
    case 'filter-panel':
      return renderFilterPanel(e);
    case 'date':
    case 'date-picker':
      return '<input type="date" class="m-input"'+styleAttr+'>';
    case 'checkbox':
      return '<label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer"><input type="checkbox"> '+(cfg.LabelKey||label)+'</label>';
    case 'textarea': {
      const ph = (cfg.Placeholder||{}).LabelKey || '';
      const lbl = cfg.LabelKey||'';
      return '<div class="m-input-wrap"'+styleAttr+'>'+(lbl?'<label class="m-input-label">'+lbl+'</label>':'')+'<textarea class="m-input" placeholder="'+ph+'" rows="3" style="resize:vertical"></textarea></div>';
    }
    case 'dropdown': {
      const opts = (cfg.Options||[]).map(o=>'<option>'+(o.LabelKey||o.label||o)+'</option>').join('');
      const ph = (cfg.Placeholder||{}).LabelKey||(cfg.LabelKey||'Select...');
      return '<select class="m-combobox"'+styleAttr+'><option value="">'+ph+'</option>'+opts+'</select>';
    }
    case 'date-select': {
      const lbl = cfg.LabelKey||'';
      return '<div class="m-datesel"'+styleAttr+'>'+(lbl?'<label>'+lbl+'</label>':'')+'<input type="date" class="m-input"></div>';
    }
    case 'numeric-stepper': {
      const lbl = cfg.LabelKey||'';
      return '<div class="m-input-wrap"'+styleAttr+'>'+(lbl?'<label class="m-input-label">'+lbl+'</label>':'')+'<div class="m-stepper"><button type="button">&#8722;</button><input type="number" value="0"><button type="button">+</button></div></div>';
    }
    case 'currency-input': {
      const lbl = cfg.LabelKey||'';
      const sym = cfg.currencySymbol||'$';
      return '<div class="m-input-wrap"'+styleAttr+'>'+(lbl?'<label class="m-input-label">'+lbl+'</label>':'')+'<div class="m-currinput"><span class="sym">'+sym+'</span><input type="text" placeholder="0.00"></div></div>';
    }
    case 'search': {
      const ph = (cfg.Placeholder||{}).LabelKey||(cfg.LabelKey||'Search...');
      return '<div class="m-search-wrap"'+styleAttr+'><span class="m-search-icon">&#128269;</span><input class="m-search-input" placeholder="'+ph+'"></div>';
    }
    case 'toggle-button': {
      const lbl = cfg.LabelKey||'';
      return '<label class="m-toggle-wrap"'+styleAttr+'><div class="m-toggle-track"><div class="m-toggle-thumb"></div></div>'+(lbl?'<span>'+lbl+'</span>':'')+'</label>';
    }
    case 'segment-panel': {
      // Support both Segments array and Filter.StaticList formats
      const filt = cfg.Filter || {};
      const ph = (filt.Placeholder||{}).LabelKey || cfg.Name || '';
      let segs = cfg.Segments || filt.StaticList || [];
      if (!segs.length) segs = [{AttributeKey:'Option 1'},{AttributeKey:'Option 2'}];
      const phHtml = ph ? '<span class="m-seg-label">'+ph+'</span>' : '';
      const tabs = segs.map((s,i)=>'<div class="m-seg-tab'+(i===0?' active':'')+'">'+( s.LabelKey||s.AttributeKey||s.Id||'Tab')+'</div>').join('');
      return '<div class="m-segment-panel"'+styleAttr+'>'+phHtml+tabs+'</div>';
    }
    case 'quick-filter': {
      const segs = cfg.Segments||[{LabelKey:'All',Id:'all'},{LabelKey:'Active',Id:'a'},{LabelKey:'Done',Id:'d'}];
      const chips = segs.map((s,i)=>'<div class="m-qf-chip'+(i===0?' active':'')+'">'+( s.LabelKey||s.Id||'')+'</div>').join('');
      return '<div class="m-quick-filter"'+styleAttr+'>'+chips+'</div>';
    }
    case 'value':
      return '<span class="m-value"'+styleAttr+'>'+(e.Input||'—')+'</span>';
    case 'value-unit': {
      const unit = cfg.unit||cfg.Unit||'';
      return '<div class="m-value-unit"'+styleAttr+'><span class="num">'+(e.Input||'—')+'</span>'+(unit?'<span class="unit">'+unit+'</span>':'')+'</div>';
    }
    case 'icon': {
      const iconMap = {info:'ℹ',warning:'⚠',error:'✕',check:'✓',check_circle:'✅',edit:'✎',delete:'🗑',add:'＋',search:'🔍',close:'✕',arrow_forward:'→',arrow_back:'←',home:'⌂',settings:'⚙',person:'👤',star:'★',calendar:'📅',download:'⬇',upload:'⬆'};
      const ico = cfg.icon||cfg.Icon||'';
      const sym = iconMap[ico]||ico||'✦';
      return '<span class="m-icon"'+styleAttr+' title="'+ico+'">'+sym+'</span>';
    }
    case 'message': {
      const msgType = (cfg.type||cfg.Type||'info').toLowerCase();
      const icons = {info:'ℹ',warning:'⚠',error:'✕',success:'✓'};
      return '<div class="m-message"'+styleAttr+'><span>'+( icons[msgType]||'ℹ')+'</span><span>'+(cfg.LabelKey||label||'')+'</span></div>';
    }
    case 'currency-format': {
      const val = e.Input||'AMOUNT';
      return '<span class="m-currency"'+styleAttr+'>'+(val.match(/^\\d/)? '$'+val : val)+'</span>';
    }
    case 'key-value-detail': {
      const lbl = cfg.LabelKey||'';
      const val = e.Input||cfg.attribute||'—';
      return '<div class="m-kvd-wrap"'+styleAttr+'><div class="m-kvd-label">'+lbl+'</div><div class="m-kvd-value">'+val+'</div></div>';
    }
    case 'progress-bar': {
      const lbl = cfg.LabelKey||'';
      const pct = e.Input||cfg.value||'65';
      return '<div class="m-progress-wrap"'+styleAttr+'>'+(lbl?'<div class="m-progress-label">'+lbl+'</div>':'')+'<div class="m-progress-track"><div class="m-progress-fill" style="width:'+pct+'%"></div></div></div>';
    }
    case 'related-link': {
      const lbl = cfg.LabelKey||'View Related';
      return '<a class="m-related-link"'+styleAttr+' href="#">'+lbl+' &#x2197;</a>';
    }
    case 'button-icon': {
      const ico = cfg.icon||cfg.Icon||'✎';
      const iconMap2 = {edit:'✎',delete:'🗑',add:'＋',search:'🔍',close:'✕',info:'ℹ',settings:'⚙'};
      return '<button class="m-btn-icon"'+styleAttr+' title="'+ico+'">'+(iconMap2[ico]||ico)+'</button>';
    }
    case 'action-button': {
      const lbl = cfg.LabelKey||label||'Action';
      return '<button class="m-action-btn"'+styleAttr+'><span>&#9889;</span>'+lbl+'</button>';
    }
    case 'agentic-actions': {
      return renderAgenticActions(e);
    }
    case 'menu-item': {
      const lbl2 = cfg.LabelKey || label || 'Menu Item';
      return '<button class="m-agentic-btn">' + _esc(lbl2) + '</button>';
    }
    default:
      return '<span style="font-size:12px;color:#64748B;padding:4px 8px;border:1px dashed #CBD5E1;border-radius:3px;display:inline-block;'+css+'">'+e.Element+(label?': '+label:'')+'</span>';
  }
}

// ── Filter panel ──────────────────────────────────────────────────
function renderFilterPanel(e) {
  const cfg = e.Config || {};
  const sections = cfg.Sections || [];
  let html = '';
  sections.forEach(sec => {
    const attrs = sec.Attributes || [];
    let fields = attrs.map(attr => {
      const filt = attr.Filter || {};
      const ph = (filt.Placeholder||{}).LabelKey || attr.LabelKey || '';
      const lbl = attr.LabelKey || attr.Attribute || '';
      const type = (filt.Type||filt.type||'').toLowerCase();
      let input;
      if (type==='select'||type==='dropdown'||type==='combobox'||type==='singleselect'||type==='multiselect') {
        const multi = type==='multiselect' ? ' multiple size="3"' : '';
        input = '<select class="m-filter-input"'+multi+'><option value="">'+ph+'</option></select>';
      } else if (type.startsWith('date')) {
        input = '<input class="m-filter-input" type="text" placeholder="'+ph+'">';
      } else {
        input = '<input class="m-filter-input" placeholder="'+ph+'" type="text">';
      }
      return '<div class="m-filter-field"><div class="m-filter-label">'+lbl+'</div>'+input+'</div>';
    }).join('');
    if (fields) {
      html += '<div class="m-filter-section"><div class="m-filter-section-header"><span>'+(sec.SectionName||sec.Label||'')+'</span><span style="font-size:10px;color:#94A3B8">&#9650;</span></div><div class="m-filter-section-body">'+fields+'</div></div>';
    }
  });
  // If no sections, try flat Attributes
  if (!html && cfg.Attributes) {
    const fields = (cfg.Attributes||[]).map(attr => {
      const filt = attr.Filter || {};
      const ph = (filt.Placeholder||{}).LabelKey || attr.LabelKey || '';
      const lbl = attr.LabelKey || attr.Attribute || '';
      return '<div class="m-filter-field"><div class="m-filter-label">'+lbl+'</div><input class="m-filter-input" placeholder="'+ph+'" type="text"></div>';
    }).join('');
    html = '<div class="m-filter-section"><div class="m-filter-section-body">'+fields+'</div></div>';
  }
  return '<div class="m-filter-panel">'
    +'<div class="m-filter-panel-top"><button class="m-filter-clearall">Clear All</button></div>'
    +'<div class="m-filter-body">'+html+'</div>'
    +'<div class="m-filter-actions"><button class="m-btn-clear">Clear</button><button class="m-btn-apply">Apply</button></div>'
    +'</div>';
}

// ── Pagination footer ─────────────────────────────────────────────
function renderPagination(c) {
  const cfg = c.Config || {};
  const sizes = ((cfg.PaginationConfig||{}).Size) || [25,50,100];
  const sizeOpts = sizes.map(s=>'<option>'+s+'</option>').join('');
  return '<div class="m-table-footer"><span>Showing 1 – 25 of —</span><div class="m-pagination"><button>&#8249;</button><button class="active">1</button><button>2</button><button>3</button><button>&#8250;</button></div><span>Rows / page: <select style="border:1px solid #CBD5E1;border-radius:3px;padding:2px 6px;font-size:12px">'+sizeOpts+'</select></span></div>';
}

// ── Chart SVG builders ────────────────────────────────────────────
function _chartSvgBars(color1,color2){
  const bh=[80,140,60,110,170,50,130,90,155,70,120,100,145];
  const bW=32,gap=14,sx=20;
  return bh.map((h,i)=>{const x=sx+i*(bW+gap),y=195-h,c=h>130?color2:color1;return '<rect x="'+x+'" y="'+y+'" width="'+bW+'" height="'+h+'" fill="'+c+'" rx="2"/>';}).join('')
    +'<line x1="0" y1="195" x2="640" y2="195" stroke="#1E293B" stroke-width="1"/>'
    +'<line x1="0" y1="145" x2="640" y2="145" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="4,4"/>'
    +'<line x1="0" y1="95" x2="640" y2="95" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="4,4"/>'
    +'<line x1="0" y1="45" x2="640" y2="45" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="4,4"/>';
}
function _chartSvgHBar(){
  const vals=[160,120,80,50,140,70,110];const labels=['Alpha','Beta','Gamma','Delta','Epsilon','Zeta','Eta'];
  return vals.map((v,i)=>{const y=15+i*26,c=i%2===0?'#2563EB':'#7C3AED';return '<rect x="80" y="'+y+'" width="'+v+'" height="18" fill="'+c+'" rx="2"/><text x="76" y="'+(y+13)+'" font-size="10" fill="#64748B" text-anchor="end">'+labels[i]+'</text>';}).join('')
    +'<line x1="80" y1="0" x2="80" y2="198" stroke="#1E293B" stroke-width="1"/>';
}
function _chartSvgLine(color,fill){
  const pts=[[20,155],[80,110],[140,130],[200,70],[260,95],[320,50],[380,80],[440,40],[500,65],[560,35],[620,55]];
  let pStr=pts.map(p=>p.join(',')).join(' ');
  let svg=fill?'<polygon points="20,198 '+pStr+' 620,198" fill="'+fill+'" opacity="0.35"/>':'';
  svg+='<polyline points="'+pStr+'" fill="none" stroke="'+color+'" stroke-width="2.5" stroke-linejoin="round"/>';
  pts.forEach(p=>{svg+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.5" fill="'+color+'" stroke="white" stroke-width="1.5"/>';});
  return svg+'<line x1="0" y1="195" x2="640" y2="195" stroke="#1E293B" stroke-width="1"/>';
}
function _chartSvgPie(){
  const slices=[{s:0,e:130,c:'#2563EB'},{s:130,e:210,c:'#EA580C'},{s:210,e:285,c:'#16A34A'},{s:285,e:360,c:'#9333EA'}];
  const cx=200,cy=100,r=85;
  let svg='';
  slices.forEach(sl=>{
    const a1=sl.s*Math.PI/180,a2=sl.e*Math.PI/180;
    const x1=cx+r*Math.cos(a1),y1=cy+r*Math.sin(a1);
    const x2=cx+r*Math.cos(a2),y2=cy+r*Math.sin(a2);
    const lf=sl.e-sl.s>180?1:0;
    svg+='<path d="M'+cx+','+cy+' L'+x1+','+y1+' A'+r+','+r+' 0 '+lf+',1 '+x2+','+y2+' Z" fill="'+sl.c+'" stroke="white" stroke-width="2"/>';
  });
  const legs=[['Category A','#2563EB'],['Category B','#EA580C'],['Category C','#16A34A'],['Category D','#9333EA']];
  legs.forEach(([lbl,c],i)=>{svg+='<rect x="400" y="'+(60+i*28)+'" width="12" height="12" fill="'+c+'" rx="2"/><text x="420" y="'+(72+i*28)+'" font-size="11" fill="#374151">'+lbl+'</text>';});
  return svg;
}
function _chartSvgScatter(){
  const pts=[[45,165],[90,120],[130,145],[175,80],[220,100],[260,55],[310,90],[340,40],[395,70],[430,110],[480,50],[520,85],[565,35],[610,60]];
  return pts.map(p=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="6" fill="#F59E0B" stroke="white" stroke-width="1.5" opacity="0.85"/>').join('')
    +'<line x1="0" y1="195" x2="640" y2="195" stroke="#1E293B" stroke-width="1"/>';
}
function _chartSvgSunburst(){
  const cx=200,cy=100;
  const rings=[{r:80,slices:[{s:0,e:135,c:'#2563EB'},{s:135,e:215,c:'#EA580C'},{s:215,e:285,c:'#16A34A'},{s:285,e:360,c:'#9333EA'}]},{r:50,slices:[{s:0,e:160,c:'#60A5FA'},{s:160,e:360,c:'#FCA5A5'}]}];
  let svg='';
  rings.forEach(ring=>{ring.slices.forEach(sl=>{const a1=sl.s*Math.PI/180,a2=sl.e*Math.PI/180;const ri=ring.r*0.55;const x1o=cx+ring.r*Math.cos(a1),y1o=cy+ring.r*Math.sin(a1),x2o=cx+ring.r*Math.cos(a2),y2o=cy+ring.r*Math.sin(a2);const x1i=cx+ri*Math.cos(a2),y1i=cy+ri*Math.sin(a2),x2i=cx+ri*Math.cos(a1),y2i=cy+ri*Math.sin(a1);const lf=sl.e-sl.s>180?1:0;svg+='<path d="M'+x1o+','+y1o+' A'+ring.r+','+ring.r+' 0 '+lf+',1 '+x2o+','+y2o+' L'+x1i+','+y1i+' A'+ri+','+ri+' 0 '+lf+',0 '+x2i+','+y2i+' Z" fill="'+sl.c+'" stroke="white" stroke-width="1.5"/>';});});
  return svg;
}
function _chartSvgWaterfall(){
  const vals=[60,-20,40,-15,50,30,-10];let cur=195;
  return vals.map((v,i)=>{const h2=Math.abs(v)*1.2,x=30+i*82;const y=v>0?cur-h2:cur;cur+=v>0?-h2:h2;return '<rect x="'+x+'" y="'+y+'" width="55" height="'+h2+'" fill="'+(v>0?'#16A34A':'#DC2626')+'" rx="2"/>';}).join('')
    +'<line x1="0" y1="195" x2="640" y2="195" stroke="#1E293B" stroke-width="1"/>';
}

// ── Chart ─────────────────────────────────────────────────────────
function _chartSampleCategories() {
  return ['08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00'];
}

function _chartSeriesColor(s, idx) {
  return (((s || {}).staticOptions || {}).color)
    || ['#A5D6A7','#90CAF9','#FFCC80','#EF9A9A','#424242','#7C3AED'][idx % 6];
}

function _chartSeriesName(s, idx) {
  return (((s || {}).staticOptions || {}).name) || ('Series ' + (idx + 1));
}

function _stackedColumnSvg(seriesMappings) {
  const cats = _chartSampleCategories();
  const series = seriesMappings.map((s, idx) => ({
    name: _chartSeriesName(s, idx),
    color: _chartSeriesColor(s, idx),
    vals: cats.map((_, cIdx) => {
      const base = [
        [22,18,25,19,14,12,17,21],
        [10,9,11,8,7,6,8,9],
        [6,5,8,7,6,5,5,7],
        [3,4,5,4,3,2,3,4],
        [1,2,1,3,2,1,2,2]
      ];
      return (base[idx] || cats.map(() => 4))[cIdx];
    })
  }));
  const totals = cats.map((_, i) => series.reduce((sum, s) => sum + s.vals[i], 0));
  const maxTotal = Math.max(...totals, 1);
  const chartLeft = 42, chartBottom = 188, chartTop = 16, chartHeight = 160;
  const step = 72, barW = 38;
  let svg = '';
  svg += '<line x1="' + chartLeft + '" y1="' + chartBottom + '" x2="620" y2="' + chartBottom + '" stroke="#1E293B" stroke-width="1"/>';
  svg += '<line x1="' + chartLeft + '" y1="' + chartTop + '" x2="' + chartLeft + '" y2="' + chartBottom + '" stroke="#1E293B" stroke-width="1"/>';
  [0.25,0.5,0.75].forEach(fr => {
    const y = chartBottom - (chartHeight * fr);
    svg += '<line x1="' + chartLeft + '" y1="' + y + '" x2="620" y2="' + y + '" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="4,4"/>';
  });
  cats.forEach((cat, cIdx) => {
    const x = 60 + cIdx * step;
    let yCursor = chartBottom;
    series.forEach(s => {
      const val = s.vals[cIdx];
      const h = (val / maxTotal) * chartHeight;
      yCursor -= h;
      svg += '<rect x="' + x + '" y="' + yCursor + '" width="' + barW + '" height="' + Math.max(h, 1) + '" fill="' + s.color + '" rx="2"/>';
    });
    svg += '<text x="' + (x + barW / 2) + '" y="204" text-anchor="middle" font-size="10" fill="#64748B">' + cat + '</text>';
  });
  return svg;
}

function renderChart(c) {
  const cfg = c.Config || {};
  const title = (cfg.chartMetadata || {}).name || cfg.LabelKey || cfg.title || cfg.Title || 'Chart';
  const sm = ((cfg.dataMapping || {}).seriesMappings) || [];
  const hcType = (((cfg.highchartsOptions || {}).chart) || {}).type || '';
  const seriesType = ((sm[0] || {}).seriesType) || '';
  const chartType = String(cfg.ChartType || cfg.chartType || seriesType || hcType || 'column').toLowerCase();
  const inner = renderSlots(c.Slots);
  const hRaw = ((c.Style || {}).css || {}).height || (c.Style || {}).height || '260px';
  const h = String(hRaw).replace(/(\d+(?:\.\d+)?)rem\b/g, '$1px');
  const chartWidth = (((cfg.chartMetadata || {}).chartWidth) || cfg.chartWidth || '').toString().trim();
  const contentPadding = (c.Style || {}).contentPadding != null
    ? (c.Style || {}).contentPadding
    : (((c.Style || {}).css || {}).contentPadding || 18);
  const isFill = (h === '100%' || h === 'auto');
  const widthStyle = (chartWidth && chartWidth !== '100%')
    ? ('flex:0 0 ' + chartWidth + ';max-width:' + chartWidth + ';')
    : 'flex:1 1 0;min-width:0;';
  const wrapStyle = isFill
    ? widthStyle + 'flex:1;min-height:0;display:flex;flex-direction:column'
    : 'height:' + h + ';' + widthStyle + 'display:flex;flex-direction:column;min-height:260px;flex-shrink:0';
  const bodyStyle = isFill
    ? 'padding:' + contentPadding + 'px;flex:1;min-height:0;overflow:hidden'
    : 'padding:' + contentPadding + 'px;height:calc(' + h + ' - 46px);overflow:hidden';

  let svgBody = '';
  if ((chartType === 'column' || chartType === 'bar') && sm.length > 1) {
    svgBody = _stackedColumnSvg(sm);
  } else if (chartType === 'line' || chartType === 'spline') {
    svgBody = _chartSvgLine('#2563EB', null);
  } else if (chartType === 'area' || chartType === 'areaspline') {
    svgBody = _chartSvgLine('#0EA5E9', '#BAE6FD');
  } else if (chartType === 'pie' || chartType === 'sunburst') {
    svgBody = chartType === 'pie' ? _chartSvgPie() : _chartSvgSunburst();
  } else {
    svgBody = _chartSvgBars('#2563EB', '#F59E0B');
  }

  const legendEnabled = (((cfg.highchartsOptions || {}).legend || {}).enabled) !== false && sm.length > 0;
  const legendHtml = legendEnabled
    ? '<div class="m-chart-legend">' + sm.map((s, idx) =>
        '<div class="m-chart-legend-item"><span class="m-chart-legend-swatch" style="background:' + _chartSeriesColor(s, idx) + '"></span>' + _esc(_chartSeriesName(s, idx)) + '</div>'
      ).join('') + '</div>'
    : '';

  const chartSvg = '<svg width="100%" height="100%" viewBox="0 0 640 210" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" style="display:block"><rect width="640" height="210" fill="#fff"/>' + svgBody + '</svg>';

  return ''
    + '<div data-ct="' + _esc(title) + '" class="m-chart-wrap" style="' + wrapStyle + '">'
    +   '<div class="m-chart-header" style="flex-shrink:0"><span class="m-chart-header-title">' + _esc(title) + '</span></div>'
    +   legendHtml
    +   '<div class="m-chart-body" style="' + bodyStyle + '">' + chartSvg + inner + '</div>'
    + '</div>';
}

// ── Table ─────────────────────────────────────────────────────────
function _findFooterNode(items) {
  for (const item of (items || [])) {
    if (!item || typeof item !== 'object') continue;
    if (item.Container === 'footer') return item;
    const slots = item.Slots || {};
    for (const arr of Object.values(slots)) {
      const hit = _findFooterNode(arr);
      if (hit) return hit;
    }
  }
  return null;
}

function _renderTableCell(col, rowIdx) {
  const cc = col.Config || {};
  const slotItems = ((col.Slots || {}).Default) || [];
  const first = slotItems[0] || {};
  const label = cc.LabelKey || col.ColumnId || '';
  if (first.Element === 'link') return renderLink(first, rowIdx, label);
  if (first.Element === 'key-value') return renderKeyValue(first, rowIdx, label);
  return '<span class="m-kv">' + _esc(_sampleValue(first.Input, label, rowIdx)) + '</span>';
}

function renderTable(c) {
  const cfg = c.Config || {};
  const cols = cfg.Columns || [];
  const selCfg = cfg.SelectionConfig || {};
  const hasSel = !!selCfg.ShowSelection;
  const isRadio = hasSel && String(selCfg.SelectionType || '').toLowerCase() === 'single';
  const css = buildCss(c.Style);
  const title = cfg.title || cfg.Title || 'Table';
  const pageSize = cfg.pageSize || 25;
  const rowsToShow = Math.min(pageSize, 8);

  const selInput = isRadio
    ? '<input type="radio" name="tbl_sel_' + Math.random().toString(36).slice(2) + '" style="cursor:pointer;accent-color:#2563EB">'
    : '<input type="checkbox" style="cursor:pointer;accent-color:#2563EB">';

  const thCb = hasSel
    ? '<th class="cb-cell">' + (isRadio ? '' : '<input type="checkbox" style="cursor:pointer;accent-color:#2563EB">') + '</th>'
    : '';

  const ths = cols.map(col => {
    const cc = col.Config || {};
    const sortable = (cc.Sort || {}).Sortable;
    const filterable = (cc.Filter || {}).Filterable;
    const lbl = cc.LabelKey || col.ColumnId || '';
    return '<th class="' + (sortable ? 'sortable' : '') + '">'
      + _esc(lbl)
      + (sortable ? '<span class="sort-icon">&#8645;</span>' : '')
      + (filterable ? '<span class="filter-icon">&#9638;</span>' : '')
      + '</th>';
  }).join('');

  const bodyRows = Array.from({ length: rowsToShow }, (_, rowIdx) => {
    const tdCb = hasSel ? '<td class="cb-cell">' + selInput + '</td>' : '';
    const tds = cols.map(col => '<td>' + _renderTableCell(col, rowIdx) + '</td>').join('');
    return '<tr>' + tdCb + tds + '</tr>';
  }).join('');

  const footerNode = _findFooterNode((c.Slots || {}).Default || []);
  const footerHtml = footerNode
    ? renderPagination(footerNode)
    : renderPagination({ Config: { PaginationConfig: { Size: [10,25,50,100] } } });
  const agentHtml = renderSlots(c.Slots, ['AgenticActions']);

  return ''
    + '<div class="m-table-card" style="' + css + '">'
    +   '<div class="m-table-toolbar">'
    +     '<div class="m-table-title">' + _esc(title) + '</div>'
    +     agentHtml
    +   '</div>'
    +   '<div class="m-table-wrap">'
    +     '<table class="m-table">'
    +       '<thead><tr>' + thCb + ths + '</tr></thead>'
    +       '<tbody>' + bodyRows + '</tbody>'
    +     '</table>'
    +   '</div>'
    +   footerHtml
    + '</div>';
}

// ── Header action bar ─────────────────────────────────────────────
function renderHeaderAction(c) {
  const css = buildCss(c.Style);
  const left   = renderSlots(c.Slots, ['Left']);
  const middle = renderSlots(c.Slots, ['Middle']);
  const right  = renderSlots(c.Slots, ['Right']);
  return '<div class="m-header-action" style="'+css+'"><div class="left-actions">'+left+'</div>'+(middle?'<div class="middle-actions">'+middle+'</div>':'')+'<div class="right-actions">'+right+'</div></div>';
}

// ── Flyout card ───────────────────────────────────────────────────
function renderFlyoutCard(c) {
  const cfg = c.Config || {};
  const css = buildCss(c.Style);
  const width = ((c.Style||{}).css||{}).width || (c.Style||{}).width || '300px';
  const inner = renderSlots(c.Slots, ['Default']);
  const panelStyle = 'width:'+width+';'+css+';display:flex;flex-direction:column;min-height:0;overflow:hidden';
  const title = cfg.title || cfg.Title || cfg.LabelKey || cfg.label || '';
  const hasHeader = Boolean(title);

  if (width === '100vw' || width === '100%') {
    return '<div style="display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden;'+css+'">'+inner+'</div>';
  }

  let html = '<div class="m-flyout" style="'+panelStyle+'">';
  if (hasHeader) {
    html += '<div class="m-flyout-header"><span>'+title+'</span>';
    html += '<button data-flyout="flyout_'+Math.random().toString(36).slice(2)+'" data-flyout-w="'+width+'" style="background:transparent;border:none;color:#94A3B8;cursor:pointer;font-size:16px">&#10005;</button>';
    html += '</div>';
  }
  html += '<div class="m-flyout-body">'+inner+'</div></div>';
  return html;
}

// ── Sidebar ───────────────────────────────────────────────────────
function renderSidebar(c) {
  const css = buildCss(c.Style);
  const leftSlot    = ((c.Slots||{}).Left||[]);
  const rightSlot   = ((c.Slots||{}).Right||[]);
  const defaultSlot = ((c.Slots||{}).Default||[]);
  const hasLeft  = leftSlot.length > 0;
  const hasRight = rightSlot.length > 0;
  const leftHtml    = leftSlot.map(renderItem).join('');
  const rightHtml   = rightSlot.map(renderItem).join('');
  const contentHtml = defaultSlot.map(renderItem).join('');
  // Sidebar always uses row layout (Left=panel, Default=content).
  // Force flex-direction:row so external style can't override the internal layout.
  return '<div class="m-sidebar-wrap" style="'+css+';flex-direction:row">'
    +(hasLeft ? '<aside class="m-sidebar-aside">'+leftHtml+'</aside>' : '')
    +'<section class="m-sidebar-content">'+contentHtml+'</section>'
    +(hasRight ? '<aside class="m-sidebar-aside" style="border-left:1px solid #1E293B;border-right:none">'+rightHtml+'</aside>' : '')
    +'</div>';
}

// ── Generic container ─────────────────────────────────────────────
function renderContainer(c) {
  const type = c.Container;
  const css  = buildCss(c.Style);
  const styleAttr = css ? ' style="'+css+'"' : '';
  switch (type) {
    case 'header-action':    return renderHeaderAction(c);
    case 'table':            return renderTable(c);
    case 'sidebar':          return renderSidebar(c);
    case 'flyout-card':      return renderFlyoutCard(c);
    case 'chart':            return renderChart(c);
    case 'footer-container': return renderSlots(c.Slots);
    case 'footer':           return renderPagination(c);
    case 'actions-popover': {
      const cfg = c.Config || {};
      const label = cfg.LabelKey || cfg.label || '';
      const actions = cfg.Actions || cfg.actions || (cfg.ActionConfig||{}).Actions || (cfg.ActionConfig||{}).actions || [];
      const items = actions.map(a => '<div class="m-actions-popover-item">'+(a.LabelKey||a.label||(a.Config||{}).LabelKey||a.type||'Action')+'</div>').join('');
      const popId = 'pop_'+Math.random().toString(36).slice(2);
      return '<div class="m-actions-popover"'+styleAttr+'><button class="m-actions-popover-trigger" data-popid="'+popId+'">'+label+' &#9660;</button><div class="m-actions-popover-menu" id="'+popId+'">'+items+'</div></div>';
    }
    case 'card':
      return '<div class="m-card"'+styleAttr+'>'+renderSlots(c.Slots)+'</div>';
    case 'flex': {
      const sn = (c.Config||{}).SectionName || '';
      const sc = (c.Style||{}).css||{};
      const tags = [];
      if (sc.width==='100%') tags.push('w:100%');
      if (String(sc.flex||'').startsWith('1')) tags.push('fill');
      if (sc.height) tags.push('h:'+sc.height);
      if (sc.flexDirection && sc.flexDirection!=='row') tags.push(sc.flexDirection);
      const ctLabel = (sn||'flex')+(tags.length?' ['+tags.join(' ')+']':'');
      // When both fill (flex:1) and width:100% are set, force flex:1 1 0 so siblings divide space equally
      const equalFlex = (tags.includes('fill') && tags.includes('w:100%')) ? ';flex:1 1 0' : '';
      return '<div data-ct="'+ctLabel+'" style="display:flex;min-width:0;min-height:0;'+css+equalFlex+'">'+renderSlots(c.Slots)+'</div>';
    }
    case 'grid': {
      const sn2 = (c.Config||{}).SectionName || '';
      const sc2 = (c.Style||{}).css||{};
      const tags2 = [];
      if (sc2.width==='100%') tags2.push('w:100%');
      if (sc2.height) tags2.push('h:'+sc2.height);
      const ctLabel2 = (sn2||'grid')+(tags2.length?' ['+tags2.join(' ')+']':'');
      return '<div data-ct="'+ctLabel2+'" style="display:grid;min-width:0;min-height:0;'+css+'">'+renderSlots(c.Slots)+'</div>';
    }
    case 'stack': {
      const cssCfg2 = ((c.Style||{}).css)||{};
      const dir2  = cssCfg2.flexDirection || (c.Config||{}).direction || 'column';
      const gap2  = cssCfg2.gap || '8px';
      return '<div style="display:flex;flex-direction:'+dir2+';gap:'+gap2+';'+css+'">'+renderSlots(c.Slots)+'</div>';
    }
    case 'section': {
      const cfg = c.Config || {};
      const title = cfg.title || cfg.Title || '';
      const titleHtml = title ? '<div class="m-section-title">'+title+'</div>' : '';
      return '<div class="m-section"'+styleAttr+'>'+titleHtml+renderSlots(c.Slots)+'</div>';
    }
    case 'banner': {
      const cfg = c.Config || {};
      const bannerType = (cfg.type||cfg.Type||'info').toLowerCase();
      const msg = cfg.message || cfg.Message || cfg.text || 'Banner message';
      const icon = bannerType==='error'?'✖':bannerType==='warning'?'⚠':bannerType==='success'?'✔':'ℹ';
      return '<div class="m-banner m-banner-'+bannerType+'"'+styleAttr+'><span class="m-banner-icon">'+icon+'</span><span class="m-banner-text">'+msg+'</span></div>';
    }
    case 'form': {
      return '<form class="m-form"'+styleAttr+' onsubmit="return false">'+renderSlots(c.Slots)+'</form>';
    }
    case 'accordion': {
      const slots = c.Slots || {};
      const slotKeys = Object.keys(slots);
      if (slotKeys.length === 0) {
        return '<div class="m-accordion"'+styleAttr+'><div class="m-accordion-empty">Accordion</div></div>';
      }
      const uid = 'acc_'+Math.random().toString(36).slice(2);
      const panels = slotKeys.map((k,i) => {
        const content = renderSlots({Default: slots[k]});
        return '<div class="m-accordion-item">'
          +'<button class="m-accordion-header" data-acc="'+uid+'" data-idx="'+i+'">'
          +k+'<span class="m-acc-arrow">'+(i===0?'▲':'▼')+'</span></button>'
          +'<div class="m-accordion-body" id="'+uid+'_'+i+'" style="'+(i===0?'':'display:none')+'">'+content+'</div>'
          +'</div>';
      }).join('');
      return '<div class="m-accordion"'+styleAttr+' id="'+uid+'">'+panels+'</div>';
    }
    case 'expandable': {
      const cfg = c.Config || {};
      const label = cfg.label || cfg.Label || cfg.title || 'Details';
      const uid2 = 'exp_'+Math.random().toString(36).slice(2);
      const content2 = renderSlots(c.Slots);
      return '<div class="m-expandable"'+styleAttr+'>'
        +'<button class="m-expandable-header" data-exp="'+uid2+'">'+label+' <span class="m-exp-arrow">▼</span></button>'
        +'<div class="m-expandable-body" id="'+uid2+'" style="display:none">'+content2+'</div>'
        +'</div>';
    }
    case 'tab-group': {
      const slots = c.Slots || {};
      const cfg3 = c.Config || {};
      // Build label map from Config.Tabs (Name → LabelKey)
      const tabLabelMap = {};
      (cfg3.Tabs||[]).forEach(t => { if (t.Name) tabLabelMap[t.Name] = t.LabelKey || t.Name; });
      // Only include tabs that have at least one item — skip empty-array slots
      const slotKeys = Object.keys(slots).filter(k => Array.isArray(slots[k]) && slots[k].length > 0);
      if (slotKeys.length === 0) {
        return '<div class="m-tab-group"'+styleAttr+'><div class="m-tab-empty">Tab Group</div></div>';
      }
      const uid3 = 'tab_'+Math.random().toString(36).slice(2);
      const tabBtns = slotKeys.map((k,i) =>
        '<button class="m-tab-btn'+(i===0?' active':'')+'" data-tab="'+uid3+'" data-idx="'+i+'">'+(tabLabelMap[k]||k)+'</button>'
      ).join('');
      const tabPanes = slotKeys.map((k,i) =>
        '<div class="m-tab-pane" id="'+uid3+'_'+i+'" style="'+(i===0?'display:flex;flex-direction:column;':'display:none')+'">'
        +renderSlots({Default: slots[k]})+'</div>'
      ).join('');
      return '<div class="m-tab-group"'+styleAttr+' id="'+uid3+'">'
        +'<div class="m-tab-bar">'+tabBtns+'</div>'
        +'<div class="m-tab-content">'+tabPanes+'</div>'
        +'</div>';
    }
    case 'search':
      return renderSearch(c);
    case 'segment-panel':
      return renderSegmentPanel(c);
    case 'list': {
      const cfg = c.Config || {};
      const itemFrag = cfg.Fragment || cfg.fragment || cfg.ItemTemplate;
      const rowCount = 3;
      let rowHtml = '';
      for (let _i = 0; _i < rowCount; _i++) {
        const inner = itemFrag ? renderContainer({...itemFrag, _listRow: _i}) : '<div class="m-list-row-placeholder">Item '+(_i+1)+'</div>';
        rowHtml += '<div class="m-list-row">'+inner+'</div>';
      }
      return '<div class="m-list"'+styleAttr+'>'+rowHtml+'</div>';
    }
    case 'carousel': {
      const cfg = c.Config || {};
      const slidesPerPage = cfg.slidesPerPage || 3;
      const nav = cfg.navigation !== false;
      const pag = cfg.pagination !== false;
      const orient = (cfg.orientation||'horizontal').toLowerCase();
      const itemFrag = cfg.Fragment || cfg.fragment || cfg.ItemTemplate;
      const slideCount = Math.max(slidesPerPage + 1, 4);
      let slidesHtml = '';
      for (let _s = 0; _s < slideCount; _s++) {
        const inner = itemFrag ? renderContainer({...itemFrag, _slideIdx: _s}) : '<div class="m-carousel-placeholder">Slide '+(_s+1)+'</div>';
        slidesHtml += '<div class="m-carousel-slide">'+inner+'</div>';
      }
      const uid4 = 'car_'+Math.random().toString(36).slice(2);
      const navHtml = nav ? '<button class="m-carousel-prev" data-car="'+uid4+'">&#8249;</button><button class="m-carousel-next" data-car="'+uid4+'">&#8250;</button>' : '';
      const dotCount = Math.ceil(slideCount / slidesPerPage);
      const dotsHtml = pag ? '<div class="m-carousel-dots">'+Array.from({length:dotCount},(_,i)=>'<span class="m-carousel-dot'+(i===0?' active':'')+'" data-car="'+uid4+'" data-dot="'+i+'"></span>').join('')+'</div>' : '';
      const isVert = orient === 'vertical';
      return '<div class="m-carousel'+(isVert?' m-carousel-vertical':'')+'"'+styleAttr+' id="'+uid4+'">'
        +(isVert?'':navHtml)
        +'<div class="m-carousel-track-wrap"><div class="m-carousel-track" id="'+uid4+'_track" data-spv="'+slidesPerPage+'">'+slidesHtml+'</div></div>'
        +(isVert?navHtml:'')
        +dotsHtml
        +'</div>';
    }
    case 'flyout-layout': {
      return '<div class="m-flyout-layout"'+styleAttr+'>'+renderSlots(c.Slots)+'</div>';
    }
    case 'header-container':
    case 'header': {
      return '<div class="m-header-container"'+styleAttr+'>'+renderSlots(c.Slots)+'</div>';
    }
    default:
      return '<div'+styleAttr+' data-container="'+type+'">'+renderSlots(c.Slots)+'</div>';
  }
}

// ── Entry point ───────────────────────────────────────────────────
function renderFragment(def) {
  const frag = def.Fragment || def;
  // The root container must fill m-body. Inject flex:1;overflow:hidden so the
  // fragment fills the viewport without affecting nested flex containers.
  if (frag.Container === 'flex') {
    const css  = buildCss(frag.Style);
    const rsc  = (frag.Style||{}).css||{};
    const rtags = ['fill'];
    if (rsc.width==='100%') rtags.push('w:100%');
    if (rsc.flexDirection) rtags.push(rsc.flexDirection);
    return '<div data-ct="root ['+rtags.join(' ')+']" style="display:flex;flex:1;min-height:0;overflow:hidden;'+css+'">'+renderSlots(frag.Slots)+'</div>';
  }
  if (frag.Container === 'grid') {
    const css  = buildCss(frag.Style);
    return '<div data-ct="root [grid fill]" style="display:grid;flex:1;min-height:0;overflow:hidden;'+css+'">'+renderSlots(frag.Slots)+'</div>';
  }
  return renderContainer(frag);
}

// ── Init ──────────────────────────────────────────────────────────
try {
  document.getElementById('frag-root').innerHTML = renderFragment(FRAG_DEF);
} catch(err) {
  document.getElementById('frag-root').innerHTML = '<div style="padding:20px;color:#dc2626;font-family:monospace;font-size:13px;background:#fff;margin:16px;border-radius:8px;border:1px solid #fca5a5"><b>Render error:</b><br>'+err+'</div>';
  console.error('Fragment render error:', err);
}

// ── Container outline toggle ──────────────────────────────────────
(function() {
  const cb = document.getElementById('toggle-containers');
  function apply() { document.body.classList.toggle('show-containers', cb.checked); }
  cb.addEventListener('change', apply);
  apply(); // on by default since checkbox is checked
})();

// ── Event delegation (popover + flyout) ──────────────────────────
document.addEventListener('click', e => {
  // Popover trigger
  const popBtn = e.target.closest('[data-popid]');
  if (popBtn) {
    const menu = document.getElementById(popBtn.dataset.popid);
    if (menu) menu.classList.toggle('open');
    e.stopPropagation();
    return;
  }
  // Flyout close button
  const flyBtn = e.target.closest('[data-flyout]');
  if (flyBtn) {
    const panel = document.getElementById(flyBtn.dataset.flyout);
    if (panel) {
      const isOpen = panel.style.width && panel.style.width !== '0px';
      panel.style.width = isOpen ? '0px' : (flyBtn.dataset.flyoutW || '300px');
    }
    return;
  }
  // Close popovers when clicking outside
  if (!e.target.closest('.m-actions-popover')) {
    document.querySelectorAll('.m-actions-popover-menu.open').forEach(m => m.classList.remove('open'));
  }
  // Tab group
  const tabBtn = e.target.closest('[data-tab]');
  if (tabBtn) {
    const uid = tabBtn.dataset.tab;
    const idx = parseInt(tabBtn.dataset.idx, 10);
    const grp = document.getElementById(uid);
    if (grp) {
      grp.querySelectorAll('.m-tab-btn').forEach(b => b.classList.remove('active'));
      grp.querySelectorAll('.m-tab-pane').forEach(p => { p.style.display = 'none'; });
      tabBtn.classList.add('active');
      const pane = document.getElementById(uid+'_'+idx);
      if (pane) { pane.style.display = 'flex'; pane.style.flexDirection = 'column'; pane.style.gap = '8px'; }
    }
    return;
  }
  // Accordion
  const accBtn = e.target.closest('[data-acc]');
  if (accBtn) {
    const uid = accBtn.dataset.acc;
    const idx = parseInt(accBtn.dataset.idx, 10);
    const body = document.getElementById(uid+'_'+idx);
    if (body) {
      const isOpen = body.style.display !== 'none';
      body.style.display = isOpen ? 'none' : '';
      const arrow = accBtn.querySelector('.m-acc-arrow');
      if (arrow) arrow.textContent = isOpen ? '▼' : '▲';
    }
    return;
  }
  // Expandable
  const expBtn = e.target.closest('[data-exp]');
  if (expBtn) {
    const uid = expBtn.dataset.exp;
    const body = document.getElementById(uid);
    if (body) {
      const isOpen = body.style.display !== 'none';
      body.style.display = isOpen ? 'none' : '';
      const arrow = expBtn.querySelector('.m-exp-arrow');
      if (arrow) arrow.textContent = isOpen ? '▼' : '▲';
    }
    return;
  }
  // Carousel prev/next
  const carBtn = e.target.closest('[data-car]');
  if (carBtn && (carBtn.classList.contains('m-carousel-prev') || carBtn.classList.contains('m-carousel-next'))) {
    const uid = carBtn.dataset.car;
    const track = document.getElementById(uid+'_track');
    if (track) {
      const spv = parseInt(track.dataset.spv, 10) || 1;
      const slides = track.querySelectorAll('.m-carousel-slide');
      const total = slides.length;
      let cur = parseInt(track.dataset.cur||'0', 10);
      if (carBtn.classList.contains('m-carousel-next')) cur = Math.min(cur+1, total-spv);
      else cur = Math.max(cur-1, 0);
      track.dataset.cur = cur;
      const slideW = slides[0] ? slides[0].offsetWidth : 180;
      track.style.transform = 'translateX(-'+(cur*slideW)+'px)';
      const grp = document.getElementById(uid);
      if (grp) {
        grp.querySelectorAll('.m-carousel-dot').forEach((d,i) => {
          d.classList.toggle('active', Math.floor(cur/spv)===i);
        });
      }
    }
    return;
  }
  // Carousel dots
  if (carBtn && carBtn.classList.contains('m-carousel-dot')) {
    const uid = carBtn.dataset.car;
    const dotIdx = parseInt(carBtn.dataset.dot, 10);
    const track = document.getElementById(uid+'_track');
    if (track) {
      const spv = parseInt(track.dataset.spv, 10) || 1;
      const slides = track.querySelectorAll('.m-carousel-slide');
      const cur = dotIdx * spv;
      track.dataset.cur = cur;
      const slideW = slides[0] ? slides[0].offsetWidth : 180;
      track.style.transform = 'translateX(-'+(cur*slideW)+'px)';
      const grp = document.getElementById(uid);
      if (grp) {
        grp.querySelectorAll('.m-carousel-dot').forEach((d,i) => d.classList.toggle('active', i===dotIdx));
      }
    }
    return;
  }
});
</script>
</body>
</html>'''
        return tpl.replace('"__FRAG_JSON__"', frag_json_str)

    def _build_fragment_patched(self):
        """Return fragment JSON using imported_fragment_root as the base tree.
        Walks the tree and patches only nodes whose canvas card was explicitly
        edited (links, events, sorting, highcharts options, element config, etc.).
        All container structure, Init, Style, flex wrappers, header-action slots,
        and unedited elements pass through verbatim — layout is never touched
        unless the user explicitly used Align Fix (_style_edited / extra_css)."""

        # ── Build match maps for all edited canvas cards ──────────────────
        # Keys used for lookup in the imported tree:
        #   ("uid",  uid)          → any card type with UID
        #   ("tbl",  ds)           → table by DataSourcePath
        #   ("chart",ds)           → grid+header chart or native chart by DS
        #   (ctype,  cfg_name)     → RIVER_TYPE elem by Container/Element type + Config.Name
        match_map: dict = {}

        for card in self.cards.values():
            _edited = (getattr(card, '_config_edited', False)
                       or getattr(card, '_style_edited', False)
                       or getattr(card, 'extra_css', {}))
            if not _edited:
                continue
            # CID fallback (canvas card ID - unique identifier)
            match_map[("cid", card.cid)] = card
            if card.uid:
                match_map[("uid", card.uid)] = card
            if card.ds:
                if card.ctype == "table":
                    match_map[("tbl", card.ds)] = card
                elif card.ctype in CHART_TYPES and card.ctype != "metrics":
                    match_map[("chart", card.ds)] = card
            # RIVER_TYPE elements: match by element type + Config.Name (unique per section)
            if card.ctype in RIVER_TYPES:
                _cfg_name = (card.elem_config or {}).get("Name", "")
                if _cfg_name:
                    match_map[(card.ctype, _cfg_name)] = card

        def _find_card(node):
            """Return the matching edited canvas card for this node, or None."""
            ctype = node.get("Container") or node.get("Element", "")
            uid   = node.get("UID", "")

            # UID is the most reliable key
            if uid:
                c = match_map.get(("uid", uid))
                if c: return c

            # Table → DataSourcePath (with fallback to title/segment matching)
            if ctype == "table":
                ds = node.get("Init", {}).get("DataSourcePath", "")
                c = match_map.get(("tbl", ds))
                if c: return c
                # Fallback: match by title if DataSourcePath fails
                node_title = (node.get("Config") or {}).get("title", "")
                if node_title:
                    for card in self.cards.values():
                        if (card.ctype == "table"
                                and getattr(card, '_config_edited', False)
                                and card.title == node_title):
                            return c
                # Fallback: match by segment and position if only one edited table in segment
                node_seg = node.get("_segment", "")
                if node_seg:
                    seg_edited_tables = [c for c in self.cards.values()
                                        if c.ctype == "table"
                                        and getattr(c, '_config_edited', False)
                                        and getattr(c, 'segment', '') == node_seg]
                    if len(seg_edited_tables) == 1:
                        return seg_edited_tables[0]

            # Generic fallback: try CID if stored in node metadata
            # (This handles cases where UID/DataSourcePath don't match)
            cid_meta = node.get("_cid")
            if cid_meta:
                c = match_map.get(("cid", cid_meta))
                if c: return c

            # Grid+header chart → extract inner chart's DataSourcePath
            if (ctype == "grid"
                    and "header" in node.get("Slots", {})
                    and "content" in node.get("Slots", {})):
                try:
                    ds = node["Slots"]["content"][0]["Slots"]["Default"][0]["Init"]["DataSourcePath"]
                    return match_map.get(("chart", ds))
                except (KeyError, IndexError, TypeError):
                    pass

            # Native chart node
            if ctype == "chart":
                ds = node.get("Init", {}).get("DataSourcePath", "")
                return match_map.get(("chart", ds))

            # RIVER_TYPE elements (search, segment-panel, button, etc.)
            if ctype in RIVER_TYPES:
                _name = node.get("Config", {}).get("Name", "")
                if _name:
                    return match_map.get((ctype, _name))

            return None

        def _patch(node):
            if not isinstance(node, dict):
                return node
            card = _find_card(node)
            if card:
                out = self._comp_json(card)
                _strip_internal_meta(out)
                return out
            # No match — recurse to find edited children deeper in the tree
            result = {}
            for k, v in node.items():
                if isinstance(v, dict):
                    result[k] = _patch(v)
                elif isinstance(v, list):
                    result[k] = [_patch(i) if isinstance(i, dict) else i for i in v]
                else:
                    result[k] = v
            return result

        patched = _patch(copy.deepcopy(self.imported_fragment_root))

        # ── Second pass: apply segment-level changes ──────────────────────
        # Groups cards by segment name for slot rebuilding.
        seg_cards: dict = {}  # seg_name → [cards sorted by canvas position]
        for _c in sorted(self.cards.values(), key=lambda c: (c.winfo_y(), c.winfo_x())):
            if _c.segment:
                seg_cards.setdefault(_c.segment, []).append(_c)

        # Segments whose canvas cards differ from what the original tree had
        # (any card edited, or any segment prop changed vs import defaults).
        # We detect "changed" conservatively: if any card in the segment is
        # _config_edited, OR if segment_dirs has keys beyond the import defaults.
        changed_segs: set = set()
        for _c in self.cards.values():
            if _c.segment and getattr(_c, '_config_edited', False):
                changed_segs.add(_c.segment)

        def _card_json(card):
            out = self._comp_json(card)
            _strip_internal_meta(out)
            return out

        def _seg_css_dict(seg_name):
            """Return CSS dict to apply for a segment from segment_dirs."""
            cfg = self.segment_dirs.get(seg_name, {})
            css = {}
            _dir = cfg.get("direction", "")
            if _dir: css["flexDirection"] = _dir
            _gap = cfg.get("gap", "")
            if _gap: css["gap"] = _gap
            _pad = cfg.get("padding", {})
            if isinstance(_pad, dict):
                _pv = [_pad.get(k, 0) for k in ("top","right","bottom","left")]
                if any(_pv):
                    css["padding"] = f"{_pv[0]}px {_pv[1]}px {_pv[2]}px {_pv[3]}px"
            for _xk, _xv in cfg.get("extra_css", {}).items():
                if _xv: css[_xk] = _xv
            return css

        def _rebuild_seg_slots(seg_name):
            """Return rebuilt Default slot list for a named segment."""
            cards_in_seg = seg_cards.get(seg_name, [])
            result = []
            for _sc in cards_in_seg:
                if _sc.ctype == "filter-panel":
                    continue
                result.append(_card_json(_sc))
            # Re-append passthrough nodes for this segment
            for _pt in getattr(self, 'passthrough_nodes', []):
                if _pt.get("segment") == seg_name:
                    result.append(copy.deepcopy(_pt["node"]))
            return result

        def _apply_seg_updates(node):
            if not isinstance(node, dict):
                return
            ctype = node.get("Container", "")

            # ── header-action: rebuild Left/Right slots when cards changed ──
            if ctype == "header-action":
                ha_sec = node.get("Config", {}).get("SectionName", "header-action")
                ha_meta = getattr(self, 'header_action_meta', {})
                # Apply any updated Style/Config/Events stored in header_action_meta
                if ha_meta.get("style"):  node["Style"]  = ha_meta["style"]
                if ha_meta.get("config"): node["Config"] = ha_meta["config"]
                if ha_meta.get("events"): node["Events"] = ha_meta["events"]
                if ha_sec in changed_segs:
                    ha_left  = []
                    ha_right = []
                    for _hc in seg_cards.get(ha_sec, []):
                        _hn = _card_json(_hc)
                        slot = getattr(_hc, '_ha_slot', 'Right')
                        if slot == "Left":   ha_left.append(_hn)
                        else:                ha_right.append(_hn)
                    new_slots = {}
                    if ha_left:  new_slots["Left"]  = ha_left
                    if ha_right: new_slots["Right"] = ha_right
                    if new_slots:
                        node["Slots"] = new_slots

            # ── Named flex/grid/stack containers: update CSS + rebuild if changed ──
            sec_name = (node.get("Config") or {}).get("SectionName", "")
            if sec_name and sec_name in self.segment_dirs:
                # Always apply latest CSS from segment_dirs (no-op if unchanged)
                _css = _seg_css_dict(sec_name)
                if _css:
                    node.setdefault("Style", {}).setdefault("css", {}).update(_css)
                # Rebuild Default slot content if cards in this segment were edited
                if sec_name in changed_segs:
                    rebuilt = _rebuild_seg_slots(sec_name)
                    if rebuilt:
                        node.setdefault("Slots", {})["Default"] = rebuilt
                # Apply segment events
                _evts = self.segment_dirs[sec_name].get("events", {})
                if _evts:
                    node["Events"] = _evts

            # Recurse into children
            for _v in node.values():
                if isinstance(_v, dict):
                    _apply_seg_updates(_v)
                elif isinstance(_v, list):
                    for _i in _v:
                        if isinstance(_i, dict):
                            _apply_seg_updates(_i)

        _apply_seg_updates(patched)
        return {"Fragment": patched}

    def _generate_fragment(self):
        try:
            if getattr(self, 'imported_fragment_root', None):
                _frag = self._build_fragment_patched()
            else:
                _frag = self._build_fragment()
            _strip_internal_meta(_frag)
            raw = re.sub(r'"\{:(?!Metric\b)([\w]+)\}"', r'{:\1}', json.dumps(_frag, indent=2))
            self._debug_save(raw)
            self._show_json("✅ Fragment JSON (agentContentsCustom)", raw, "mhe_fragment.json")
        except Exception as e: messagebox.showerror("Generation Error", f"Failed to build Fragment JSON:\n{str(e)}")

    def _generate_action(self): 
        try: self._show_json("⚡ Action JSON (renderUI Task)", json.dumps(self._action_json(), indent=2), "mhe_action.json")
        except Exception as e: messagebox.showerror("Generation Error", f"Failed to build Action JSON:\n{str(e)}")
            
    def _clear(self):
        if messagebox.askyesno("Clear All","Remove all components?"):
            self._debug_log_event("CLEAR_ALL", f"Cleared canvas: {len(self.cards)} cards, {len(self.filters)} filters removed")
            self.imported_fragment_root = None
            for cid in list(self.cards.keys()): self.remove_comp(cid)
            for f in list(self.filters): self.remove_filter(f.fid)

    # ── Debug mode ──────────────────────────────────────────────────
    def _toggle_strict_import(self):
        if self.strict_roundtrip_import.get():
            # Turning OFF → canvas rebuild mode (reflow card positions/widths)
            self.strict_roundtrip_import.set(False)
            self._strict_btn.config(bg="#374151", fg="#9CA3AF", text="🔓 Strict Mode: OFF")
            self._do_import_layout()
        else:
            # Turning ON → strict preserve mode (no auto-reflow, no width redistribution)
            self.strict_roundtrip_import.set(True)
            self._strict_btn.config(bg="#14532D", fg="#86EFAC", text="🔒 Strict Mode: ON")

    def _toggle_debug(self):
        import datetime as _dt
        if self.debug_mode.get():
            # Turning OFF
            self.debug_mode.set(False)
            self._debug_btn.config(bg="#374151", fg="#9CA3AF", text="🐛 Debug")
            self._debug_log_event("DEBUG_OFF", "Debug mode disabled")
        else:
            # Turning ON
            self.debug_mode.set(True)
            self._debug_session_start = _dt.datetime.now()
            self._debug_log = []
            self._debug_imported_json = None
            self._debug_btn.config(bg="#16A34A", fg="white", text="🐛 Debug ON")
            self._debug_log_event("DEBUG_ON", f"Debug session started — {self._debug_session_start.strftime('%Y-%m-%d %H:%M:%S')}")

    def _debug_log_event(self, action, detail):
        if not self.debug_mode.get():
            return
        import datetime as _dt
        entry = {
            "time": _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "action": action,
            "detail": detail,
        }
        self._debug_log.append(entry)
        print(f"[DEBUG] {entry['time']} | {action:25s} | {detail}")

    def _debug_save(self, exported_json_str):
        import datetime as _dt, os
        if not self.debug_mode.get():
            return
        self._debug_log_event("EXPORT", f"Fragment JSON generated — {len(exported_json_str)} chars")
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"FragDesgDebug_{ts}.json"
        try:
            imported = None
            if self._debug_imported_json:
                try:
                    imported = json.loads(self._debug_imported_json)
                except Exception:
                    imported = self._debug_imported_json
            exported = None
            try:
                exported = json.loads(exported_json_str)
            except Exception:
                exported = exported_json_str
            # Build changes summary
            changes = {"cards_on_canvas": [], "filters_on_canvas": []}
            for cid, card in self.cards.items():
                changes["cards_on_canvas"].append({
                    "cid": cid, "ctype": card.ctype,
                    "title": card.title, "segment": getattr(card, "segment", ""),
                    "ds": getattr(card, "ds", ""),
                    "css_width": getattr(card, "css_width", ""),
                    "css_height": getattr(card, "css_height", ""),
                })
            for flt in self.filters:
                changes["filters_on_canvas"].append({
                    "fid": flt.fid, "ftype": getattr(flt, 'ftype', '?'),
                    "label": getattr(flt, "label", ""), "key": getattr(flt, "key", ""),
                })
            report = {
                "debug_session": {
                    "start_time": self._debug_session_start.strftime("%Y-%m-%d %H:%M:%S") if self._debug_session_start else "",
                    "end_time": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fragment_designer_version": APP_VERSION,
                    "total_actions": len(self._debug_log),
                },
                "imported_json": imported,
                "exported_json": exported,
                "canvas_state_at_export": changes,
                "action_log": self._debug_log,
            }
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            messagebox.showinfo("Debug Report Saved",
                                f"Debug report saved to:\n{os.path.abspath(fname)}\n\n"
                                f"Actions logged: {len(self._debug_log)}\n"
                                f"Canvas cards: {len(self.cards)}, Filters: {len(self.filters)}",
                                parent=self)
        except Exception as e:
            messagebox.showwarning("Debug Save Error", f"Could not save debug file:\n{e}", parent=self)

if __name__=="__main__": Designer().mainloop()
