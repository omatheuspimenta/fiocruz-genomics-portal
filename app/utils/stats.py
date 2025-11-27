from typing import Dict, Any

def get_global_stats_query(query_conditions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds an Elasticsearch query to retrieve global statistics for a set of variants.
    
    Args:
        query_conditions: The 'query' part of the ES body (e.g., {"bool": ...})
    
    Returns:
        A dictionary representing the ES request body with aggregations.
    """
    return {
        "query": query_conditions,
        "size": 0,  # We only want aggregations, not hits
        "aggs": {
            # 1. Variant Types
            "variant_types": {
                "terms": {"field": "variant_type.keyword", "size": 20}
            },
            
            # 2. AF Stats (Min, Max, Avg)
            "gnomad_af_stats": {
                "extended_stats": {"field": "gnomad_af"}
            },
            
            # 3. ClinVar Significance
            "clinvar": {
                "terms": {"field": "clinvar_significance.keyword", "size": 20}
            },
            
            # 4. Consequences
            "consequences": {
                "terms": {"field": "all_consequences.keyword", "size": 20}
            },
            
            # 5. AF Ranges (for Pie Chart)
            "af_ranges": {
                "range": {
                    "field": "gnomad_af",
                    "ranges": [
                        {"to": 0.0001, "key": "Ultra-rare (<0.01%)"},
                        {"from": 0.0001, "to": 0.001, "key": "Rare (0.01-0.1%)"},
                        {"from": 0.001, "to": 0.01, "key": "Low freq (0.1-1%)"},
                        {"from": 0.01, "to": 0.05, "key": "Common (1-5%)"},
                        {"from": 0.05, "key": "Very common (>5%)"}
                    ]
                }
            },
            
            # 6. Population Averages
            "pop_afr": {"avg": {"field": "gnomad_afr_af"}},
            "pop_amr": {"avg": {"field": "gnomad_amr_af"}},
            "pop_eas": {"avg": {"field": "gnomad_eas_af"}},
            "pop_nfe": {"avg": {"field": "gnomad_nfe_af"}},
            "pop_sas": {"avg": {"field": "gnomad_sas_af"}},
            
            # 7. Quality Histogram
            "quality_hist": {
                "range": {
                    "field": "quality",
                    "ranges": [
                        {"to": 30, "key": "<30"},
                        {"from": 30, "to": 100, "key": "30-100"},
                        {"from": 100, "to": 500, "key": "100-500"},
                        {"from": 500, "to": 1000, "key": "500-1000"},
                        {"from": 1000, "key": ">1000"}
                    ]
                }
            },
            
            # 8. Conservation Scores
            "avg_phylop": {"avg": {"field": "phylop_score"}},
            "avg_gerp": {"avg": {"field": "gerp_score"}},
            "avg_dann": {"avg": {"field": "dann_score"}},
            
            # 9. Scatter Plot Data (Sampled)
            # We can't return all points for scatter plot if there are millions.
            # But for gene/region scale (usually < 10k), we might be able to return a subset or simple terms.
            # For now, let's skip complex scatter data aggregation and rely on frontend or separate endpoint if needed.
            # Or we can just return the raw values for the first N variants if we really want, but that's what search is for.
            # The frontend currently maps `filteredVariants` for scatter. 
            # If we want GLOBAL scatter, we'd need all data. 
            # Let's stick to aggregations for now.
        }
    }

def format_stats_response(agg_response: Dict[str, Any], total_count: int) -> Dict[str, Any]:
    """
    Formats the ES aggregation response into a clean statistics object for the frontend.
    """
    aggs = agg_response['aggregations']
    
    # Format Pie Data
    pie_data = [
        {"name": bucket['key'], "value": bucket['doc_count']}
        for bucket in aggs['af_ranges']['buckets']
        if bucket['doc_count'] > 0
    ]
    # Sort by value desc
    pie_data.sort(key=lambda x: x['value'], reverse=True)
    
    # Format Population Data
    pop_data = [
        {"name": "AFR", "val": aggs['pop_afr']['value'] or 0},
        {"name": "AMR", "val": aggs['pop_amr']['value'] or 0},
        {"name": "EAS", "val": aggs['pop_eas']['value'] or 0},
        {"name": "NFE", "val": aggs['pop_nfe']['value'] or 0},
        {"name": "SAS", "val": aggs['pop_sas']['value'] or 0},
    ]
    
    # Format Variant Types
    variant_type_data = [
        {"name": bucket['key'], "value": bucket['doc_count']}
        for bucket in aggs['variant_types']['buckets']
    ]
    
    # Format Quality Distribution
    quality_dist = [
        {"name": bucket['key'], "value": bucket['doc_count']}
        for bucket in aggs['quality_hist']['buckets']
    ]
    
    # Format Conservation Data
    conservation_data = [
        {"name": "PHYLOP", "avg": aggs['avg_phylop']['value'] or 0},
        {"name": "GERP", "avg": aggs['avg_gerp']['value'] or 0},
        {"name": "DANN", "avg": aggs['avg_dann']['value'] or 0},
    ]
    
    return {
        "count": total_count,
        "uniqueTypes": len(variant_type_data),
        "meanAF": aggs['gnomad_af_stats']['avg'] or 0,
        "maxAF": aggs['gnomad_af_stats']['max'] or 0,
        "clinvarCount": sum(b['doc_count'] for b in aggs['clinvar']['buckets']),
        "pieData": pie_data,
        "popData": pop_data,
        "variantTypeData": variant_type_data,
        "qualityDist": quality_dist,
        "conservationData": conservation_data,
        "coverage": "100%" # Since this is global stats
    }
