# server/main.py
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, SecretStr

# Use your SDK internally; keep HTTP models tiny and stable
from openhands.sdk import (
    LLM,
    Agent,
    Conversation as SDKConversation,
    Message,
    TextContent,
    __version__ as sdk_version,
)
from openhands.tools import BashTool, FileEditorTool, TaskTrackerTool


security = HTTPBearer()
app = FastAPI(title="OpenHands Server for Agent SDK", version=sdk_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_auth(credentials: HTTPAuthorizationCredentials = Security(security)):
    expected = os.getenv("OPENHANDS_MASTER_KEY")
    if not expected:
        raise HTTPException(401, "OPENHANDS_MASTER_KEY not configured")
    if credentials.credentials != expected:
        raise HTTPException(401, "Invalid API key")
    return True


# -------- HTTP DTOs --------
class CreateConversationIn(BaseModel):
    id: str | None = None
    agent_preset: str | None = "default"
    persist: bool = False
    persist_dir: str | None = None


class CreateConversationOut(BaseModel):
    id: str


class MessageIn(BaseModel):
    text: str = Field(min_length=1)


class RunIn(BaseModel):
    max_iters: int | None = Field(default=None, ge=1, le=10000)  # optional step mode


class StatusOut(BaseModel):
    agent_finished: bool
    agent_paused: bool
    waiting_for_confirmation: bool
    event_count: int


class EventOut(BaseModel):
    id: str
    type: str
    content: str


# -------- In-memory registry --------
_CONVS: dict[str, SDKConversation] = {}


def _build_agent(preset: str) -> Agent:
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        raise HTTPException(500, "LITELLM_API_KEY not set")
    llm = LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )
    tools = [
        BashTool.create(working_dir=os.getcwd()),
        FileEditorTool.create(),
        TaskTrackerTool.create(save_dir=os.getcwd()),
    ]
    return Agent(llm=llm, tools=tools)


def _new_conversation(
    conv_id: str, agent: Agent, persist: bool, persist_dir: str | None
):
    if persist:
        from openhands.sdk import LocalFileStore

        fs = LocalFileStore(persist_dir or f"./.conversations/{conv_id}")
        return SDKConversation(
            agent=agent, persist_filestore=fs, conversation_id=conv_id
        )
    return SDKConversation(agent=agent, conversation_id=conv_id)


def _get_conv(cid: str) -> SDKConversation:
    conv = _CONVS.get(cid)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


# -------- Routes --------
@app.get("/alive")
def alive():
    return {"ok": True}


@app.post(
    "/conversations",
    response_model=CreateConversationOut,
    dependencies=[Depends(verify_auth)],
)
def create_conv(body: CreateConversationIn):
    conv_id = body.id or str(uuid.uuid4())
    if conv_id in _CONVS:
        raise HTTPException(409, "Conversation already exists")
    agent = _build_agent(body.agent_preset or "default")
    conv = _new_conversation(conv_id, agent, body.persist, body.persist_dir)
    _CONVS[conv_id] = conv
    return CreateConversationOut(id=conv_id)


@app.post("/conversations/{cid}/messages", dependencies=[Depends(verify_auth)])
def add_message(cid: str, body: MessageIn):
    conv = _get_conv(cid)
    conv.send_message(Message(role="user", content=[TextContent(text=body.text)]))
    return {"ok": True}


@app.post("/conversations/{cid}/run", dependencies=[Depends(verify_auth)])
def run(cid: str, body: RunIn | None = None):
    conv = _get_conv(cid)
    # You can implement step mode in the future using body.max_iters if you like
    conv.run()
    return {"ok": True}


@app.get(
    "/conversations/{cid}/events",
    response_model=list[EventOut],
    dependencies=[Depends(verify_auth)],
)
def events(cid: str, after: int | None = None):
    conv = _get_conv(cid)
    out: list[EventOut] = []
    for e in conv.get_events(after=after):
        text = getattr(e, "visualize", None)
        content = text.plain if text is not None else str(e)
        out.append(EventOut(id=e.id, type=e.__class__.__name__, content=content))
    return out


@app.get(
    "/conversations/{cid}/status",
    response_model=StatusOut,
    dependencies=[Depends(verify_auth)],
)
def status(cid: str):
    conv = _get_conv(cid)
    st = conv.get_status()
    return StatusOut(
        agent_finished=st["agent_finished"],
        agent_paused=st["agent_paused"],
        waiting_for_confirmation=st["agent_waiting_for_confirmation"],
        event_count=st["event_count"],
    )


@app.post("/conversations/{cid}/pause", dependencies=[Depends(verify_auth)])
def pause(cid: str):
    _get_conv(cid).pause()
    return {"ok": True}


@app.post("/conversations/{cid}/close", dependencies=[Depends(verify_auth)])
def close(cid: str):
    conv = _get_conv(cid)
    conv.close()
    _CONVS.pop(cid, None)
    return {"ok": True}
