from pydantic import BaseModel
from typing import List, Dict, Any

class StatItem(BaseModel):
    name: str
    value: int

class PopStat(BaseModel):
    name: str
    val: float

class ConservationStat(BaseModel):
    name: str
    avg: float

class GeneStatistics(BaseModel):
    count: int
    uniqueTypes: int
    meanAF: float
    maxAF: float
    clinvarCount: int
    pieData: List[StatItem]
    popData: List[PopStat]
    variantTypeData: List[StatItem]
    qualityDist: List[StatItem]
    conservationData: List[ConservationStat]
    coverage: str

class GeneResponse(BaseModel):
    gene: str
    total_variants: int
    page: int
    page_size: int
    total_pages: int
    variants: List[Dict[str, Any]]
    statistics: GeneStatistics
