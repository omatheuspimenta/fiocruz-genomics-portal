import hail as hl
import pandas as pd

# Initialize Hail
hl.init(quiet=True, log='../logs/hail')

# Read the matrix table
mt = hl.read_matrix_table('/home/matheus/Documents/gnomeAD-tb/data/multisample_espanha.mt')

print("="*60)
print("MATRIX TABLE STRUCTURE")
print("="*60)
mt.describe()

print("\n" + "="*60)
print("INFO FIELD STRUCTURE")
print("="*60)
print(mt.info.dtype)
print("\nAvailable INFO fields:")
info_fields = list(mt.info.dtype.fields)
print(info_fields)

print("\n" + "="*60)
print("SAMPLE DATA - First 5 variants")
print("="*60)

# Get first 5 variants with their full info
sample = mt.rows().head(5)
sample_df = sample.to_pandas()

print("\nFull row data for first variant:")
print(sample_df.iloc[0].to_dict())

# Check if there are any entries (genotype calls)
print("\n" + "="*60)
print("GENOTYPE DATA CHECK")
print("="*60)
print(f"Number of samples (columns): {mt.count_cols()}")
print(f"Number of variants (rows): {mt.count_rows()}")

# Check if GT field exists
if 'GT' in mt.entry.dtype.fields:
    print("✅ Genotype (GT) field exists")
    
    # Sample some genotypes
    sample_gt = mt.GT.take(10)
    print(f"\nSample genotypes: {sample_gt}")
else:
    print("❌ No genotype (GT) field found")
    print("Available entry fields:", list(mt.entry.dtype.fields))

print("\n" + "="*60)
print("FINDING EXAMPLE VARIANTS")
print("="*60)

# Get variants table
variants = mt.rows()

# Try to find variants with rsID
variants_with_rsid = variants.filter(hl.is_defined(variants.rsid))
print(f"\nVariants with rsID: {variants_with_rsid.count()}")

if variants_with_rsid.count() > 0:
    print("\n5 example variants with rsID:")
    examples_with_rsid = variants_with_rsid.head(5).to_pandas()
    print(examples_with_rsid[['chrom', 'pos', 'ref', 'alleles', 'rsid']])

# Get variants from different chromosomes
print("\n" + "="*60)
print("VARIANTS BY CHROMOSOME (first from each)")
print("="*60)

for chrom in ['1', '2', 'X', 'MT']:
    chrom_variants = variants.filter(variants.locus.contig == chrom)
    count = chrom_variants.count()
    if count > 0:
        example = chrom_variants.head(1).to_pandas()
        print(f"\nChr {chrom}: {count} variants")
        print(f"  Example: {chrom}:{example['pos'].iloc[0]} {example['ref'].iloc[0]}>{example['alleles'].iloc[0][1]}")
        if 'rsid' in example.columns and pd.notna(example['rsid'].iloc[0]):
            print(f"  rsID: {example['rsid'].iloc[0]}")

print("\n" + "="*60)
print("CHECKING FOR GENE ANNOTATIONS")
print("="*60)

# Check if VEP or other gene annotations exist
has_vep = 'vep' in info_fields
has_csq = 'CSQ' in info_fields
has_ann = 'ANN' in info_fields

print(f"VEP annotation: {'✅' if has_vep else '❌'}")
print(f"CSQ annotation: {'✅' if has_csq else '❌'}")
print(f"ANN annotation: {'✅' if has_ann else '❌'}")

if has_vep:
    # Try to extract gene names from VEP
    print("\nExtracting genes from VEP field...")
    vep_sample = variants.head(100)
    vep_df = vep_sample.select('locus', 'alleles', 'rsid', vep=variants.info.vep).to_pandas()
    
    # Look for gene names in VEP
    genes_found = set()
    for idx, row in vep_df.iterrows():
        if pd.notna(row['vep']) and len(row['vep']) > 0:
            # VEP format is usually: Allele|Gene|Feature|...
            for vep_entry in row['vep']:
                if '|' in vep_entry:
                    parts = vep_entry.split('|')
                    if len(parts) > 1 and parts[1]:  # Gene symbol usually in position 1
                        genes_found.add(parts[1])
    
    if genes_found:
        print(f"\nFound {len(genes_found)} unique genes in first 100 variants")
        print(f"Example genes: {list(genes_found)[:10]}")
    else:
        print("\nNo gene names found in VEP annotation")
        print("Sample VEP entry:")
        if len(vep_df) > 0 and pd.notna(vep_df['vep'].iloc[0]):
            print(vep_df['vep'].iloc[0][:3] if isinstance(vep_df['vep'].iloc[0], list) else vep_df['vep'].iloc[0])

elif has_csq or has_ann:
    ann_field = 'CSQ' if has_csq else 'ANN'
    print(f"\nExtracting genes from {ann_field} field...")
    ann_sample = variants.head(100)
    ann_df = ann_sample.select('locus', 'alleles', ann=variants.info[ann_field]).to_pandas()
    print("Sample annotation:")
    if len(ann_df) > 0:
        print(ann_df['ann'].iloc[0])

print("\n" + "="*60)
print("RECOMMENDATIONS FOR SEARCHING")
print("="*60)

# Provide specific search examples based on the data
variants_sample = variants.head(10).to_pandas()

print("\n📍 VARIANT SEARCH EXAMPLES:")
for idx in range(min(3, len(variants_sample))):
    row = variants_sample.iloc[idx]
    chrom = row['chrom']
    pos = row['pos']
    ref = row['ref']
    alt = row['alleles'][1] if len(row['alleles']) > 1 else 'N/A'
    
    print(f"\nExample {idx + 1}:")
    print(f"  Position format: {chrom}:{pos}")
    print(f"  Full variant: {chrom}-{pos}-{ref}-{alt}")
    if 'rsid' in row and pd.notna(row['rsid']):
        print(f"  rsID: {row['rsid']}")

print("\n🧬 REGION SEARCH EXAMPLES:")
print(f"  Chr 1, first 100kb: 1:1-100000")
print(f"  Chr X: X:1000000-2000000")

if has_vep and genes_found:
    print("\n🔬 GENE SEARCH:")
    print(f"  Try these genes: {', '.join(list(genes_found)[:5])}")
else:
    print("\n⚠️  Gene search may not work - no gene annotations found")