"""Tests for the pi_client module."""

import pi_client


def test_pi_client_imports():
    """Smoke test: pi_client module loads and exposes create_session."""
    assert hasattr(pi_client, "create_session")
    assert callable(pi_client.create_session)

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import pi_client


# Feature: pi-to-sliicer-automation, Property 9: Missing Environment Variable Error
# Validates: Requirements 1.4

_STRING_VARS = ["PIWEBAPI_URL", "PIWEBAPI_USER", "PIWEBAPI_PASS"]

_VAR_TO_ARG = {
    "PIWEBAPI_URL": "url",
    "PIWEBAPI_USER": "user",
    "PIWEBAPI_PASS": "password",
}

_PLACEHOLDER = "placeholder"


@settings(max_examples=100)
@given(
    missing_vars=st.frozensets(
        st.sampled_from(_STRING_VARS),
        min_size=1,
    )
)
def test_missing_string_env_var_raises_value_error(missing_vars):
    """Property 9: For any non-empty subset of the string-based required params,
    create_session raises ValueError naming at least one missing variable."""
    kwargs = {
        "url": "" if "PIWEBAPI_URL" in missing_vars else _PLACEHOLDER,
        "user": "" if "PIWEBAPI_USER" in missing_vars else _PLACEHOLDER,
        "password": "" if "PIWEBAPI_PASS" in missing_vars else _PLACEHOLDER,
        "verify_tls": True,
    }

    with pytest.raises(ValueError) as exc_info:
        pi_client.create_session(**kwargs)

    error_message = str(exc_info.value)
    assert any(var in error_message for var in missing_vars), (
        f"Expected at least one of {missing_vars} to appear in error message, "
        f"but got: {error_message!r}"
    )


def test_verify_tls_none_raises_value_error():
    """When verify_tls is None, create_session should raise ValueError
    naming PIWEBAPI_VERIFY_TLS."""
    with pytest.raises(ValueError) as exc_info:
        pi_client.create_session(
            url=_PLACEHOLDER,
            user=_PLACEHOLDER,
            password=_PLACEHOLDER,
            verify_tls=None,
        )

    assert "PIWEBAPI_VERIFY_TLS" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 2.4 — Property 4: Non-Numeric Value Filtering
# Feature: pi-to-sliicer-automation, Property 4: Non-Numeric Value Filtering
# Validates: Requirements 3.3, 3.4
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategies for individual value types
_numeric_value = st.one_of(
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)

_digital_state = st.fixed_dictionaries({"Name": st.text(min_size=1, max_size=20), "Value": st.integers()})

_non_numeric_value = st.one_of(
    _digital_state,
    st.text(min_size=0, max_size=20),
    st.none(),
)

_timestamp = st.just("2024-06-12T00:00:00Z")


def _make_item(value):
    return {"Timestamp": "2024-06-12T00:00:00Z", "Value": value}


def _make_interpolated_response(items):
    """Build a mock /streamsets/interpolated JSON response."""
    return {"Items": [{"Name": "test_tag", "Items": items}]}


def _mock_session_for_response(payload):
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_resp.status_code = 200
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    return mock_session


@settings(max_examples=100)
@given(
    numeric_values=st.lists(_numeric_value, min_size=0, max_size=10),
    non_numeric_values=st.lists(_non_numeric_value, min_size=0, max_size=10),
)
def test_non_numeric_value_filtering(numeric_values, non_numeric_values):
    """Property 4: parsed output contains exactly the numeric items, no non-numeric items."""
    numeric_items = [_make_item(v) for v in numeric_values]
    non_numeric_items = [_make_item(v) for v in non_numeric_values]
    all_items = numeric_items + non_numeric_items

    payload = _make_interpolated_response(all_items)
    mock_session = _mock_session_for_response(payload)

    result = pi_client.get_interpolated_data(
        mock_session, "https://pi/piwebapi", "WEBID123",
        "2024-06-12T00:00:00Z", "2024-06-12T01:00:00Z",
    )

    # All returned values must be numeric (int or float, not bool)
    for _ts, val in result:
        assert isinstance(val, float), f"Expected float, got {type(val)}: {val!r}"

    # Count of returned items must equal count of numeric inputs
    assert len(result) == len(numeric_values), (
        f"Expected {len(numeric_values)} numeric results, got {len(result)}"
    )


# ---------------------------------------------------------------------------
# Task 2.5 — Property 5: Timestamp Timezone Conversion
# Feature: pi-to-sliicer-automation, Property 5: Timestamp Timezone Conversion
# Validates: Requirements 3.5
# ---------------------------------------------------------------------------

from datetime import datetime, timezone, timedelta
from hypothesis.strategies import datetimes


@settings(max_examples=100)
@given(
    dt=datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31, 23, 59, 59),
        timezones=st.just(timezone.utc),
    )
)
def test_timestamp_timezone_conversion_roundtrip(dt):
    """Property 5: converting a UTC timestamp to local and back yields the same instant."""
    # PI Web API returns second-precision timestamps; truncate microseconds
    dt = dt.replace(microsecond=0)

    # Format as ISO 8601 with Z suffix (as PI Web API returns)
    ts_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Use the module's _parse_iso function
    parsed = pi_client._parse_iso(ts_str)
    local_dt = parsed.astimezone()  # convert to system local tz

    # Convert back to UTC
    back_to_utc = local_dt.astimezone(timezone.utc)

    # Should represent the same instant (same UTC time, ignoring sub-second)
    assert back_to_utc.replace(tzinfo=None) == dt.replace(tzinfo=None), (
        f"Round-trip failed: original={dt}, local={local_dt}, back_to_utc={back_to_utc}"
    )


# ---------------------------------------------------------------------------
# Task 2.6 — Property 11: Data Server Not Found Error
# Feature: pi-to-sliicer-automation, Property 11: Data Server Not Found Error
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------

_server_name_text = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=1,
    max_size=30,
)

TARGET_SERVER = "masterpi"


@settings(max_examples=100)
@given(
    server_names=st.lists(_server_name_text, min_size=0, max_size=10)
)
def test_data_server_not_found_raises_value_error(server_names):
    """Property 11: when no server in the list matches the target, ValueError is raised."""
    # Ensure none of the generated names match the target (case-insensitive)
    filtered = [n for n in server_names if n.lower() != TARGET_SERVER.lower()]

    items = [{"Name": n, "WebId": f"WEBID_{i}"} for i, n in enumerate(filtered)]
    payload = {"Items": items}

    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_resp.status_code = 200
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with pytest.raises(ValueError, match=TARGET_SERVER):
        pi_client.find_data_server(mock_session, "https://pi/piwebapi", TARGET_SERVER)


# ---------------------------------------------------------------------------
# Task 2.7 — Property 10: HTTP Error Propagation
# Feature: pi-to-sliicer-automation, Property 10: HTTP Error Propagation
# Validates: Requirements 1.5, 8.3
# ---------------------------------------------------------------------------

import requests as _requests

_http_error_status = st.one_of(
    st.integers(min_value=400, max_value=499),
    st.integers(min_value=500, max_value=599),
)

_body_text = st.text(min_size=0, max_size=200)


@settings(max_examples=100)
@given(
    status_code=_http_error_status,
    body=_body_text,
)
def test_http_error_propagation(status_code, body):
    """Property 10: HTTP 4xx/5xx responses raise an error containing the status code and body."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = body
    mock_resp.json.return_value = {}

    # Make raise_for_status actually raise an HTTPError
    http_error = _requests.HTTPError(
        f"{status_code} Error",
        response=mock_resp,
    )
    mock_resp.raise_for_status.side_effect = http_error

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with pytest.raises(_requests.HTTPError) as exc_info:
        pi_client.find_data_server(mock_session, "https://pi/piwebapi", "masterpi")

    error_str = str(exc_info.value)
    assert str(status_code) in error_str, (
        f"Status code {status_code} not found in error: {error_str!r}"
    )
    # _raise_for_status includes body[:500] in the message
    if body:
        truncated_body = body[:500]
        assert truncated_body in error_str, (
            f"Body text not found in error: {error_str!r}"
        )


# ---------------------------------------------------------------------------
# Task 2.8 — Unit tests for PI client functions
# ---------------------------------------------------------------------------


def _make_mock_response(json_data, status_code=200):
    """Helper: create a mock response with .json(), .status_code, .raise_for_status(), .text."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.return_value = None
    mock_resp.text = str(json_data)
    return mock_resp


def _make_mock_session(response):
    mock_session = MagicMock()
    mock_session.get.return_value = response
    return mock_session


# --- find_data_server ---

def test_find_data_server_happy_path():
    """find_data_server returns the WebId when the server name matches (case-insensitive)."""
    payload = {
        "Items": [
            {"Name": "OtherServer", "WebId": "WEBID_OTHER"},
            {"Name": "MasterPI", "WebId": "WEBID_MASTER"},
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.find_data_server(mock_session, "https://pi/piwebapi", "masterpi")
    assert result == "WEBID_MASTER"


def test_find_data_server_case_insensitive():
    """find_data_server matches server name case-insensitively."""
    payload = {"Items": [{"Name": "MASTERPI", "WebId": "WEBID_UPPER"}]}
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.find_data_server(mock_session, "https://pi/piwebapi", "masterpi")
    assert result == "WEBID_UPPER"


def test_find_data_server_not_found():
    """find_data_server raises ValueError when server name is not in the list."""
    payload = {"Items": [{"Name": "otherserver", "WebId": "WEBID_OTHER"}]}
    mock_session = _make_mock_session(_make_mock_response(payload))

    with pytest.raises(ValueError, match="masterpi"):
        pi_client.find_data_server(mock_session, "https://pi/piwebapi", "masterpi")


def test_find_data_server_empty_list():
    """find_data_server raises ValueError when Items list is empty."""
    payload = {"Items": []}
    mock_session = _make_mock_session(_make_mock_response(payload))

    with pytest.raises(ValueError):
        pi_client.find_data_server(mock_session, "https://pi/piwebapi", "masterpi")


# --- find_point_webid ---

def test_find_point_webid_happy_path():
    """find_point_webid returns the WebId of the first matching point."""
    payload = {
        "Items": [
            {"Name": "wwl:south:wes8617b_realtmmetflo", "WebId": "POINT_WEBID_1"},
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.find_point_webid(
        mock_session, "https://pi/piwebapi", "SERVER_WEBID", "wwl:south:wes8617b_realtmmetflo"
    )
    assert result == "POINT_WEBID_1"


def test_find_point_webid_not_found():
    """find_point_webid raises ValueError when no points are returned."""
    payload = {"Items": []}
    mock_session = _make_mock_session(_make_mock_response(payload))

    with pytest.raises(ValueError, match="wwl:south:wes8617b_realtmmetflo"):
        pi_client.find_point_webid(
            mock_session, "https://pi/piwebapi", "SERVER_WEBID", "wwl:south:wes8617b_realtmmetflo"
        )


def test_find_point_webid_returns_first_match():
    """find_point_webid returns the first item's WebId when multiple items exist."""
    payload = {
        "Items": [
            {"Name": "tag1", "WebId": "FIRST_WEBID"},
            {"Name": "tag2", "WebId": "SECOND_WEBID"},
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.find_point_webid(
        mock_session, "https://pi/piwebapi", "SERVER_WEBID", "tag1"
    )
    assert result == "FIRST_WEBID"


# --- get_interpolated_data ---

def test_get_interpolated_data_numeric_values_returned():
    """get_interpolated_data returns (datetime, float) pairs for numeric values."""
    payload = {
        "Items": [
            {
                "Name": "test_tag",
                "Items": [
                    {"Timestamp": "2024-06-12T00:00:00Z", "Value": 2.184343173, "Good": True},
                    {"Timestamp": "2024-06-12T00:01:00Z", "Value": 1.5, "Good": True},
                ],
            }
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.get_interpolated_data(
        mock_session, "https://pi/piwebapi", "WEBID",
        "2024-06-12T00:00:00Z", "2024-06-12T01:00:00Z",
    )

    assert len(result) == 2
    for ts, val in result:
        assert isinstance(ts, datetime)
        assert isinstance(val, float)


def test_get_interpolated_data_digital_states_filtered():
    """get_interpolated_data filters out digital state dicts (non-numeric values)."""
    payload = {
        "Items": [
            {
                "Name": "test_tag",
                "Items": [
                    {"Timestamp": "2024-06-12T00:00:00Z", "Value": 2.184343173, "Good": True},
                    {"Timestamp": "2024-06-12T00:01:00Z", "Value": {"Name": "Shutdown", "Value": 0}, "Good": False},
                    {"Timestamp": "2024-06-12T00:02:00Z", "Value": 1.5, "Good": True},
                    {"Timestamp": "2024-06-12T00:03:00Z", "Value": None, "Good": False},
                    {"Timestamp": "2024-06-12T00:04:00Z", "Value": "No Data", "Good": False},
                ],
            }
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.get_interpolated_data(
        mock_session, "https://pi/piwebapi", "WEBID",
        "2024-06-12T00:00:00Z", "2024-06-12T01:00:00Z",
    )

    # Only the two numeric values should be returned
    assert len(result) == 2
    values = [val for _ts, val in result]
    assert values[0] == pytest.approx(2.184343173)
    assert values[1] == pytest.approx(1.5)


def test_get_interpolated_data_empty_response():
    """get_interpolated_data returns empty list when Items is empty."""
    payload = {"Items": []}
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.get_interpolated_data(
        mock_session, "https://pi/piwebapi", "WEBID",
        "2024-06-12T00:00:00Z", "2024-06-12T01:00:00Z",
    )
    assert result == []


def test_get_interpolated_data_integer_values_returned_as_float():
    """get_interpolated_data coerces integer values to float."""
    payload = {
        "Items": [
            {
                "Name": "test_tag",
                "Items": [
                    {"Timestamp": "2024-06-12T00:00:00Z", "Value": 42, "Good": True},
                ],
            }
        ]
    }
    mock_session = _make_mock_session(_make_mock_response(payload))

    result = pi_client.get_interpolated_data(
        mock_session, "https://pi/piwebapi", "WEBID",
        "2024-06-12T00:00:00Z", "2024-06-12T01:00:00Z",
    )

    assert len(result) == 1
    _ts, val = result[0]
    assert isinstance(val, float)
    assert val == 42.0
