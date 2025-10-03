import json
import statistics

import pytest

from zorobench.requester.request_statistics import RequestStatistics


@pytest.fixture()
def sample_statistics():
    return [
        RequestStatistics(e2e=1.0, ttft=0.4, itl=(0.3,), token_num=3, status_code=200),
        RequestStatistics(e2e=1.2, ttft=0.42, itl=(0.26,), token_num=4, status_code=200),
        RequestStatistics(e2e=1.4, ttft=0.44, itl=(0.24,), token_num=5, status_code=200),
        RequestStatistics(e2e=1.6, ttft=0.46, itl=(0.228,), token_num=1, status_code=201),
        RequestStatistics(e2e=1.8, ttft=0.48, itl=(0.22,), token_num=1, status_code=201),
        RequestStatistics(e2e=2.0, ttft=0.5, itl=(0.2142857143,), token_num=8, status_code=201),
        RequestStatistics(e2e=2.2, ttft=0.52, itl=(0.21,), token_num=9, status_code=202),
        RequestStatistics(e2e=2.4, ttft=0.54, itl=(0.2066666667,), token_num=10, status_code=202),
        RequestStatistics(e2e=2.6, ttft=0.56, itl=(0.204,), token_num=11, status_code=204),
        RequestStatistics(e2e=2.8, ttft=0.58, itl=(0.2018181818,), token_num=12, status_code=204),
        RequestStatistics(e2e=15.0, ttft=None, itl=(), token_num=None, status_code=400),
        RequestStatistics(e2e=30.0, ttft=None, itl=(), token_num=None, status_code=429),
        RequestStatistics(e2e=45.0, ttft=None, itl=(), token_num=None, status_code=500),
    ]


def test_save_to_json_filters_non_successful_requests(tmp_path, sample_statistics):
    output_file = tmp_path / "stats.json"

    RequestStatistics.save_to_json(sample_statistics, str(output_file))

    data = json.loads(output_file.read_text())

    successful = [
        s
        for s in sample_statistics
        if s.status_code is not None and 200 <= s.status_code < 300
    ]

    e2e_values = [s.e2e for s in successful]
    ttft_values = [s.ttft for s in successful if s.ttft is not None]
    token_values = [s.token_num for s in successful if s.token_num is not None]

    expected_e2e_mean = statistics.mean(e2e_values)
    expected_e2e_p50 = statistics.median(e2e_values)

    expected_ttft_mean = statistics.mean(ttft_values)
    expected_ttft_p50 = statistics.median(ttft_values)

    expected_tokens_mean = statistics.mean(token_values)
    expected_tokens_p50 = statistics.median(token_values)

    assert data["E2E"]["mean"] == pytest.approx(expected_e2e_mean)
    assert data["E2E"]["p50"] == pytest.approx(expected_e2e_p50)

    assert data["TTFT"]["mean"] == pytest.approx(expected_ttft_mean)
    assert data["TTFT"]["p50"] == pytest.approx(expected_ttft_p50)

    assert data["Output tokens"]["mean"] == pytest.approx(expected_tokens_mean)
    assert data["Output tokens"]["p50"] == pytest.approx(expected_tokens_p50)

    assert data["Status codes"] == {
        "200": 3,
        "201": 3,
        "202": 2,
        "204": 2,
        "400": 1,
        "429": 1,
        "500": 1,
    }


def test_itl_derived_from_successful_requests_only(tmp_path, sample_statistics):
    output_file = tmp_path / "stats.json"

    RequestStatistics.save_to_json(sample_statistics, str(output_file))

    data = json.loads(output_file.read_text())

    successful = [
        s
        for s in sample_statistics
        if s.status_code is not None and 200 <= s.status_code < 300
    ]

    itl_values = []
    for s in successful:
        if s.ttft is None or s.token_num is None or s.token_num <= 1:
            continue
        itl_values.append((s.e2e - s.ttft) / (s.token_num - 1))

    expected_itl_mean = statistics.mean(itl_values)
    expected_itl_p50 = statistics.median(itl_values)

    assert data["ITL"]["mean"] == pytest.approx(expected_itl_mean)
    assert data["ITL"]["p50"] == pytest.approx(expected_itl_p50)
