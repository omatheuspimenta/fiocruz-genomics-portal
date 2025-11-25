from typing import Optional

# Define ClinVar values
SET_PATHOGENIC = {
    "Pathogenic", "Likely pathogenic", 
    "Pathogenic/Likely pathogenic", "Likely pathogenic/Pathogenic"
}
SET_BENIGN = {
    "Benign", "Likely benign", 
    "Benign/Likely benign", "Likely benign/Benign"
}
SET_VUS = {"Uncertain significance"}
SET_CONFLICTING = {"Conflicting classifications of pathogenicity"}
SET_DRUG = {"drug response"}
SET_AFFECTS = {"Affects"}
SET_PROTECTIVE = {"protective"}
SET_LOW_PENETRANCE = {
    "Pathogenic/Likely pathogenic/Pathogenic, low penetrance",
    "Pathogenic/Pathogenic, low penetrance",
    "Likely risk allele",
    "Uncertain risk allele",
    "Uncertain significance/Uncertain risk allele"
}
SET_NOT_PROVIDED = {"not provided", "NA", "", "nan"}
SET_ASSOCIATION = {"association"}
SET_RISK_FACTOR = {"risk factor"}

def clinvar_transform(clinvar_value: Optional[str]) -> str:
    """
    Transformation of ClinVar string to consensus classification.
    Input: 'Pathogenic;Likely pathogenic'
    Output: 'Likely pathogenic/Pathogenic'
    Args:
        clinvar_value (str): Semicolon-separated ClinVar significance terms.
    Returns:
        str: Consensus classification.
    """
    # Exit for empty/None values
    if not clinvar_value:
        return "Not provided"

    # Splits the string, strips whitespace, and creates a set of unique terms.
    terms = {term.strip() for term in clinvar_value.split(';') if term.strip()}
    
    # If cleaning resulted in an empty set (e.g. input was "; "), return Not Provided
    if not terms:
        return "Not provided"

    # Classification Logic using Set Operations
    
    if terms.issubset(SET_PATHOGENIC):
        return "Likely pathogenic/Pathogenic"
        
    if terms.issubset(SET_BENIGN):
        return "Likely benign/Benign"
        
    if terms.issubset(SET_VUS):
        return "Uncertain significance"
        
    if terms.issubset(SET_CONFLICTING):
        return "Conflicting classifications of pathogenicity"
        
    if terms.issubset(SET_DRUG):
        return "Drug response"
        
    if terms.issubset(SET_AFFECTS):
        return "Affects a non-disease phenotype"
        
    if terms.issubset(SET_PROTECTIVE):
        return "Protective"
        
    if terms.issubset(SET_LOW_PENETRANCE):
        return "Low penetrance for Mendelian diseases"
        
    if terms.issubset(SET_NOT_PROVIDED):
        return "Not provided"
        
    if terms.issubset(SET_ASSOCIATION):
        return "GWAS hits"
        
    if terms.issubset(SET_RISK_FACTOR):
        return "Risk factor"

    return "Other"
