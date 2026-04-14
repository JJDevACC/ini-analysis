"""Tests for the csv_formatter module.

Covers unit tests (Task 4.5) and property-based tests (Tasks 4.6–4.11).
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import csv_formatter


# ===========================================================================
# Task 4.5 — Unit tests for csv_formatter
# ===========================================================================


# --- derive_site_id ---

def test_derive_site_id_wes8617():
    assert csv_formatter.derive_site_id("wwl:south:wes8617b_realtmmetflo") == "WES8617"


def test_derive_site_id_bra10477():
    assert csv_formatter.derive_site_id("wwl:east:bra10477B_REALTMMETFLO") == "BRA10477"


# --- format_timestamp ---

def test_format_timestamp_midnight():
    assert csv_formatter.format_timestamp(datetime(2024, 6, 12, 0, 0, 0)) == "06/12/2024 12:00:00 AM"


def test_format_timestamp_noon():
    assert csv_formatter.format_timestamp(datetime(2024, 6, 12, 12, 0, 0)) == "06/12/2024 12:00:00 PM"


def test_format_timestamp_1am():
    assert csv_formatter.format_timestamp(datetime(2024, 6, 12, 1, 0, 0)) == "06/12/2024 01:00:00 AM"


def test_format_timestamp_1pm():
    assert csv_formatter.format_timestamp(datetime(2024, 6, 12, 13, 0, 0)) == "06/12/2024 01:00:00 PM"


# --- format_value ---

def test_format_value_float():
    result = csv_formatter.format_value(2.184343173)
    assert result == "2.184343173"


def test_format_value_none():
    assert csv_formatter.format_value(None) == "#VALUE!"


def test_format_value_integer_like():
    result = csv_formatter.format_value(42.0)
    assert result == "42", f"Expected '42' but got '{result}'"


# --- write_sliicer_csv header ---

def test_write_sliicer_csv_header():
    """Verify the 3-line header matches the expected Sliicer format exactly."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        rows = [(datetime(2024, 6, 12, 0, 0, 0), 2.184343173)]
        csv_formatter.write_sliicer_csv(tmp.name, "WES8617", rows)

        with open(tmp.name, "r") as f:
            lines = f.readlines()

        assert lines[0].rstrip("\r\n") == "WES8617,Average=None,QualityFlag=FALSE,QualityValue=FALSE"
        assert lines[1].rstrip("\r\n") == "DateTime,MP1\\QFINAL,MP1\\QCONTINUITY,MP1\\QUANTITY"
        assert lines[2].rstrip("\r\n") == "MM/dd/yyyy h:mm:ss tt,MGD,MGD,MGD"
    finally:
        os.unlink(tmp.name)


# --- write_sliicer_csv data row ---

def test_write_sliicer_csv_data_row():
    """Verify a data row has the correct format: timestamp + value repeated 3 times."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        rows = [(datetime(2024, 6, 12, 0, 0, 0), 2.184343173)]
        csv_formatter.write_sliicer_csv(tmp.name, "WES8617", rows)

        with open(tmp.name, "r") as f:
            lines = f.readlines()

        data_line = lines[3].rstrip("\r\n")
        assert data_line == "06/12/2024 12:00:00 AM,2.184343173,2.184343173,2.184343173"
    finally:
        os.unlink(tmp.name)


# --- write_sliicer_csv #VALUE! row ---

def test_write_sliicer_csv_value_error_row():
    """Verify that None values produce #VALUE! in all 3 columns."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        rows = [(datetime(2024, 6, 12, 0, 0, 0), None)]
        csv_formatter.write_sliicer_csv(tmp.name, "WES8617", rows)

        with open(tmp.name, "r") as f:
            lines = f.readlines()

        data_line = lines[3].rstrip("\r\n")
        assert data_line == "06/12/2024 12:00:00 AM,#VALUE!,#VALUE!,#VALUE!"
    finally:
        os.unlink(tmp.name)


# --- compute_hourly_averages ---

def test_compute_hourly_averages_simple():
    """3 values in the same hour (all < 30 min) should produce a single entry with their mean."""
    data = [
        (datetime(2024, 6, 12, 0, 0, 0), 3.0),
        (datetime(2024, 6, 12, 0, 10, 0), 6.0),
        (datetime(2024, 6, 12, 0, 20, 0), 9.0),
    ]
    result = csv_formatter.compute_hourly_averages(data)
    assert len(result) == 1
    ts, avg = result[0]
    assert ts == datetime(2024, 6, 12, 0, 0, 0)
    assert avg == pytest.approx(6.0)


def test_compute_hourly_averages_rounding():
    """Values at minute >= 30 round up to the next hour (matching R's round_date)."""
    data = [
        (datetime(2024, 6, 12, 0, 29, 0), 10.0),  # rounds to 0:00
        (datetime(2024, 6, 12, 0, 30, 0), 20.0),  # rounds to 1:00
    ]
    result = csv_formatter.compute_hourly_averages(data)
    assert len(result) == 2
    assert result[0] == (datetime(2024, 6, 12, 0, 0, 0), 10.0)
    assert result[1] == (datetime(2024, 6, 12, 1, 0, 0), 20.0)


def test_compute_hourly_averages_empty():
    """Empty input returns empty list."""
    assert csv_formatter.compute_hourly_averages([]) == []


# --- parse_sliicer_csv round-trip ---

def test_parse_sliicer_csv_roundtrip():
    """Write then parse: verify data matches."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        rows = [
            (datetime(2024, 6, 12, 0, 0, 0), 2.184343173),
            (datetime(2024, 6, 12, 1, 0, 0), 1.872502524),
            (datetime(2024, 6, 12, 2, 0, 0), None),
        ]
        csv_formatter.write_sliicer_csv(tmp.name, "WES8617", rows)
        parsed = csv_formatter.parse_sliicer_csv(tmp.name)

        assert len(parsed) == len(rows)
        for (orig_ts, orig_val), (parsed_ts, parsed_val) in zip(rows, parsed):
            assert orig_ts == parsed_ts
            if orig_val is None:
                assert parsed_val is None
            else:
                assert parsed_val == pytest.approx(orig_val, rel=1e-9)
    finally:
        os.unlink(tmp.name)


# ===========================================================================
# Task 4.6 — Property 1: CSV Round-Trip
# Feature: pi-to-sliicer-automation, Property 1: CSV Round-Trip
# Validates: Requirements 6.1, 6.2
# ===========================================================================

_hourly_datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2029, 12, 31, 23, 0, 0),
).map(lambda dt: dt.replace(minute=0, second=0, microsecond=0))

_csv_values = st.one_of(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    st.none(),
)


@settings(max_examples=100)
@given(
    data=st.lists(
        st.tuples(_hourly_datetimes, _csv_values),
        min_size=0,
        max_size=30,
    )
)
def test_csv_round_trip(data):
    """Property 1: write → parse produces equivalent data."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        csv_formatter.write_sliicer_csv(tmp.name, "TEST001", data)
        parsed = csv_formatter.parse_sliicer_csv(tmp.name)

        assert len(parsed) == len(data)
        for (orig_ts, orig_val), (parsed_ts, parsed_val) in zip(data, parsed):
            # Timestamps match to the minute
            assert orig_ts.replace(second=0, microsecond=0) == parsed_ts.replace(second=0, microsecond=0)
            # Values match
            if orig_val is None:
                assert parsed_val is None
            else:
                # Match to 9 significant digits
                assert parsed_val == pytest.approx(orig_val, rel=1e-9)
    finally:
        os.unlink(tmp.name)


# ===========================================================================
# Task 4.7 — Property 2: Hourly Grouping Structure
# Feature: pi-to-sliicer-automation, Property 2: Hourly Grouping Structure
# Validates: Requirements 4.1, 4.3
# ===========================================================================

_base_hour = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2029, 12, 31, 23, 0, 0),
).map(lambda dt: dt.replace(minute=0, second=0, microsecond=0))


@settings(max_examples=100)
@given(
    base=_base_hour,
    n_hours=st.integers(min_value=1, max_value=10),
    points_per_hour=st.integers(min_value=1, max_value=10),
)
def test_hourly_grouping_structure(base, n_hours, points_per_hour):
    """Property 2: N distinct clock hours → exactly N output entries."""
    data = []
    for h in range(n_hours):
        hour_start = base + timedelta(hours=h)
        for m in range(points_per_hour):
            ts = hour_start + timedelta(minutes=m)
            data.append((ts, float(h * 10 + m)))

    result = csv_formatter.compute_hourly_averages(data)
    assert len(result) == n_hours

    # Each output hour should correspond to a distinct clock hour
    output_hours = [ts for ts, _val in result]
    assert len(set(output_hours)) == n_hours


# ===========================================================================
# Task 4.8 — Property 3: Hourly Average Value
# Feature: pi-to-sliicer-automation, Property 3: Hourly Average Value
# Validates: Requirements 4.2
# ===========================================================================

@settings(max_examples=100)
@given(
    base=_base_hour,
    values=st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=60,
    ),
)
def test_hourly_average_value(base, values):
    """Property 3: all values in one clock hour → single entry equal to arithmetic mean."""
    data = []
    for i, v in enumerate(values):
        ts = base + timedelta(minutes=i % 60)
        data.append((ts, v))

    result = csv_formatter.compute_hourly_averages(data)
    assert len(result) == 1

    _ts, avg = result[0]
    expected = sum(values) / len(values)
    assert avg == pytest.approx(expected, rel=1e-9)


# ===========================================================================
# Task 4.9 — Property 6: Data Row Format
# Feature: pi-to-sliicer-automation, Property 6: Data Row Format
# Validates: Requirements 5.4
# ===========================================================================

@settings(max_examples=100)
@given(
    dt=st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2029, 12, 31, 23, 59, 59),
    ),
    value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_data_row_format(dt, value):
    """Property 6: formatted CSV row has 4 comma-separated fields, value repeated 3 times."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        rows = [(dt, value)]
        csv_formatter.write_sliicer_csv(tmp.name, "TEST001", rows)

        with open(tmp.name, "r") as f:
            lines = f.readlines()

        # Line 3 (index 3) is the first data row
        data_line = lines[3].rstrip("\r\n")
        fields = data_line.split(",")
        assert len(fields) == 4, f"Expected 4 fields, got {len(fields)}: {data_line}"

        # The 3 value columns should be identical
        assert fields[1] == fields[2] == fields[3], (
            f"Value columns differ: {fields[1]!r}, {fields[2]!r}, {fields[3]!r}"
        )

        # Timestamp should contain AM or PM
        assert "AM" in fields[0] or "PM" in fields[0], (
            f"Timestamp missing AM/PM: {fields[0]!r}"
        )
    finally:
        os.unlink(tmp.name)


# ===========================================================================
# Task 4.10 — Property 7: Numeric Formatting Fidelity
# Feature: pi-to-sliicer-automation, Property 7: Numeric Formatting Fidelity
# Validates: Requirements 5.5, 6.2
# ===========================================================================

@settings(max_examples=100)
@given(
    value=st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_numeric_formatting_fidelity(value):
    """Property 7: format_value produces no trailing zeros, parse back recovers value."""
    formatted = csv_formatter.format_value(value)

    # Should not be #VALUE!
    assert formatted != "#VALUE!"

    # No trailing zeros after decimal point (check mantissa only, not exponent)
    if "." in formatted:
        # Split off any exponent part before checking trailing zeros
        mantissa = formatted.split("e")[0].split("E")[0]
        assert not mantissa.endswith("0"), (
            f"Trailing zero in formatted value: {formatted!r}"
        )

    # Parse back and verify precision
    parsed = float(formatted)
    if value == 0.0:
        assert parsed == 0.0
    else:
        assert parsed == pytest.approx(value, rel=1e-9), (
            f"Precision loss: {value} -> {formatted!r} -> {parsed}"
        )


# ===========================================================================
# Task 4.11 — Property 8: Site ID Derivation
# Feature: pi-to-sliicer-automation, Property 8: Site ID Derivation
# Validates: Requirements 7.3
# ===========================================================================

_prefix = st.sampled_from(["wwl", "ww", "sys"])
_location = st.sampled_from(["south", "east", "north", "west", "central"])
_alpha_part = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=2,
    max_size=5,
)
_numeric_part = st.integers(min_value=1, max_value=99999).map(str)
_suffix_char = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=1,
    max_size=1,
)


@settings(max_examples=100)
@given(
    prefix=_prefix,
    location=_location,
    alpha=_alpha_part,
    numeric=_numeric_part,
    suffix=_suffix_char,
)
def test_site_id_derivation(prefix, location, alpha, numeric, suffix):
    """Property 8: derive_site_id returns uppercase site ID from tag name convention."""
    tag_name = f"{prefix}:{location}:{alpha}{numeric}{suffix}_realtmmetflo"
    expected = (alpha + numeric).upper()

    result = csv_formatter.derive_site_id(tag_name)
    assert result == expected, (
        f"Tag: {tag_name!r}, expected: {expected!r}, got: {result!r}"
    )
