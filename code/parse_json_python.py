import gzip
from typing import Any, Dict, Generator, List, Optional
import sys
import ijson
import pandas as pd
import pydantic
import hail as hl
pd.set_option('display.max_columns', None)

from decimal import Decimal
import numpy as np

HAIL_SCHEMA = {
    'chromosome': hl.tstr,
    'position': hl.tint32,
    'ref': hl.tstr,
    'alt': hl.tstr,
    'vid': hl.tstr,
    # floats (AF fields)
    'gnomad_af': hl.tfloat64,
    'gnomad_exome_af': hl.tfloat64,
    'gnomad_afr_af': hl.tfloat64,
    'gnomad_amr_af': hl.tfloat64,
    'gnomad_eas_af': hl.tfloat64,
    'gnomad_fin_af': hl.tfloat64,
    'gnomad_nfe_af': hl.tfloat64,
    'gnomad_asj_af': hl.tfloat64,
    'gnomad_sas_af': hl.tfloat64,
    'gnomad_oth_af': hl.tfloat64,
    # transcript summaries
    'n_transcripts': hl.tint32,
}


def _convert_for_hail(obj):
    """Recursively convert Decimal and numpy types to plain Python types Hail accepts."""
    if isinstance(obj, dict):
        return {k: _convert_for_hail(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_for_hail(v) for v in obj]
    if isinstance(obj, Decimal):
        # choose float or str depending on required precision
        return float(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    # leave None, str, bool, int, float as-is
    return obj

class BaseClass(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow')

    def get_top_level(self) -> pd.DataFrame:
        return pd.json_normalize(self.get_top_level_dict())

    def get_top_level_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def to_df(self, key: str = "") -> pd.DataFrame:
        if not key:
            return pd.json_normalize(self.model_dump())

        values = self.model_dump().get(key)

        if isinstance(values, list):
            merged = [self.get_top_level_dict() | value for value in values]
        else:
            merged = [self.get_top_level_dict() | {key: values}]

        return pd.json_normalize(merged)


class Transcript(BaseClass):
    transcript: str
    source: str
    bioType: Optional[str] = None
    geneId: Optional[str] = None
    hgnc: Optional[str] = None
    consequence: Optional[List[str]] = None
    impact: Optional[str] = None
    isCanonical: Optional[bool] = None

    def get_top_level_dict(self) -> Dict[str, Any]:
        return dict(zip(("transcript", "isCanonical"), (self.transcript, self.isCanonical)))


class Variant(BaseClass):
    vid: str
    chromosome: str
    begin: int
    end: int
    refAllele: str
    altAllele: str
    variantType: Optional[str] = None
    hgvsg: Optional[str] = None
    phylopScore: Optional[float] = None
    phyloPPrimateScore: Optional[float] = None
    transcripts: Optional[List[Transcript]] = None

    def get_top_level_dict(self) -> Dict[str, Any]:
        return dict(
            zip(
                ("chromosome", "begin", "end", "refAllele", "altAllele", "hgvsg"),
                (self.chromosome, self.begin, self.end, self.refAllele, self.altAllele, self.hgvsg),
            )
        )


class Position(BaseClass):
    chromosome: str
    position: int
    refAllele: str
    altAlleles: List[str]
    filters: Optional[List[str]] = None
    mappingQuality: Optional[float] = None
    cytogeneticBand: Optional[str] = None
    vcfInfo: Optional[Dict[str, Any]] = None
    samples: Optional[List[Dict[str, Any]]] = None
    variants: Optional[List[Variant]] = None

    def get_top_level_dict(self) -> Dict[str, Any]:
        return dict(
            zip(
                (
                    "chromosome",
                    "position",
                    "refAllele",
                    "altAlleles",
                    "filters",
                    "mappingQuality",
                    "cytogeneticBand",
                    "vcfInfo",
                ),
                (
                    self.chromosome,
                    self.position,
                    self.refAllele,
                    self.altAlleles,
                    self.filters,
                    self.mappingQuality,
                    self.cytogeneticBand,
                    self.vcfInfo,
                ),
            )
        )


class AnnotatedData:
    def __init__(self, filename: str):
        self._filename = filename

        for key in ("annotator", "genomeAssembly", "creationTime"):
            print(f"{key}: {self.header[key]}")

    @property
    def header(self) -> Dict[str, Any]:
        with gzip.open(self._filename, 'r') as f:
            return next(ijson.items(f, "header"))

    @property
    def data_sources(self) -> pd.DataFrame:
        return pd.DataFrame(self.header["dataSources"]).set_index("name").sort_index()

    @property
    def genes(self) -> pd.DataFrame:
        with gzip.open(self._filename, 'r') as f:
            return pd.json_normalize(ijson.items(f, "genes.item"))

    @property
    def positions(self) -> Any:
        f = gzip.open(self._filename, 'r')
        return ijson.items(f, "positions.item")

    def get_annotation(self, chromosome: str, position: int) -> Dict[str, Any]:
        annotation = next(
            (
                position_item
                for position_item in self.positions
                if chromosome == position_item.get("chromosome") and position == position_item.get("position")
            ),
            {},
        )
        
        if not annotation:
            raise Exception(f"Cannot find annotation for {chromosome=} and {position=}")
            
        return annotation

    def get_annotation_range(self, chromosome: str, position: int, end: int) -> Generator[Any, Any, None]:
        return (
            position_item
            for position_item in self.positions
            if chromosome == position_item.get("chromosome") and position <= position_item.get("position") <= end
        )

    @staticmethod
    def multiple_to_df(items: List[BaseClass], key: str = "") -> pd.DataFrame:
        return pd.concat((item.to_df(key) for item in items))

class Parser:
    def __init__(self, annotated_data: AnnotatedData):
        self.annotated_data = annotated_data

    def get_variants_above_gnomad_freq(
        self,
        frequency_key: str,
        frequency_threshold_low: float = float("-inf"),
        frequency_threshold_high: float = float("inf"),
    ) -> Generator[Any, Any, None]:
        positions = (
            Position.model_validate(position)
            for position in self.annotated_data.positions
            for variant in position.get("variants", {})
            if (freq := variant.get("gnomad", {}).get(frequency_key, None))
            and frequency_threshold_low < freq < frequency_threshold_high
        )
        return positions

    def get_positions_with_cannonical_transcripts(self) -> Generator[Any, Any, None]:
        positions = (
            Position.model_validate(position)
            for position in self.annotated_data.positions
            for variant in position.get("variants", {})
            for transcript in variant.get("transcripts", [])
            if transcript.get("isCanonical")
        )

        return positions

    def filter_transcripts_by_consequence(
        self, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None
    ) -> Generator[Any, Any, None]:
        if not exclude:
            exclude = []

        if not include:
            include = []

        positions = (
            Position.model_validate(position)
            for position in self.annotated_data.positions
            for variant in position.get("variants", {})
            for transcript in variant.get("transcripts", [])
            for consequence in transcript.get("consequence", [])
            if (not bool(include) or consequence in include) and consequence not in exclude
        )
        return positions

######
"""
Convert Nirvana JSON to Hail Table using the PROVIDED Pydantic parser
"""
def variant_to_dict(
    position: Position,
    variant: Variant,
    include_transcripts: bool = True
) -> Dict[str, Any]:
    """
    Convert a Pydantic Variant object to a dictionary for Hail
    
    Parameters:
    -----------
    position : Position
        Position object containing variant
    variant : Variant
        Variant object to convert
    include_transcripts : bool
        Whether to include transcripts as nested array
    """
    # Get variant dict from Pydantic model
    variant_dict = variant.model_dump()
    
    # Base record with position info
    record = {
        # Locus
        'chromosome': position.chromosome,
        'position': position.position,
        'ref': position.refAllele,
        'alt': variant.altAllele,
        
        # Variant identifiers
        'vid': variant.vid,
        'hgvsg': variant.hgvsg,
        'variant_type': variant.variantType,
        'begin': variant.begin,
        'end': variant.end,
        
        # Position-level quality
        'filters': ','.join(position.filters) if position.filters else None,
        'mapping_quality': position.mappingQuality,
        'fisher_strand_bias': variant_dict.get('fisherStrandBias'),
        'quality': variant_dict.get('quality'),
        'cytogenetic_band': position.cytogeneticBand,
        
        # Conservation scores
        'phylop_score': variant.phylopScore,
        'phylop_primate_score': variant.phyloPPrimateScore,
        'gerp_score': variant_dict.get('gerpScore'),
        'dann_score': variant_dict.get('dannScore'),
    }
    
    # Extract dbSNP ID
    dbsnp = variant_dict.get('dbsnp', {})
    if dbsnp and isinstance(dbsnp, dict):
        rsids = dbsnp.get('ids', [])
        record['rsid'] = rsids[0] if rsids else None
    else:
        record['rsid'] = None
    
    # Extract gnomAD genome frequencies
    gnomad = variant_dict.get('gnomad', {})
    if gnomad:
        record.update({
            'gnomad_af': gnomad.get('allAf'),
            'gnomad_ac': gnomad.get('allAc'),
            'gnomad_an': gnomad.get('allAn'),
            'gnomad_hc': gnomad.get('allHc'),
            'gnomad_afr_af': gnomad.get('afrAf'),
            'gnomad_amr_af': gnomad.get('amrAf'),
            'gnomad_eas_af': gnomad.get('easAf'),
            'gnomad_fin_af': gnomad.get('finAf'),
            'gnomad_nfe_af': gnomad.get('nfeAf'),
            'gnomad_asj_af': gnomad.get('asjAf'),
            'gnomad_sas_af': gnomad.get('sasAf'),
            'gnomad_oth_af': gnomad.get('othAf'),
            'gnomad_failed_filter': gnomad.get('failedFilter'),
        })
    
    # Extract gnomAD exome frequencies
    gnomad_exome = variant_dict.get('gnomad-exome', {})
    if gnomad_exome:
        record.update({
            'gnomad_exome_af': gnomad_exome.get('allAf'),
            'gnomad_exome_ac': gnomad_exome.get('allAc'),
            'gnomad_exome_an': gnomad_exome.get('allAn'),
            'gnomad_exome_hc': gnomad_exome.get('allHc'),
            'gnomad_exome_failed_filter': gnomad_exome.get('failedFilter'),
        })
    
    # Extract TOPMed frequencies
    topmed = variant_dict.get('topmed', {})
    if topmed:
        record.update({
            'topmed_af': topmed.get('allAf'),
            'topmed_ac': topmed.get('allAc'),
            'topmed_an': topmed.get('allAn'),
            'topmed_hc': topmed.get('allHc'),
            'topmed_failed_filter': topmed.get('failedFilter'),
        })
    
    # Extract ClinVar if present
    clinvar = variant_dict.get('clinvar', {})

    if clinvar:
        if isinstance(clinvar, dict):
            record['clinvar_significance'] = (
                ";".join(clinvar['significance'])
                if isinstance(clinvar.get('significance'), list)
                else clinvar.get('significance')
            )
            record['clinvar_id'] = (
                ";".join(map(str, clinvar['id']))
                if isinstance(clinvar.get('id'), list)
                else str(clinvar.get('id'))
            )
    
        elif isinstance(clinvar, list):
            record['clinvar_significance'] = ";".join(
                ";".join(map(str, c.get('significance')))
                if isinstance(c.get('significance'), list)
                else str(c.get('significance', ''))
                for c in clinvar if isinstance(c, dict)
            )
            record['clinvar_id'] = ";".join(
                ";".join(map(str, c.get('id')))
                if isinstance(c.get('id'), list)
                else str(c.get('id', ''))
                for c in clinvar if isinstance(c, dict)
            )

    
    # Include transcripts as nested structure
    if include_transcripts and variant.transcripts:
        record['transcripts'] = [
            {
                'transcript_id': t.transcript,
                'source': t.source,
                'bio_type': t.bioType,
                'gene_id': t.geneId,
                'hgnc': t.hgnc,
                'consequences': t.consequence if t.consequence else [],
                'impact': t.impact,
                'is_canonical': t.isCanonical if t.isCanonical else False,
            }
            for t in variant.transcripts
        ]
        record['n_transcripts'] = len(variant.transcripts)
    else:
        record['transcripts'] = []
        record['n_transcripts'] = 0
    
    # Include sample genotypes if present
    if position.samples:
        record['samples'] = [
            {
                'genotype': s.get('genotype'),
                'variant_frequencies': s.get('variantFrequencies', []),
                'total_depth': s.get('totalDepth'),
                'genotype_quality': s.get('genotypeQuality'),
                'allele_depths': s.get('alleleDepths', []),
            }
            for s in position.samples
        ]
    else:
        record['samples'] = None
    
    return record


def convert_nirvana_to_hail(
    nirvana_json_file: str,
    output_path: str,
    max_positions: Optional[int] = None,
    batch_size: int = 5000,
) -> hl.Table:
    """
    Convert Nirvana JSON to Hail Table using the provided Pydantic parser
    
    Parameters:
    -----------
    nirvana_json_file : str
        Path to Nirvana JSON.gz file
    output_path : str
        Path to save Hail Table
    max_positions : int, optional
        Limit number of positions to process (for testing)
    batch_size : int
        Number of variants to accumulate before creating intermediate table
    """
    
    print(f"Loading Nirvana data from {nirvana_json_file}...")
    annotated_data = AnnotatedData(filename=nirvana_json_file)
    
    print("\nData sources:")
    print(annotated_data.data_sources)
    
    print("\nProcessing positions...")
    all_records = []
    position_count = 0
    variant_count = 0
    batch_tables = []
    
    # Stream through positions using the parser's generator
    for position_dict in annotated_data.positions:
        if position_count % 1000 == 0 and position_count > 0:
            print(f"  Processed {position_count} positions, {variant_count} variants...")

        
        # Use Pydantic to validate and parse
        position = Position.model_validate(position_dict)
        
        # Process each variant in this position
        if position.variants:
            for variant in position.variants:
                record = variant_to_dict(position, variant, include_transcripts=True)
                all_records.append(record)
                variant_count += 1
                
                # Create intermediate table when batch is full
                if len(all_records) >= batch_size:
                    print(f"  Creating batch table with {len(all_records)} variants...")
                    all_records_clean = [_convert_for_hail(r) for r in all_records]
                    batch_ht = hl.Table.parallelize(all_records_clean, partial_type=HAIL_SCHEMA)
                    print("  Annotating locus and alleles...")
                    batch_ht = batch_ht.annotate(
                        locus=hl.locus(batch_ht.chromosome, batch_ht.position, reference_genome='GRCh38'),
                        alleles=hl.array([batch_ht.ref, batch_ht.alt])
                    )
                    batch_tables.append(batch_ht)
                    all_records = []
        
        position_count += 1
        
        # Stop if max_positions reached
        if max_positions and position_count >= max_positions:
            print(f"Reached max_positions limit of {max_positions}")
            break
    
    # Process remaining records
    if all_records:
        print(f"  Creating final batch with {len(all_records)} variants...")
        all_records_clean = [_convert_for_hail(r) for r in all_records]
        batch_ht = hl.Table.parallelize(all_records_clean)
        batch_ht = batch_ht.annotate(
            locus=hl.locus(batch_ht.chromosome, batch_ht.position, reference_genome='GRCh38'),
            alleles=hl.array([batch_ht.ref, batch_ht.alt])
        )
        batch_tables.append(batch_ht)
    
    print(f"\nTotal: {position_count} positions, {variant_count} variants")
    
    # Union all batch tables
    print("Combining batches...")
    if len(batch_tables) == 1:
        ht = batch_tables[0]
    else:
        ht = batch_tables[0].union(*batch_tables[1:])
    
    # Key by locus and alleles
    print("Setting key (locus, alleles)...")
    ht = ht.key_by(ht.locus, ht.alleles)
    
    # Add computed annotations
    print("Adding computed annotations...")
    ht = ht.annotate(
        # Maximum gnomAD AF across genome and exome
        max_gnomad_af=hl.max(
            hl.array([ht.gnomad_af, ht.gnomad_exome_af]).filter(hl.is_defined)
        ),
        
        # Maximum population-specific AF
        max_pop_af=hl.max(
            hl.array([
                ht.gnomad_afr_af, ht.gnomad_amr_af, ht.gnomad_eas_af,
                ht.gnomad_fin_af, ht.gnomad_nfe_af, ht.gnomad_asj_af,
                ht.gnomad_sas_af, ht.gnomad_oth_af
            ]).filter(hl.is_defined)
        ),
        
        # Get canonical transcript (if exists)
        canonical_transcript=hl.or_missing(
            hl.len(ht.transcripts) > 0,
            ht.transcripts.filter(lambda t: t.is_canonical)[0]
        ),
        
        # All unique consequences across transcripts
        all_consequences=hl.set(
            hl.flatten(ht.transcripts.map(lambda t: t.consequences))
        ),
        
        # Gene symbols from transcripts
        genes=hl.set(
            ht.transcripts.map(lambda t: t.hgnc).filter(hl.is_defined)
        ),
    )
    
    # Write to disk
    print(f"\nWriting Hail Table to {output_path}...")
    ht = ht.checkpoint(output_path, overwrite=True)
    
    # Summary
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    print(f"Output: {output_path}")
    print(f"Total variants: {ht.count()}")
    print("\nSchema:")
    ht.describe()
    
    return ht


def create_transcript_exploded_table(
    nirvana_json_file: str,
    output_path: str,
    max_positions: Optional[int] = None,
) -> hl.Table:
    """
    Create table with one row per variant-transcript combination
    Uses the provided Pydantic parser
    """
    print(f"Loading Nirvana data from {nirvana_json_file}...")
    annotated_data = AnnotatedData(filename=nirvana_json_file)
    
    print("Processing positions (transcript-exploded mode)...")
    all_records = []
    position_count = 0
    
    for position_dict in annotated_data.positions:
        if position_count % 1000 == 0 and position_count > 0:
            print(f"  Processed {position_count} positions, {len(all_records)} transcript records...")
        
        position = Position.model_validate(position_dict)
        
        if position.variants:
            for variant in position.variants:
                # Base variant info
                base_record = {
                    'chromosome': position.chromosome,
                    'position': position.position,
                    'ref': position.refAllele,
                    'alt': variant.altAllele,
                    'vid': variant.vid,
                    'variant_type': variant.variantType,
                    'hgvsg': variant.hgvsg,
                    'gnomad_af': variant.model_dump().get('gnomad', {}).get('allAf'),
                    'gnomad_exome_af': variant.model_dump().get('gnomad-exome', {}).get('allAf'),
                    'phylop_score': variant.phylopScore,
                    'gerp_score': variant.model_dump().get('gerpScore'),
                }
                
                # Explode by transcript
                if variant.transcripts:
                    for trans in variant.transcripts:
                        record = base_record.copy()
                        record.update({
                            'transcript_id': trans.transcript,
                            'gene_id': trans.geneId,
                            'hgnc': trans.hgnc,
                            'source': trans.source,
                            'bio_type': trans.bioType,
                            'consequences': trans.consequence if trans.consequence else [],
                            'impact': trans.impact,
                            'is_canonical': trans.isCanonical if trans.isCanonical else False,
                        })
                        all_records.append(record)
                else:
                    # Variant without transcripts
                    all_records.append(base_record)
        
        position_count += 1
        if max_positions and position_count >= max_positions:
            break
    
    print(f"Creating Hail Table with {len(all_records)} transcript records...")
    ht = hl.Table.parallelize(all_records)
    
    ht = ht.annotate(
        locus=hl.locus(ht.chromosome, ht.position, reference_genome='GRCh38'),
        alleles=hl.array([ht.ref, ht.alt])
    )
    
    # Key by locus, alleles, and transcript
    ht = ht.key_by(ht.locus, ht.alleles, ht.transcript_id)
    
    print(f"Writing to {output_path}...")
    ht = ht.checkpoint(output_path, overwrite=True)
    
    print(f"\nDone! Total transcript records: {ht.count()}")
    return ht


# Example usage
if __name__ == "__main__":
    hl.init()
    print("Spark master:", hl.default_reference().name)
    print("Default parallelism:", hl.spark_context().defaultParallelism)
    
    json_file = "/home/matheus/Documents/gnomeAD-tb/data/NA12878.bed.filtered.json.gz"
    
    print("="*60)
    print("VARIANT-LEVEL TABLE (one row per variant)")
    print("="*60)
    
    # Create variant-level table
    ht = convert_nirvana_to_hail(
        nirvana_json_file=json_file,
        output_path="nirvana_variants.ht",
        max_positions=None,  # Use None for all data, or a number for testing
        batch_size=5000,
    )
    
    # Example queries
    print("\n" + "="*60)
    print("EXAMPLE QUERIES")
    print("="*60)
    
    print("\n1. First 5 variants:")
    ht.show(5)
    
    print("\n2. Rare variants (gnomAD AF < 0.01):")
    rare = ht.filter(
        (ht.max_gnomad_af < 0.01) | hl.is_missing(ht.max_gnomad_af)
    )
    print(f"   Count: {rare.count()}")
    
    print("\n3. Loss-of-function variants:")
    lof = ht.filter(
        ht.all_consequences.contains('stop_gained') |
        ht.all_consequences.contains('frameshift_variant') |
        ht.all_consequences.contains('splice_donor_variant')
    )
    print(f"   Count: {lof.count()}")
    
    print("\n4. Variants in specific gene (e.g., BRCA1):")
    gene_variants = ht.filter(ht.genes.contains('BRCA1'))
    print(f"   Count: {gene_variants.count()}")
    
    print("\n5. High conservation variants:")
    conserved = ht.filter(
        (ht.phylop_score > 2) & (ht.gerp_score > 2)
    )
    print(f"   Count: {conserved.count()}")
    
    # Uncomment to create transcript-exploded table
    # print("\n" + "="*60)
    # print("TRANSCRIPT-EXPLODED TABLE")
    # print("="*60)
    # ht_transcripts = create_transcript_exploded_table(
    #     nirvana_json_file=json_file,
    #     output_path="nirvana_transcripts.ht",
    # )