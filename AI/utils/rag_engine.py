"""
WellFinanced — RAG Engine
Handles document embedding, ChromaDB vector storage, and similarity search
for the Financial Advisor chatbot.
"""

import os

# Fix TF/Keras 3 compatibility before any imports
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"

import glob
import numpy as np
import chromadb

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(PROJECT_ROOT, "knowledge")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")

# Cache the model globally
_model = None


def _get_model():
    """Load the sentence transformer model (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class _CustomEmbeddingFunction(chromadb.EmbeddingFunction):
    """Custom embedding function using SentenceTransformer directly."""

    def __call__(self, input: list) -> list:
        model = _get_model()
        embeddings = model.encode(input, show_progress_bar=False)
        return embeddings.tolist()


def _get_client():
    """Get or create a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _get_collection(client=None):
    """Get or create the knowledge base collection."""
    if client is None:
        client = _get_client()
    return client.get_or_create_collection(
        name="wellfinanced_knowledge",
        embedding_function=_CustomEmbeddingFunction(),
        metadata={"description": "WellFinanced financial knowledge base"},
    )


def _chunk_document(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Split a document into overlapping chunks for embedding.

    Args:
        text: Full document text
        chunk_size: Target characters per chunk
        overlap: Characters of overlap between consecutive chunks

    Returns:
        List of text chunks
    """
    # Split by paragraphs first (preserve semantic units)
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += ("\n\n" + para if current_chunk else para)
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Start new chunk with overlap from previous
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_knowledge_base(force_rebuild: bool = False):
    """
    Build/rebuild the ChromaDB knowledge base from markdown files.

    Args:
        force_rebuild: If True, delete existing collection and rebuild from scratch

    Returns:
        dict: {
            status: "success" | "already_exists",
            documents_processed: int,
            total_chunks: int
        }
    """
    client = _get_client()

    # Check if already built
    if not force_rebuild:
        try:
            collection = client.get_collection(
                name="wellfinanced_knowledge",
                embedding_function=_CustomEmbeddingFunction(),
            )
            if collection.count() > 0:
                return {
                    "status": "already_exists",
                    "documents_processed": 0,
                    "total_chunks": collection.count(),
                }
        except Exception:
            pass  # Collection doesn't exist, create it

    # Delete existing collection if rebuilding
    try:
        client.delete_collection("wellfinanced_knowledge")
    except Exception:
        pass

    collection = _get_collection(client)

    # Load all markdown files
    md_files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md"))
    if not md_files:
        return {
            "status": "no_documents",
            "documents_processed": 0,
            "total_chunks": 0,
        }

    all_chunks = []
    all_ids = []
    all_metadata = []

    for filepath in md_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = _chunk_document(content)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadata.append({
                "source": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    # Add to ChromaDB
    if all_chunks:
        # ChromaDB has a batch limit, process in batches of 40
        batch_size = 40
        for start in range(0, len(all_chunks), batch_size):
            end = min(start + batch_size, len(all_chunks))
            collection.add(
                documents=all_chunks[start:end],
                ids=all_ids[start:end],
                metadatas=all_metadata[start:end],
            )

    return {
        "status": "success",
        "documents_processed": len(md_files),
        "total_chunks": len(all_chunks),
    }


def search_knowledge(query: str, n_results: int = 3) -> list:
    """
    Search the knowledge base for relevant documents.

    Args:
        query: User's question or search query
        n_results: Number of results to return

    Returns:
        List of dicts: [{content, source, relevance_score}, ...]
    """
    try:
        collection = _get_collection()
    except Exception:
        # Collection doesn't exist, try building first
        build_knowledge_base()
        collection = _get_collection()

    if collection.count() == 0:
        build_knowledge_base()

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
    )

    documents = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            documents.append({
                "content": doc,
                "source": results["metadatas"][0][i]["source"] if results["metadatas"] else "unknown",
                "relevance_score": round(
                    1 - results["distances"][0][i], 3
                ) if results["distances"] else 0,
            })

    return documents


def get_relevant_context(query: str, n_results: int = 3) -> str:
    """
    Get relevant knowledge base content as a formatted string.

    Args:
        query: User's question
        n_results: Number of relevant chunks to include

    Returns:
        Formatted string of relevant knowledge for the LLM prompt
    """
    results = search_knowledge(query, n_results)

    if not results:
        return "No relevant knowledge base articles found."

    parts = ["## Relevant Financial Knowledge\n"]
    for r in results:
        parts.append(f"**Source**: {r['source']} (relevance: {r['relevance_score']:.2f})")
        parts.append(r["content"])
        parts.append("---")

    return "\n\n".join(parts)


if __name__ == "__main__":
    print("Building knowledge base...")
    result = build_knowledge_base(force_rebuild=True)
    print(f"Status: {result['status']}")
    print(f"Documents: {result['documents_processed']}")
    print(f"Chunks: {result['total_chunks']}")

    print("\n--- Test Search ---")
    test_queries = [
        "How should I budget as a freelancer?",
        "What's the best way to pay off debt?",
        "هل المفروض أشتري بالتقسيط؟",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        results = search_knowledge(q, n_results=2)
        for r in results:
            print(f"  [{r['source']}] (score: {r['relevance_score']}) "
                  f"{r['content'][:80]}...")
