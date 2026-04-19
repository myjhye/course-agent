"""
kspo_client 단위 테스트.

실제 API는 부르지 않고 monkeypatch로 응답을 주입한다.
"""

from typing import Any, Dict

import pytest

from app import cache
from app.kspo_client import (
    KspoApiError,
    _normalize_item,
    _parse_response,
    search_facilities,
)


# 샘플 응답 (실제 API와 동일 구조)
SAMPLE_RESPONSE: Dict[str, Any] = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "pageNo": 1,
            "totalCount": 2,
            "numOfRows": 2,
            "items": {
                "item": [
                    {
                        "faci_cd": "ABC123",
                        "faci_nm": "테스트 수영장",
                        "ftype_nm": "수영장",
                        "fcob_nm": "수영장업",
                        "addr_ctpv_nm": "서울특별시",
                        "addr_cpb_nm": "강남구",
                        "addr_emd_nm": "역삼동",
                        "faci_addr": "서울 강남구 역삼동 100",
                        "faci_road_addr": "서울 강남구 테헤란로 1",
                        "faci_lat": "37.5000",
                        "faci_lot": "127.0000",
                        "faci_stat_nm": "정상운영",
                    },
                    {
                        "faci_cd": "XYZ999",
                        "faci_nm": "폐업 수영장",
                        "ftype_nm": "수영장",
                        "fcob_nm": "수영장업",
                        "addr_ctpv_nm": "서울특별시",
                        "addr_cpb_nm": "강남구",
                        "addr_emd_nm": "역삼동",
                        "faci_addr": "주소",
                        "faci_road_addr": "도로명",
                        "faci_lat": "37.5",
                        "faci_lot": "127.0",
                        "faci_stat_nm": "폐업",
                    },
                ]
            },
        },
    }
}


def test_normalize_item():
    raw = SAMPLE_RESPONSE["response"]["body"]["items"]["item"][0]
    out = _normalize_item(raw)
    assert out["id"] == "ABC123"
    assert out["name"] == "테스트 수영장"
    assert out["lat"] == 37.5
    assert out["lng"] == 127.0
    assert out["status"] == "정상운영"


def test_normalize_item_bad_lat():
    raw = {"faci_cd": "X", "faci_lat": "", "faci_lot": "not-a-number"}
    out = _normalize_item(raw)
    assert out["lat"] is None
    assert out["lng"] is None


def test_parse_response_ok():
    parsed = _parse_response(SAMPLE_RESPONSE)
    assert parsed["total_count"] == 2
    assert len(parsed["items_raw"]) == 2


def test_parse_response_error_code():
    bad = {
        "response": {
            "header": {"resultCode": "30", "resultMsg": "SERVICE KEY ERROR"},
            "body": {},
        }
    }
    with pytest.raises(KspoApiError):
        _parse_response(bad)


def test_parse_response_single_item_as_dict():
    """item이 단건일 때 dict로 올 수 있음을 검증."""
    body = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "OK"},
            "body": {
                "pageNo": 1,
                "totalCount": 1,
                "items": {"item": {"faci_cd": "SOLO", "faci_stat_nm": "정상운영"}},
            },
        }
    }
    parsed = _parse_response(body)
    assert isinstance(parsed["items_raw"], list)
    assert parsed["items_raw"][0]["faci_cd"] == "SOLO"


@pytest.mark.asyncio
async def test_search_facilities_filters_closed(monkeypatch):
    """
    _fetch_page를 모킹해 SAMPLE_RESPONSE를 돌려주게 하고,
    search_facilities가 폐업을 걸러내는지 확인.
    """
    cache.clear()

    async def fake_fetch(params):
        return SAMPLE_RESPONSE

    monkeypatch.setattr("app.kspo_client._fetch_page", fake_fetch)

    result = await search_facilities(sido="서울특별시", facility_type="수영장")
    assert result["returned"] == 1  # 폐업 제외
    assert result["items"][0]["id"] == "ABC123"


@pytest.mark.asyncio
async def test_search_facilities_include_closed(monkeypatch):
    cache.clear()

    async def fake_fetch(params):
        return SAMPLE_RESPONSE

    monkeypatch.setattr("app.kspo_client._fetch_page", fake_fetch)

    result = await search_facilities(
        sido="서울특별시", facility_type="수영장", include_closed=True
    )
    assert result["returned"] == 2


@pytest.mark.asyncio
async def test_cache_hits_on_second_call(monkeypatch):
    """동일 파라미터 2회 호출 시 _fetch_page는 1회만 불려야 한다."""
    cache.clear()

    call_count = {"n": 0}

    async def fake_fetch(params):
        call_count["n"] += 1
        return SAMPLE_RESPONSE

    monkeypatch.setattr("app.kspo_client._fetch_page", fake_fetch)

    await search_facilities(sido="서울특별시", facility_type="수영장")
    await search_facilities(sido="서울특별시", facility_type="수영장")
    assert call_count["n"] == 1
