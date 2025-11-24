"""
Export Hail Table to Elasticsearch.

This script reads a Hail Table from disk and exports it to an Elasticsearch index.
It configures the Spark context required by Hail and handles the connection details.

Usage:
    uv run scripts/export_to_es.py --input-path <path> --index <index_name>
"""

import argparse
import hail as hl


def export_table(input_path: str, host: str, port: int, index: str) -> None:
    """
    Export a Hail Table to Elasticsearch.

    Args:
        input_path (str): Path to the input Hail Table directory.
        host (str): Elasticsearch host address.
        port (int): Elasticsearch port number.
        index (str): Name of the target Elasticsearch index.
    """
    # Initialize Hail with Spark configuration optimized for large datasets
    hl.init(spark_conf={
        'spark.driver.memory': '320g',
        'spark.executor.memory': '320g',
        'spark.driver.maxResultSize': '100g',
        'spark.kryoserializer.buffer.max': '2047G'
    })
    
    print(f"Loading Hail Table from {input_path}...")
    ht = hl.read_table(input_path)
    
    # Flatten the table structure for easier indexing in Elasticsearch
    ht = ht.flatten()
    
    # Print schema for verification
    print("Table Schema:")
    ht.describe()
    
    print(f"Exporting to Elasticsearch ({host}:{port}/{index})...")
    
    # Export to Elasticsearch
    # Note: 'es.nodes.wan.only' is set to true to allow connecting to container/remote IPs
    hl.export_elasticsearch(
        ht,
        host=host,
        port=port,
        index=index,
        index_type='_doc',
        block_size=10000,
        config={
            "es.nodes.wan.only": "true"
        }
    )
    
    print(f"Successfully exported table to index '{index}'.")


def get_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Export Hail Table to Elasticsearch",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-path", 
        type=str, 
        required=True, 
        help="Path to the input Hail Table"
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


def main() -> None:
    """Main entry point."""
    parser = get_parser()
    args = parser.parse_args()
    
    export_table(
        input_path=args.input_path,
        host=args.host,
        port=args.port,
        index=args.index
    )


if __name__ == "__main__":
    main()
