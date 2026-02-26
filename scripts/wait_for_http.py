#!/usr/bin/env python3
"""
Small helper to wait for an HTTP endpoint to return a 2xx/3xx.
Usage: python scripts/wait_for_http.py <url> <timeout_seconds> [interval_seconds]
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: wait_for_http.py <url> <timeout_seconds> [interval_seconds]", file=sys.stderr)
        return 2

    url = sys.argv[1]
    try:
        timeout = float(sys.argv[2])
    except ValueError:
        print("timeout_seconds must be a number", file=sys.stderr)
        return 2

    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    deadline = time.time() + timeout
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # nosec B310 - simple GET probe
                status = resp.getcode()
                if 200 <= status < 400:
                    print(f"ready: {url} [{status}]")
                    return 0
        except Exception as exc:  # broad: polling helper
            last_error = exc

        time.sleep(interval)

    print(f"timed out waiting for {url}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
