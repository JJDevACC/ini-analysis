"""PI to Sliicer export pipeline.

Orchestrates the full pipeline: connect to PI Web API, retrieve flow data,
compute hourly averages (if needed), and write a Sliicer-compatible CSV.

Usage:
    python main.py <tag> <start> <end> [--method METHOD] [--interval INTERVAL]
                   [--summary-type TYPE] [--output PATH] [--post-to-sliicer]
                   [--log-level LEVEL]

Methods:
    summary       - PI server-side summaries (default, duration from --interval, default 1h)
    interpolated  - Raw interpolated data at --interval spacing (default 1m),
                    then compute hourly averages client-side

Examples:
    python main.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*"
    python main.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*" --method interpolated
    python main.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*" --method summary --interval 1h
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import pi_client
import csv_formatter

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Export PI Web API flow data to Sliicer CSV format",
    )
    parser.add_argument("tag", help="PI Point tag name (e.g. wwl:south:wes8617b_realtmmetflo)")
    parser.add_argument("start", help="Start time (e.g. *-5d, 2024-06-12)")
    parser.add_argument("end", help="End time (e.g. *, 2024-06-15)")
    parser.add_argument(
        "--method",
        choices=["summary", "interpolated"],
        default="summary",
        help="Data retrieval method (default: summary)",
    )
    parser.add_argument(
        "--interval",
        default=None,
        help="Interval for interpolated (default: 1m) or summary duration (default: 1h)",
    )
    parser.add_argument(
        "--summary-type",
        default="Average",
        help="Summary calculation type: Average, Minimum, Maximum, Total, etc. (default: Average)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV file path (default: {site_id}.csv)",
    )
    parser.add_argument(
        "--post-to-sliicer",
        action="store_true",
        default=False,
        help="Post data to ADS Prism Sliicer API (Phase 3)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO)",
    )
    return parser


def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the PI-to-Sliicer export pipeline.

    Args:
        args: Parsed CLI arguments.
    """
    # Log run parameters
    logger.info("Tag: %s", args.tag)
    logger.info("Time range: %s to %s", args.start, args.end)
    logger.info("Method: %s", args.method)

    # Read config from environment (loaded from .env by caller)
    url = os.getenv("PIWEBAPI_URL", "")
    user = os.getenv("PIWEBAPI_USER", "")
    password = os.getenv("PIWEBAPI_PASS", "")
    verify_tls = os.getenv("PIWEBAPI_VERIFY_TLS", "true").lower() not in ("false", "0", "no")
    server_name = os.getenv("PIWEBAPI_SERVER", "masterpi")

    # Step 1: Create authenticated session
    logger.info("Creating PI Web API session...")
    session = pi_client.create_session(url, user, password, verify_tls)

    # Step 2: Find data server
    logger.info("Looking up data server '%s'...", server_name)
    server_webid = pi_client.find_data_server(session, url, server_name)
    logger.info("Found server WebID: %s", server_webid)

    # Step 3: Find PI Point
    logger.info("Looking up PI Point '%s'...", args.tag)
    point_webid = pi_client.find_point_webid(session, url, server_webid, args.tag)
    logger.info("Found point WebID: %s", point_webid)

    # Step 4: Retrieve data based on method
    if args.method == "summary":
        duration = args.interval or "1h"
        logger.info(
            "Fetching summary data (type=%s, duration=%s)...",
            args.summary_type, duration,
        )
        rows = pi_client.get_summary_data(
            session, url, point_webid, args.start, args.end,
            summary_type=args.summary_type, summary_duration=duration,
        )
    else:  # interpolated
        interval = args.interval or "1m"
        logger.info("Fetching interpolated data (interval=%s)...", interval)
        raw_data = pi_client.get_interpolated_data(
            session, url, point_webid, args.start, args.end, interval,
        )
        logger.info("Retrieved %d raw data points, computing hourly averages...", len(raw_data))
        rows = csv_formatter.compute_hourly_averages(raw_data)

    logger.info("Retrieved %d data rows.", len(rows))

    # Step 5: Derive site ID and determine output path
    site_id = csv_formatter.derive_site_id(args.tag)
    output_path = args.output or f"{site_id}.csv"
    logger.info("Site ID: %s", site_id)

    # Step 6: Write Sliicer CSV
    row_count = csv_formatter.write_sliicer_csv(output_path, site_id, rows)
    logger.info("Wrote %d data rows to %s", row_count, output_path)

    # Step 7: Post to Sliicer (Phase 3 — not yet implemented)
    if args.post_to_sliicer:
        logger.info("--post-to-sliicer: not yet implemented (Phase 3)")


def main() -> None:
    """Entry point: parse args, load .env, configure logging, run pipeline."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Load .env from the same directory as this script
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env")

    try:
        run_pipeline(args)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
