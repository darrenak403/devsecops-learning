import argparse
import statistics
import time

import httpx


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = max(0, min(len(sorted_values) - 1, int(round((p / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def measure(url: str, total_requests: int, timeout: float) -> None:
    latencies: list[float] = []
    with httpx.Client(timeout=timeout) as client:
        for _ in range(total_requests):
            start = time.perf_counter()
            response = client.get(url)
            elapsed_ms = (time.perf_counter() - start) * 1000
            response.raise_for_status()
            latencies.append(elapsed_ms)

    latencies.sort()
    print(f"url={url}")
    print(f"count={len(latencies)}")
    print(f"p50={percentile(latencies, 50):.2f}ms")
    print(f"p95={percentile(latencies, 95):.2f}ms")
    print(f"p99={percentile(latencies, 99):.2f}ms")
    print(f"avg={statistics.mean(latencies):.2f}ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple latency baseline sampler")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://localhost:3636")
    parser.add_argument("--path", required=True, help="Path to test, e.g. /api/v1/subjects")
    parser.add_argument("--requests", type=int, default=50, help="Number of requests")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout seconds")
    args = parser.parse_args()
    measure(f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}", total_requests=args.requests, timeout=args.timeout)


if __name__ == "__main__":
    main()
