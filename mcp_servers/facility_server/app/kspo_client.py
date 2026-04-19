"""
KSPO 전국체육시설 API 클라이언트.

공공데이터포털의 Open API를 httpx async로 호출하고 응답을 정규화한다.
폐업 시설을 필터링하고, 위경도를 float로 변환해 반환한다.

MCP 도구로의 노출은 app/tools/facility.py(Step 10)에서 처리.
"""

from typing import Any, Dict, List, Optional

import httpx

from app.cache import get_or_fetch
from app.config import settings


class KspoApiError(Exception):
    """KSPO API 호출 또는 응답 해석 실패."""


def _normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    응답의 item 1개를 정규화한다.
    - 위경도를 float로 변환 (변환 실패 시 None)
    - 우리가 쓰는 필드만 추림 (페이로드 축소, 프론트 전달 편의)
    """

    def _to_float(v: Any) -> Optional[float]:
        try:
            return float(v) if v not in (None, "", "null") else None
        except (TypeError, ValueError):
            return None

    return {
        "id": raw.get("faci_cd"),
        "name": raw.get("faci_nm"),
        "type": raw.get("ftype_nm"),  # 시설유형 ("수영장")
        "category": raw.get("fcob_nm"),  # 업종 ("수영장업")
        "sido": raw.get("addr_ctpv_nm"),
        "sigungu": raw.get("addr_cpb_nm"),
        "dong": raw.get("addr_emd_nm"),
        "address": raw.get("faci_addr"),
        "road_address": raw.get("faci_road_addr"),
        "lat": _to_float(raw.get("faci_lat")),
        "lng": _to_float(raw.get("faci_lot")),
        "status": raw.get("faci_stat_nm"),
    }


def _parse_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    API 응답 dict에서 header 결과 코드와 item 리스트를 추출한다.
    resultCode가 "00"이 아니면 KspoApiError를 올린다.
    """
    try:
        response = body["response"]
        header = response["header"]
        rbody = response["body"]
    except (KeyError, TypeError) as e:
        raise KspoApiError(f"Unexpected response shape: {e}") from e

    code = header.get("resultCode")
    if code != "00":
        msg = header.get("resultMsg", "UNKNOWN")
        raise KspoApiError(f"KSPO API returned error: {code} ({msg})")

    # items가 없거나 item이 없는 경우에도 일관되게 빈 리스트로 처리
    items = rbody.get("items") or {}
    raw_list = items.get("item") or []
    # 단건 응답 시 dict로 올 수도 있음
    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    return {
        "total_count": rbody.get("totalCount", 0),
        "page_no": rbody.get("pageNo", 1),
        "items_raw": raw_list,
    }


async def _fetch_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """실제 HTTP 호출. 캐시는 get_or_fetch에서 감싼다."""
    async with httpx.AsyncClient(timeout=settings.kspo_timeout_seconds) as client:
        url = f"{settings.kspo_base_url}/TODZ_API_SFMS_FACI"
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise KspoApiError(f"HTTP error: {e}") from e

        try:
            return resp.json()
        except ValueError as e:
            # JSON 파싱 실패 = 포털이 XML로 돌려줬거나 장애
            raise KspoApiError(f"Invalid JSON response: {e}") from e


async def search_facilities(
    sido: Optional[str] = None,
    sigungu: Optional[str] = None,
    facility_type: Optional[str] = None,  # ftype_nm
    category: Optional[str] = None,  # fcob_nm
    name: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    include_closed: bool = False,
) -> Dict[str, Any]:
    """
    조건에 맞는 체육시설을 검색한다.

    - 파라미터가 None이면 해당 필터는 생략되어 전국·전체에서 조회
    - 기본적으로 폐업 시설은 제외 (include_closed=False)
    - 위경도는 float로 변환되어 반환 (값이 없으면 None)

    Returns:
        {
            "total_count": int,   # API가 보고하는 전체 건수 (필터 전 서버측 수)
            "page_no": int,
            "returned": int,      # 이 호출에서 반환하는 건수 (폐업 제외 후)
            "items": [ {...}, ... ]
        }
    """
    params: Dict[str, Any] = {
        "serviceKey": settings.kspo_api_key,
        "pageNo": page,
        "numOfRows": page_size,
        "resultType": "json",
    }
    if sido:
        params["cp_nm"] = sido
    if sigungu:
        params["cpb_nm"] = sigungu
    if facility_type:
        params["ftype_nm"] = facility_type
    if category:
        params["fcob_nm"] = category
    if name:
        params["faci_nm"] = name

    # 캐시 키 산출에는 serviceKey를 제외한다 (키 바뀔 때 전체 캐시 무효화 방지).
    # get_or_fetch는 closure로 전달된 fetcher만 호출하므로
    # 실제 HTTP 호출에는 serviceKey가 그대로 들어간다.
    cache_params = {k: v for k, v in params.items() if k != "serviceKey"}

    async def _fetch() -> Dict[str, Any]:
        return await _fetch_page(params)

    body = await get_or_fetch(cache_params, _fetch)

    parsed = _parse_response(body)
    items: List[Dict[str, Any]] = [_normalize_item(r) for r in parsed["items_raw"]]

    if not include_closed:
        items = [it for it in items if it.get("status") == "정상운영"]

    return {
        "total_count": parsed["total_count"],
        "page_no": parsed["page_no"],
        "returned": len(items),
        "items": items,
    }
