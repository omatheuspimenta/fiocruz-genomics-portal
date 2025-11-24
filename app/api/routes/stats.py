from fastapi import APIRouter, HTTPException, Query, Request
from app.db.elasticsearch import get_es_client
from app.core.config import settings

router = APIRouter()

@router.get("/search/autocomplete")
async def autocomplete(
    query: str = Query(..., min_length=2),
    type: str = Query("gene", regex="^(gene|variant)$")
):
    """
    Autocomplete suggestions for genes or variant IDs.
    """
    try:
        es = await get_es_client()
        if type == "gene":
            search_query = {
                "query": {
                    "prefix": {"genes.keyword": query.upper()}
                },
                "size": 10,
                "collapse": {"field": "genes.keyword"},
                "_source": ["genes"]
            }
        else:
            search_query = {
                "query": {
                    "prefix": {"vid.keyword": query}
                },
                "size": 10,
                "_source": ["vid"]
            }
        
        response = await es.search(index=settings.ES_INDEX, body=search_query)
        
        if type == "gene":
            suggestions = list(set(
                gene for hit in response['hits']['hits']
                for gene in hit['_source'].get('genes', [])
                if gene.upper().startswith(query.upper())
            ))[:10]
        else:
            suggestions = [hit['_source']['vid'] for hit in response['hits']['hits']]
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/stats")
async def get_stats():
    """Get database statistics."""
    try:
        es = await get_es_client()
        count_response = await es.count(index=settings.ES_INDEX)
        
        agg_query = {
            "size": 0,
            "aggs": {
                "variant_types": {
                    "terms": {"field": "variant_type.keyword"}
                },
                "chromosomes": {
                    "terms": {"field": "chromosome.keyword", "size": 25}
                }
            }
        }
        
        agg_response = await es.search(index=settings.ES_INDEX, body=agg_query)
        
        return {
            "total_variants": count_response['count'],
            "variant_types": {
                bucket['key']: bucket['doc_count']
                for bucket in agg_response['aggregations']['variant_types']['buckets']
            },
            "chromosomes": {
                bucket['key']: bucket['doc_count']
                for bucket in agg_response['aggregations']['chromosomes']['buckets']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
