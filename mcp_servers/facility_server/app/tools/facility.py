"""
체육시설 검색 MCP 도구.

Step 9의 kspo_client.search_facilities를 FastMCP @mcp.tool로 래핑한다.
좌표 (lat, lng)가 주어지면 거리순 정렬을 적용한다.
"""

import math
from typing import Any, Dict, List, Optional

from app.kspo_client import search_facilities as _search_facilities_core


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이 거리(km). 소수점 고려 없이 대략적 구면 근사."""
    r_earth_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a_val = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c_val = 2 * math.atan2(math.sqrt(a_val), math.sqrt(1 - a_val))
    return r_earth_km * c_val


def _apply_distance_sort(
    items: List[Dict[str, Any]],
    user_lat: float,
    user_lng: float,
) -> List[Dict[str, Any]]:
    """
    각 시설에 distance_km 필드를 추가하고 거리순 정렬한다.
    좌표 없는 시설은 distance_km=None으로, 리스트 뒤쪽에 배치.
    """
    enriched: List[Dict[str, Any]] = []
    for item in items:
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is None or lng is None:
            enriched.append({**item, "distance_km": None})
        else:
            distance = _haversine_km(user_lat, user_lng, lat, lng)
            enriched.append({**item, "distance_km": round(distance, 2)})

    enriched.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return enriched


def register_facility_tools(mcp) -> None:
    """FastMCP 인스턴스에 체육시설 검색 도구를 등록한다."""

    @mcp.tool
    async def search_facilities(
        sido: Optional[str] = None,
        sigungu: Optional[str] = None,
        facility_type: Optional[str] = None,
        category: Optional[str] = None,
        name: Optional[str] = None,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        page: int = 1,
        page_size: int = 30,
    ) -> Dict[str, Any]:
        """
        공공 체육시설을 검색한다. 좌표가 주어지면 거리순으로 정렬한다.

        Args:
            sido: 시도명 (예: "서울특별시", "경기도").
            sigungu: 시군구명 (예: "강남구", "고양시 덕양구").
            facility_type: 시설유형 (예: "수영장", "체력단련장").
            category: 업종 (예: "수영장업").
            name: 시설명 부분 매칭.
            user_lat, user_lng: 사용자 위치. 둘 다 주어지면 거리순 정렬.
            page: 페이지 번호 (기본 1).
            page_size: 페이지 크기 (기본 30, 최대 권장 100).
        """
        result = await _search_facilities_core(
            sido=sido,
            sigungu=sigungu,
            facility_type=facility_type,
            category=category,
            name=name,
            page=page,
            page_size=page_size,
        )

        items = result["items"]
        if user_lat is not None and user_lng is not None:
            items = _apply_distance_sort(items, user_lat, user_lng)

        return {
            "total_count": result["total_count"],
            "returned": len(items),
            "items": items,
        }
