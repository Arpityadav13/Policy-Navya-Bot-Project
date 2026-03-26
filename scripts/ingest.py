"""
NyayaBot Document Ingestion Script
Run this to index all policy documents in data/policies/
"""

import sys
import json
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def ingest_all():
    from rag.engine import NyayaBotRAGEngine, PolicyDocumentProcessor, EmbeddingEngine, FAISSVectorStore

    logger.info("=" * 60)
    logger.info("NyayaBot Document Ingestion")
    logger.info("=" * 60)

    processor = PolicyDocumentProcessor()
    embedder = EmbeddingEngine()
    store = FAISSVectorStore(dimension=embedder.dimension)

    policies_dir = Path("data/policies")
    training_file = Path("data/training/training_data.json")
    all_chunks = []

    # 1. Process PDF files
    pdf_files = list(policies_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    for pdf in pdf_files:
        scheme_name = pdf.stem.replace('_', ' ').replace('-', ' ').title()
        logger.info(f"  Processing: {pdf.name} → '{scheme_name}'")
        chunks = processor.process_pdf(str(pdf), scheme_name)
        all_chunks.extend(chunks)
        logger.info(f"    → {len(chunks)} chunks")

    # 2. Process text files
    txt_files = list(policies_dir.glob("*.txt")) + list(policies_dir.glob("*.md"))
    logger.info(f"Found {len(txt_files)} text files")
    for txt in txt_files:
        scheme_name = txt.stem.replace('_', ' ').replace('-', ' ').title()
        with open(txt, 'r', encoding='utf-8') as f:
            text = f.read()
        chunks = processor.process_text(text, scheme_name, txt.name)
        all_chunks.extend(chunks)
        logger.info(f"  Processed: {txt.name} → {len(chunks)} chunks")

    # 3. Load training data
    if training_file.exists():
        logger.info(f"Loading training data from {training_file}")
        with open(training_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for doc in data.get('policy_documents', []):
            text = f"{doc['title']}\n\n{doc['content']}"
            chunks = processor.process_text(text, doc['title'], "training_data.json")
            all_chunks.extend(chunks)
            logger.info(f"  Loaded: {doc['title']} → {len(chunks)} chunks")

        logger.info(f"  Total from training: {len(data.get('policy_documents', []))} schemes")

    if not all_chunks:
        logger.error("No chunks created! Add PDF/text files to data/policies/")
        return

    # 4. Embed and store
    logger.info(f"\nEmbedding {len(all_chunks)} chunks...")
    store.add_chunks(all_chunks, embedder)
    store.save()

    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Ingestion complete!")
    logger.info(f"   Total chunks: {len(all_chunks)}")
    logger.info(f"   Unique schemes: {len(set(c.scheme_name for c in all_chunks))}")
    logger.info(f"   Index saved to: data/faiss_index/")
    logger.info("=" * 60)

    # Print scheme summary
    scheme_counts = {}
    for c in all_chunks:
        scheme_counts[c.scheme_name] = scheme_counts.get(c.scheme_name, 0) + 1
    
    print("\nScheme Summary:")
    for scheme, count in sorted(scheme_counts.items()):
        print(f"  {scheme}: {count} chunks")


if __name__ == "__main__":
    ingest_all()
