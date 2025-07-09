from pydantic import BaseModel
from typing import List

class GenerationRequest(BaseModel):
    barHeights: List[float]
    baseModel: str  # file name (e.g. "circle.step")
    extrusionHeight: float
