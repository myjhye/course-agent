"""
facility_agent 단위 테스트.
MCP 클라이언트는 monkeypatch로 교체해 외부 호출을 차단한다.
"""

import pytest
from importlib import import_module

from app.services.ai.agents import facility_agent


facility_agent_module = import_module("app.services.ai.agents.facility_agent")


@pytest.mark.asyncio
async def test_facility_agent_success(monkeypatch):
    """MCP가 items를 돌려주면 성공 경로."""

    async def fake_call_tool(tool_name, arguments):
        _ = (tool_name, arguments)

        class FakeResult:
            data = {
                "total_count": 1,
                "returned": 1,
                "items": [{"id": "X", "name": "테스트 수영장", "sido": "서울특별시"}],
            }

        return FakeResult()

    async def fake_extract(client, state):
        _ = (client, state)
        return {"sido": "서울특별시", "facility_type": "수영장"}

    monkeypatch.setattr(
        "app.services.ai.mcp_client.facility_mcp_client.call_tool",
        fake_call_tool,
    )
    monkeypatch.setattr(facility_agent_module, "_extract_facility_args", fake_extract)

    state = {"user_message": "서울에서 수영장 찾아줘", "agent_outputs": {}}
    result = await facility_agent(state)

    outputs = result.get("agent_outputs") or {}
    assert "facility" in outputs
    assert outputs["facility"]["success"] is True
    assert outputs["facility"]["data"]["returned"] == 1


@pytest.mark.asyncio
async def test_facility_agent_mcp_error(monkeypatch):
    """MCP 호출 예외 시 에이전트 결과는 success=False로 들어와야 함."""

    async def fake_call_tool(tool_name, arguments):
        _ = (tool_name, arguments)
        raise RuntimeError("MCP server unreachable")

    async def fake_extract(client, state):
        _ = (client, state)
        return {"sido": "서울특별시"}

    monkeypatch.setattr(
        "app.services.ai.mcp_client.facility_mcp_client.call_tool",
        fake_call_tool,
    )
    monkeypatch.setattr(facility_agent_module, "_extract_facility_args", fake_extract)

    state = {"user_message": "서울에서 수영장 찾아줘", "agent_outputs": {}}
    result = await facility_agent(state)

    outputs = result.get("agent_outputs") or {}
    assert "facility" in outputs
    assert outputs["facility"]["success"] is False
