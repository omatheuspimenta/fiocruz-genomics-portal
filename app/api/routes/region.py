from fastapi import APIRouter, HTTPException, Query
from app.db.elasticsearch import get_es_client
from app.core.config import settings
import re

router = APIRouter()

def validate_region(region: str) -> bool:
    """
    Validate genomic region format (chr:start-end).
    Accepts: '17:100-200', 'chr17:100-200', '17:1,000-2,000'
    """
    pattern = r'^(?:chr)?([0-9]{1,2}|X|Y|MT?):([\d,]+)-([\d,]+)$'
    return bool(re.match(pattern, region.strip(), re.IGNORECASE))

def parse_region(region: str) -> tuple:
    """Parse region string into normalized chromosome, start, end"""
    clean_region = region.replace(',', '').strip()
    match = re.match(r'^(?:chr)?([0-9]{1,2}|X|Y|MT?):(\d+)-(\d+)$', clean_region, re.IGNORECASE)
    if match:
        chrom = match.group(1).upper()
        start = int(match.group(2))
        end = int(match.group(3))
        return chrom, start, end
    return None, None, None

@router.get("/{region}")
async def get_region(
    region: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """
    Get variants in a genomic region.
    Example: /region/17:43000000-43100000
    """
    if not validate_region(region):
        raise HTTPException(
            status_code=400,
            detail="Invalid region format. Expected: CHR:START-END"
        )
    
    chrom, start, end = parse_region(region)
    
    if end - start > 10_000_000:
        raise HTTPException(
            status_code=400,
            detail="Region too large. Maximum size: 10Mb"
        )
    
    try:
        es = await get_es_client()
        possible_chroms = [chrom, f"chr{chrom}"] 
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"terms": {"chromosome.keyword": possible_chroms}},
                        {"range": {"position": {"gte": start, "lte": end}}}
                    ]
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"position": "asc"}]
        }
        
        response = await es.search(index=settings.ES_INDEX, body=query)
        total = response['hits']['total']['value']
        variants = [hit['_source'] for hit in response['hits']['hits']]
        
        return {
            "region": region,
            "chromosome": chrom,
            "start": start,
            "end": end,
            "total_variants": total,
            "page": page,
            "page_size": page_size,
            "variants": variants
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
