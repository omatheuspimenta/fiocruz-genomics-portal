from fastapi import APIRouter, HTTPException, Request
from app.db.elasticsearch import get_es_client
from app.core.config import settings
from app.schemas.variant import VariantDetail
# from app.utils.clinvar import clinvar_transform
import re

router = APIRouter()

def validate_variant_id(variant_id: str) -> bool:
    """Validate variant ID format (chr-pos-ref-alt, rsid, or chr:start-end)"""
    # RSID format
    if variant_id.lower().startswith('rs'):
        return True
    
    # Standard format: CHR-POS-REF-ALT
    standard_pattern = r'^([0-9]{1,2}|X|Y|MT?)-\d+-[ACGT]+-[ACGT]+$'
    if re.match(standard_pattern, variant_id, re.IGNORECASE):
        return True

    # New format: CHR:POS-REF-ALT
    colon_pattern = r'^([0-9]{1,2}|X|Y|MT?):\d+-[ACGT]+-[ACGT]+$'
    if re.match(colon_pattern, variant_id, re.IGNORECASE):
        return True
        
    # Region format: CHR:START-END
    region_pattern = r'^([0-9]{1,2}|X|Y|MT?):\d+-\d+$'
    if re.match(region_pattern, variant_id, re.IGNORECASE):
        return True
        
    return False

@router.get("/{variant_id}", response_model=VariantDetail)
async def get_variant(variant_id: str):
    """
    Get detailed information about a specific variant.
    Supports:
    - Standard ID: CHR-POS-REF-ALT
    - RSID: rs12345
    - Region-like ID: CHR:START-END (searches for exact match on vid or location)
    """
    if not validate_variant_id(variant_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid variant ID format. Expected: CHR-POS-REF-ALT, rs..., or CHR:START-END"
        )
    
    try:
        es = await get_es_client()
        query = {"size": 1}
        # Handle RSID search
        if variant_id.lower().startswith('rs'):
            query["query"] = {"term": {"rsid.keyword": variant_id.lower()}}
        else:
            # Normalize variant ID to uppercase (handles case-insensitivity for REF/ALT/CHR)
            variant_id = variant_id.upper()
            # Handle CHR:POS-REF-ALT format by converting to CHR-POS-REF-ALT
            if ':' in variant_id and '-' in variant_id:
                variant_id = variant_id.replace(':', '-')
            query["query"] = {"term": {"vid.keyword": variant_id}}
        
        response = await es.search(index=settings.ES_INDEX, body=query)
        hits = response['hits']['hits']
        
        if not hits:
            raise HTTPException(status_code=404, detail="Variant not found")
        
        variant = hits[0]['_source']
        
        # Map to Pydantic model
        return {
            "variant": variant,
            "summary": {
                "id": variant.get('vid'),
                "position": f"{variant.get('chromosome')}:{variant.get('position')}",
                "ref": variant.get('ref'),
                "alt": variant.get('alt'),
                "type": variant.get('variant_type'),
                "quality": variant.get('quality'),
                "filter": variant.get('filters').split(',') if variant.get('filters') else [],
                "rsid": variant.get('rsid'),
                "gnomad_af": variant.get('gnomad_af'),
                "max_pop_af": variant.get('max_pop_af'),
                # "clinvar_significance": clinvar_transform(variant.get('clinvar_significance')),
                "clinvar_significance": variant.get('clinvar_significance'),
                "clinvar_variant_type": variant.get('clinvar_variant_type'),
                "clinvar_id": variant.get('clinvar_id'),
                "gene": variant.get('genes') if variant.get('genes') else [],
            },
            "population_frequencies": {
                "gnomad_total": variant.get('gnomad_af'),
                "gnomad_afr": variant.get('gnomad_afr_af'),
                "gnomad_amr": variant.get('gnomad_amr_af'),
                "gnomad_eas": variant.get('gnomad_eas_af'),
                "gnomad_fin": variant.get('gnomad_fin_af'),
                "gnomad_nfe": variant.get('gnomad_nfe_af'),
                "gnomad_asj": variant.get('gnomad_asj_af'),
                "gnomad_sas": variant.get('gnomad_sas_af'),
                "topmed": variant.get('topmed_af'),
            },
            "quality_metrics": {
                "mapping_quality": variant.get('mapping_quality'),
                "fisher_strand_bias": variant.get('fisher_strand_bias'),
                "quality_score": variant.get('quality'),
            },
            "conservation_scores": {
                "phylop": variant.get('phylop_score'),
                "phylop_primate": variant.get('phylop_primate_score'),
                "gerp": variant.get('gerp_score'),
                "dann": variant.get('dann_score'),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
