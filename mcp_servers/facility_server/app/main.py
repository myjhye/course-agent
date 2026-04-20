"""
Facility MCP Server 진입점.

FastMCP로 HTTP 엔드포인트를 노출해, Course Agent(또는 Claude Desktop 등 외부 MCP 클라이언트)가
체육시설 검색 도구를 호출할 수 있게 한다.

Step 8: 헬스 체크 도구 ping만 노출. 실제 시설 검색은 Step 10에서 추가.
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from app.tools.facility import register_facility_tools
from app.tools.health import register_health_tools

load_dotenv()

# FastMCP 서버 인스턴스.
# name은 MCP 프로토콜상 서버 식별자로 쓰이며, 로그·디버그에도 표시된다.
mcp = FastMCP("facility-mcp-server")

# 도구 등록: 도구 모듈들은 mcp 인스턴스를 받아 @mcp.tool 데코레이터로 등록한다.
register_health_tools(mcp)
register_facility_tools(mcp)


if __name__ == "__main__":
    # HTTP transport: Course Agent 등 원격 MCP 클라이언트 연결용.
    # 포트는 .env의 MCP_PORT(기본 8001).
    # Docker·Railway에서는 별도 스크립트로 구동할 수도 있다 (Step 10·12).
    port = int(os.getenv("MCP_PORT", "8001"))
    host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp.run(transport="http", host=host, port=port)
