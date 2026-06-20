"""
Google Calendar MCP Server 진입점.
FastMCP로 구글 캘린더 연동 API 도구를 노출합니다.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import settings

load_dotenv()

mcp = FastMCP("google-calendar-mcp-server")


def get_calendar_service():
    """Google Calendar v3 API 서비스 인스턴스를 빌드합니다."""
    if not settings.google_service_account_info:
        raise ValueError("환경 변수 GOOGLE_SERVICE_ACCOUNT_INFO가 비어 있습니다.")
        
    try:
        info = json.loads(settings.google_service_account_info)
    except Exception as e:
        raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_INFO JSON 파싱 실패: {str(e)}")

    credentials = Credentials.from_service_account_info(
        info,
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    return build('calendar', 'v3', credentials=credentials)


@mcp.tool()
async def ping() -> str:
    """헬스 체크용 도구입니다. 'pong'을 반환합니다."""
    return "pong"


@mcp.tool()
async def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = ""
) -> str:
    """구글 캘린더에 새로운 일정(예: 스포츠 강습 일정)을 생성합니다.

    Args:
        summary: 일정 제목 (예: '수영 강습 수강')
        start_time: 일정 시작 시간 (ISO 8601 형식, 예: '2026-05-15T10:00:00+09:00')
        end_time: 일정 종료 시간 (ISO 8601 형식, 예: '2026-05-15T11:00:00+09:00')
        description: 일정 상세 설명 (선택 사항)
    """
    service = get_calendar_service()
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Seoul',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Seoul',
        },
    }
    created_event = service.events().insert(
        calendarId=settings.google_calendar_id,
        body=event
    ).execute()
    return (
        f"일정이 성공적으로 생성되었습니다.\n"
        f"제목: {summary}\n"
        f"시간: {start_time} ~ {end_time}\n"
        f"ID: {created_event.get('id')}\n"
        f"링크: {created_event.get('htmlLink')}"
    )


@mcp.tool()
async def list_calendar_events(
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10
) -> str:
    """구글 캘린더의 일정 목록을 조회하여 반환합니다.

    Args:
        time_min: 조회 시작 범위 (ISO 8601 형식, 예: '2026-05-15T00:00:00+09:00')
        time_max: 조회 종료 범위 (ISO 8601 형식, 예: '2026-05-15T23:59:59+09:00')
        max_results: 최대 결과 개수 (기본 10)
    """
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId=settings.google_calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    if not events:
        return "해당 조회 기간 내 등록된 구글 캘린더 일정이 없습니다."

    result_lines = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event.get('summary', '제목 없음')
        result_lines.append(f"- {summary} ({start} ~ {end}) [ID: {event.get('id')}]")
        
    return "\n".join(result_lines)


if __name__ == "__main__":
    # MCP HTTP transport 구동
    port = int(os.getenv("MCP_PORT", "8002"))
    host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp.run(transport="http", host=host, port=port)
