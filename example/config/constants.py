from enum import Enum


class EnvironmentChoices(str, Enum):
    DEV = "development"
    DEMO = "demo_production"
    STATIC = "static_generation"
    BENCH = "benchmark"
