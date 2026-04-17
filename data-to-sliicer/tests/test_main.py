"""Tests for main.py — CLI argument parsing and pipeline orchestration.

Covers Tasks 6.1, 6.2, 6.4:
- argparse configuration (required args, defaults, optional flags)
- Pipeline wiring with mocked pi_client and csv_formatter
- Error handling for missing env vars, PI API errors
"""

import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

import main


# ===========================================================================
# Import smoke test
# ===========================================================================

def test_main_module_imports():
    """main.py can be imported and exposes expected functions."""
    assert hasattr(main, "build_parser")
    assert hasattr(main, "run_pipeline")
    assert hasattr(main, "main")
    assert callable(main.build_parser)
    assert callable(main.run_pipeline)


# ===========================================================================
# Argparse configuration tests
# ===========================================================================

class TestArgparse:
    """Test CLI argument parsing via build_parser."""

    def test_required_positional_args(self):
        """tag, start, end are required positional arguments."""
        parser = main.build_parser()
        args = parser.parse_args(["my-tag", "*-5d", "*"])
        assert args.tag == "my-tag"
        assert args.start == "*-5d"
        assert args.end == "*"

    def test_missing_positional_args_exits(self):
        """Missing positional args cause SystemExit."""
        parser = main.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_missing_start_end_exits(self):
        """Missing start and end cause SystemExit."""
        parser = main.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["my-tag"])

    def test_default_method_is_summary(self):
        """--method defaults to 'summary'."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.method == "summary"

    def test_method_interpolated(self):
        """--method interpolated is accepted."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--method", "interpolated"])
        assert args.method == "interpolated"

    def test_method_summary(self):
        """--method summary is accepted."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--method", "summary"])
        assert args.method == "summary"

    def test_invalid_method_exits(self):
        """Invalid --method value causes SystemExit."""
        parser = main.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["tag", "start", "end", "--method", "bogus"])

    def test_default_interval_is_none(self):
        """--interval defaults to None."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.interval is None

    def test_interval_custom(self):
        """--interval accepts custom values."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--interval", "15m"])
        assert args.interval == "15m"

    def test_default_summary_type(self):
        """--summary-type defaults to 'Average'."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.summary_type == "Average"

    def test_summary_type_custom(self):
        """--summary-type accepts custom values."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--summary-type", "Maximum"])
        assert args.summary_type == "Maximum"

    def test_default_output_is_none(self):
        """--output defaults to None (will use {site_id}.csv)."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.output is None

    def test_output_custom(self):
        """--output accepts a custom path."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--output", "my_output.csv"])
        assert args.output == "my_output.csv"

    def test_post_to_sliicer_default_false(self):
        """--post-to-sliicer defaults to False."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.post_to_sliicer is False

    def test_post_to_sliicer_flag(self):
        """--post-to-sliicer sets the flag to True."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--post-to-sliicer"])
        assert args.post_to_sliicer is True

    def test_default_log_level(self):
        """--log-level defaults to 'INFO'."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end"])
        assert args.log_level == "INFO"

    def test_log_level_custom(self):
        """--log-level accepts custom values."""
        parser = main.build_parser()
        args = parser.parse_args(["tag", "start", "end", "--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"


# ===========================================================================
# Pipeline wiring tests (mocked pi_client and csv_formatter)
# ===========================================================================

def _make_mock_session():
    """Create a mock requests.Session."""
    return MagicMock()


def _make_pipeline_args(**overrides):
    """Build a Namespace with default pipeline args, applying overrides."""
    defaults = {
        "tag": "wwl:south:wes8617b_realtmmetflo",
        "start": "*-5d",
        "end": "*",
        "method": "summary",
        "interval": None,
        "summary_type": "Average",
        "units": "gpm-to-mgd",
        "output": None,
        "output_suffix": "",
        "post_to_sliicer": False,
        "log_level": "INFO",
    }
    defaults.update(overrides)
    import argparse
    return argparse.Namespace(**defaults)


_SAMPLE_SUMMARY_DATA = [
    (datetime(2024, 6, 12, 0, 0), 2.184),
    (datetime(2024, 6, 12, 1, 0), 1.872),
    (datetime(2024, 6, 12, 2, 0), 1.654),
]

_SAMPLE_INTERPOLATED_RAW = [
    (datetime(2024, 6, 12, 0, 0), 2.1),
    (datetime(2024, 6, 12, 0, 1), 2.2),
    (datetime(2024, 6, 12, 1, 0), 1.8),
    (datetime(2024, 6, 12, 1, 1), 1.9),
]

_SAMPLE_HOURLY_AVG = [
    (datetime(2024, 6, 12, 0, 0), 2.15),
    (datetime(2024, 6, 12, 1, 0), 1.85),
]

_FAKE_ENV = {
    "PIWEBAPI_URL": "https://fake.example.com/piwebapi",
    "PIWEBAPI_USER": "DOMAIN\\user",
    "PIWEBAPI_PASS": "secret",
    "PIWEBAPI_VERIFY_TLS": "false",
    "PIWEBAPI_SERVER": "masterpi",
}


def _env_side_effect(key, default=""):
    """Side effect for os.getenv that returns fake env values."""
    return _FAKE_ENV.get(key, default)


# ===========================================================================
# Pipeline wiring tests — summary method
# ===========================================================================

class TestPipelineSummary:
    """Test run_pipeline with method='summary' using mocked pi_client/csv_formatter."""

    @patch("main.csv_formatter.write_sliicer_csv", return_value=3)
    @patch("main.csv_formatter.convert_values", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.csv_formatter.derive_site_id", return_value="WES8617")
    @patch("main.pi_client.get_summary_data", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session")
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_summary_calls_get_summary_data(
        self, mock_getenv, mock_session, mock_find_server,
        mock_find_point, mock_get_summary, mock_derive, mock_convert, mock_write,
    ):
        """Summary method calls get_summary_data and write_sliicer_csv."""
        args = _make_pipeline_args(method="summary")
        main.run_pipeline(args)

        mock_session.assert_called_once()
        mock_find_server.assert_called_once()
        mock_find_point.assert_called_once()
        mock_get_summary.assert_called_once()
        mock_derive.assert_called_once_with(args.tag)
        mock_write.assert_called_once_with("WES8617.csv", "WES8617", _SAMPLE_SUMMARY_DATA)

    @patch("main.csv_formatter.write_sliicer_csv", return_value=3)
    @patch("main.csv_formatter.convert_values", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.csv_formatter.derive_site_id", return_value="WES8617")
    @patch("main.pi_client.get_summary_data", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session")
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_summary_uses_custom_output_path(
        self, mock_getenv, mock_session, mock_find_server,
        mock_find_point, mock_get_summary, mock_derive, mock_convert, mock_write,
    ):
        """When --output is specified, write_sliicer_csv uses that path."""
        args = _make_pipeline_args(method="summary", output="custom_out.csv")
        main.run_pipeline(args)

        mock_write.assert_called_once_with("custom_out.csv", "WES8617", _SAMPLE_SUMMARY_DATA)

    @patch("main.csv_formatter.write_sliicer_csv", return_value=3)
    @patch("main.csv_formatter.convert_values", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.csv_formatter.derive_site_id", return_value="WES8617")
    @patch("main.pi_client.get_summary_data", return_value=_SAMPLE_SUMMARY_DATA)
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session")
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_summary_passes_summary_type_and_duration(
        self, mock_getenv, mock_session, mock_find_server,
        mock_find_point, mock_get_summary, mock_derive, mock_convert, mock_write,
    ):
        """Summary method passes summary_type and interval as summary_duration."""
        args = _make_pipeline_args(method="summary", summary_type="Maximum", interval="2h")
        main.run_pipeline(args)

        call_kwargs = mock_get_summary.call_args
        assert call_kwargs[1]["summary_type"] == "Maximum"
        assert call_kwargs[1]["summary_duration"] == "2h"


# ===========================================================================
# Pipeline wiring tests — interpolated method
# ===========================================================================

class TestPipelineInterpolated:
    """Test run_pipeline with method='interpolated' using mocked pi_client/csv_formatter."""

    @patch("main.csv_formatter.write_sliicer_csv", return_value=2)
    @patch("main.csv_formatter.convert_values", return_value=_SAMPLE_HOURLY_AVG)
    @patch("main.csv_formatter.derive_site_id", return_value="WES8617")
    @patch("main.csv_formatter.compute_hourly_averages", return_value=_SAMPLE_HOURLY_AVG)
    @patch("main.pi_client.get_interpolated_data", return_value=_SAMPLE_INTERPOLATED_RAW)
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session")
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_interpolated_calls_compute_hourly_averages(
        self, mock_getenv, mock_session, mock_find_server,
        mock_find_point, mock_get_interp, mock_hourly, mock_derive, mock_convert, mock_write,
    ):
        """Interpolated method calls get_interpolated_data, compute_hourly_averages, then write."""
        args = _make_pipeline_args(method="interpolated")
        main.run_pipeline(args)

        mock_get_interp.assert_called_once()
        mock_hourly.assert_called_once_with(_SAMPLE_INTERPOLATED_RAW)
        mock_write.assert_called_once_with("WES8617.csv", "WES8617", _SAMPLE_HOURLY_AVG)

    @patch("main.csv_formatter.write_sliicer_csv", return_value=2)
    @patch("main.csv_formatter.convert_values", return_value=_SAMPLE_HOURLY_AVG)
    @patch("main.csv_formatter.derive_site_id", return_value="WES8617")
    @patch("main.csv_formatter.compute_hourly_averages", return_value=_SAMPLE_HOURLY_AVG)
    @patch("main.pi_client.get_interpolated_data", return_value=_SAMPLE_INTERPOLATED_RAW)
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session")
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_interpolated_uses_custom_interval(
        self, mock_getenv, mock_session, mock_find_server,
        mock_find_point, mock_get_interp, mock_hourly, mock_derive, mock_convert, mock_write,
    ):
        """Interpolated method passes custom --interval to get_interpolated_data."""
        args = _make_pipeline_args(method="interpolated", interval="5m")
        main.run_pipeline(args)

        # interval should be the 6th positional arg to get_interpolated_data
        call_args = mock_get_interp.call_args[0]
        assert call_args[5] == "5m"


# ===========================================================================
# Error handling tests
# ===========================================================================

class TestPipelineErrorHandling:
    """Test that run_pipeline propagates errors from pi_client."""

    @patch("main.pi_client.create_session", side_effect=ValueError("Missing required PI Web API configuration: PIWEBAPI_URL"))
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_create_session_valueerror_propagates(self, mock_getenv, mock_session):
        """ValueError from create_session propagates out of run_pipeline."""
        args = _make_pipeline_args()
        with pytest.raises(ValueError, match="Missing required"):
            main.run_pipeline(args)

    @patch("main.pi_client.find_data_server", side_effect=ValueError("Data server 'masterpi' not found"))
    @patch("main.pi_client.create_session", return_value=MagicMock())
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_find_data_server_valueerror_propagates(self, mock_getenv, mock_session, mock_find):
        """ValueError from find_data_server propagates out of run_pipeline."""
        args = _make_pipeline_args()
        with pytest.raises(ValueError, match="not found"):
            main.run_pipeline(args)

    @patch("main.pi_client.find_point_webid", side_effect=ValueError("PI Point 'bad_tag' not found"))
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session", return_value=MagicMock())
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_find_point_valueerror_propagates(self, mock_getenv, mock_session, mock_find_server, mock_find_point):
        """ValueError from find_point_webid propagates out of run_pipeline."""
        args = _make_pipeline_args()
        with pytest.raises(ValueError, match="not found"):
            main.run_pipeline(args)

    @patch("main.pi_client.get_summary_data")
    @patch("main.pi_client.find_point_webid", return_value="POINT_WEBID")
    @patch("main.pi_client.find_data_server", return_value="SERVER_WEBID")
    @patch("main.pi_client.create_session", return_value=MagicMock())
    @patch("main.os.getenv", side_effect=_env_side_effect)
    def test_http_error_propagates(self, mock_getenv, mock_session, mock_find_server, mock_find_point, mock_get_summary):
        """requests.HTTPError from pi_client propagates out of run_pipeline."""
        import requests
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get_summary.side_effect = requests.HTTPError("500 Server Error", response=mock_resp)

        args = _make_pipeline_args(method="summary")
        with pytest.raises(requests.HTTPError):
            main.run_pipeline(args)