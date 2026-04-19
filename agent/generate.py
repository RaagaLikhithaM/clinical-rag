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
import time
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

LIST_ANSWER_PROMPT = """You are a clinical knowledge assistant. The user
is asking for a list, comparison, or structured breakdown.

Answer using only the evidence provided below. Format your response as a
structured list or table. Label each item clearly. Cite every item with
its source using [Source: filename, Page: number].

If the evidence does not contain enough information, say exactly:
I cannot answer this based on the available guidelines.

Evidence:
{context}

Question: {query}

Structured answer:"""


PII_REFUSAL = """I cannot process queries that contain personal health
information such as patient names, dates of birth, medical record numbers,
or Social Security numbers.

Please rephrase your question using general clinical terms without
identifying information. For example, instead of asking about a specific
patient, describe the clinical scenario in general terms."""


MEDICAL_DISCLAIMER = """

---
*Clinical disclaimer: This response is generated from published clinical
guidelines for informational purposes only. It does not constitute medical
advice and should not replace clinical judgment. Always consult the
original guideline documents and applicable institutional protocols before
making clinical decisions.*"""
# ══ PII detection ══════════════════════════════════════════════════════════════

import re

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",          # SSN format
    r"\bMRN\s*[:#]?\s*\d+\b",          # medical record number
    r"\bDOB\s*[:#]?\s*\d{1,2}/\d{1,2}", # date of birth
    r"\bpatient\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # "patient John Smith"
]


def contains_pii(query: str) -> bool:
    """Return True if the query appears to contain personal health information.

    Checks for SSN patterns, MRN references, DOB formats, and explicit
    patient name patterns. Clinical questions phrased in general terms
    will not be flagged.

    Args:
        query: the raw user question string.

    Returns:
        True if PII patterns are detected, False otherwise.
    """
    for pattern in PII_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False

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
def detect_answer_shape(query: str) -> str:
    """Classify whether the query needs a structured list or prose answer.

    List queries ask for comparisons, rankings, options, or enumerations.
    Prose queries ask for explanations, recommendations, or single answers.

    Args:
        query: the rewritten query string.

    Returns:
        The string LIST or PROSE.
    """
    list_triggers = [
        "list", "compare", "differences", "options", "steps",
        "criteria", "what are", "which are", "enumerate", "summarise",
        "summary", "breakdown", "types of", "examples of",
    ]
    q_lower = query.lower()
    for trigger in list_triggers:
        if trigger in q_lower:
            return "LIST"
    return "PROSE"



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

    Selects between prose and structured list prompt templates based on
    the query shape. Appends a medical disclaimer to all clinical answers.
    Runs a hallucination check as a second Mistral call.

    Args:
        query:  the original user question.
        chunks: top-k chunks returned by hybrid_search.

    Returns:
        Dict with keys:
            answer:   the verified answer string with disclaimer.
            sources:  list of unique source filenames cited.
    """
    import time

    context = build_context(chunks)
    client = Mistral(api_key=MISTRAL_API_KEY)

    # Choose prompt template based on query shape
    shape = detect_answer_shape(query)
    prompt_template = LIST_ANSWER_PROMPT if shape == "LIST" else ANSWER_PROMPT

    # First call: generate the answer
    answer_response = client.chat.complete(
        model=GENERATION_MODEL,
        messages=[{
            "role": "user",
            "content": prompt_template.format(context=context, query=query)
        }],
        max_tokens=600,
        temperature=0.2,
    )
    raw_answer = answer_response.choices[0].message.content.strip()

    # Small delay to respect free tier rate limits
    time.sleep(1)

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

    # Append medical disclaimer to all clinical answers
    final_answer = verified_answer + MEDICAL_DISCLAIMER

    sources = list({chunk["source"] for chunk in chunks})

    return {
        "answer":  final_answer,
        "sources": sources,
    }


