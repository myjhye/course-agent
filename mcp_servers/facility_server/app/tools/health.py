"""
헬스 체크 도구.

Step 8의 목적: FastMCP 스켈레톤이 제대로 동작하는지 외부에서 확인 가능하게 하는 최소 도구.
실제 체육시설 검색 도구(search_facilities, find_nearby_facilities)는 Step 10에서 추가.
"""

from typing import Dict


def register_health_tools(mcp) -> None:
    """FastMCP 인스턴스에 헬스 체크 도구를 등록한다."""

    @mcp.tool
    def ping() -> Dict[str, str]:
        """
        Facility MCP Server가 살아있는지 확인한다.

        Returns:
            서버 상태와 이름을 담은 dict.
        """
        return {
            "status": "ok",
            "server": "facility-mcp-server",
            "version": "0.1.0",
        }
