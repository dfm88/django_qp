"""Chart generation for benchmark results."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for Docker
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from benchmark import BenchmarkResult

CHARTS_DIR = Path("/app/results/charts")

COLORS = {"pydantic": "#4A90D9", "msgspec": "#2ECC71"}


def generate_charts(results: list[BenchmarkResult]) -> None:
    """Generate speed and memory comparison charts."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = list(dict.fromkeys(r.scenario for r in results))
    backends = ["pydantic", "msgspec"]

    _generate_speed_chart(results, scenarios, backends)
    _generate_memory_chart(results, scenarios, backends)


def _get_values(
    results: list[BenchmarkResult],
    scenarios: list[str],
    backend: str,
    attr: str,
) -> list[float]:
    """Extract values for a given backend and attribute across scenarios."""
    lookup = {(r.scenario, r.backend): r for r in results}
    return [getattr(lookup[(s, backend)], attr) for s in scenarios]


def _generate_speed_chart(
    results: list[BenchmarkResult],
    scenarios: list[str],
    backends: list[str],
) -> None:
    """Generate grouped bar chart for ops/sec."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(scenarios))
    width = 0.35

    for i, backend in enumerate(backends):
        values = _get_values(results, scenarios, backend, "ops_per_sec")
        offset = (i - 0.5) * width
        bars = ax.bar(x + offset, values, width, label=backend, color=COLORS[backend])
        ax.bar_label(bars, fmt="{:,.0f}", padding=3, fontsize=8)

    ax.set_ylabel("Operations / second")
    ax.set_title("django-qp Validation Speed: pydantic vs msgspec")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "speed.png", dpi=150)
    plt.close(fig)


def _generate_memory_chart(
    results: list[BenchmarkResult],
    scenarios: list[str],
    backends: list[str],
) -> None:
    """Generate grouped bar chart for peak memory."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(scenarios))
    width = 0.35

    for i, backend in enumerate(backends):
        values = _get_values(results, scenarios, backend, "peak_memory_kb")
        offset = (i - 0.5) * width
        bars = ax.bar(x + offset, values, width, label=backend, color=COLORS[backend])
        ax.bar_label(bars, fmt="{:.1f}", padding=3, fontsize=8)

    ax.set_ylabel("Peak Memory (KB)")
    ax.set_title("django-qp Peak Memory: pydantic vs msgspec")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "memory.png", dpi=150)
    plt.close(fig)
