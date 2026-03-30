"""Benchmark runner — measures speed and memory for msgspec vs pydantic through django-qp."""

from __future__ import annotations

import gc
import json
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import django
from django.conf import settings

# Minimal Django setup (no database, no apps needed)
if not settings.configured:
    settings.configure(
        DEBUG=False,
        DATABASES={},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()

from django.http import HttpRequest, QueryDict

from django_qp.core import create_error_response, process_query_params
from django_qp.exceptions import QueryParamsError

from models import (
    MsgspecComplex,
    MsgspecSimple,
    PydanticComplex,
    PydanticSimple,
)

WARMUP = 1_000
ITERATIONS = 10_000
MEMORY_ITERATIONS = 1_000

RESULTS_DIR = Path("/app/results")
CHARTS_DIR = RESULTS_DIR / "charts"


@dataclass
class BenchmarkResult:
    scenario: str
    backend: str
    ops_per_sec: float
    avg_us: float
    p99_us: float
    peak_memory_kb: float


def make_request(params: dict[str, str]) -> HttpRequest:
    """Create a Django HttpRequest with the given query parameters."""
    request = HttpRequest()
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    request.GET = QueryDict(query_string)
    return request


# === Test data ===

SIMPLE_VALID = {"search": "django", "page": "1", "active": "true", "tags": "python,web,api", "category": "backend"}
SIMPLE_INVALID = {"search": "django", "page": "not_a_number", "active": "true"}
COMPLEX_VALID = {
    "date_from": "2025-01-01",
    "date_to": "2025-12-31",
    "min_price": "10",
    "max_price": "100",
    "sort_by": "price",
    "order": "asc",
    "status": "active,pending",
    "limit": "50",
}
COMPLEX_INVALID = {
    "date_from": "2025-12-31",
    "date_to": "2025-01-01",  # date_to before date_from
    "min_price": "100",
    "max_price": "10",  # max < min
    "sort_by": "price",
    "order": "asc",
    "status": "active",
    "limit": "200",  # over 100
}


def run_speed_benchmark(
    request: HttpRequest,
    model: type,
    expect_error: bool,
) -> tuple[float, float, float]:
    """Run speed benchmark, return (ops_per_sec, avg_us, p99_us)."""
    # Warmup
    for _ in range(WARMUP):
        try:
            process_query_params(request, model)
        except QueryParamsError as exc:
            if expect_error:
                create_error_response(exc, model=model)
            else:
                raise

    # Measured run
    timings: list[float] = []
    for _ in range(ITERATIONS):
        start = time.perf_counter_ns()
        try:
            process_query_params(request, model)
        except QueryParamsError as exc:
            if expect_error:
                create_error_response(exc, model=model)
            else:
                raise
        elapsed_ns = time.perf_counter_ns() - start
        timings.append(elapsed_ns)

    total_ns = sum(timings)
    ops_per_sec = ITERATIONS / (total_ns / 1e9)
    avg_us = (total_ns / ITERATIONS) / 1e3
    p99_us = statistics.quantiles(timings, n=100)[98] / 1e3  # 99th percentile

    return ops_per_sec, avg_us, p99_us


def run_memory_benchmark(
    request: HttpRequest,
    model: type,
    expect_error: bool,
) -> float:
    """Run memory benchmark, return peak memory in KB."""
    gc.collect()
    tracemalloc.start()

    for _ in range(MEMORY_ITERATIONS):
        try:
            process_query_params(request, model)
        except QueryParamsError as exc:
            if expect_error:
                create_error_response(exc, model=model)
            else:
                raise

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return peak / 1024  # bytes to KB


SCENARIOS: list[dict[str, Any]] = [
    {"name": "simple-valid", "data": SIMPLE_VALID, "pydantic": PydanticSimple, "msgspec": MsgspecSimple, "error": False},
    {"name": "simple-invalid", "data": SIMPLE_INVALID, "pydantic": PydanticSimple, "msgspec": MsgspecSimple, "error": True},
    {"name": "complex-valid", "data": COMPLEX_VALID, "pydantic": PydanticComplex, "msgspec": MsgspecComplex, "error": False},
    {"name": "complex-invalid", "data": COMPLEX_INVALID, "pydantic": PydanticComplex, "msgspec": MsgspecComplex, "error": True},
]


def run_all() -> list[BenchmarkResult]:
    """Run all benchmark scenarios and return results."""
    results: list[BenchmarkResult] = []

    for scenario in SCENARIOS:
        request = make_request(scenario["data"])

        for backend_name, model in [("pydantic", scenario["pydantic"]), ("msgspec", scenario["msgspec"])]:
            print(f"  Running {scenario['name']} / {backend_name}...", flush=True)

            ops, avg, p99 = run_speed_benchmark(request, model, scenario["error"])
            peak_mem = run_memory_benchmark(request, model, scenario["error"])

            results.append(BenchmarkResult(
                scenario=scenario["name"],
                backend=backend_name,
                ops_per_sec=round(ops, 1),
                avg_us=round(avg, 2),
                p99_us=round(p99, 2),
                peak_memory_kb=round(peak_mem, 2),
            ))

    return results


def write_results(results: list[BenchmarkResult]) -> None:
    """Write results as markdown table and JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON output
    json_data = [
        {
            "scenario": r.scenario,
            "backend": r.backend,
            "ops_per_sec": r.ops_per_sec,
            "avg_us": r.avg_us,
            "p99_us": r.p99_us,
            "peak_memory_kb": r.peak_memory_kb,
        }
        for r in results
    ]
    (RESULTS_DIR / "results.json").write_text(json.dumps(json_data, indent=2))

    # Markdown table
    lines = [
        "# Benchmark Results",
        "",
        f"- **Warmup:** {WARMUP:,} iterations",
        f"- **Measured:** {ITERATIONS:,} iterations",
        f"- **Memory sample:** {MEMORY_ITERATIONS:,} iterations",
        f"- **Python:** {sys.version.split()[0]}",
        "",
        "| Scenario | Backend | Ops/sec | Avg (us) | P99 (us) | Peak Mem (KB) |",
        "|----------|---------|--------:|---------:|---------:|--------------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.scenario} | {r.backend} | {r.ops_per_sec:,.1f} | {r.avg_us:.2f} | {r.p99_us:.2f} | {r.peak_memory_kb:.2f} |"
        )
    lines.append("")

    (RESULTS_DIR / "results.md").write_text("\n".join(lines))


def main() -> None:
    print("=" * 60)
    print("django-qp Benchmark: msgspec vs pydantic")
    print("=" * 60)
    print(f"  Warmup:     {WARMUP:,} iterations")
    print(f"  Measured:   {ITERATIONS:,} iterations")
    print(f"  Memory:     {MEMORY_ITERATIONS:,} iterations")
    print(f"  Python:     {sys.version.split()[0]}")
    print()

    results = run_all()
    write_results(results)

    # Generate charts
    from plot import generate_charts
    generate_charts(results)

    print()
    print("Done! Results written to /app/results/")
    print("  - results.md")
    print("  - results.json")
    print("  - charts/speed.png")
    print("  - charts/memory.png")


if __name__ == "__main__":
    main()
