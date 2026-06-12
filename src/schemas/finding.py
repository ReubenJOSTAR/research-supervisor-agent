from typing import Literal
from pydantic import BaseModel

class RouteDecision(BaseModel):
    next: Literal[
        "reseracher",
        "critic",
        "writer",
        "FINSIH"
    ]