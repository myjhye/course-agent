"""
app/tools/facility.py 단위 테스트.
실제 API 호출은 monkeypatch로 _search_facilities_core를 교체해 차단한다.
"""

import pytest

from app.tools.facility import _apply_distance_sort, _haversine_km


def test_haversine_same_point():
    assert _haversine_km(37.5, 127.0, 37.5, 127.0) == pytest.approx(0.0, abs=0.01)


def test_haversine_seoul_busan_roughly_325km():
    # 서울 (37.5665, 126.9780) ↔ 부산 (35.1796, 129.0756) ≈ 325km
    dist = _haversine_km(37.5665, 126.9780, 35.1796, 129.0756)
    assert 300 < dist < 360


def test_apply_distance_sort_orders_by_distance():
    items = [
        {"name": "far", "lat": 37.60, "lng": 127.10},
        {"name": "near", "lat": 37.50, "lng": 127.00},
        {"name": "mid", "lat": 37.55, "lng": 127.05},
    ]
    sorted_items = _apply_distance_sort(items, user_lat=37.50, user_lng=127.00)
    assert [item["name"] for item in sorted_items] == ["near", "mid", "far"]
    assert sorted_items[0]["distance_km"] == 0.0


def test_apply_distance_sort_handles_none_coords():
    items = [
        {"name": "nocoord", "lat": None, "lng": None},
        {"name": "near", "lat": 37.50, "lng": 127.00},
    ]
    sorted_items = _apply_distance_sort(items, user_lat=37.50, user_lng=127.00)
    assert sorted_items[0]["name"] == "near"
    assert sorted_items[1]["name"] == "nocoord"
    assert sorted_items[1]["distance_km"] is None
