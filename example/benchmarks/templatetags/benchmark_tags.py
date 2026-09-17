"""Template tags providing benchmark metrics and headline data to templates."""

from django import template

from benchmarks.metrics.summary import BenchmarkSummary, load_benchmark_summary

register = template.Library()


@register.simple_tag
def get_benchmark_summary() -> BenchmarkSummary:
    """Return the precomputed benchmark summary instance."""
    return load_benchmark_summary()
