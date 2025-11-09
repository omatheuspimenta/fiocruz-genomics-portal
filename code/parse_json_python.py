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
import tempfile
import os

# Define complete Hail schema with proper types
HAIL_SCHEMA = {
    'chromosome': hl.tstr,
    'position': hl.tint32,
    'ref': hl.tstr,
    'alt': hl.tstr,
    'vid': hl.tstr,
    'hgvsg': hl.tstr,
    'variant_type': hl.tstr,
    'begin': hl.tint32,
    'end': hl.tint32,
    
    # Quality metrics
    'filters': hl.tstr,
    'mapping_quality': hl.tfloat64,
    'fisher_strand_bias': hl.tfloat64,
    'quality': hl.tfloat64,
    'cytogenetic_band': hl.tstr,
    
    # Conservation scores
    'phylop_score': hl.tfloat64,
    'phylop_primate_score': hl.tfloat64,
    'gerp_score': hl.tfloat64,
    'dann_score': hl.tfloat64,
    
    # dbSNP
    'rsid': hl.tstr,
    
    # gnomAD genome frequencies
    'gnomad_af': hl.tfloat64,
    'gnomad_ac': hl.tint32,
    'gnomad_an': hl.tint32,
    'gnomad_hc': hl.tint32,
    'gnomad_afr_af': hl.tfloat64,
    'gnomad_amr_af': hl.tfloat64,
    'gnomad_eas_af': hl.tfloat64,
    'gnomad_fin_af': hl.tfloat64,
    'gnomad_nfe_af': hl.tfloat64,
    'gnomad_asj_af': hl.tfloat64,
    'gnomad_sas_af': hl.tfloat64,
    'gnomad_oth_af': hl.tfloat64,
    'gnomad_failed_filter': hl.tbool,
    
    # gnomAD exome frequencies
    'gnomad_exome_af': hl.tfloat64,
    'gnomad_exome_ac': hl.tint32,
    'gnomad_exome_an': hl.tint32,
    'gnomad_exome_hc': hl.tint32,
    'gnomad_exome_failed_filter': hl.tbool,
    
    # TOPMed
    'topmed_af': hl.tfloat64,
    'topmed_ac': hl.tint32,
    'topmed_an': hl.tint32,
    'topmed_hc': hl.tint32,
    'topmed_failed_filter': hl.tbool,
    
    # ClinVar
    'clinvar_significance': hl.tstr,
    'clinvar_id': hl.tstr,
    
    # Transcript count
    'n_transcripts': hl.tint32,
    
    # Transcripts - nested structure
    'transcripts': hl.tarray(hl.tstruct(
        transcript_id=hl.tstr,
        source=hl.tstr,
        bio_type=hl.tstr,
        gene_id=hl.tstr,
        hgnc=hl.tstr,
        consequences=hl.tarray(hl.tstr),
        impact=hl.tstr,
        is_canonical=hl.tbool,
    )),
    
    # Samples - nested structure (optional)
    'samples': hl.tarray(hl.tstruct(
        genotype=hl.tstr,
        variant_frequencies=hl.tarray(hl.tfloat64),
        total_depth=hl.tint32,
        genotype_quality=hl.tint32,
        allele_depths=hl.tarray(hl.tint32),
    )),
}


def _convert_for_hail(obj):
    """Recursively convert Decimal and numpy types to plain Python types Hail accepts."""
    if isinstance(obj, dict):
        return {k: _convert_for_hail(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_for_hail(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)): # type: ignore[arg-type]
        return float(obj)
    if isinstance(obj, (np.integer, np.int32, np.int64)): # type: ignore[arg-type]
        return int(obj)
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


def variant_to_dict(
    position: Position,
    variant: Variant,
    include_transcripts: bool = True
) -> Dict[str, Any]:
    """
    Convert a Pydantic Variant object to a dictionary for Hail.
    Ensures ALL schema fields are present with None as default.
    """
    variant_dict = variant.model_dump()
    
    # Initialize with ALL fields from schema set to None
    record = {
        'chromosome': position.chromosome,
        'position': position.position,
        'ref': position.refAllele,
        'alt': variant.altAllele,
        'vid': variant.vid,
        'hgvsg': variant.hgvsg,
        'variant_type': variant.variantType,
        'begin': variant.begin,
        'end': variant.end,
        'filters': ','.join(position.filters) if position.filters else None,
        'mapping_quality': position.mappingQuality,
        'fisher_strand_bias': variant_dict.get('fisherStrandBias'),
        'quality': variant_dict.get('quality'),
        'cytogenetic_band': position.cytogeneticBand,
        'phylop_score': variant.phylopScore,
        'phylop_primate_score': variant.phyloPPrimateScore,
        'gerp_score': variant_dict.get('gerpScore'),
        'dann_score': variant_dict.get('dannScore'),
        'rsid': None,
        # Initialize all gnomAD genome fields
        'gnomad_af': None,
        'gnomad_ac': None,
        'gnomad_an': None,
        'gnomad_hc': None,
        'gnomad_afr_af': None,
        'gnomad_amr_af': None,
        'gnomad_eas_af': None,
        'gnomad_fin_af': None,
        'gnomad_nfe_af': None,
        'gnomad_asj_af': None,
        'gnomad_sas_af': None,
        'gnomad_oth_af': None,
        'gnomad_failed_filter': None,
        # Initialize all gnomAD exome fields
        'gnomad_exome_af': None,
        'gnomad_exome_ac': None,
        'gnomad_exome_an': None,
        'gnomad_exome_hc': None,
        'gnomad_exome_failed_filter': None,
        # Initialize TOPMed fields
        'topmed_af': None,
        'topmed_ac': None,
        'topmed_an': None,
        'topmed_hc': None,
        'topmed_failed_filter': None,
        # Initialize ClinVar fields
        'clinvar_significance': None,
        'clinvar_id': None,
        # Initialize transcript fields
        'n_transcripts': 0,
        'transcripts': [],
        'samples': None,
    }
    
    # Extract dbSNP
    dbsnp = variant_dict.get('dbsnp', {})
    if dbsnp and isinstance(dbsnp, dict):
        rsids = dbsnp.get('ids', [])
        record['rsid'] = rsids[0] if rsids else None
    
    # Extract gnomAD genome
    gnomad = variant_dict.get('gnomad', {})
    if gnomad:
        record['gnomad_af'] = gnomad.get('allAf')
        record['gnomad_ac'] = gnomad.get('allAc')
        record['gnomad_an'] = gnomad.get('allAn')
        record['gnomad_hc'] = gnomad.get('allHc')
        record['gnomad_afr_af'] = gnomad.get('afrAf')
        record['gnomad_amr_af'] = gnomad.get('amrAf')
        record['gnomad_eas_af'] = gnomad.get('easAf')
        record['gnomad_fin_af'] = gnomad.get('finAf')
        record['gnomad_nfe_af'] = gnomad.get('nfeAf')
        record['gnomad_asj_af'] = gnomad.get('asjAf')
        record['gnomad_sas_af'] = gnomad.get('sasAf')
        record['gnomad_oth_af'] = gnomad.get('othAf')
        record['gnomad_failed_filter'] = gnomad.get('failedFilter')
    
    # Extract gnomAD exome
    gnomad_exome = variant_dict.get('gnomad-exome', {})
    if gnomad_exome:
        record['gnomad_exome_af'] = gnomad_exome.get('allAf')
        record['gnomad_exome_ac'] = gnomad_exome.get('allAc')
        record['gnomad_exome_an'] = gnomad_exome.get('allAn')
        record['gnomad_exome_hc'] = gnomad_exome.get('allHc')
        record['gnomad_exome_failed_filter'] = gnomad_exome.get('failedFilter')
    
    # Extract TOPMed
    topmed = variant_dict.get('topmed', {})
    if topmed:
        record['topmed_af'] = topmed.get('allAf')
        record['topmed_ac'] = topmed.get('allAc')
        record['topmed_an'] = topmed.get('allAn')
        record['topmed_hc'] = topmed.get('allHc')
        record['topmed_failed_filter'] = topmed.get('failedFilter')
    
    # Extract ClinVar
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
                else str(clinvar.get('id')) if clinvar.get('id') else None
            )
        elif isinstance(clinvar, list):
            record['clinvar_significance'] = ";".join(
                ";".join(map(str, c.get('significance', [])))
                if isinstance(c.get('significance'), list)
                else str(c.get('significance', ''))
                for c in clinvar if isinstance(c, dict)
            ) or None
            record['clinvar_id'] = ";".join(
                ";".join(map(str, c.get('id', [])))
                if isinstance(c.get('id'), list)
                else str(c.get('id', ''))
                for c in clinvar if isinstance(c, dict)
            ) or None
    
    # Include transcripts
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
    
    # Include samples
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
    
    return record


def convert_to_hail(
    json_file: str,
    output_path: str,
    max_positions: Optional[int] = None,
    batch_size: int = 10000,
    temp_dir: Optional[str] = None,
) -> hl.Table:
    """
    Convert JSON to Hail Table using batched approach with disk-based intermediate tables
    
    Parameters:
    -----------
    json_file : str
        Path to JSON.gz file
    output_path : str
        Path to save final Hail Table
    max_positions : int, optional
        Limit number of positions (for testing)
    batch_size : int
        Number of variants per batch (default 10000)
    temp_dir : str, optional
        Directory for temporary batch tables
    """
    
    print(f"Loading data from {json_file}...")
    annotated_data = AnnotatedData(filename=json_file)
    
    print("\nData sources:")
    print(annotated_data.data_sources)
    
    # Setup temp directory
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="_batches_")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"\nUsing temp directory: {temp_dir}")
    
    print("\nProcessing positions...")
    batch_records = []
    position_count = 0
    variant_count = 0
    batch_num = 0
    batch_paths = []
    
    for position_dict in annotated_data.positions:
        if position_count % 1000 == 0 and position_count > 0:
            print(f"  Processed {position_count} positions, {variant_count} variants...")
        
        position = Position.model_validate(position_dict)
        
        if position.variants:
            for variant in position.variants:
                record = variant_to_dict(position, variant, include_transcripts=True)
                batch_records.append(record)
                variant_count += 1
                
                # Write batch to disk when full
                if len(batch_records) >= batch_size:
                    batch_path = os.path.join(temp_dir, f"batch_{batch_num}.ht")
                    print(f"  Writing batch {batch_num} with {len(batch_records)} variants to {batch_path}")
                    
                    # Convert and create table with schema
                    clean_records = [_convert_for_hail(r) for r in batch_records]
                    batch_ht = hl.Table.parallelize(clean_records, schema=hl.tstruct(**HAIL_SCHEMA))
                    
                    # Add locus and alleles
                    batch_ht = batch_ht.annotate(
                        locus=hl.locus(batch_ht.chromosome, batch_ht.position, reference_genome='GRCh38'),
                        alleles=hl.array([batch_ht.ref, batch_ht.alt])
                    )
                    
                    # Write to disk
                    batch_ht.write(batch_path, overwrite=True)
                    batch_paths.append(batch_path)
                    
                    # Clear memory
                    batch_records = []
                    batch_num += 1
        
        position_count += 1
        
        if max_positions and position_count >= max_positions:
            print(f"Reached max_positions limit of {max_positions}")
            break
    
    # Handle remaining records
    if batch_records:
        batch_path = os.path.join(temp_dir, f"batch_{batch_num}.ht")
        print(f"  Writing final batch {batch_num} with {len(batch_records)} variants to {batch_path}")
        
        clean_records = [_convert_for_hail(r) for r in batch_records]
        batch_ht = hl.Table.parallelize(clean_records, schema=hl.tstruct(**HAIL_SCHEMA))
        batch_ht = batch_ht.annotate(
            locus=hl.locus(batch_ht.chromosome, batch_ht.position, reference_genome='GRCh38'),
            alleles=hl.array([batch_ht.ref, batch_ht.alt])
        )
        batch_ht.write(batch_path, overwrite=True)
        batch_paths.append(batch_path)
    
    print(f"\nTotal: {position_count} positions, {variant_count} variants")
    print(f"Created {len(batch_paths)} batch tables")
    
    # Union all batches
    print("\nCombining batches...")
    if len(batch_paths) == 1:
        ht = hl.read_table(batch_paths[0])
    else:
        tables = [hl.read_table(path) for path in batch_paths]
        ht = tables[0].union(*tables[1:])
    
    # Key by locus and alleles
    print("Setting key (locus, alleles)...")
    ht = ht.key_by(ht.locus, ht.alleles)
    
    # Add computed annotations
    print("Adding computed annotations...")
    ht = ht.annotate(
        max_gnomad_af=hl.max(
            hl.array([ht.gnomad_af, ht.gnomad_exome_af]).filter(hl.is_defined)
        ),
        max_pop_af=hl.max(
            hl.array([
                ht.gnomad_afr_af, ht.gnomad_amr_af, ht.gnomad_eas_af,
                ht.gnomad_fin_af, ht.gnomad_nfe_af, ht.gnomad_asj_af,
                ht.gnomad_sas_af, ht.gnomad_oth_af
            ]).filter(hl.is_defined)
        ),
        # Get canonical transcript safely - check if any exist after filtering
        canonical_transcript=hl.bind(
            lambda canonical_transcripts: hl.if_else(
                hl.len(canonical_transcripts) > 0,
                canonical_transcripts[0],
                hl.missing(ht.transcripts.dtype.element_type)
            ),
            ht.transcripts.filter(lambda t: t.is_canonical)
        ),
        all_consequences=hl.set(
            hl.flatten(ht.transcripts.map(lambda t: t.consequences))
        ),
        genes=hl.set(
            ht.transcripts.map(lambda t: t.hgnc).filter(hl.is_defined)
        ),
    )
    
    # Write final table
    print(f"\nWriting final Hail Table to {output_path}...")
    ht = ht.checkpoint(output_path, overwrite=True)
    
    # Cleanup temp files
    print(f"\nCleaning up temp directory: {temp_dir}")
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Summary
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    print(f"Output: {output_path}")
    print(f"Total variants: {ht.count()}")
    print("\nSchema:")
    ht.describe()
    
    return ht


# Example usage
if __name__ == "__main__":
    REFERENCE_GENOME = 'GRCh38'

    LOG_PATH = '../logs/hail'
    print("Initializing Hail...")
    hl.init(app_name='Parse Illumina JSON', log=LOG_PATH, default_reference=REFERENCE_GENOME)
    
    # print("Spark master:", hl.default_reference().name)
    # print("Default parallelism:", hl.spark_context().defaultParallelism)
    
    json_file = "../data/NA12878.bed.filtered.json.gz"
    
    print("="*60)
    print("VARIANT-LEVEL TABLE (one row per variant)")
    print("="*60)
    
    ht = convert_to_hail(
        json_file=json_file,
        output_path="../data/variants.ht",
        max_positions=None,  # Use None for all data
        batch_size=5000,     # Adjust based on available memory
    )