"""
MAWM Agent Tools — FastAPI backend proxy for Glean AI.

Routes:
  POST /api/glean/chat     → Glean /chat (generic, Agent Creator)
  POST /api/glean/agent    → Glean /runworkflow (Fragment Designer agent)
  POST /api/glean/upload   → Glean /uploadfile (image uploads)

All Glean requests use Chrome cookies loaded via browser-cookie3.
Streaming responses are forwarded as SSE  (data: {"text": "..."}\n\n).
"""

from __future__ import annotations
import json, os, time, pathlib
from datetime import datetime, timezone
from typing import Any

import browser_cookie3
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agent_creator_prompt import GLEAN_SYSTEM_PROMPT
from fragment_designer_prompt import ALIGN_FIX_SYSTEM

app = FastAPI(title="MAWM Agent Tools Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GLEAN_BASE       = "https://manhattan-associates-be.glean.com/api/v1"
GLEAN_HOST       = "manhattan-associates-be.glean.com"
GLEAN_ORIGIN     = f"https://{GLEAN_HOST}"

# Cookies persisted to disk so they survive hot-reloads and restarts
_COOKIE_FILE = pathlib.Path(__file__).parent / ".glean_cookies.json"

def _load_persisted_cookies() -> dict[str, str]:
    try:
        return json.loads(_COOKIE_FILE.read_text())
    except Exception:
        return {}

def _save_persisted_cookies(cookies: dict[str, str]) -> None:
    _COOKIE_FILE.write_text(json.dumps(cookies))

_runtime_cookies: dict[str, str] = _load_persisted_cookies()
GLEAN_API_PARAMS = {"clientVersion": "fe-release-2026-05-28-9a91fc9", "locale": "en"}
GLEAN_AGENT_ID   = "2491a8dae7254256975430b2c635a26b"


def _get_glean_cookies() -> dict[str, str]:
    """Load Glean cookies — extension push takes priority, then browser_cookie3."""
    global _runtime_cookies
    # 1. Cookies pushed by Chrome extension (all domain cookies)
    if _runtime_cookies:
        return _runtime_cookies

    # 2. Auto-read from Chrome via browser_cookie3
    cookies: dict[str, str] = {}
    for domain in [GLEAN_HOST, ".glean.com", "glean.com"]:
        try:
            jar = browser_cookie3.chrome(domain_name=domain)
            for ck in jar:
                cookies[ck.name] = ck.value
        except Exception:
            pass

    if not cookies:
        raise HTTPException(
            status_code=401,
            detail="Glean cookies not found. Install the MAWM Chrome extension or log in to Glean in Chrome first.",
        )
    return cookies


@app.get("/api/debug/cookies")
async def debug_cookies():
    """List Glean cookie names found by browser_cookie3 (for troubleshooting)."""
    found: dict[str, list[str]] = {}
    for domain in ["manhattan-associates-be.glean.com", ".glean.com", "glean.com"]:
        names = []
        try:
            jar = browser_cookie3.chrome(domain_name=domain)
            names = [ck.name for ck in jar]
        except Exception as e:
            names = [f"ERROR: {e}"]
        found[domain] = names
    manual = os.environ.get("GLEAN_SESSION_COOKIE", "")
    return {
        "manual_override_set": bool(manual),
        "cookies_by_domain": found,
    }


def _glean_headers() -> dict[str, str]:
    # Match exactly what the working Python desktop app sends
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        "Referer":      "https://app.glean.com/",
        "Origin":       "https://app.glean.com",
        "Content-Type": "text/plain",
    }


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def _stream_glean(url: str, body: dict, cookies: dict):
    """
    Stream a Glean request and yield SSE lines.
    Client lives inside the generator so it is not closed prematurely by the route handler.
    """
    last_text = ""
    buf = ""  # accumulate partial JSON lines across chunks

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST", url,
                params={"timezoneOffset": "240", **GLEAN_API_PARAMS},
                content=json.dumps(body),
                headers=_glean_headers(),
                cookies=cookies,
                timeout=180,
            ) as resp:
                if resp.status_code == 401:
                    yield f"data: {json.dumps({'error': 'Glean 401 — session expired'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if not resp.is_success:
                    body_text = await resp.aread()
                    yield f"data: {json.dumps({'error': f'Glean HTTP {resp.status_code}: {body_text[:200].decode()}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for raw_chunk in resp.aiter_text():
                    buf += raw_chunk
                    # process every complete newline-terminated segment
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            for m in obj.get("messages", []):
                                if m.get("author") == "USER":
                                    continue
                                chunk_text = "".join(
                                    f["text"]
                                    for f in m.get("fragments", [])
                                    if isinstance(f, dict) and "text" in f
                                )
                                if not chunk_text:
                                    continue
                                # Glean sends snapshots (full text each time) or deltas
                                if chunk_text.startswith(last_text):
                                    last_text = chunk_text
                                else:
                                    last_text += chunk_text
                                yield f"data: {json.dumps({'text': last_text})}\n\n"
                        except json.JSONDecodeError:
                            pass  # partial chunk — wait for more

        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    yield "data: [DONE]\n\n"


# ── Request models ────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    conversation: list[ChatMessage]
    chatId: str | None = None
    agent_context: dict | None = None

class AgentRequest(BaseModel):
    prompt: str
    uploadedFileIds: list[str] = Field(default_factory=list)
    fragment_json: dict = Field(default_factory=dict)
    issues: list = Field(default_factory=list)
    conversation: list[ChatMessage] = Field(default_factory=list)


# ── Routes ────────────────────────────────────────────────────────────

def _build_chat_body(req: ChatRequest) -> dict[str, Any]:
    """Pure request-body construction for Glean /chat (Agent Creator) — no cookies, no network call.
    Shared by the server-side proxy route and the extension-relay "build" route."""
    now = _now_iso()
    messages = []
    if not req.chatId:
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": "USER",
            "fragments": [{"text": GLEAN_SYSTEM_PROMPT}],
            "messageType": "CONTENT",
            "ts": now,
        })
        if req.agent_context:
            import json as _json
            context_lines = ["[Current Agent Context]"]
            if req.agent_context.get("flowId"):
                context_lines.append(f"Flow: {req.agent_context['flowId']}  Task: {req.agent_context.get('taskId', 'default')}")
            if req.agent_context.get("actions"):
                context_lines.append(f"Actions ({len(req.agent_context['actions'])} total):")
                for a in req.agent_context["actions"]:
                    name = a.get("name", "?")
                    atype = a.get("type", "?")
                    desc = a.get("description", "")
                    context_lines.append(f"  - {name} ({atype}){': ' + desc if desc else ''}")
                context_lines.append("")
                context_lines.append("Full action JSON:")
                context_lines.append(_json.dumps(req.agent_context["actions"], indent=2))
            if req.agent_context.get("fragments"):
                context_lines.append("")
                context_lines.append(f"Fragment Contents ({len(req.agent_context['fragments'])} item(s)):")
                for frag in req.agent_context["fragments"]:
                    fname = frag.get("name", "?")
                    fcontent = frag.get("content", "")
                    context_lines.append(f"  Fragment: {fname}")
                    if fcontent:
                        context_lines.append(f"  Content: {fcontent}")
                    context_lines.append("")
            context_lines.append("[End Context]")
            messages.append({
                "agentConfig": {"agent": "FAST"},
                "author": "CHATBOT",
                "fragments": [{"text": "\n".join(context_lines)}],
                "messageType": "CONTENT",
                "ts": now,
            })
    for msg in req.conversation:
        if msg.role != "user":
            continue
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": "USER",
            "fragments": [{"text": msg.text}],
            "messageType": "CONTENT",
            "ts": now,
        })

    body: dict[str, Any] = {
        "agentConfig": {
            "agent": "FAST",
            "toolSets": {"enableCompanyTools": True, "enableWebSearch": True},
            "useCanvas": False,
            "useImageGeneration": False,
            "clientCapabilities": {
                "artifacts": {"allowedArtifactTypes": ["PAPER", "HTML_CODE"]},
                "canRenderImages": False,
            },
        },
        "background": False,
        "clientTools": [],
        "messages": messages,
        "saveChat": True,
        "sourceInfo": {
            "feature": "CHAT", "initiator": "USER", "platform": "WEB",
            "hasCopyPaste": False, "isDebug": False,
        },
        "stream": True,
        "sc": "",
        "sessionInfo": {
            "lastSeen": now,
            "sessionTrackingToken": "agentcreator-web",
            "tabId": "agentcreator-tab",
            "clickedInJsSession": True,
            "firstEngageTsSec": int(time.time()),
        },
    }
    if req.chatId:
        body["chatId"] = req.chatId
    return body


@app.post("/api/glean/chat")
async def proxy_chat(req: ChatRequest):
    """Proxy to Glean /chat (generic, used by Agent Creator). Uses the shared backend cookie —
    prefer the extension relay (/api/glean/chat/build + browser-side fetch) when available,
    since that uses each user's own session instead of one shared server-side cookie."""
    cookies = _get_glean_cookies()
    body = _build_chat_body(req)
    return StreamingResponse(
        _stream_glean(f"{GLEAN_BASE}/chat", body, cookies),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/glean/chat/build")
async def build_chat_request(req: ChatRequest):
    """Pure request-body builder for the extension relay — no cookies needed, no network call.
    The browser extension fetches Glean directly with this using the user's own ambient session."""
    return {
        "url": f"{GLEAN_BASE}/chat",
        "params": {"timezoneOffset": "240", **GLEAN_API_PARAMS},
        "body": _build_chat_body(req),
    }


def _build_agent_body(req: AgentRequest) -> dict[str, Any]:
    """Pure request-body construction for Glean /chat using ALIGN_FIX_SYSTEM (Fragment Designer) —
    no cookies, no network call. Shared by the server-side proxy route and the extension-relay
    "build" route."""
    now = _now_iso()
    payload_obj = {
        "user_prompt": req.prompt,
        "fragment_json": req.fragment_json,
        "issues": req.issues,
        "tool_context": {
            "source": "Fragment UI Designer Align Fix Validate",
            "goal": "Render suggested fixes in Validate section and allow Apply Suggested Fix",
            "apply_behavior": {
                "supported_ops": ["set_props", "set_config", "set_events", "add_child", "replace_node", "delete_node", "merge_json"],
                "path_syntax": "Dot/bracket path from the Fragment root, e.g. Fragment.Slots.Default[1].Slots['Fill Rate'][0]. "
                                "Slot keys with spaces or special characters MUST use bracket-quote notation ['Slot Name'] — "
                                "never dot-then-apostrophe (Slots'Fill Rate' is invalid and will fail to apply).",
            },
        },
    }

    messages = [
        {
            "agentConfig": {"agent": "FAST"},
            "author": "USER",
            "fragments": [{"text": ALIGN_FIX_SYSTEM}],
            "messageType": "CONTENT",
            "ts": now,
        },
    ]
    # Replay prior turns so Glean actually has conversation memory — matches the pattern
    # /api/glean/chat (Agent Creator) already uses. Without this every message was a fresh,
    # context-free call: follow-ups like "again give" or "no, fix the other one" had nothing
    # to refer back to, so the AI would ignore/misread what the user actually meant.
    for msg in req.conversation:
        if msg.role != "user":
            continue
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": "USER",
            "fragments": [{"text": msg.text}],
            "messageType": "CONTENT",
            "ts": now,
        })
    messages.append({
        "agentConfig": {"agent": "FAST"},
        "author": "USER",
        "fragments": [{"text": json.dumps(payload_obj, indent=2)}],
        "messageType": "CONTENT",
        "ts": now,
    })

    body: dict[str, Any] = {
        "agentConfig": {
            "agent": "FAST",
            # Fragment fixes are a pure structural transform over the fragment_json we already
            # send in full — company/web search adds nothing but latency and off-topic retrieved
            # docs that dilute context (observed: Glean would search Confluence/SharePoint/Bitbucket
            # for generic "json sample" docs even when the whole fragment tree was already given).
            "toolSets": {"enableCompanyTools": False, "enableWebSearch": False},
            "useCanvas": False,
            "useImageGeneration": False,
            "clientCapabilities": {
                "artifacts": {"allowedArtifactTypes": ["PAPER", "HTML_CODE"]},
                "canRenderImages": False,
            },
        },
        "background": False,
        "clientTools": [],
        "messages": messages,
        "saveChat": True,
        "sourceInfo": {
            "feature": "CHAT", "initiator": "USER", "platform": "WEB",
            "hasCopyPaste": False, "isDebug": False,
        },
        "stream": True,
        "sc": "",
        "sessionInfo": {
            "lastSeen": now,
            "sessionTrackingToken": "fragdesigner-web",
            "tabId": "fragdesigner-tab",
            "clickedInJsSession": True,
            "firstEngageTsSec": int(time.time()),
        },
    }
    return body


@app.post("/api/glean/agent")
async def proxy_agent(req: AgentRequest):
    """Proxy to Glean /chat using ALIGN_FIX_SYSTEM (Fragment Designer AI). Uses the shared backend
    cookie — prefer the extension relay (/api/glean/agent/build + browser-side fetch) when
    available, since that uses each user's own session instead of one shared server-side cookie."""
    cookies = _get_glean_cookies()
    body = _build_agent_body(req)
    return StreamingResponse(
        _stream_glean(f"{GLEAN_BASE}/chat", body, cookies),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/glean/agent/build")
async def build_agent_request(req: AgentRequest):
    """Pure request-body builder for the extension relay — no cookies needed, no network call."""
    return {
        "url": f"{GLEAN_BASE}/chat",
        "params": {"timezoneOffset": "240", **GLEAN_API_PARAMS},
        "body": _build_agent_body(req),
    }


@app.post("/api/glean/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to Glean /uploadchatfiles and return its fileId."""
    cookies = _get_glean_cookies()
    content = await file.read()
    filename = file.filename or "attachment"
    content_type = file.content_type or "application/octet-stream"
    hdrs = _glean_headers()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.post(
                f"{GLEAN_BASE}/uploadchatfiles",
                params=GLEAN_API_PARAMS,
                headers={k: v for k, v in hdrs.items() if k.lower() != 'content-type'},
                cookies=cookies,
                files={"files": (filename, content, content_type)},
            )
        if not resp.is_success:
            raise HTTPException(status_code=resp.status_code, detail=f"Glean upload failed {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        file_ids = data.get("fileIds") or [f["id"] for f in data.get("files", []) if f.get("id")]
        if not file_ids:
            raise HTTPException(status_code=500, detail=f"No fileId in upload response: {data}")
        return JSONResponse({"fileId": file_ids[0], "filename": filename})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e!r}")


class SetCookieRequest(BaseModel):
    cookies: dict[str, str] = {}  # full cookie dict from extension
    cookie: str = ""              # legacy single-cookie fallback

@app.post("/api/glean/set-cookie")
async def set_cookie(req: SetCookieRequest):
    """Accept cookies pushed by the Chrome extension and persist them to disk."""
    global _runtime_cookies
    if req.cookies:
        _runtime_cookies = req.cookies
    elif req.cookie:
        _runtime_cookies = {"glean-session-store": req.cookie.strip()}
    _save_persisted_cookies(_runtime_cookies)
    return {"status": "ok", "count": len(_runtime_cookies)}


@app.get("/api/debug/glean-raw")
async def debug_glean_raw():
    """Detailed Glean request debug — shows exactly what is sent and received."""
    cookies = _get_glean_cookies()
    now = _now_iso()
    hdrs = _glean_headers()
    body = {
        "agentConfig": {"agent": "FAST", "toolSets": {"enableCompanyTools": False}},
        "messages": [{"author": "USER", "fragments": [{"text": "Say hello in 5 words."}],
                      "messageType": "CONTENT", "ts": now,
                      "agentConfig": {"agent": "FAST"}}],
        "saveChat": False, "stream": True, "background": False,
        "sourceInfo": {"feature": "CHAT", "initiator": "USER", "platform": "WEB"},
        "sc": "",
    }
    lines = []
    resp_headers = {}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream(
            "POST", f"{GLEAN_BASE}/chat",
            params={"timezoneOffset": "240", **GLEAN_API_PARAMS},
            content=json.dumps(body),
            headers=hdrs,
            cookies=cookies,
            timeout=30,
        ) as resp:
            resp_headers = dict(resp.headers)
            raw = ""
            async for chunk in resp.aiter_text():
                raw += chunk
                while "\n" in raw:
                    line, raw = raw.split("\n", 1)
                    line = line.strip()
                    if line:
                        lines.append(line)
                    if len(lines) >= 5:
                        break
                if len(lines) >= 5:
                    break
    return {
        "status_code": resp.status_code,
        "request_headers": hdrs,
        "cookie_keys_sent": list(cookies.keys()),
        "response_headers": resp_headers,
        "first_lines": lines,
    }


@app.get("/api/health")
async def health():
    cookies = _load_persisted_cookies()
    return {"status": "ok", "cookies_loaded": len(cookies), "cookie_names": list(cookies.keys())}


# Serve the built frontend (npm run build → dist/) when present, so a single process can
# host both the API and the SPA in production. No-op for local dev where dist/ doesn't exist —
# `npm run dev`'s Vite dev server handles the frontend there instead.
_dist_dir = pathlib.Path(__file__).resolve().parent.parent / "dist"
if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
