# backend/models/order.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Annotated


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(BaseModel):
    order_id: Annotated[str, Field(min_length=1)]
    symbol: Annotated[str, Field(min_length=1)]
    side: Side
    qty: Annotated[int, Field(gt=0)]
    px: Annotated[float, Field(gt=0)]
