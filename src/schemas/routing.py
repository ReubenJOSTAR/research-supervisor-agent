from typing import Literal
from pydantic import BaseModel


class RouteDecision(BaseModel):

    next: Literal[
        "researcher",
        "writer"
    ]