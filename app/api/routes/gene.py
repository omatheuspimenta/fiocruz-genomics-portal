from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db.elasticsearch import get_es_client
from app.core.config import settings
from app.schemas.gene import GeneResponse

router = APIRouter()

@router.get("/{gene_name}", response_model=GeneResponse)
async def get_gene(
    gene_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    consequence: Optional[str] = None,
    min_af: Optional[float] = Query(None, ge=0, le=1),
    max_af: Optional[float] = Query(None, ge=0, le=1)
):
    """
    Get all variants in a specific gene with filtering and pagination.
    """
    try:
        es = await get_es_client()
        # Build query with filters
        must_conditions = [{"term": {"genes.keyword": gene_name.upper()}}]
        
        if consequence:
            must_conditions.append({
                "term": {"all_consequences.keyword": consequence}
            })
        
        if min_af is not None or max_af is not None:
            range_query = {}
            if min_af is not None:
                range_query["gte"] = min_af
            if max_af is not None:
                range_query["lte"] = max_af
            must_conditions.append({
                "range": {"max_gnomad_af": range_query}
            })
        
        query = {
            "query": {"bool": {"must": must_conditions}},
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"position": "asc"}]
        }
        
        response = await es.search(index=settings.ES_INDEX, body=query)
        total = response['hits']['total']['value']
        variants = []
        for hit in response['hits']['hits']:
            variant = hit['_source']
            # Apply ClinVar transformation
            # if 'clinvar_significance' in variant:
            #     variant['clinvar_significance'] = clinvar_transform(variant['clinvar_significance'])
            variants.append(variant)
        
        # Get aggregations for statistics (GLOBAL scope)
        from app.utils.stats import get_global_stats_query, format_stats_response
        
        # We need a separate query for stats because we want stats for ALL variants matching the filters,
        # not just the paginated ones.
        # The 'query' part is the same as the main query.
        stats_query = get_global_stats_query(query["query"])
        
        agg_response = await es.search(index=settings.ES_INDEX, body=stats_query)
        statistics = format_stats_response(agg_response, total)
        
        return {
            "gene": gene_name,
            "total_variants": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "variants": variants,
            "statistics": statistics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
