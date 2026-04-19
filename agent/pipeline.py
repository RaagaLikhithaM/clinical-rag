"""
agent/pipeline.py

Orchestrates the full query flow by connecting intent detection,
query rewriting, hybrid search, and answer generation in the correct
order. This is the single function the server calls for every user
question.

Keeping orchestration here means the server and frontend stay thin.
Neither of them needs to know about retrieval or generation details.
"""

from .generate import detect_intent, rewrite_query, generate_answer
from .retrieval import hybrid_search


# ══ Public API ═════════════════════════════════════════════════════════════════

def run_query(query: str) -> dict:
    """Run the full RAG pipeline for one user question.

    The steps in order:
    1. Detect intent. If the query is conversational, return a chat
       response immediately without touching the knowledge base.
    2. Rewrite the query to improve retrieval quality.
    3. Run hybrid search to get the top-k most relevant chunks.
    4. Check whether the top chunk meets the similarity threshold.
       If not, return an insufficient evidence response.
    5. Generate a cited, hallucination-checked answer from the chunks.

    Args:
        query: the raw user question string.

    Returns:
        Dict with keys:
            answer:    the final answer string shown to the user.
            sources:   list of source filenames cited in the answer.
            intent:    SEARCH or CHAT, for the UI to display.
            top_score: cosine similarity of the best retrieved chunk.
    """
    # Step 1: intent detection
    intent = detect_intent(query)

    if intent == "CHAT":
        return {
            "answer":    "Hello! I am a clinical protocol assistant. "
                         "Ask me a question about treatment guidelines.",
            "sources":   [],
            "intent":    "CHAT",
            "top_score": 0.0,
        }

    # Step 2: rewrite the query for better retrieval
    rewritten = rewrite_query(query)

    # Step 3: hybrid search using the rewritten query
    search_result = hybrid_search(rewritten)

    # Step 4: threshold check
    if not search_result["sufficient"]:
        return {
            "answer":    "Insufficient evidence — the knowledge base does "
                         "not contain reliable information to answer this "
                         "question. Please upload relevant clinical guidelines.",
            "sources":   [],
            "intent":    "SEARCH",
            "top_score": search_result["top_score"],
        }

    # Step 5: generate answer from retrieved chunks
    result = generate_answer(query, search_result["chunks"])

    return {
        "answer":    result["answer"],
        "sources":   result["sources"],
        "intent":    "SEARCH",
        "top_score": search_result["top_score"],
    }
