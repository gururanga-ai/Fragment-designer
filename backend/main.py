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
import io, json, os, time, pathlib, zipfile
from datetime import datetime, timezone
from typing import Any

import browser_cookie3
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agent_creator_prompt import GLEAN_SYSTEM_PROMPT
from fragment_designer_prompt import ALIGN_FIX_SYSTEM

# Enhance Prompt uses this instead of GLEAN_SYSTEM_PROMPT — GLEAN_SYSTEM_PROMPT frames the whole
# exchange as "generate agent JSON in one of these 3 modes", which made Glean respond to Enhance's
# plain-text request with a full CONFIG/FLOW/FRAGMENT-shaped JSON blob (sometimes inventing/reusing
# unrelated existing-agent context it found via company search) instead of a rewritten description,
# even though the per-call meta-prompt explicitly asked for plain text only. Enhance needs a system
# framing that has no JSON-mode concept at all.
ENHANCE_SYSTEM_PROMPT = """You are a research assistant helping refine a short, informal request for a new data agent into a detailed, implementation-ready description.

Use your company search tools (Confluence, Bitbucket, Jira, Salesforce, entity/data-schema knowledge, similar existing agents) to ground the rewrite in real, confirmed facts — never invent field names, table names, service endpoint names, or entity names you can't confirm.

You are NOT building or configuring an agent yourself. Do not output agent JSON, flow actions, fragment JSON, or any structured data of any kind. Always respond with plain prose text only — no JSON, no markdown code fences, no bullet-only outline, no preamble like "Here is...". Just the rewritten description, ready to paste into another tool."""

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

# Manhattan Active platform OAuth — same "omnicomponent.1.0.0" client used by the other internal
# scripts in this repo (Archived Tools/mawmfunc.py) for password-grant token retrieval.
MANH_OAUTH_CLIENT_BASIC = "Basic b21uaWNvbXBvbmVudC4xLjAuMDpiNHM4cmdUeWc1NVhZTnVu"

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
    last_message_id = None
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
                                # Glean tags its own "**Searching company knowledge**" / "**Reading:**"
                                # progress narration as messageType UPDATE, distinct from the real
                                # streamed answer (messageType CONTENT) — same shape (author/fragments),
                                # so without this check the narration text gets concatenated straight
                                # into the accumulated response the moment the two don't share a prefix.
                                if m.get("messageType") not in (None, "CONTENT"):
                                    continue
                                # Deep Research mode streams its OWN visible reasoning/planning trace
                                # under messageType CONTENT too (not just UPDATE) — messageType alone
                                # can't tell "thinking out loud" apart from the real final answer.
                                # Confirmed via raw capture: a single call streamed 3 distinct CONTENT
                                # messageIds in sequence (2 reasoning passes, then the real answer
                                # arriving ~1200 lines later) — only the LATEST messageId is the actual
                                # deliverable, so start over whenever a new one begins.
                                msg_id = m.get("messageId")
                                if msg_id != last_message_id:
                                    last_message_id = msg_id
                                    last_text = ""
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
    uploadedFileIds: list[str] = Field(default_factory=list)
    useDeepResearch: bool = False
    mode: str = "agent_creator"  # "agent_creator" (default, CONFIG/FLOW/FRAGMENT JSON modes) | "enhance" (plain-text research rewrite, no JSON)

class AgentRequest(BaseModel):
    prompt: str
    uploadedFileIds: list[str] = Field(default_factory=list)
    fragment_json: dict = Field(default_factory=dict)
    issues: list = Field(default_factory=list)
    # Node currently selected in the canvas ({path, type, config, css, init}) — lets the model
    # target the exact container the user is looking at instead of guessing from prose alone.
    selected_node: dict | None = None
    # Agent Creator's variable pool (dataMap: {dataKey: backendVar}) for the linked agent, when
    # this fragment was handed off from / is tied to an Agent Creator agent — real field names to
    # bind Init.DataSourcePath / column Input / filter Input to, instead of invented ones.
    var_pool: dict = Field(default_factory=dict)
    conversation: list[ChatMessage] = Field(default_factory=list)
    useDeepResearch: bool = False


class StackTokenRequest(BaseModel):
    stackName: str
    domain: str = "sce.manh.com"  # e.g. sce.manh.com, cp.manh.cloud, or a custom domain
    username: str
    password: str


class StackPublishRequest(BaseModel):
    stackName: str
    domain: str = "sce.manh.com"
    accessToken: str
    org: str
    facilityId: str
    businessUnit: str | None = None
    agent: dict


class StackChatAuthBase(BaseModel):
    """Shared auth fields for the Test-flow chat routes — same shape as StackPublishRequest."""
    stackName: str
    domain: str = "sce.manh.com"
    accessToken: str
    org: str
    facilityId: str
    businessUnit: str | None = None


class StackChatStartRequest(StackChatAuthBase):
    agentId: str


class StackChatSendRequest(StackChatAuthBase):
    chatbotId: str
    sessionId: str
    message: str


class StackChatEndRequest(StackChatAuthBase):
    sessionId: str


class StackChatTraceRequest(StackChatAuthBase):
    sessionId: str
    turn: str = "TURN1"


# ── Routes ────────────────────────────────────────────────────────────

def _build_chat_body(req: ChatRequest) -> dict[str, Any]:
    """Pure request-body construction for Glean /chat (Agent Creator) — no cookies, no network call.
    Shared by the server-side proxy route and the extension-relay "build" route."""
    now = _now_iso()
    messages = []
    if not req.chatId:
        system_text = ENHANCE_SYSTEM_PROMPT if req.mode == "enhance" else GLEAN_SYSTEM_PROMPT
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": "USER",
            "fragments": [{"text": system_text}],
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
    # Include the assistant's OWN prior replies (not just user turns) — a question that refers
    # back to something Glean itself said last turn (e.g. "what is operation: asIs?" after Glean
    # returned action JSON containing that field) is unanswerable if that reply was stripped from
    # the replay; the model then has nothing to anchor the question to and falls back to whatever
    # mode the static context makes likeliest (usually re-continuing the fix instead of answering).
    for msg in req.conversation:
        if msg.role == "user":
            author = "USER"
        elif msg.role in ("ai", "assistant"):
            author = "CHATBOT"
        else:
            continue
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": author,
            "fragments": [{"text": msg.text}],
            "messageType": "CONTENT",
            "ts": now,
        })

    # Attach uploaded files to the newest USER message — confirmed via real Glean HAR capture,
    # a message carries its attachments as a sibling "uploadedFileIds" list on the message object
    # itself (messages[-1]), not as a top-level request field. Without this, files upload
    # successfully and get a real fileId back, but Glean never actually sees/analyzes them.
    if req.uploadedFileIds and messages and messages[-1]["author"] == "USER":
        messages[-1]["uploadedFileIds"] = req.uploadedFileIds

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
            # "Thinking" mode toggle — matches the real glean.com UI's own deep-research flag
            # (confirmed via HAR capture: every real request carries this field, default false).
            "useDeepResearch": req.useDeepResearch,
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
        "selected_node": req.selected_node,
        "var_pool": req.var_pool,
        "tool_context": {
            "source": "Fragment UI Designer Align Fix Validate",
            "goal": "Render suggested fixes in Validate section and allow Apply Suggested Fix",
            "apply_behavior": {
                "supported_ops": ["set_props", "set_config", "set_events", "add_child", "replace_node", "delete_node", "merge_json"],
                "path_syntax": "Dot/bracket path from the Fragment root, e.g. Fragment.Slots.Default[1].Slots['Fill Rate'][0]. "
                                "Slot keys with spaces or special characters MUST use bracket-quote notation ['Slot Name'] — "
                                "never dot-then-apostrophe (Slots'Fill Rate' is invalid and will fail to apply).",
            },
            "selected_node_meaning": "selected_node (if not null) is the exact container/element the user currently "
                                      "has selected in the canvas — its 'path' is already a correct Fragment-root-relative "
                                      "path you can use directly. When the user's request doesn't name a different "
                                      "section explicitly (e.g. 'fix this', 'correct this container', 'this looks off'), "
                                      "selected_node IS the target — do not guess a different node.",
            "var_pool_meaning": "var_pool (if non-empty) is the real dataMap from this fragment's linked Agent Creator "
                                 "agent: {dataKey: backendVariablePath}. These are confirmed real field/variable names — "
                                 "prefer them over invented ones for Init.DataSourcePath, column/filter Input, and any "
                                 "other data binding. If a container's existing binding already matches a var_pool key, "
                                 "preserve it as-is unless the user explicitly asks to change that binding.",
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
    # Must include the assistant's OWN prior replies (not just user turns) — a bare confirmation
    # like "yes please" or "fix it" only means something if the model can see what it itself
    # proposed last turn (e.g. the suggestions/explanation it gave); dropping those turns made
    # every confirmation land with nothing to confirm, so the model fell back to CONVERSATION mode
    # and re-explained the same issue instead of applying the fix.
    for msg in req.conversation:
        if msg.role == "user":
            author = "USER"
        elif msg.role in ("ai", "assistant"):
            author = "CHATBOT"
        else:
            continue
        messages.append({
            "agentConfig": {"agent": "FAST"},
            "author": author,
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

    # Attach uploaded files to this final USER message — confirmed via real Glean HAR capture,
    # a message carries its attachments as a sibling "uploadedFileIds" list on the message object
    # itself, not as a top-level request field. Without this, files upload successfully and get a
    # real fileId back, but Glean never actually sees/analyzes them in the response.
    if req.uploadedFileIds:
        messages[-1]["uploadedFileIds"] = req.uploadedFileIds

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
            "useDeepResearch": req.useDeepResearch,
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


_EXTENSION_DIR = pathlib.Path(__file__).resolve().parent.parent / "chrome-extension"
# Never ship the private signing key or its derived DER — only manifest.json (which already
# embeds the public key) is needed for the extension to install with its stable id.
_EXTENSION_EXCLUDE = {"extension_key.pem", "extension_pub.der", ".gitignore"}


@app.get("/api/extension/download")
async def download_extension():
    """Zips chrome-extension/ (minus the signing key) for in-app download — lets the web app
    offer "download the Glean bridge extension" without the user needing repo/VM access."""
    if not _EXTENSION_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Extension source not found on this server")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(_EXTENSION_DIR.rglob("*")):
            if path.is_dir() or path.name in _EXTENSION_EXCLUDE:
                continue
            zf.write(path, arcname=f"mawm-glean-bridge/{path.relative_to(_EXTENSION_DIR)}")
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=mawm-glean-bridge-extension.zip"},
    )


# ── Manhattan Active stack login + publish ──────────────────────────────────
# Neither route stores the token/credentials server-side — both are stateless pass-throughs.
# The frontend keeps the access token in its own localStorage, per browser/user, same lesson
# learned from the Glean cookie-sharing issue: a shared backend must never hold one person's
# credentials on behalf of everyone hitting it.

@app.post("/api/stack/token")
async def stack_token(req: StackTokenRequest):
    """Password-grant OAuth against a Manhattan Active stack. Returns the access token only —
    never persisted here."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    auth_url = f"https://{req.stackName}-auth.{domain}/oauth/token"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                auth_url,
                headers={
                    "Authorization": MANH_OAUTH_CLIENT_BASIC,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "password", "username": req.username, "password": req.password},
                timeout=30,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach {auth_url}: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Stack login failed: {resp.text[:300]}")

    data = resp.json()
    if not data.get("access_token"):
        raise HTTPException(status_code=502, detail="Stack auth response had no access_token")
    return {"access_token": data["access_token"], "expires_in": data.get("expires_in")}


@app.post("/api/stack/publish")
async def stack_publish(req: StackPublishRequest):
    """Publishes an agent to a Manhattan Active stack via commonui-facade. Caller supplies the
    access token per-request (see /api/stack/token) — nothing is cached here."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    save_url = f"https://{req.stackName}.{domain}/commonui-facade/api/commonui-facade/chatbot/agent/save"
    headers = {
        "Authorization": f"Bearer {req.accessToken}",
        "SelectedOrganization": req.org,
        "SelectedLocation": req.facilityId,
        "Content-Type": "application/json",
    }
    if req.businessUnit:
        headers["SelectedBusinessUnit"] = req.businessUnit

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(save_url, headers=headers, json=req.agent, timeout=60)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach {save_url}: {exc}")

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:2000]}

    if not resp.is_success:
        detail = body if isinstance(body, str) else json.dumps(body)[:2000]
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return body


def _stack_headers(req: StackChatAuthBase) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {req.accessToken}",
        "SelectedOrganization": req.org,
        "SelectedLocation": req.facilityId,
        "Content-Type": "application/json",
    }
    if req.businessUnit:
        headers["SelectedBusinessUnit"] = req.businessUnit
    return headers


async def _stack_post(url: str, headers: dict, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=60)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach {url}: {exc}")
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:4000]}
    if not resp.is_success:
        detail = body if isinstance(body, str) else json.dumps(body)[:2000]
        raise HTTPException(status_code=resp.status_code, detail=detail)
    # Composer can return HTTP 200 with a business-logic failure in the body itself
    # ({"success": false, ...}) — without this check that silently looked like success here,
    # e.g. a chat/send call that never actually executed the turn, only surfacing later as a
    # confusing "trace query returned no records" instead of the real failure at the real step.
    if isinstance(body, dict) and body.get("success") is False:
        detail = json.dumps(body)[:2000]
        raise HTTPException(status_code=400, detail=detail)
    return body


@app.post("/api/stack/chat/start")
async def stack_chat_start(req: StackChatStartRequest):
    """Test-flow step 1: start a chatbot session for the just-published agent. Goes through
    /composer/api/chatbot/startChat directly (NOT the /commonui-facade/api/commonui-facade proxy
    path — that's only correct for agentTrace, confirmed by the user against a real working
    curl sequence). SessionParams.UsePublishedVersionOnly:false matters — Composer defaults this
    to true when omitted, meaning a test right after Publish would still run the PREVIOUSLY
    published version instead of what was just saved."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    url = f"https://{req.stackName}.{domain}/composer/api/chatbot/startChat"
    payload = {"ChatBotId": req.agentId, "SessionParams": {"UsePublishedVersionOnly": False}}
    return await _stack_post(url, _stack_headers(req), payload)


@app.post("/api/stack/chat/send")
async def stack_chat_send(req: StackChatSendRequest):
    """Test-flow step 2: send a message into the already-started session. Same
    /composer/api/chatbot path family as startChat (not commonui-facade) — chat/{message} is a
    distinct endpoint from startChat, ChatBotId + the real SessionId + the message duplicated
    into BOTH "Chat" and "userInput" (different layers apparently read different fields for
    this) + the same UsePublishedVersionOnly:false SessionParams as the start call."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    url = f"https://{req.stackName}.{domain}/composer/api/chatbot/chat"
    payload = {
        "ChatBotId": req.chatbotId,
        "SessionId": req.sessionId,
        "Chat": req.message,
        "userInput": req.message,
        "SessionParams": {"UsePublishedVersionOnly": False},
    }
    return await _stack_post(url, _stack_headers(req), payload)


@app.post("/api/stack/chat/end")
async def stack_chat_end(req: StackChatEndRequest):
    """Optional Test-flow cleanup: ends the test session. Same /composer/api/chatbot path family.
    Best-effort — callers should not fail the overall test run if this errors, it's just tidy-up."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    url = f"https://{req.stackName}.{domain}/composer/api/chatbot/endChat"
    payload = {"SessionId": req.sessionId}
    return await _stack_post(url, _stack_headers(req), payload)


@app.post("/api/stack/chat/trace")
async def stack_chat_trace(req: StackChatTraceRequest):
    """Test-flow step 3: query the recorded trace for a turn. Payload shape confirmed against a
    real captured request/response for this exact endpoint."""
    domain = req.domain.strip().lstrip(".") or "sce.manh.com"
    url = f"https://{req.stackName}.{domain}/commonui-facade/api/commonui-facade/chatbot/agent/agentTrace"
    payload = {"Query": f"SessionId = '{req.sessionId}' AND TurnProvoked = '{req.turn}'"}
    return await _stack_post(url, _stack_headers(req), payload)


# Serve the built frontend (npm run build → dist/) when present, so a single process can
# host both the API and the SPA in production. No-op for local dev where dist/ doesn't exist —
# `npm run dev`'s Vite dev server handles the frontend there instead.
_dist_dir = pathlib.Path(__file__).resolve().parent.parent / "dist"
if _dist_dir.is_dir():
    # index.html references hashed asset filenames (index-<hash>.js/.css) that change on every
    # build — but the plain StaticFiles(html=True) mount sends no Cache-Control at all, so a
    # browser's default heuristic caching can keep serving a stale index.html (and therefore a
    # stale JS bundle) across a normal reload even after a fresh deploy. index.html itself must
    # always be revalidated; the hashed assets underneath it are safe to cache indefinitely since
    # a content change always produces a new filename.
    @app.get("/", include_in_schema=False)
    async def _serve_index():
        return FileResponse(_dist_dir / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        candidate = _dist_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist_dir / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
