"""
Strategy Template
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class StrategyConfig:
    """Strategy parameters. Pre-registered before backtesting."""
    name: str
    version: str
    params: dict
    experiment_type: str  # "confirmatory" or "exploratory"


class Strategy(ABC):
    """Base class for all strategies."""

    def __init__(self, config: StrategyConfig):
        self.config = config

    @abstractmethod
    def hypothesis(self) -> str:
        """Economic rationale."""
        raise NotImplementedError

    @abstractmethod
    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features. Must be causal."""
        raise NotImplementedError

    @abstractmethod
    def target_position(self, df: pd.DataFrame) -> pd.Series:
        """Return desired position at each bar: +1, 0, -1, or fractional."""
        raise NotImplementedError
