import pytest
from pydantic import BaseModel, Field

from openhands.sdk.tool import Observation, ToolDefinition, ToolExecutor
from openhands.sdk.tool.schema import Action


class A(Action):
    y: int = Field(description="y")


class Obs(Observation):
    value: int

    @property
    def to_llm_content(self):  # type: ignore[override]
        from openhands.sdk.llm import TextContent

        return [TextContent(text=str(self.value))]


def test_tool_call_with_observation_none_result_shapes():
    # When observation_type is None, results are wrapped/coerced to Observation
    # 1) dict -> Observation
    class E1(ToolExecutor[A, dict[str, int]]):
        def __call__(self, action: A) -> dict[str, int]:
            return {"foo": 1}

    t = ToolDefinition(
        name="t",
        description="d",
        action_type=A,
        observation_type=None,
        executor=E1(),
    )
    obs = t(A(y=1))
    assert isinstance(obs, Observation)

    # 2) BaseModel -> Observation via model_dump
    class M(BaseModel):
        foo: int

    class E2(ToolExecutor[A, BaseModel]):
        def __call__(self, action: A) -> BaseModel:
            return M(foo=2)

    t2 = ToolDefinition(
        name="t2",
        description="d",
        action_type=A,
        observation_type=None,
        executor=E2(),
    )
    obs2 = t2(A(y=2))
    assert isinstance(obs2, Observation)

    # 3) invalid type -> raises TypeError
    class E3(ToolExecutor[A, list[int]]):
        def __call__(self, action: A) -> list[int]:
            return [1, 2, 3]

    t3 = ToolDefinition(
        name="t3",
        description="d",
        action_type=A,
        observation_type=None,
        executor=E3(),
    )
    with pytest.raises(TypeError, match="Output must be dict or BaseModel"):
        t3(A(y=3))
