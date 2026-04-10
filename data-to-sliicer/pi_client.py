"""PI Web API client module.

Handles authentication and communication with the AVEVA PI Web API server
using NTLM auth. Credentials are passed in from the caller (loaded from
.env by main.py).
"""

import logging
import urllib3
from datetime import datetime

import requests
from requests_ntlm import HttpNtlmAuth

try:
    from dateutil.parser import isoparse as _isoparse
    def _parse_iso(ts: str) -> datetime:
        return _isoparse(ts)
except ImportError:
    def _parse_iso(ts: str) -> datetime:  # type: ignore[misc]
        return datetime.fromisoformat(ts)

logger = logging.getLogger(__name__)


def create_session(
    url: str,
    user: str,
    password: str,
    verify_tls: bool,
) -> requests.Session:
    """Create a requests Session pre-configured with NTLM authentication.

    Args:
        url: Base URL for PI Web API (e.g. https://host/piwebapi).
        user: NTLM username (DOMAIN\\user).
        password: NTLM password.
        verify_tls: Whether to verify TLS certificates.

    Returns:
        A configured ``requests.Session``.

    Raises:
        ValueError: If any required parameter is missing or empty.
    """
    required = {
        "PIWEBAPI_URL": url,
        "PIWEBAPI_USER": user,
        "PIWEBAPI_PASS": password,
    }
    missing = [name for name, value in required.items() if not value]

    # verify_tls is a bool, so check it was explicitly provided (not None)
    if verify_tls is None:
        missing.append("PIWEBAPI_VERIFY_TLS")

    if missing:
        raise ValueError(
            f"Missing required PI Web API configuration: {', '.join(missing)}"
        )

    session = requests.Session()
    session.auth = HttpNtlmAuth(user, password)
    session.verify = verify_tls

    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return session


def _raise_for_status(response: requests.Response) -> None:
    """Call raise_for_status, enriching the error with the response body."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:500]
        raise requests.HTTPError(
            f"{exc} — body: {body}",
            response=response,
        ) from exc


def find_data_server(
    session: requests.Session,
    base_url: str,
    server_name: str,
) -> str:
    """Query /dataservers, find server by name (case-insensitive), return WebId.

    Args:
        session: Authenticated requests session.
        base_url: PI Web API base URL (e.g. ``https://host/piwebapi``).
        server_name: Data server name to find (e.g. ``masterpi``).

    Returns:
        The ``WebId`` string for the matched data server.

    Raises:
        ValueError: If no server matches *server_name*.
        requests.HTTPError: On HTTP error responses.
    """
    url = f"{base_url}/dataservers"
    resp = session.get(url)
    _raise_for_status(resp)

    items = resp.json().get("Items", [])
    target = server_name.lower()
    for item in items:
        if item.get("Name", "").lower() == target:
            return item["WebId"]

    raise ValueError(f"Data server '{server_name}' not found")


def find_point_webid(
    session: requests.Session,
    base_url: str,
    server_webid: str,
    tag_name: str,
) -> str:
    """Look up a PI Point by tag name and return its WebId.

    Args:
        session: Authenticated requests session.
        base_url: PI Web API base URL.
        server_webid: WebId of the data server to search.
        tag_name: PI Point tag name (e.g. ``wwl:south:wes8617b_realtmmetflo``).

    Returns:
        The ``WebId`` string for the matched PI Point.

    Raises:
        ValueError: If no point matches *tag_name*.
        requests.HTTPError: On HTTP error responses.
    """
    url = f"{base_url}/dataservers/{server_webid}/points?namefilter={tag_name}"
    resp = session.get(url)
    _raise_for_status(resp)

    items = resp.json().get("Items", [])
    if not items:
        raise ValueError(
            f"PI Point '{tag_name}' not found on server '{server_webid}'"
        )
    return items[0]["WebId"]


def get_interpolated_data(
    session: requests.Session,
    base_url: str,
    web_id: str,
    start_time: str,
    end_time: str,
    interval: str = "1m",
) -> list[tuple[datetime, float]]:
    """Retrieve interpolated time-series data from PI Web API.

    Queries ``/streamsets/interpolated`` and returns numeric timestamp-value
    pairs.  Non-numeric values (digital states, error objects) are silently
    filtered out with a warning log.

    Args:
        session: Authenticated requests session.
        base_url: PI Web API base URL.
        web_id: WebId of the PI Point stream.
        start_time: Start time string accepted by PI Web API.
        end_time: End time string accepted by PI Web API.
        interval: Interpolation interval (default ``"1m"``).

    Returns:
        List of ``(local_datetime, value)`` tuples for numeric items.

    Raises:
        requests.HTTPError: On HTTP error responses.
    """
    url = f"{base_url}/streamsets/interpolated"
    params = {
        "webId": web_id,
        "startTime": start_time,
        "endTime": end_time,
        "interval": interval,
    }
    resp = session.get(url, params=params)
    _raise_for_status(resp)

    data = resp.json()
    results: list[tuple[datetime, float]] = []

    # Response structure: Items[0].Items[] each with Timestamp and Value
    outer_items = data.get("Items", [])
    if not outer_items:
        logger.warning("Empty response from /streamsets/interpolated")
        return results

    inner_items = outer_items[0].get("Items", [])
    for item in inner_items:
        value = item.get("Value")

        # Filter non-numeric values (dicts like {"Name": "Shutdown", "Value": 0})
        if isinstance(value, dict):
            logger.warning(
                "Skipping non-numeric value at %s: %s",
                item.get("Timestamp"),
                value,
            )
            continue
        if not isinstance(value, (int, float)):
            logger.warning(
                "Skipping non-numeric value at %s: %r",
                item.get("Timestamp"),
                value,
            )
            continue

        # Parse timestamp and convert to local timezone
        try:
            ts = _parse_iso(item["Timestamp"])
            ts_local = ts.astimezone()  # system local tz
        except (ValueError, KeyError) as exc:
            logger.warning("Skipping item with bad timestamp: %s", exc)
            continue

        results.append((ts_local, float(value)))

    return results


def get_summary_data(
    session: requests.Session,
    base_url: str,
    web_id: str,
    start_time: str,
    end_time: str,
    summary_type: str = "Average",
    summary_duration: str = "1h",
) -> list[tuple[datetime, float]]:
    """Retrieve summary (e.g. hourly average) data from PI Web API.

    Queries ``/streams/{webId}/summary`` and returns one value per summary
    period.  This lets PI compute the time-weighted average server-side
    instead of pulling 1-minute data and averaging client-side.

    Args:
        session: Authenticated requests session.
        base_url: PI Web API base URL.
        web_id: WebId of the PI Point stream.
        start_time: Start time string accepted by PI Web API.
        end_time: End time string accepted by PI Web API.
        summary_type: Summary calculation type (default ``"Average"``).
            Other options: ``"Total"``, ``"Minimum"``, ``"Maximum"``, etc.
        summary_duration: Duration of each summary period (default ``"1h"``).

    Returns:
        List of ``(local_datetime, value)`` tuples for each summary period.

    Raises:
        requests.HTTPError: On HTTP error responses.
    """
    url = f"{base_url}/streams/{web_id}/summary"
    params = {
        "startTime": start_time,
        "endTime": end_time,
        "summaryType": summary_type,
        "summaryDuration": summary_duration,
    }
    resp = session.get(url, params=params)
    _raise_for_status(resp)

    data = resp.json()
    results: list[tuple[datetime, float]] = []

    # Response structure: Items[] each with Value.Timestamp and Value.Value
    items = data.get("Items", [])
    if not items:
        logger.warning("Empty response from /streams/summary")
        return results

    for item in items:
        value_obj = item.get("Value", {})
        value = value_obj.get("Value")
        timestamp_str = value_obj.get("Timestamp")

        # Filter non-numeric values
        if isinstance(value, dict):
            logger.warning("Skipping non-numeric summary value at %s: %s", timestamp_str, value)
            continue
        if not isinstance(value, (int, float)):
            logger.warning("Skipping non-numeric summary value at %s: %r", timestamp_str, value)
            continue

        # Parse timestamp and convert to local timezone
        try:
            ts = _parse_iso(timestamp_str)
            ts_local = ts.astimezone()
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("Skipping summary item with bad timestamp: %s", exc)
            continue

        results.append((ts_local, float(value)))

    return results
