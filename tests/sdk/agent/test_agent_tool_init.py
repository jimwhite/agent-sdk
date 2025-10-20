from collections.abc import Sequence
from unittest.mock import patch

from openhands.sdk import LLM, Conversation
from openhands.sdk.agent import Agent
from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool import ToolDefinition
from openhands.sdk.tool.registry import register_tool
from openhands.sdk.tool.spec import Tool
from openhands.sdk.tool.tool import Action, Observation, ToolExecutor


class _Action(Action):
    text: str


class _Obs(Observation):
    out: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        return [TextContent(text=self.out)]


class _Exec(ToolExecutor[_Action, _Obs]):
    def __call__(self, action: _Action) -> _Obs:
        return _Obs(out=action.text.upper())


def _make_tool(conv_state=None, **kwargs) -> Sequence[ToolDefinition]:
    return [
        ToolDefinition(
            name="upper",
            description="Uppercase",
            action_type=_Action,
            observation_type=_Obs,
            executor=_Exec(),
        )
    ]


def test_agent_initializes_tools_from_toolspec_locally(monkeypatch):
    # Register a simple local tool via registry
    register_tool("upper", _make_tool)

    llm = LLM(model="test-model", usage_id="test-llm")
    agent = Agent(llm=llm, tools=[Tool(name="upper")])

    # Build a conversation; this should call agent._initialize() internally
    Conversation(agent=agent, visualize=False)

    # Access the agent's runtime tools via a small shim
    # (We don't rely on private internals; we verify init_state produced a system prompt
    # with tools included by checking that agent.step can access tools without error.)
    with patch.object(Agent, "step", wraps=agent.step):
        runtime_tools = agent.tools_map
        assert "upper" in runtime_tools
        assert "finish" in runtime_tools
        assert "think" in runtime_tools
