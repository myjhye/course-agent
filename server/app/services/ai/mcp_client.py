"""
Facility MCP Server HTTP 클라이언트.

fastmcp.Client를 감싼 얇은 래퍼. 요청 단위로 Client를 열고 닫는다.

설계:
- URL 미설정 시 예외를 발생시켜 facility_agent가 표준 실패 경로를 타게 한다
- 타임아웃/예외는 호출자(facility_agent)에게 전파한다
- 응답 언팩은 facility_agent에서 처리한다 (도메인 로직 분리)
"""

from typing import Any, Dict, Optional

from fastmcp import Client

from app.config import settings


class FacilityMcpClient:
    """facility MCP 서버 호출 전용 클라이언트."""

    def __init__(self, url: Optional[str] = None, timeout: Optional[float] = None):
        self.url = url or settings.facility_mcp_url
        self.timeout = timeout or settings.facility_mcp_timeout_seconds

    def is_configured(self) -> bool:
        """URL이 설정됐는지 확인. False면 호출 시도하지 말 것."""
        return bool(self.url)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        facility MCP 서버의 tool을 호출한다.
        예외(연결 실패, 타임아웃, MCP 에러)는 호출자에게 그대로 전파한다.
        """
        if not self.is_configured():
            raise RuntimeError("FACILITY_MCP_URL is not configured")

        async with Client(self.url, timeout=self.timeout) as client:
            return await client.call_tool(tool_name, arguments)


class CalendarMcpClient:
    """calendar MCP 서버 호출 전용 클라이언트."""

    def __init__(self, url: Optional[str] = None, timeout: Optional[float] = None):
        self.url = url or settings.calendar_mcp_url
        self.timeout = timeout or settings.calendar_mcp_timeout_seconds

    def is_configured(self) -> bool:
        """URL이 설정됐는지 확인. False면 호출 시도하지 말 것."""
        return bool(self.url)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        calendar MCP 서버의 tool을 호출한다.
        """
        if not self.is_configured():
            raise RuntimeError("CALENDAR_MCP_URL is not configured")

        async with Client(self.url, timeout=self.timeout) as client:
            return await client.call_tool(tool_name, arguments)


facility_mcp_client = FacilityMcpClient()
calendar_mcp_client = CalendarMcpClient()

