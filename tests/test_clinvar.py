from app.utils.clinvar import clinvar_transform

def test_clinvar_transform_pathogenic():
    assert clinvar_transform("Pathogenic") == "Likely pathogenic/Pathogenic"
    assert clinvar_transform("Pathogenic;Likely pathogenic") == "Likely pathogenic/Pathogenic"
    assert clinvar_transform("Likely pathogenic; Pathogenic") == "Likely pathogenic/Pathogenic"

def test_clinvar_transform_benign():
    assert clinvar_transform("Benign") == "Likely benign/Benign"
    assert clinvar_transform("Benign;Likely benign") == "Likely benign/Benign"

def test_clinvar_transform_vus():
    assert clinvar_transform("Uncertain significance") == "Uncertain significance"

def test_clinvar_transform_conflicting():
    assert clinvar_transform("Conflicting classifications of pathogenicity") == "Conflicting classifications of pathogenicity"

def test_clinvar_transform_mixed_returns_other():
    # If it contains terms from different sets (e.g. Pathogenic AND Benign), it should return "Other"
    # unless it matches Conflicting explicitly.
    # Based on the logic: if terms.issubset(SET_PATHOGENIC) ...
    # So if terms = {"Pathogenic", "Benign"}, it is NOT a subset of SET_PATHOGENIC nor SET_BENIGN.
    # So it falls through to "Other".
    assert clinvar_transform("Pathogenic;Benign") == "Other"

def test_clinvar_transform_empty():
    assert clinvar_transform(None) == "Not provided"
    assert clinvar_transform("") == "Not provided"
    assert clinvar_transform("   ") == "Not provided"
    assert clinvar_transform(";") == "Not provided"
