from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class VariantSummary(BaseModel):
    id: str
    position: str
    ref: str
    alt: str
    type: Optional[str] = None
    quality: Optional[float] = None
    filter: Optional[List[str]] = None
    rsid: Optional[str] = None
    gnomad_af: Optional[float] = None
    max_pop_af: Optional[float] = None
    clinvar_significance: Optional[str] = None
    clinvar_variant_type: Optional[str] = None
    clinvar_id: Optional[str] = None
    gene: Optional[List[str]] = None

class PopulationFrequencies(BaseModel):
    gnomad_total: Optional[float] = None
    gnomad_afr: Optional[float] = None
    gnomad_amr: Optional[float] = None
    gnomad_eas: Optional[float] = None
    gnomad_fin: Optional[float] = None
    gnomad_nfe: Optional[float] = None
    gnomad_asj: Optional[float] = None
    gnomad_sas: Optional[float] = None
    topmed: Optional[float] = None

class QualityMetrics(BaseModel):
    mapping_quality: Optional[float] = None
    fisher_strand_bias: Optional[float] = None
    quality_score: Optional[float] = None

class ConservationScores(BaseModel):
    phylop: Optional[float] = None
    phylop_primate: Optional[float] = None
    gerp: Optional[float] = None
    dann: Optional[float] = None

class VariantDetail(BaseModel):
    variant: Dict
    summary: VariantSummary
    population_frequencies: PopulationFrequencies
    quality_metrics: QualityMetrics
    conservation_scores: ConservationScores
