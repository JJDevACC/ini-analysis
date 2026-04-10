"""Manual test script for PI Web API connection.

Run this to verify that pi_client.py can connect to your PI Web API,
discover the data server, find a PI Point, and pull data.

Usage:
    python test_connection.py <tag_name> <start_time> <end_time> [--method METHOD] [--interval INTERVAL]

Methods:
    interpolated  - Get interpolated data at a fixed interval (default: 1m)
    summary       - Get server-side hourly averages from PI (default: 1h Average)

Examples:
    python test_connection.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*"
    python test_connection.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*" --method summary
    python test_connection.py "wwl:south:wes8617b_realtmmetflo" "*-5d" "*" --method interpolated --interval 1h

Output is written to both the console and a JSON file in the output/ folder.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import pi_client

# Load .env from the same directory as this script
SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def main():
    parser = argparse.ArgumentParser(description="Test PI Web API connection and data retrieval")
    parser.add_argument("tag", help="PI Point tag name (e.g. wwl:south:wes8617b_realtmmetflo)")
    parser.add_argument("start", help="Start time (e.g. *-5d, 2024-06-12)")
    parser.add_argument("end", help="End time (e.g. *, 2024-06-15)")
    parser.add_argument("--method", choices=["interpolated", "summary"], default="summary",
                        help="Data retrieval method (default: summary)")
    parser.add_argument("--interval", default=None,
                        help="Interval for interpolated (default: 1m) or summary duration (default: 1h)")
    parser.add_argument("--summary-type", default="Average",
                        help="Summary calculation type: Average, Minimum, Maximum, Total, etc. (default: Average)")
    args = parser.parse_args()

    # Read config from .env
    url = os.getenv("PIWEBAPI_URL", "")
    user = os.getenv("PIWEBAPI_USER", "")
    password = os.getenv("PIWEBAPI_PASS", "")
    verify_tls = os.getenv("PIWEBAPI_VERIFY_TLS", "true").lower() not in ("false", "0", "no")
    server_name = os.getenv("PIWEBAPI_SERVER", "masterpi")

    print(f"PI Web API URL: {url}")
    print(f"User: {user}")
    print(f"Verify TLS: {verify_tls}")
    print(f"Server name: {server_name}")
    print(f"Tag: {args.tag}")
    print(f"Time range: {args.start} to {args.end}")
    print(f"Method: {args.method}")
    print("-" * 60)

    # Step 1: Create session
    print("\n[1] Creating NTLM session...")
    session = pi_client.create_session(url, user, password, verify_tls)
    print("    Session created.")

    # Step 2: Find data server
    print(f"\n[2] Looking up data server '{server_name}'...")
    server_webid = pi_client.find_data_server(session, url, server_name)
    print(f"    Found server WebID: {server_webid}")

    # Step 3: Find PI Point
    print(f"\n[3] Looking up PI Point '{args.tag}'...")
    point_webid = pi_client.find_point_webid(session, url, server_webid, args.tag)
    print(f"    Found point WebID: {point_webid}")

    # Step 4: Get data using the selected method
    if args.method == "interpolated":
        interval = args.interval or "1m"
        print(f"\n[4] Fetching interpolated data (interval={interval})...")
        data = pi_client.get_interpolated_data(
            session, url, point_webid, args.start, args.end, interval
        )
    else:  # summary
        duration = args.interval or "1h"
        print(f"\n[4] Fetching summary data (type={args.summary_type}, duration={duration})...")
        data = pi_client.get_summary_data(
            session, url, point_webid, args.start, args.end,
            summary_type=args.summary_type, summary_duration=duration
        )

    print(f"    Retrieved {len(data)} data points.")

    # Show first/last few rows
    if data:
        print(f"\n    First 5 rows:")
        for ts, val in data[:5]:
            print(f"      {ts}  ->  {val}")
        if len(data) > 10:
            print(f"    ...")
            print(f"    Last 5 rows:")
            for ts, val in data[-5:]:
                print(f"      {ts}  ->  {val}")

    # Write output to JSON
    output_dir = SCRIPT_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    safe_tag = args.tag.replace(":", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{safe_tag}_{args.method}_{timestamp}.json"

    output_data = {
        "tag": args.tag,
        "method": args.method,
        "start_time": args.start,
        "end_time": args.end,
        "server_webid": server_webid,
        "point_webid": point_webid,
        "row_count": len(data),
        "rows": [
            {"timestamp": ts.isoformat(), "value": val}
            for ts, val in data
        ],
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n[5] Output written to: {output_file}")
    print(f"    Total rows: {len(data)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
