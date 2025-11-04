import hail as hl
import pandas as pd
import json
import gzip
import time

# --- Parameters ---
# Your gzipped JSON annotation file
ANNOTATION_JSON_PATH = '../data/NA12878.bed.filtered.json.gz' 
# The output Hail Table
HAIL_TABLE_OUT_PATH = '../data/illumina_annotations.ht'
REFERENCE_GENOME = 'GRCh38'

LOG_PATH = '../logs/hail'
# ---

print("Initializing Hail...")
hl.init(app_name='Parse Illumina JSON', log=LOG_PATH, default_reference=REFERENCE_GENOME)

print(f"Loading and parsing JSON: {ANNOTATION_JSON_PATH}")
print("This may take several minutes for a large file...")
start_time = time.time()

# 1. Load the entire gzipped JSON file in Python
# We use gzip.open to read the .gz file directly
with gzip.open(ANNOTATION_JSON_PATH, 'rt', encoding='utf-8') as f:
    data = json.load(f)

print(f"JSON loaded in {time.time() - start_time:.2f} seconds.")

# 2. Use pandas.json_normalize to flatten the nested data
# We "dive" into the 'positions' list, then into the 'variants' list inside each position
# We keep 'position' and 'chromosome' from the parent 'positions' level
df = pd.json_normalize(
    data['positions'],
    record_path=['variants'], # Explode the 'variants' list
    meta=['position'] # Keep these fields from the 'positions' level
)

print(f"Parsed {len(df):,} variants into pandas DataFrame.")
print("DataFrame columns (sample):", df.columns.tolist()[:15])

# --- SOLUTION: Convert complex columns to JSON strings ---
print("\n--- Applying fix: Converting complex columns to JSON strings ---")

# We know these columns are simple strings
simple_string_cols = ['vid', 'chromosome', 'refAllele', 'altAllele', 'variantType', 'hgvsg']

# Find all columns that are 'object' type and are NOT simple strings
object_cols = df.select_dtypes(include=['object']).columns
cols_to_convert = [col for col in object_cols if col not in simple_string_cols]

# Also find columns that pandas parsed as lists/dicts but not 'object'
# This checks the first non-null value's type to find list/dict columns
for col in df.columns:
    if col in cols_to_convert or col in simple_string_cols or col.startswith('gnomad.'):
        continue # Skip already-found columns and gnomad flat fields
        
    # Get the first non-null value to check its type
    first_val_series = df[col].dropna()
    if not first_val_series.empty:
        first_val = first_val_series.iloc[0]
        if isinstance(first_val, (list, dict)):
            if col not in cols_to_convert:
                cols_to_convert.append(col)

print(f"Found complex list/dict columns to convert: {cols_to_convert}")

def safe_json_dumps(row):
    """Safely convert list/dict to JSON string, pass others as None"""
    if isinstance(row, (list, dict)):
        return json.dumps(row)
    # Return None for NaN, None, or other types
    return None

for col in cols_to_convert:
    if col in df.columns:
        print(f"Converting column '{col}'...")
        # Apply the conversion
        df[col] = df[col].apply(safe_json_dumps)
        # After conversion, fill any remaining NaNs with None
        df[col] = df[col].where(pd.notnull(df[col]), None)

print("Pandas conversion complete.")
# --- END SOLUTION ---

print("\nConverting to Hail Table (with fix)...")
# This will now succeed because all complex types are just strings
ht = hl.Table.from_pandas(df)
print("Conversion to Hail Table successful!")

# 4. Create the necessary keys for joining
print("Adding locus and alleles keys...")
ht = ht.annotate(
    locus=hl.locus(ht.chromosome, ht.position, reference_genome=REFERENCE_GENOME)
)
ht = ht.annotate(
    alleles=[ht.refAllele, ht.altAllele]
)

# --- NEW STEP: Parse the JSON strings back in Hail ---
print("Parsing stringified JSON columns back into Hail structs...")

# We need to re-parse the columns we stringified.
# We tell Hail to parse them as JSON, and it will infer the schema.
annotations_to_parse = {}
for col in cols_to_convert:
    if col in ht.row:
        print(f"Setting up parser for '{col}'...")
        # We use hl.parse_json. Hail infers the complex type.
        # This creates a new column (or overwrites the old) with the correct Hail type
        annotations_to_parse[col] = hl.parse_json(ht[col]) 

# Apply all parsers at once
if annotations_to_parse:
    ht = ht.annotate(**annotations_to_parse)
print("Hail parsing complete.")
# --- END NEW STEP ---

# 5. Key the table by locus and alleles for fast joining
ht = ht.key_by('locus', 'alleles')

print("Final Hail Table schema:")
ht.describe()

# 6. Write the final table
print(f"Writing Hail Table to: {HAIL_TABLE_OUT_PATH}")
ht.write(HAIL_TABLE_OUT_PATH, overwrite=True)

print(f"--- Done in {time.time() - start_time:.2f} seconds ---")