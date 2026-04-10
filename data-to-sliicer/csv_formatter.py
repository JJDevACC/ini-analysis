"""Sliicer CSV formatter module.

Handles writing and parsing the ADS Prism Sliicer CSV format, computing
hourly averages from 1-minute data, and deriving site IDs from PI tag names.
"""

import re
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def derive_site_id(tag_name: str) -> str:
    """Extract the site ID from a PI Point tag name.

    Convention: tag names follow ``{system}:{area}:{siteid}{suffix}``
    where the site ID is the uppercase alphanumeric prefix before any
    trailing single-letter suffix and underscore-separated descriptor.

    Examples:
        ``wwl:south:wes8617b_realtmmetflo`` → ``WES8617``
        ``wwl:east:bra10477B_REALTMMETFLO``  → ``BRA10477``

    Args:
        tag_name: Full PI Point tag name.

    Returns:
        Uppercase site ID string.
    """
    # Take the last colon-separated segment, split on underscore, take first part
    last_segment = tag_name.rsplit(":", maxsplit=1)[-1]
    before_underscore = last_segment.split("_")[0]

    # Strip trailing single alpha character (e.g. "b" in "wes8617b")
    match = re.match(r"^([A-Za-z]+\d+)", before_underscore)
    if match:
        return match.group(1).upper()

    return before_underscore.upper()


def compute_hourly_averages(
    data: list[tuple[datetime, float]],
) -> list[tuple[datetime, Optional[float]]]:
    """Group 1-minute data by clock hour and compute the arithmetic mean.

    Args:
        data: List of (timestamp, value) pairs at sub-hourly intervals.

    Returns:
        List of (hour_timestamp, average_value) pairs sorted chronologically.
        ``None`` for hours where all values were missing/non-numeric.
    """
    if not data:
        return []

    groups: dict[datetime, list[float]] = defaultdict(list)
    for ts, val in data:
        hour_key = ts.replace(minute=0, second=0, microsecond=0)
        groups[hour_key].append(val)

    results: list[tuple[datetime, Optional[float]]] = []
    for hour_key in sorted(groups):
        values = groups[hour_key]
        if values:
            results.append((hour_key, sum(values) / len(values)))
        else:
            results.append((hour_key, None))

    return results


def format_timestamp(dt: datetime) -> str:
    """Format a datetime as ``MM/dd/yyyy h:mm:ss tt`` (12-hour AM/PM).

    Matches the Sliicer CSV timestamp format exactly:
    - Zero-padded month and day (``06/12/2024``)
    - Non-zero-padded hour (``12:00:00 AM``, not ``00:00:00``)
    - AM/PM uppercase

    Args:
        dt: Datetime to format.

    Returns:
        Formatted timestamp string.
    """
    # %I gives zero-padded 12-hour, but Sliicer uses non-padded
    # Actually looking at the CSV: "06/12/2024 12:00:00 AM" — the hour IS zero-padded
    # %I in Python gives 01-12 (zero-padded). The CSV shows "12:00:00 AM" and "01:00:00 AM"
    # So %I is correct.
    return dt.strftime("%m/%d/%Y %I:%M:%S %p")


def format_value(value: Optional[float]) -> str:
    """Format a numeric value for the Sliicer CSV.

    Args:
        value: Flow value in MGD, or ``None`` for missing data.

    Returns:
        Decimal string without trailing zeros, or ``#VALUE!`` for None.
    """
    if value is None:
        return "#VALUE!"

    # Format with enough precision, then strip trailing zeros
    # Use repr-style formatting to preserve full precision
    formatted = f"{value:.15g}"
    return formatted


def write_sliicer_csv(
    file_path: str,
    site_id: str,
    rows: list[tuple[datetime, Optional[float]]],
) -> int:
    """Write flow data in the ADS Prism Sliicer CSV format.

    Format:
        Line 1: ``{site_id},Average=None,QualityFlag=FALSE,QualityValue=FALSE``
        Line 2: ``DateTime,MP1\\QFINAL,MP1\\QCONTINUITY,MP1\\QUANTITY``
        Line 3: ``MM/dd/yyyy h:mm:ss tt,MGD,MGD,MGD``
        Data:   ``06/12/2024 12:00:00 AM,2.184343173,2.184343173,2.184343173``

    Args:
        file_path: Output file path.
        site_id: Station identifier for the header.
        rows: List of (timestamp, value|None) pairs.

    Returns:
        Number of data rows written.
    """
    with open(file_path, "w", newline="") as f:
        # Write header lines with \r\n
        f.write(f"{site_id},Average=None,QualityFlag=FALSE,QualityValue=FALSE\r\n")
        f.write("DateTime,MP1\\QFINAL,MP1\\QCONTINUITY,MP1\\QUANTITY\r\n")
        f.write("MM/dd/yyyy h:mm:ss tt,MGD,MGD,MGD\r\n")

        # Write data rows
        for ts, val in rows:
            ts_str = format_timestamp(ts)
            val_str = format_value(val)
            f.write(f"{ts_str},{val_str},{val_str},{val_str}\r\n")

    logger.info("Wrote %d data rows to %s", len(rows), file_path)
    return len(rows)


def parse_sliicer_csv(
    file_path: str,
) -> list[tuple[datetime, Optional[float]]]:
    """Parse a Sliicer CSV file back into (datetime, value|None) pairs.

    Skips the 3-line header and parses each data row.
    Used for round-trip verification.

    Args:
        file_path: Path to the Sliicer CSV file.

    Returns:
        List of (datetime, value|None) pairs.
    """
    results: list[tuple[datetime, Optional[float]]] = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Skip 3-line header
    for line in lines[3:]:
        line = line.strip()
        if not line:
            continue

        parts = line.split(",")
        if len(parts) < 2:
            continue

        ts_str = parts[0]
        val_str = parts[1]  # Use first data column

        # Parse timestamp
        try:
            ts = datetime.strptime(ts_str, "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            logger.warning("Skipping row with unparseable timestamp: %s", ts_str)
            continue

        # Parse value
        if val_str == "#VALUE!":
            results.append((ts, None))
        else:
            try:
                results.append((ts, float(val_str)))
            except ValueError:
                logger.warning("Skipping row with unparseable value: %s", val_str)
                continue

    return results
