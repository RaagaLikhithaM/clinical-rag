"""
scripts/seed_demo.py

Pre-ingests the demo PDF files into the knowledge base so the system
is ready to answer questions without the user needing to upload files
manually during a demo.

Place your PDF files in the data/pdfs/ folder then run:
    python scripts/seed_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.ingest import ingest_pdf

PDF_DIR = "data/pdfs"


def seed():
    """Find all PDFs in data/pdfs and ingest each one."""
    if not os.path.exists(PDF_DIR):
        print(f"Folder {PDF_DIR} does not exist. Create it and add PDFs.")
        return

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in {PDF_DIR}.")
        return

    print(f"Found {len(pdf_files)} PDF files. Starting ingestion...")

    for filename in pdf_files:
        path = os.path.join(PDF_DIR, filename)
        print(f"  Ingesting {filename}...")
        result = ingest_pdf(path)
        print(
            f"  Done — status: {result['status']}, "
            f"pages: {result.get('pages', 0)}, "
            f"chunks: {result.get('chunks', 0)}"
        )

    print("Seeding complete.")


if __name__ == "__main__":
    seed()