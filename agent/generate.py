"""
agent/generate.py

Handles everything between receiving a user query and returning a
final answer. The steps are: detect whether the query needs a
knowledge base search, rewrite the query to improve retrieval,
build a prompt from the retrieved chunks, call Mistral to generate
an answer, and inject citations into the response.

We keep all prompt templates as module-level constants so they are
easy to find and modify without touching any logic.
"""

import os
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GENERATION_MODEL = "mistral-large-latest"


# ══ Prompt templates ═══════════════════════════════════════════════════════════

INTENT_PROMPT = """You are a classifier. Decide if the user message
requires searching a clinical knowledge base.

Reply with exactly one word: SEARCH or CHAT.

SEARCH means the message is a clinical question that needs retrieved
evidence to answer correctly.

CHAT means the message is a greeting, small talk, or something that
does not need medical documents.

User message: {query}"""


REWRITE_PROMPT = """You are a search query optimizer for a clinical
knowledge base containing treatment guidelines and protocols.

Rewrite the following question into a concise search query that will
retrieve the most relevant clinical passages. Remove conversational
words. Keep medical terms exact.

Original question: {query}

Rewritten query:"""


ANSWER_PROMPT = """You are a clinical knowledge assistant. Answer the
question using only the evidence provided below. Do not use any
knowledge outside of these passages.

If the evidence does not contain enough information to answer, say
exactly: I cannot answer this based on the available guidelines.

For every claim in your answer cite the source using the format
[Source: filename, Page: number].

Evidence:
{context}

Question: {query}

Answer:"""


HALLUCINATION_CHECK_PROMPT = """You are a fact checker. You will be
given an answer and the source passages it was based on.

Check every factual claim in the answer against the passages.
If any claim is not supported by the passages, rewrite the answer
removing that claim.

If all claims are supported, return the answer unchanged.

Source passages:
{context}

Answer to check:
{answer}

Verified answer:"""


# ══ Intent detection ═══════════════════════════════════════════════════════════

def detect_intent(query: str) -> str:
    """Classify the query as SEARCH or CHAT using Mistral.

    We run intent detection before retrieval so that greetings and
    off-topic messages never hit the knowledge base. This saves API
    calls and prevents irrelevant chunks from being returned.

    Args:
        query: the raw user message.

    Returns:
        The string SEARCH or CHAT.
    """
    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=GENERATION_MODEL,
        messages=[{
            "role": "user",
            "content": INTENT_PROMPT.format(query=query)
        }],
        max_tokens=5,
        temperature=0.0,
    )
    result = response.choices[0].message.content.strip().upper()
    return "SEARCH" if "SEARCH" in result else "CHAT"


# ══ Query rewriting ════════════════════════════════════════════════════════════

def rewrite_query(query: str) -> str:
    """Rewrite the user query for better retrieval.

    Conversational phrasing like 'can you tell me about' reduces
    retrieval quality because the embedding model attends to those
    words. Rewriting to a concise clinical phrase improves the cosine
    similarity match against guideline text.

    Args:
        query: the original user question.

    Returns:
        A rewritten query string optimised for embedding search.
    """
    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=GENERATION_MODEL,
        messages=[{
            "role": "user",
            "content": REWRITE_PROMPT.format(query=query)
        }],
        max_tokens=60,
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


# ══ Context building ═══════════════════════════════════════════════════════════

def build_context(chunks: list) -> str:
    """Format retrieved chunks into a numbered context block.

    Each chunk is labelled with its source file and page number so
    the model can produce accurate citations in its answer.

    Args:
        chunks: list of chunk dicts from hybrid_search.

    Returns:
        A formatted string ready to insert into the answer prompt.
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        header = f"[{i}] Source: {chunk['source']}, Page: {chunk['page']}"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(parts)


# ══ Generation ═════════════════════════════════════════════════════════════════

def generate_answer(query: str, chunks: list) -> dict:
    """Generate a cited answer from retrieved chunks using Mistral.

    The function runs two Mistral calls. The first generates the
    initial answer grounded in the retrieved passages. The second
    runs a hallucination check that removes any claim not supported
    by the source text.

    Args:
        query:  the original user question.
        chunks: top-k chunks returned by hybrid_search.

    Returns:
        Dict with keys:
            answer:   the verified answer string.
            sources:  list of unique source filenames cited.
    """
    context = build_context(chunks)
    client = Mistral(api_key=MISTRAL_API_KEY)

    # First call: generate the answer
    answer_response = client.chat.complete(
        model=GENERATION_MODEL,
        messages=[{
            "role": "user",
            "content": ANSWER_PROMPT.format(context=context, query=query)
        }],
        max_tokens=600,
        temperature=0.2,
    )
    raw_answer = answer_response.choices[0].message.content.strip()

    # Second call: hallucination check
    verified_response = client.chat.complete(
        model=GENERATION_MODEL,
        messages=[{
            "role": "user",
            "content": HALLUCINATION_CHECK_PROMPT.format(
                context=context, answer=raw_answer
            )
        }],
        max_tokens=600,
        temperature=0.0,
    )
    verified_answer = verified_response.choices[0].message.content.strip()

    sources = list({chunk["source"] for chunk in chunks})

    return {
        "answer":  verified_answer,
        "sources": sources,
    }