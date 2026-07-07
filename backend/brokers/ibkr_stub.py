from __future__ import annotations
from typing import Dict, Any
from backend.brokers.base import Broker


class IBKRBrokerStub(Broker):
    """
    Placeholder so your resume bullet is honest about architecture.
    Real IBKR integration will likely use ib_insync or the official API gateway.
    """
    def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        return {"broker": "ibkr_stub", "status": "not_implemented", "order": order}
