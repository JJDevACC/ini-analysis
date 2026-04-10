#!/usr/bin/env python3
"""
Generate an ADS PRISM import CSV from a PI AF Attribute via PI Web API.

CSV format:
<LOCATION>,Average=None,QualityFlag=FALSE,QualityValue=FALSE
DateTime,MP1\\QFINAL,MP1\\QCONTINUITY,MP1\\QUANTITY
MM/dd/yyyy h:mm:ss tt,MGD,MGD,MGD
MM/DD/YYYY hh:mm:ss AM/PM,<same>,<same>,<same>

Supports:
- .env for URL + credentials (python-dotenv)
- interpolated hourly values (server-side)
- hourly Average values:
    a) server-side summaries if PI Web API exposes Links["Summaries"]
    b) fallback to client-side time-weighted hourly average if summaries endpoint is not available
- automatic use of PI Web API Links (most compatible)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

try:
    import urllib3
except Exception:  # pragma: no cover
    urllib3 = None


# PRISM constants (raw strings avoid escape warnings)
PRISM_META_COLS = ["Average=None", "QualityFlag=FALSE", "QualityValue=FALSE"]
PRISM_MP_COLS = [r"MP1\QFINAL", r"MP1\QCONTINUITY", r"MP1\QUANTITY"]
PRISM_DATETIME_FORMAT_ROW = "MM/dd/yyyy h:mm:ss tt"


def fmt_prism_timestamp(dt: datetime) -> str:
    # Required by PRISM: MM/DD/YYYY hh:mm:ss AM/PM
    # We output in local time representation of the datetime object provided.
    return dt.strftime("%m/%d/%Y %I:%M:%S %p")


def parse_piwebapi_timestamp(ts: str) -> datetime:
    """
    PI Web API timestamps: '2024-06-12T01:00:00Z' or with offsets.
    """
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def convert_flow(value: float, input_unit: str, output_unit: str) -> float:
    iu = input_unit.strip().lower()
    ou = output_unit.strip().lower()

    if iu == ou:
        return value

    # gpm -> MGD
    if iu in ("gpm", "gal/min", "gallon/min", "gallons/min") and ou == "mgd":
        return value * 0.00144

    # MGD -> gpm
    if iu == "mgd" and ou in ("gpm", "gal/min", "gallon/min", "gallons/min"):
        return value / 0.00144

    raise ValueError(f"Unsupported unit conversion: {input_unit} -> {output_unit}")


def truthy_env(s: Optional[str]) -> Optional[bool]:
    if s is None:
        return None
    v = s.strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return None


def extract_numeric(val_raw: Any) -> Optional[float]:
    if val_raw is None or isinstance(val_raw, (dict, list)):
        return None
    try:
        return float(val_raw)
    except Exception:
        return None


@dataclass
class AttributeRef:
    webid: str
    links: Dict[str, str]


@dataclass
class PIWebAPIClient:
    base_url: str  # e.g. https://host/piwebapi
    username: Optional[str] = None
    password: Optional[str] = None
    verify_tls: bool = True
    ca_bundle: Optional[str] = None
    timeout_sec: int = 60

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.session = requests.Session()

        self.session.verify = self.ca_bundle if self.ca_bundle else self.verify_tls
        self.session.headers.update({"Accept": "application/json"})

        if self.username:
            self.session.auth = (self.username, self.password or "")

        # If we are intentionally skipping TLS verification, suppress the noisy warnings.
        if self.session.verify is False and urllib3 is not None:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def get_json(self, path_or_url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        r = self.session.get(self._url(path_or_url), params=params, timeout=self.timeout_sec)
        r.raise_for_status()
        return r.json()

    def get_items(self, path_or_url: str, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        data = self.get_json(path_or_url, params=params)
        return data.get("Items", []) if isinstance(data, dict) else []

    def get_attribute_by_path(self, af_attribute_path: str) -> AttributeRef:
        data = self.get_json("/attributes", params={"path": af_attribute_path})
        webid = data.get("WebId")
        links = data.get("Links") or {}
        if not webid:
            raise RuntimeError(f"Could not resolve WebId for attribute path: {af_attribute_path}")
        if not isinstance(links, dict):
            links = {}
        # Normalize keys for easier lookup (case-insensitive)
        norm_links = {str(k).lower(): str(v) for k, v in links.items()}
        return AttributeRef(webid=str(webid), links=norm_links)

    # -----------------------
    # Server-side fetches via links (most compatible)
    # -----------------------

    def fetch_interpolated_via_links(
        self,
        attr: AttributeRef,
        start: str,
        end: str,
        interval: str,
    ) -> List[Dict[str, Any]]:
        link = attr.links.get("interpolated")
        if link:
            return self.get_items(link, params={"startTime": start, "endTime": end, "interval": interval})

        # fallback guess if link missing
        try:
            return self.get_items(f"/streams/{attr.webid}/interpolated", params={"startTime": start, "endTime": end, "interval": interval})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return self.get_items(f"/streamsets/{attr.webid}/interpolated", params={"startTime": start, "endTime": end, "interval": interval})
            raise

    def fetch_summaries_via_links(
        self,
        attr: AttributeRef,
        start: str,
        end: str,
        summary_duration: str,
        summary_type: str,
        calculation_basis: str,
        time_type: str,
    ) -> List[Dict[str, Any]]:
        link = attr.links.get("summaries")
        if link:
            return self.get_items(
                link,
                params={
                    "startTime": start,
                    "endTime": end,
                    "summaryDuration": summary_duration,
                    "summaryType": summary_type,
                    "calculationBasis": calculation_basis,
                    "timeType": time_type,
                },
            )

        # fallback guess if link missing
        params = {
            "startTime": start,
            "endTime": end,
            "summaryDuration": summary_duration,
            "summaryType": summary_type,
            "calculationBasis": calculation_basis,
            "timeType": time_type,
        }
        try:
            return self.get_items(f"/streams/{attr.webid}/summaries", params=params)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return self.get_items(f"/streamsets/{attr.webid}/summaries", params=params)
            raise


def write_prism_csv(
    out_csv_path: str,
    station_id: str,
    unit_label: str,
    timestamps_and_values: List[Tuple[datetime, float]],
) -> None:
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow([station_id] + PRISM_META_COLS)
        w.writerow(["DateTime"] + PRISM_MP_COLS)
        w.writerow([PRISM_DATETIME_FORMAT_ROW] + [unit_label] * len(PRISM_MP_COLS))

        for dt_obj, val in timestamps_and_values:
            ts = fmt_prism_timestamp(dt_obj)
            val_str = f"{val:.9f}".rstrip("0").rstrip(".")
            w.writerow([ts, val_str, val_str, val_str])


def parse_interval_summaries_to_rows(
    intervals: List[Dict[str, Any]],
    timestamp_mode: str,  # "start" or "end"
) -> List[Tuple[datetime, float]]:
    """
    Typical /summaries interval shape:
      Items: [
        { StartTime, EndTime, Items: [ {Type:"Average", Value: ...}, ... ] },
        ...
      ]
    """
    rows: List[Tuple[datetime, float]] = []
    for interval in intervals:
        start_ts = interval.get("StartTime")
        end_ts = interval.get("EndTime")
        summary_items = interval.get("Items") or []

        picked = None
        if isinstance(summary_items, list):
            for s in summary_items:
                if isinstance(s, dict) and (s.get("Type") == "Average" or str(s.get("Type")).lower() == "average"):
                    picked = s
                    break
            if picked is None and summary_items and isinstance(summary_items[0], dict):
                picked = summary_items[0]

        avg_val = extract_numeric(picked.get("Value") if isinstance(picked, dict) else None)
        if avg_val is None:
            continue

        if timestamp_mode == "end" and end_ts:
            dt_obj = parse_piwebapi_timestamp(end_ts)
        elif start_ts:
            dt_obj = parse_piwebapi_timestamp(start_ts)
        else:
            continue

        rows.append((dt_obj, avg_val))
    return rows


def hourly_boundaries_utc(start_dt: datetime, end_dt: datetime) -> List[datetime]:
    """
    Returns a list of hour boundary datetimes [startHour, startHour+1h, ..., endHour]
    in UTC.
    """
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    # floor to hour
    start_floor = start_dt.replace(minute=0, second=0, microsecond=0)
    end_floor = end_dt.replace(minute=0, second=0, microsecond=0)

    # include end boundary
    boundaries = []
    cur = start_floor
    while cur <= end_floor:
        boundaries.append(cur)
        cur = cur + timedelta(hours=1)
    return boundaries


def client_side_time_weighted_hourly_average(
    samples: List[Tuple[datetime, float]],
    start_dt: datetime,
    end_dt: datetime,
) -> List[Tuple[datetime, float]]:
    """
    Compute time-weighted hourly averages from a stepwise-hold series.

    We assume the value holds until the next sample timestamp.
    This approximates PI time-weighted average fairly well if samples are frequent enough
    (or if you feed interpolated samples at fine resolution).

    Returns list of (hour_start_dt, avg_value) for each full hour interval in range.
    """
    if not samples:
        return []

    # Ensure sorted
    samples = sorted(samples, key=lambda x: x[0])

    # Clip range
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    # Hour boundaries
    bounds = hourly_boundaries_utc(start_dt, end_dt)
    if len(bounds) < 2:
        return []

    # Helper: get value at time t (stepwise hold from last sample <= t)
    idx = 0
    current_val = samples[0][1]
    for i, (t, v) in enumerate(samples):
        if t <= bounds[0]:
            current_val = v
            idx = i
        else:
            break

    out: List[Tuple[datetime, float]] = []

    # Iterate each hour interval [b0,b1)
    for h0, h1 in zip(bounds[:-1], bounds[1:]):
        # accumulate area
        area = 0.0
        t_cursor = h0

        # advance idx to first sample after h0
        while idx < len(samples) and samples[idx][0] < h0:
            current_val = samples[idx][1]
            idx += 1

        # process samples within the hour
        j = idx
        while j < len(samples) and samples[j][0] < h1:
            t_next = samples[j][0]
            if t_next > t_cursor:
                area += current_val * (t_next - t_cursor).total_seconds()
                t_cursor = t_next
            current_val = samples[j][1]
            j += 1

        # finish to h1
        if t_cursor < h1:
            area += current_val * (h1 - t_cursor).total_seconds()

        duration = (h1 - h0).total_seconds()
        if duration > 0:
            out.append((h0, area / duration))

        # move idx
        idx = j

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ADS PRISM flow CSV from PI AF Attribute via PI Web API.")
    ap.add_argument("--env-file", default=None, help="Optional path to .env file (default: .env in cwd)")

    ap.add_argument("--piwebapi", required=False, help="PI Web API base URL, e.g. https://host/piwebapi")
    ap.add_argument("--username", default=None, help="PI Web API username (Basic auth)")
    ap.add_argument("--password", default=None, help="PI Web API password (Basic auth)")

    ap.add_argument("--af-attribute-path", required=True,
                    help=r"AF attribute path, e.g. \\AFSERVER\AFDB\ELEMENT\Sub\|Attribute")
    ap.add_argument("--station-id", required=True, help="Location name in Cell A1 (e.g., WES8617B)")
    ap.add_argument("--start", required=True, help="Start time (PI Web API), e.g. 2024-06-12T00:00:00Z")
    ap.add_argument("--end", required=True, help="End time (PI Web API), e.g. 2024-09-10T00:00:00Z")

    ap.add_argument("--method", choices=["interpolated", "average"], default="interpolated",
                    help="interpolated (server) or average (hourly Average)")
    ap.add_argument("--interval", default="1h", help="For interpolated: interval (default: 1h)")

    ap.add_argument("--avg-basis", choices=["TimeWeighted", "EventWeighted"], default="TimeWeighted",
                    help="For average: calculationBasis (default: TimeWeighted)")
    ap.add_argument("--avg-time-type", default="Auto", help="For average: timeType (default: Auto)")
    ap.add_argument("--avg-timestamp", choices=["start", "end"], default="start",
                    help="For average: stamp hour rows at interval start or end")
    ap.add_argument("--avg-fallback-resolution", default="5m",
                    help="If server summaries are unavailable, compute hourly averages client-side by "
                         "pulling interpolated samples at this resolution (default: 5m).")

    ap.add_argument("--input-unit", default="gpm", help="Input unit (default: gpm)")
    ap.add_argument("--output-unit", default="MGD", help="Output unit label (default: MGD)")
    ap.add_argument("--out", required=True, help="Output CSV path")

    ap.add_argument("--no-verify-tls", action="store_true", help="Disable TLS certificate verification")
    ap.add_argument("--ca-bundle", default=None, help="Path to CA bundle PEM file to trust")

    args = ap.parse_args()

    # Load env
    load_dotenv(dotenv_path=args.env_file) if args.env_file else load_dotenv()

    piwebapi = args.piwebapi or os.getenv("PIWEBAPI_URL")
    username = args.username or os.getenv("PIWEBAPI_USER")
    password = args.password or os.getenv("PIWEBAPI_PASS")

    verify_tls = not args.no_verify_tls
    env_verify = truthy_env(os.getenv("PIWEBAPI_VERIFY_TLS"))
    if env_verify is not None and not args.no_verify_tls and not args.ca_bundle:
        verify_tls = env_verify

    ca_bundle = args.ca_bundle or os.getenv("PIWEBAPI_CA_BUNDLE")

    if not piwebapi:
        raise RuntimeError("Missing PI Web API URL. Provide --piwebapi or set PIWEBAPI_URL in .env.")
    if not username or not password:
        raise RuntimeError("Missing credentials. Provide --username/--password or set PIWEBAPI_USER/PIWEBAPI_PASS in .env.")

    client = PIWebAPIClient(
        base_url=piwebapi,
        username=username,
        password=password,
        verify_tls=verify_tls,
        ca_bundle=ca_bundle,
    )

    # Resolve attribute (and links)
    attr = client.get_attribute_by_path(args.af_attribute_path)

    rows: List[Tuple[datetime, float]] = []

    if args.method == "interpolated":
        items = client.fetch_interpolated_via_links(attr, args.start, args.end, args.interval)
        for it in items:
            ts_raw = it.get("Timestamp")
            val = extract_numeric(it.get("Value"))
            if not ts_raw or val is None:
                continue
            dt_obj = parse_piwebapi_timestamp(ts_raw)
            rows.append((dt_obj, convert_flow(val, args.input_unit, args.output_unit)))

    else:
        # First try server-side summaries using attribute Links
        try:
            intervals = client.fetch_summaries_via_links(
                attr=attr,
                start=args.start,
                end=args.end,
                summary_duration="1h",
                summary_type="Average",
                calculation_basis=args.avg_basis,
                time_type=args.avg_time_type,
            )
            avg_rows = parse_interval_summaries_to_rows(intervals, timestamp_mode=args.avg_timestamp)
            if avg_rows:
                for dt_obj, avg_val in avg_rows:
                    rows.append((dt_obj, convert_flow(avg_val, args.input_unit, args.output_unit)))
            else:
                raise RuntimeError("Summaries returned no usable interval averages.")
        except (requests.HTTPError, RuntimeError) as e:
            # If summaries are not supported (404) or empty, fall back to client-side averaging.
            # This keeps you moving even if PI Web API doesn't expose /summaries for AF attributes.
            msg = str(e)
            print(f"WARNING: Server-side summaries unavailable/failed; using client-side TimeWeighted fallback. ({msg})")

            # Pull interpolated samples at a finer resolution, then compute hourly time-weighted average
            fine_items = client.fetch_interpolated_via_links(attr, args.start, args.end, args.avg_fallback_resolution)
            samples: List[Tuple[datetime, float]] = []
            for it in fine_items:
                ts_raw = it.get("Timestamp")
                val = extract_numeric(it.get("Value"))
                if not ts_raw or val is None:
                    continue
                dt_obj = parse_piwebapi_timestamp(ts_raw)
                samples.append((dt_obj, val))

            if not samples:
                raise RuntimeError("No data returned for fallback averaging.")

            start_dt = parse_piwebapi_timestamp(args.start)
            end_dt = parse_piwebapi_timestamp(args.end)

            hourly = client_side_time_weighted_hourly_average(samples, start_dt, end_dt)
            for dt_obj, avg_val in hourly:
                # timestamp choice
                dt_stamp = dt_obj if args.avg_timestamp == "start" else (dt_obj + timedelta(hours=1))
                rows.append((dt_stamp, convert_flow(avg_val, args.input_unit, args.output_unit)))

    if not rows:
        raise RuntimeError("No numeric data returned for the specified range/interval.")

    write_prism_csv(args.out, args.station_id, args.output_unit, rows)
    print(f"Wrote Prism CSV: {args.out} ({len(rows)} rows, method={args.method})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        if getattr(e, "response", None) is not None:
            try:
                print(e.response.text, file=sys.stderr)
            except Exception:
                pass
        raise
