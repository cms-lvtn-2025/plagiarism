#!/usr/bin/env python3
"""Setup Elasticsearch index for plagiarism detection."""

import sys
import argparse

# Add project root to path
sys.path.insert(0, ".")

from src.storage import get_es_client


def main():
    parser = argparse.ArgumentParser(description="Setup Elasticsearch index")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate index (WARNING: deletes existing data)",
    )
    args = parser.parse_args()

    print("Setting up Elasticsearch...")

    client = get_es_client()

    # Check health
    health = client.health_check()
    if not health.get("healthy"):
        print(f"ERROR: Elasticsearch not healthy: {health}")
        sys.exit(1)

    print(f"Connected to: {health.get('cluster_name')} (status: {health.get('status')})")

    # Create index
    if args.force:
        print("WARNING: Force mode - existing data will be deleted!")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    success = client.create_index(force=args.force)

    if success:
        print(f"Index created successfully: {client.index_name}")
        print(f"Chunks index: {client.index_name}_chunks")
    else:
        print("Failed to create index")
        sys.exit(1)


if __name__ == "__main__":
    main()
