"""
외부 MCP 서버(체육시설 검색, 구글 캘린더)의 원격 도구(Tool)를 비동기로 호출하는 클라이언트 모듈.
- 도구를 호출할 때마다 연결을 새로 열고, 작업이 끝나면 자동으로 닫히도록 설계되어 있다.
"""

from typing import Any, Dict, Optional

from fastmcp import Client

from app.config import settings


class FacilityMcpClient:
    """공공 체육시설(Facility) 검색 MCP 서버 호출용 클라이언트."""

    def __init__(self, url: Optional[str] = None, timeout: Optional[float] = None):
        self.url = url or settings.facility_mcp_url
        self.timeout = timeout or settings.facility_mcp_timeout_seconds

    def is_configured(self) -> bool:
        """클라이언트 접속 엔드포인트 URL이 설정되어 있는지 확인한다."""
        return bool(self.url)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        체육시설 검색 MCP 서버에 기동된 원격 도구(Tool)를 직접 실행하고 결과를 반환한다.
        - 예외(네트워크 타임아웃, 연동 서버 실패 등)는 안전한 폴백(Relaxation) 유도를 위해 호출자에게 그대로 전파한다.
        """
        if not self.is_configured():
            raise RuntimeError("FACILITY_MCP_URL is not configured")

        async with Client(self.url, timeout=self.timeout) as client:
            return await client.call_tool(tool_name, arguments)


class CalendarMcpClient:
    """구글 캘린더(Calendar) 일정 연동 MCP 서버 호출용 클라이언트."""

    def __init__(self, url: Optional[str] = None, timeout: Optional[float] = None):
        self.url = url or settings.calendar_mcp_url
        self.timeout = timeout or settings.calendar_mcp_timeout_seconds

    def is_configured(self) -> bool:
        """클라이언트 접속 엔드포인트 URL이 설정되어 있는지 확인한다."""
        return bool(self.url)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        구글 캘린더 연동 MCP 서버에 기동된 원격 도구(Tool)를 직접 실행하고 결과를 반환한다.
        - 예외(구글 인증 에러, 네트워크 타임아웃 등)는 호출 에이전트 계층에게 직접 전파한다.
        """
        if not self.is_configured():
            raise RuntimeError("CALENDAR_MCP_URL is not configured")

        async with Client(self.url, timeout=self.timeout) as client:
            return await client.call_tool(tool_name, arguments)


# 전역에서 재사용할 싱글톤 게이트웨이 인스턴스 정의
facility_mcp_client = FacilityMcpClient()
calendar_mcp_client = CalendarMcpClient()


