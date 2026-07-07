from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any


class Broker(ABC):
    @abstractmethod
    def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
