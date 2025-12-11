"""
Parse Illumina Nirvana JSON to Hail Table.

This script parses the JSON output from Illumina Nirvana, converts the nested structure
into a flat format suitable for analysis, and saves it as a Hail Table (`.ht`).
It handles large files by processing variants in batches.

Usage:
    uv run scripts/parse_nirvana.py --json_file <path> --output_path <path>
"""

import argparse
import gzip
import os
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import hail as hl
import ijson
import numpy as np
import pandas as pd
import pydantic

# Configure Pandas to show all columns for debugging
pd.set_option("display.max_columns", None)

# # Define ClinVar values
# SET_PATHOGENIC = {
#     "Pathogenic", "Likely pathogenic", 
#     "Pathogenic/Likely pathogenic", "Likely pathogenic/Pathogenic"
# }
# SET_BENIGN = {
#     "Benign", "Likely benign", 
#     "Benign/Likely benign", "Likely benign/Benign"
# }
# SET_VUS = {"Uncertain significance"}
# SET_CONFLICTING = {"Conflicting classifications of pathogenicity"}
# SET_DRUG = {"drug response"}
# SET_AFFECTS = {"Affects"}
# SET_PROTECTIVE = {"protective"}
# SET_LOW_PENETRANCE = {
#     "Pathogenic/Likely pathogenic/Pathogenic, low penetrance",
#     "Pathogenic/Pathogenic, low penetrance",
#     "Likely risk allele",
#     "Uncertain risk allele",
#     "Uncertain significance/Uncertain risk allele"
# }
# SET_NOT_PROVIDED = {"not provided", "NA", "", "nan"}
# SET_ASSOCIATION = {"association"}
# SET_RISK_FACTOR = {"risk factor"}

# Define complete Hail schema with proper types
HAIL_SCHEMA = {
    "chromosome": hl.tstr,
    "position": hl.tint32,
    "ref": hl.tstr,
    "alt": hl.tstr,
    "vid": hl.tstr,
    "hgvsg": hl.tstr,
    "variant_type": hl.tstr,
    "begin": hl.tint32,
    "end": hl.tint32,
    # Quality metrics
    "filters": hl.tstr,
    "mapping_quality": hl.tfloat64,
    "fisher_strand_bias": hl.tfloat64,
    "quality": hl.tfloat64,
    "cytogenetic_band": hl.tstr,
    # Conservation scores
    "phylop_score": hl.tfloat64,
    "phylop_primate_score": hl.tfloat64,
    "gerp_score": hl.tfloat64,
    "dann_score": hl.tfloat64,
    # dbSNP
    "rsid": hl.tstr,
    # gnomAD genome frequencies
    "gnomad_af": hl.tfloat64,
    "gnomad_ac": hl.tint32,
    "gnomad_an": hl.tint32,
    "gnomad_hc": hl.tint32,
    "gnomad_afr_af": hl.tfloat64,
    "gnomad_amr_af": hl.tfloat64,
    "gnomad_eas_af": hl.tfloat64,
    "gnomad_fin_af": hl.tfloat64,
    "gnomad_nfe_af": hl.tfloat64,
    "gnomad_asj_af": hl.tfloat64,
    "gnomad_sas_af": hl.tfloat64,
    "gnomad_oth_af": hl.tfloat64,
    "gnomad_failed_filter": hl.tbool,
    # gnomAD exome frequencies
    "gnomad_exome_af": hl.tfloat64,
    "gnomad_exome_ac": hl.tint32,
    "gnomad_exome_an": hl.tint32,
    "gnomad_exome_hc": hl.tint32,
    "gnomad_exome_failed_filter": hl.tbool,
    # TOPMed
    "topmed_af": hl.tfloat64,
    "topmed_ac": hl.tint32,
    "topmed_an": hl.tint32,
    "topmed_hc": hl.tint32,
    "topmed_failed_filter": hl.tbool,
    # ClinVar
    "clinvar_variant_type": hl.tstr,
    "clinvar_significance": hl.tstr,
    "clinvar_id": hl.tstr,
    # Transcript count
    "n_transcripts": hl.tint32,
    # Transcripts - nested structure
    "transcripts": hl.tarray(
        hl.tstruct(
            transcript_id=hl.tstr,
            source=hl.tstr,
            bio_type=hl.tstr,
            gene_id=hl.tstr,
            hgnc=hl.tstr,
            consequences=hl.tarray(hl.tstr),
            impact=hl.tstr,
            is_canonical=hl.tbool,
        )
    ),
    # Samples - nested structure (optional)
    "samples": hl.tarray(
        hl.tstruct(
            genotype=hl.tstr,
            variant_frequencies=hl.tarray(hl.tfloat64),
            total_depth=hl.tint32,
            genotype_quality=hl.tint32,
            allele_depths=hl.tarray(hl.tint32),
        )
    ),
}


# def clinvar_transform(clinvar_value: str | None) -> str:
#     """
#     Transformation of ClinVar string to consensus classification.
#     Input: 'Pathogenic;Likely pathogenic'
#     Output: 'Likely pathogenic/Pathogenic'
#     Args:
#         clinvar_value (str): Semicolon-separated ClinVar significance terms.
#     Returns:
#         str: Consensus classification.
#     """
#     # Exit for empty/None values
#     if not clinvar_value:
#         return "Not provided"

#     # Splits the string, strips whitespace, and creates a set of unique terms.
#     terms = {term.strip() for term in clinvar_value.split(';') if term.strip()}
    
#     # If cleaning resulted in an empty set (e.g. input was "; "), return Not Provided
#     if not terms:
#         return "Not provided"

#     # Classification Logic using Set Operations
#     # terms.issubset(TARGET) is semantically identical to R's: all(v %in% TARGET) (R version)
    
#     if terms.issubset(SET_PATHOGENIC):
#         return "Likely pathogenic/Pathogenic"
        
#     if terms.issubset(SET_BENIGN):
#         return "Likely benign/Benign"
        
#     if terms.issubset(SET_VUS):
#         return "Uncertain significance"
        
#     if terms.issubset(SET_CONFLICTING):
#         return "Conflicting classifications of pathogenicity"
        
#     if terms.issubset(SET_DRUG):
#         return "Drug response"
        
#     if terms.issubset(SET_AFFECTS):
#         return "Affects a non-disease phenotype"
        
#     if terms.issubset(SET_PROTECTIVE):
#         return "Protective"
        
#     if terms.issubset(SET_LOW_PENETRANCE):
#         return "Low penetrance for Mendelian diseases"
        
#     if terms.issubset(SET_NOT_PROVIDED):
#         return "Not provided"
        
#     if terms.issubset(SET_ASSOCIATION):
#         return "GWAS hits"
        
#     if terms.issubset(SET_RISK_FACTOR):
#         return "Risk factor"

#     return "Other"

# Classes and functions to parse JSON and convert to Hail Table are imported from
# script from Illumina Nirvana JSON parsing github repository with modifications.
# https://github.com/Illumina/IlluminaConnectedAnnotationsDocumentation/blob/master/static/files/parse-json-python.ipynb


def _convert_for_hail(obj: Any) -> Any:
    """
    Recursively convert Decimal and numpy types to plain Python types Hail accepts.

    Args:
        obj: The object to convert.
    Returns:
        The converted object.
    """
    if isinstance(obj, dict):
        return {k: _convert_for_hail(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_for_hail(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)):  # type: ignore[arg-type]
        return float(obj)
    if isinstance(obj, (np.integer, np.int32, np.int64)):  # type: ignore[arg-type]
        return int(obj)
    return obj


class BaseClass(pydantic.BaseModel):
    """
    Base class for Pydantic models with methods to convert to DataFrames.
    Allows extra fields in the model.
    """

    model_config = pydantic.ConfigDict(extra="allow")

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
    """
    Basic transcript annotation model.
    """

    transcript: str
    source: str
    bioType: Optional[str] = None
    geneId: Optional[str] = None
    hgnc: Optional[str] = None
    consequence: Optional[List[str]] = None
    impact: Optional[str] = None
    isCanonical: Optional[bool] = None

    def get_top_level_dict(self) -> Dict[str, Any]:
        return dict(
            zip(("transcript", "isCanonical"), (self.transcript, self.isCanonical))
        )


class Variant(BaseClass):
    """
    Basic variant annotation model.
    """

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
                (
                    self.chromosome,
                    self.begin,
                    self.end,
                    self.refAllele,
                    self.altAllele,
                    self.hgvsg,
                ),
            )
        )


class Position(BaseClass):
    """
    Basic position annotation model.
    """

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
    """
    Class to parse and access annotated data from a Nirvana JSON file.
    
    This class provides lazy access to the JSON structure using `ijson` to avoid
    loading the entire file into memory.
    """

    def __init__(self, filename: str):
        """
        Initialize the parser.

        Args:
            filename (str): Path to the gzipped JSON file.
        """
        self._filename = filename

        # Print metadata on initialization
        for key in ("annotator", "genomeAssembly", "creationTime"):
            print(f"{key}: {self.header[key]}")

    @property
    def header(self) -> Dict[str, Any]:
        """Get the JSON header section."""
        with gzip.open(self._filename, "r") as f:
            return next(ijson.items(f, "header"))

    @property
    def data_sources(self) -> pd.DataFrame:
        """Get data sources as a DataFrame."""
        return pd.DataFrame(self.header["dataSources"]).set_index("name").sort_index()

    @property
    def genes(self) -> pd.DataFrame:
        """Get genes section as a DataFrame."""
        with gzip.open(self._filename, "r") as f:
            return pd.json_normalize(ijson.items(f, "genes.item"))

    @property
    def positions(self) -> Generator[Any, None, None]:
        """
        Generator yielding position items.
        
        Returns:
            Generator[Any, None, None]: Stream of position dictionaries.
        """
        f = gzip.open(self._filename, "r")
        return ijson.items(f, "positions.item")

    def get_annotation(self, chromosome: str, position: int) -> Dict[str, Any]:
        """
        Retrieve annotation for a specific chromosome and position.

        Args:
            chromosome (str): Chromosome name (e.g., "chr1").
            position (int): Genomic position.

        Returns:
            Dict[str, Any]: The annotation dictionary.

        Raises:
            Exception: If annotation is not found.
        """
        annotation = next(
            (
                position_item
                for position_item in self.positions
                if chromosome == position_item.get("chromosome")
                and position == position_item.get("position")
            ),
            {},
        )

        if not annotation:
            raise Exception(f"Cannot find annotation for {chromosome=} and {position=}")

        return annotation

    def get_annotation_range(
        self, chromosome: str, position: int, end: int
    ) -> Generator[Any, Any, None]:
        """
        Retrieve annotations within a genomic range.

        Args:
            chromosome (str): Chromosome name.
            position (int): Start position.
            end (int): End position.

        Returns:
            Generator[Any, Any, None]: Generator of annotation dictionaries.
        """
        return (
            position_item
            for position_item in self.positions
            if chromosome == position_item.get("chromosome")
            and position <= position_item.get("position") <= end
        )

    @staticmethod
    def multiple_to_df(items: List[BaseClass], key: str = "") -> pd.DataFrame:
        """Convert a list of Pydantic models to a DataFrame."""
        return pd.concat((item.to_df(key) for item in items))


class Parser:
    """
    Class to parse annotated data and provide filtering methods.
    """

    def __init__(self, annotated_data: AnnotatedData):
        """
        Initialize the parser.

        Args:
            annotated_data (AnnotatedData): The data source.
        """
        self.annotated_data = annotated_data

    def get_variants_above_gnomad_freq(
        self,
        frequency_key: str,
        frequency_threshold_low: float = float("-inf"),
        frequency_threshold_high: float = float("inf"),
    ) -> Generator[Any, Any, None]:
        """
        Filter variants based on gnomAD frequency.

        Args:
            frequency_key (str): The gnomAD field to check (e.g., "allAf").
            frequency_threshold_low (float): Minimum frequency (exclusive).
            frequency_threshold_high (float): Maximum frequency (exclusive).

        Returns:
            Generator: Filtered variants.
        """
        positions = (
            Position.model_validate(position)
            for position in self.annotated_data.positions
            for variant in position.get("variants", {})
            if (freq := variant.get("gnomad", {}).get(frequency_key, None))
            and frequency_threshold_low < freq < frequency_threshold_high
        )
        return positions

    def get_positions_with_cannonical_transcripts(self) -> Generator[Any, Any, None]:
        """
        Get positions that have at least one canonical transcript.

        Returns:
            Generator: Positions with canonical transcripts.
        """
        positions = (
            Position.model_validate(position)
            for position in self.annotated_data.positions
            for variant in position.get("variants", {})
            for transcript in variant.get("transcripts", [])
            if transcript.get("isCanonical")
        )

        return positions

    # def filter_transcripts_by_consequence(
    #     self, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None
    # ) -> Generator[Any, Any, None]:
    #     """
    #     Filter transcripts based on consequence terms.

    #     Args:
    #         include (List[str], optional): List of consequences to include.
    #         exclude (List[str], optional): List of consequences to exclude.

    #     Returns:
    #         Generator: Filtered positions.
    #     """
    #     if not exclude:
    #         exclude = []

    #     if not include:
    #         include = []

    #     positions = (
    #         Position.model_validate(position)
    #         for position in self.annotated_data.positions
    #         for variant in position.get("variants", {})
    #         for transcript in variant.get("transcripts", [])
    #         for consequence in transcript.get("consequence", [])
    #         if (not bool(include) or consequence in include)
    #         and consequence not in exclude
    #     )
    #     return positions


def variant_to_dict(
    position: Position, variant: Variant, include_transcripts: bool = True
) -> Dict[str, Any]:
    """
    Convert a Pydantic Variant object to a dictionary for Hail.
    Ensures ALL schema fields are present with None as default.

    Args:
        position: Position object
        variant: Variant object
        include_transcripts: Whether to include transcript annotations
    Returns:
        Dictionary with all fields for Hail Table
    """
    variant_dict = variant.model_dump()

    # Initialize with ALL fields from schema set to None
    record = {
        "chromosome": position.chromosome,
        "position": position.position,
        "ref": position.refAllele,
        "alt": variant.altAllele,
        "vid": variant.vid,
        "hgvsg": variant.hgvsg,
        "variant_type": variant.variantType,
        "begin": variant.begin,
        "end": variant.end,
        "filters": ",".join(position.filters) if position.filters else None,
        "mapping_quality": position.mappingQuality,
        "fisher_strand_bias": variant_dict.get("fisherStrandBias"),
        "quality": variant_dict.get("quality"),
        "cytogenetic_band": position.cytogeneticBand,
        "phylop_score": variant.phylopScore,
        "phylop_primate_score": variant.phyloPPrimateScore,
        "gerp_score": variant_dict.get("gerpScore"),
        "dann_score": variant_dict.get("dannScore"),
        "rsid": None,
        # Initialize all gnomAD genome fields
        "gnomad_af": None,
        "gnomad_ac": None,
        "gnomad_an": None,
        "gnomad_hc": None,
        "gnomad_afr_af": None,
        "gnomad_amr_af": None,
        "gnomad_eas_af": None,
        "gnomad_fin_af": None,
        "gnomad_nfe_af": None,
        "gnomad_asj_af": None,
        "gnomad_sas_af": None,
        "gnomad_oth_af": None,
        "gnomad_failed_filter": None,
        # Initialize all gnomAD exome fields
        "gnomad_exome_af": None,
        "gnomad_exome_ac": None,
        "gnomad_exome_an": None,
        "gnomad_exome_hc": None,
        "gnomad_exome_failed_filter": None,
        # Initialize TOPMed fields
        "topmed_af": None,
        "topmed_ac": None,
        "topmed_an": None,
        "topmed_hc": None,
        "topmed_failed_filter": None,
        # Initialize ClinVar fields
        "clinvar_variant_type": None,
        "clinvar_significance": None,
        "clinvar_id": None,
        # Initialize transcript fields
        "n_transcripts": 0,
        "transcripts": [],
        "samples": None,
    }

    # Extract dbSNP
    dbsnp = variant_dict.get("dbsnp", {})
    rsids = []
    if dbsnp and isinstance(dbsnp, dict):
        rsids = dbsnp.get("ids", [])
    elif dbsnp and isinstance(dbsnp, list):
        rsids.extend(dbsnp)
    record["rsid"] = ','.join(rsids) if rsids else None

    # Extract gnomAD genome
    gnomad = variant_dict.get("gnomad", {})
    if gnomad:
        record["gnomad_af"] = gnomad.get("allAf")
        record["gnomad_ac"] = gnomad.get("allAc")
        record["gnomad_an"] = gnomad.get("allAn")
        record["gnomad_hc"] = gnomad.get("allHc")
        record["gnomad_afr_af"] = gnomad.get("afrAf")
        record["gnomad_amr_af"] = gnomad.get("amrAf")
        record["gnomad_eas_af"] = gnomad.get("easAf")
        record["gnomad_fin_af"] = gnomad.get("finAf")
        record["gnomad_nfe_af"] = gnomad.get("nfeAf")
        record["gnomad_asj_af"] = gnomad.get("asjAf")
        record["gnomad_sas_af"] = gnomad.get("sasAf")
        record["gnomad_oth_af"] = gnomad.get("othAf")
        record["gnomad_failed_filter"] = gnomad.get("failedFilter")

    # Extract gnomAD exome
    gnomad_exome = variant_dict.get("gnomad-exome", {})
    if gnomad_exome:
        record["gnomad_exome_af"] = gnomad_exome.get("allAf")
        record["gnomad_exome_ac"] = gnomad_exome.get("allAc")
        record["gnomad_exome_an"] = gnomad_exome.get("allAn")
        record["gnomad_exome_hc"] = gnomad_exome.get("allHc")
        record["gnomad_exome_failed_filter"] = gnomad_exome.get("failedFilter")

    # Extract TOPMed
    topmed = variant_dict.get("topmed", {})
    if topmed:
        record["topmed_af"] = topmed.get("allAf")
        record["topmed_ac"] = topmed.get("allAc")
        record["topmed_an"] = topmed.get("allAn")
        record["topmed_hc"] = topmed.get("allHc")
        record["topmed_failed_filter"] = topmed.get("failedFilter")

    # Extract ClinVar
    clinvar = variant_dict.get("clinvar-preview", {})
    if clinvar:
        if isinstance(clinvar, dict):
            # Check for isAlleleSpecific
            if clinvar.get("isAlleleSpecific") is True:
                # Extract variantType
                record["clinvar_variant_type"] = clinvar.get("variantType")
                
                # Extract classification from germlineClassification
                classifications = clinvar.get("classifications", {}).get("germlineClassification", {})
                record["clinvar_significance"] = classifications.get("classification")
                
                # Extract accession and version
                accession = clinvar.get("accession")
                version = clinvar.get("version")
                record["clinvar_id"] = f"{accession}.{version}" if accession and version else accession
            
        elif isinstance(clinvar, list):
            # Filter for isAlleleSpecific == True
            filtered_clinvar = [
                c for c in clinvar 
                if isinstance(c, dict) and c.get("isAlleleSpecific") is True
            ]

            # Collect variantTypes
            variant_types = [
                str(vt) for c in filtered_clinvar 
                if (vt := c.get("variantType")) is not None
            ]
            record["clinvar_variant_type"] = ";".join(variant_types) if variant_types else None
            
            # Collect classifications
            classifications = []
            for c in filtered_clinvar:
                germline_class = c.get("classifications", {}).get("germlineClassification", {})
                classification = germline_class.get("classification")
                if classification:
                    classifications.append(classification)
            record["clinvar_significance"] = ";".join(classifications) if classifications else None
            
            # Collect accessions
            accessions = []
            for c in filtered_clinvar:
                accession = c.get("accession")
                version = c.get("version")
                if accession and version:
                    accessions.append(f"{accession}.{version}")
                elif accession:
                    accessions.append(accession)
            record["clinvar_id"] = ";".join(accessions) if accessions else None
    # Include transcripts
    if include_transcripts and variant.transcripts:
        record["transcripts"] = [
            {
                "transcript_id": t.transcript,
                "source": t.source,
                "bio_type": t.bioType,
                "gene_id": t.geneId,
                "hgnc": t.hgnc,
                "consequences": t.consequence if t.consequence else [],
                "impact": t.impact,
                "is_canonical": t.isCanonical if t.isCanonical else False,
            }
            for t in variant.transcripts
        ]
        record["n_transcripts"] = len(variant.transcripts)

    # Include samples
    if position.samples:
        record["samples"] = [
            {
                "genotype": s.get("genotype"),
                "variant_frequencies": s.get("variantFrequencies", []),
                "total_depth": s.get("totalDepth"),
                "genotype_quality": s.get("genotypeQuality"),
                "allele_depths": s.get("alleleDepths", []),
            }
            for s in position.samples
        ]

    return record


def convert_to_hail(
    json_file: str,
    output_path: str,
    max_positions: Optional[int] = None,
    batch_size: int = 2500,
    temp_dir: Optional[str] = None,
) -> hl.Table:
    """
    Convert JSON to Hail Table using batched approach with disk-based intermediate tables

    Args:
        json_file: Path to input JSON file
        output_path: Path to output Hail Table
        max_positions: Maximum number of positions to process (None for all)
        batch_size: Number of variants per batch
        temp_dir: Temporary directory for intermediate files (None for auto-generated)
    Returns:
        Hail Table with variant-level annotations
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
            print(
                f"  Processed {position_count} positions, {variant_count} variants..."
            )

        position = Position.model_validate(position_dict)

        if position.variants:
            for variant in position.variants:
                record = variant_to_dict(position, variant, include_transcripts=True)
                # clinvar_consensus = clinvar_transform(record["clinvar_significance"])
                # record["clinvar_significance"] = clinvar_consensus
                batch_records.append(record)
                variant_count += 1

                # Write batch to disk when full
                if len(batch_records) >= batch_size:
                    batch_path = os.path.join(temp_dir, f"batch_{batch_num}.ht")
                    print(
                        f"  Writing batch {batch_num} with {len(batch_records)} variants to {batch_path}"
                    )

                    # Convert and create table with schema
                    clean_records = [_convert_for_hail(r) for r in batch_records]
                    batch_ht = hl.Table.parallelize(
                        clean_records, schema=hl.tstruct(**HAIL_SCHEMA)
                    )

                    # Add locus and alleles
                    batch_ht = batch_ht.annotate(
                        locus=hl.locus(
                            batch_ht.chromosome,
                            batch_ht.position,
                            reference_genome="GRCh38",
                        ),
                        alleles=hl.array([batch_ht.ref, batch_ht.alt]),
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
        print(
            f"  Writing final batch {batch_num} with {len(batch_records)} variants to {batch_path}"
        )

        clean_records = [_convert_for_hail(r) for r in batch_records]
        batch_ht = hl.Table.parallelize(clean_records, schema=hl.tstruct(**HAIL_SCHEMA))
        batch_ht = batch_ht.annotate(
            locus=hl.locus(
                batch_ht.chromosome, batch_ht.position, reference_genome="GRCh38"
            ),
            alleles=hl.array([batch_ht.ref, batch_ht.alt]),
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
            hl.array(
                [
                    ht.gnomad_afr_af,
                    ht.gnomad_amr_af,
                    ht.gnomad_eas_af,
                    ht.gnomad_fin_af,
                    ht.gnomad_nfe_af,
                    ht.gnomad_asj_af,
                    ht.gnomad_sas_af,
                    ht.gnomad_oth_af,
                ]
            ).filter(hl.is_defined)
        ),
        # Get canonical transcript safely - check if any exist after filtering
        canonical_transcript=hl.bind(
            lambda canonical_transcripts: hl.if_else(
                hl.len(canonical_transcripts) > 0,
                canonical_transcripts[0],
                hl.missing(ht.transcripts.dtype.element_type),
            ),
            ht.transcripts.filter(lambda t: t.is_canonical),
        ),
        all_consequences=hl.set(
            hl.flatten(ht.transcripts.map(lambda t: t.consequences))
        ),
        genes=hl.set(ht.transcripts.map(lambda t: t.hgnc).filter(hl.is_defined)),
    )

    # Write final table
    print(f"\nWriting final Hail Table to {output_path}...")
    ht = ht.checkpoint(output_path, overwrite=True)

    # Cleanup temp files
    print(f"\nCleaning up temp directory: {temp_dir}")
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"Output: {output_path}")
    print(f"Total variants: {ht.count()}")
    print("\nSchema:")
    ht.describe()

    return ht


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Illumina Nirvana JSON to Hail Table"
    )
    parser.add_argument(
        "--json_file", type=str, required=True, help="Path to input JSON file"
    )
    parser.add_argument(
        "--output_path", type=str, required=True, help="Path to output Hail Table"
    )
    parser.add_argument(
        "--log_path",
        type=str,
        default=None,
        help="Path to Hail log file (default: None)",
    )
    parser.add_argument(
        "--genome_ref",
        type=str,
        default="GRCh38",
        help="Reference genome (default: GRCh38)",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=2500,
        help="Number of variants per batch (default: 10000)",
    )
    parser.add_argument(
        "--max_positions",
        type=int,
        default=None,
        help="Maximum number of positions to process (default: None for all)",
    )
    
    parser.add_argument(
        "--host", 
        type=str, 
        default="localhost", 
        help="Elasticsearch host"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=9200, 
        help="Elasticsearch port"
    )
    parser.add_argument(
        "--index", 
        type=str, 
        default="fiocruz_variants",
        help="Elasticsearch index name"
    )
    
    return parser


# Example usage
if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    # check if log path is provided and exists, if not, create it
    if args.log_path:
        log_dir = Path(args.log_path)
    else:
        log_dir_path = "logs/hail"
        log_dir = Path(log_dir_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_dir = log_dir / "hail.log"
    # print the complete path of the log directory in str format
    print(f"Hail log directory: {str(log_dir)}")

    # check if output path directory exists, if not, create it
    output_dir = Path(args.output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir / "variants.ht"
    output_dir_str = str(output_dir)
    print("Initializing Hail...")
    hl.init(
        app_name="Parse Illumina JSON",
        log=str(log_dir),
        default_reference=args.genome_ref,
        spark_conf={
        'spark.driver.memory': '320g',
        'spark.executor.memory': '320g',
        'spark.driver.maxResultSize': '100g',
        'spark.kryoserializer.buffer.max': '2047G'
    }
    )

    # print("Spark master:", hl.default_reference().name)
    # print("Default parallelism:", hl.spark_context().defaultParallelism)

    json_file = args.json_file

    print("=" * 60)
    print("VARIANT-LEVEL TABLE (one row per variant)")
    print("=" * 60)

    ht = convert_to_hail(
        json_file=json_file,
        output_path=output_dir_str,
        max_positions=args.max_positions,  # Use None for all data
        batch_size=args.batch_size,  # Adjust based on available memory
    )
    
    print("\nFinal Hail Table:")
    ht = ht.flatten()
    ht.describe()
    
    print("\nExporting to Elasticsearch...")

    hl.export_elasticsearch(
        ht,
        host=args.host,
        port=args.port,
        index=args.index,
        index_type='_doc',
        block_size=10000,
        config={
            "es.nodes.wan.only": "true"   # necessário quando acessar container via IP
        }

    )

    print(
        "Done!\nIf you wish to explore the generated Hail Table, you can use the 'test_table.ipynb' notebook."
    )
