from pydantic import BaseModel
from typing import List, Dict, Any

class GeneStatistics(BaseModel):
    consequences: Dict[str, int]
    impacts: Dict[str, int]

class GeneResponse(BaseModel):
    gene: str
    total_variants: int
    page: int
    page_size: int
    total_pages: int
    variants: List[Dict[str, Any]]
    statistics: GeneStatistics
