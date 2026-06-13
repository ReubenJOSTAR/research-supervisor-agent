from pydantic import BaseModel


class Critique(BaseModel):
    sufficient: bool
    critique: str