import json

import pytest

from zorobench.requester.request_statistics import RequestStatistics


@pytest.fixture()
def sample_statistics():
    return [
        RequestStatistics(e2e=1.0, ttft=0.5, itl=(0.5,), token_num=2, status_code=200),
        RequestStatistics(e2e=2.0, ttft=0.7, itl=(0.65,), token_num=3, status_code=201),
        RequestStatistics(e2e=10.0, ttft=None, itl=(), token_num=None, status_code=400),
    ]


def test_save_to_json_filters_non_successful_requests(tmp_path, sample_statistics):
    output_file = tmp_path / "stats.json"

    RequestStatistics.save_to_json(sample_statistics, str(output_file))

    data = json.loads(output_file.read_text())

    assert data["E2E"]["mean"] == pytest.approx((1.0 + 2.0) / 2)
    assert data["TTFT"]["mean"] == pytest.approx((0.5 + 0.7) / 2)
    assert data["Output tokens"]["mean"] == pytest.approx((2 + 3) / 2)
    assert data["Status codes"] == {"200": 1, "201": 1, "400": 1}


def test_itl_derived_from_successful_requests_only(tmp_path, sample_statistics):
    output_file = tmp_path / "stats.json"

    RequestStatistics.save_to_json(sample_statistics, str(output_file))

    data = json.loads(output_file.read_text())

    # ITL should be computed from the same successful requests used for E2E/TTFT statistics.
    expected_itl_mean = ((1.0 - 0.5) / (2 - 1) + (2.0 - 0.7) / (3 - 1)) / 2
    assert data["ITL"]["mean"] == pytest.approx(expected_itl_mean)
