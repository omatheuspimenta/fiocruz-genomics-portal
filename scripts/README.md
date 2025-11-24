# Data Ingestion Scripts

This directory contains scripts for processing variant data and loading it into Elasticsearch.

## Prerequisites

- Python 3.11+
- Java 8+ (for Hail)
- Dependencies: `hail`, `pandas`, `pydantic`, `ijson`

## Scripts

### 1. `parse_nirvana.py`
Converts Illumina Nirvana JSON annotations into a Hail Table (`.ht`).

**Usage:**
```bash
python scripts/parse_nirvana.py \
  --json_file /path/to/nirvana.json.gz \
  --output_path /path/to/output.ht \
  --batch_size 5000
```

### 2. `export_to_es.py`
Exports a Hail Table to Elasticsearch.

**Usage:**
```bash
python scripts/export_to_es.py \
  --input-path /path/to/output.ht \
  --index fiocruz_variants \
  --host localhost \
  --port 9200
```

## Workflow

1.  **Parse**: Convert the raw JSON from Nirvana into a structured Hail Table.
2.  **Export**: Load the Hail Table into Elasticsearch for the API to consume.
