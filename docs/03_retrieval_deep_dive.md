# 03 — Retrieval Deep Dive

## Why retrieval is the hardest part

Generation is solved — any sufficiently capable LLM can produce a
coherent, well-formatted clinical answer if you give it good context.
The hard problem is retrieval: finding the right 5 chunks out of 2868
that actually answer the specific clinical question being asked.

A system that retrieves the wrong chunks and generates fluently from
them is more dangerous than one that retrieves nothing. It produces
confident-sounding wrong answers.

This system uses three retrieval mechanisms working together.

---

## Semantic search — cosine similarity

### What an embedding is

An embedding is a list of 1024 numbers produced by the `mistral-embed`
model. These numbers represent the meaning of a piece of text as a
point in a 1024-dimensional mathematical space. Two pieces of text with
similar meaning have embeddings that point in similar directions.

```
embed("ACL reconstruction indication") → [0.021, -0.134, 0.887, ..., 0.042]
embed("ACL surgery criteria")          → [0.019, -0.128, 0.891, ..., 0.039]
embed("heart failure ejection fraction") → [-0.412, 0.033, -0.201, ..., 0.187]
```

The first two are close. The third is far away. This is the foundation
of semantic search.

### The cosine similarity formula

```
similarity(A, B) = (A · B) / (|A| × |B|)
```

Where:
- `A · B` = dot product = sum of element-wise multiplications
- `|A|` = magnitude of vector A = √(sum of A squared)
- `|B|` = magnitude of vector B

Result is between -1 and 1. For text embeddings, always between 0 and 1.
A score of 1.0 means identical direction — same meaning. A score of 0.0
means perpendicular — no relationship.

### Why cosine and not Euclidean distance

Euclidean distance measures how far apart two points are in space.
Cosine similarity measures the angle between them. For text:

A short clinical sentence and a long clinical paragraph about the same
topic have different magnitudes but similar directions. Cosine similarity
correctly identifies them as related. Euclidean distance would penalise
the length difference and rank them as distant.

### Implementation — 6 lines of numpy

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
```

No external libraries. The computation runs in microseconds per chunk
on modern hardware.

### Where semantic search fails in clinical text

Semantic search blurs precise values. The embedding for "LVEF ≤35%"
and "LVEF ≤40%" are similar because both are about ejection fraction
thresholds in heart failure. But the 5% difference changes the
treatment recommendation — ICD implantation is indicated at ≤35%, not
≤40%.

Similarly, "semaglutide 0.25mg" and "semaglutide 2.4mg" are
semantically close but clinically very different — one is the diabetes
dose, one is the obesity dose, and payer criteria treat them differently.

This is why BM25 is indispensable.

---

## BM25 — keyword search from scratch

### What BM25 is

BM25 (Best Match 25) is a probabilistic keyword scoring algorithm
developed in the 1970s. Despite its age, it remains one of the strongest
baseline retrieval algorithms and is the foundation of Elasticsearch's
relevance scoring.

The "25" refers to the 25th iteration of the Okapi BM probabilistic
retrieval framework. It encodes two insights that naive term frequency
scoring misses: term frequency saturation, and document length
normalisation.

### The formula

```
BM25(query, doc) = Σ IDF(term) × [tf × (k1+1)] / [tf + k1×(1 - b + b×|d|/avgdl)]
```

Each term:

**IDF(term) = log((N - df + 0.5) / (df + 0.5))**
- N = total number of chunks
- df = number of chunks containing this term
- A term in 2 out of 2868 chunks scores high (rare = informative)
- A term in 1400 chunks scores near zero (common = uninformative)

**tf** = how many times the term appears in this chunk

**k1 = 1.5** — saturation parameter
- Without saturation, a chunk containing "ACL" 50 times would score
  50× higher than one containing it once
- k1 limits this — at k1=1.5, the gain from the 10th occurrence is
  much smaller than from the 1st
- After the first few occurrences, additional repetitions add little

**b = 0.75** — length normalisation
- A longer chunk has more words and more opportunities to match
  query terms by chance
- b=0.75 penalises longer chunks relative to the corpus average
- b=0: no length normalisation
- b=1: full length normalisation

**|d| / avgdl** = this chunk's length divided by average chunk length

### Why BM25 catches what semantic search misses

BM25 treats text as exact tokens. "35" and "40" are different tokens.
"semaglutide" and "liraglutide" are different tokens. "I219" and "I21"
are different tokens.

Clinical text is dense with precise numerical thresholds, drug names,
ICD codes, CPT codes, and laboratory values where exact matching matters.
BM25 is the right tool for this precision while semantic search handles
the meaning and paraphrase.

---

## Reciprocal Rank Fusion

### The problem with combining two ranked lists

After semantic search and BM25 each produce 10 results, we have two
ranked lists that cannot simply be combined by averaging scores.

Cosine similarity ranges from 0 to 1. BM25 scores are unbounded positive
numbers — a typical BM25 score in this corpus might be 3.2 or 7.8.
Averaging them directly would give BM25 scores ~5× the weight of cosine
scores just because of scale, not because of quality.

### The RRF solution

Reciprocal Rank Fusion converts ranks to scores using:

```
RRF_score(chunk) = Σ 1 / (k + rank)
```

Where k=60 (from Cormack, Clarke, Buettcher 2009) and rank is the
position in each list.

**Example:**

| Chunk | Semantic rank | BM25 rank | RRF score |
|---|---|---|---|
| A | 1 | 1 | 1/61 + 1/61 = 0.0328 |
| B | 1 | 10 | 1/61 + 1/70 = 0.0307 |
| C | 3 | 2 | 1/63 + 1/62 = 0.0318 |
| D | 50 | 50 | 1/110 + 1/110 = 0.0182 |

Chunk A (top of both lists) wins. Chunk C (3rd in semantic, 2nd in BM25)
outranks Chunk B (1st in semantic, 10th in BM25) because consistent
strong performance across both lists is rewarded.

### Why k=60

The constant prevents a single top-ranked result from dominating too
strongly. Without k, the #1 result would get score 1.0 and #2 would
get 0.5 — a 2× advantage for being one rank higher. With k=60, #1 gets
1/61 and #2 gets 1/62 — still better, but not unreasonably so.

The value 60 was shown empirically in the original paper to outperform
other values across a wide range of retrieval tasks.

### Why RRF over weighted combination

A weighted combination like `0.6 × cosine + 0.4 × normalised_bm25`
requires choosing the weights. Any choice is arbitrary and
domain-dependent. A different corpus, a different query distribution,
a different chunking strategy could all shift the optimal weights.

RRF is tuning-free. It uses only the ranks, not the raw scores, so it
is naturally scale-invariant. It consistently outperforms naive score
combination in benchmark evaluations.

---

## The 0.70 similarity threshold

### What it does

If the top chunk's cosine similarity to the query is below 0.70, the
pipeline returns "I cannot answer this based on the available guidelines"
instead of generating an answer.

### Why 0.70 specifically

0.70 was determined empirically. Below this value, retrieved chunks
were topically adjacent to the query but not directly relevant to the
specific question:

- Query: "ibuprofen dosage for children under 5"
- Top retrieved chunk: CDC opioid guideline passage stating the guideline
  "does not apply to patients under 18"
- Cosine similarity: 0.75 (above threshold but the content is a refusal)
- The generation correctly returned "cannot answer" because the evidence
  doesn't cover this question

- Query: "what is the treatment for cancer"
- Top cosine similarity: 0.52 (below threshold)
- Returned: insufficient evidence

In clinical use, refusing to answer is safer than generating an answer
from weakly related evidence. A clinician who gets "insufficient evidence"
knows to consult a different source. A clinician who gets a fluent,
confident, but wrong answer based on a tangentially related chunk may
act on it.

### Production consideration

0.70 is hardcoded. In production it should be:
- A configurable environment variable
- Potentially domain-specific — oncology queries against an NCCN KB
  may need a different threshold than general medicine queries
- Calibrated against a test set of known good and bad retrievals

---

## Chunking decisions and their impact on retrieval

### Why chunk size matters for retrieval

A chunk that is too small loses clinical context. A criterion like
"ACL reconstruction is recommended when the patient has failed
conservative therapy AND presents with functional instability AND the
concomitant injury pattern warrants surgical repair" must appear intact
in at least one chunk to be retrieved correctly. If split across two
chunks, neither half is retrievable.

A chunk that is too large introduces noise. A 2048-token chunk from a
clinical guideline will contain the specific recommendation you want
AND several other recommendations about different patient populations.
The embedding of that chunk reflects all the content — it is pulled in
multiple directions and may not rank highly for any specific query.

### Why 512 tokens with 50-token overlap

512 tokens ≈ 1-2 clinical paragraphs. This is the right size for most
guideline content:

- Large enough to contain a complete recommendation with its qualifying
  conditions
- Small enough that the embedding reflects a coherent topic
- The 50-token overlap ensures criteria at chunk boundaries appear
  complete in at least one chunk

### Why tiktoken specifically

We tokenise using `cl100k_base` — the same encoding the Mistral API
uses internally. Chunking by characters or words would create chunks
of unpredictable token length. A chunk of 400 words might be 450 or
650 tokens depending on the content. By chunking in actual tokens, we
guarantee every chunk is within the embedding model's context window.

### Why pdfplumber over PyPDF2

Clinical guidelines contain:
- Multi-column layouts (recommendation on left, evidence on right)
- Tables of graded recommendations
- Footnotes with key caveats
- Headers and subheaders that structure content

PyPDF2 reads PDF byte streams in order — it concatenates columns left
to right, top to bottom, in the order they appear in the file's internal
structure. For multi-column documents this produces garbled text where
column 1 and column 2 are interleaved.

pdfplumber uses spatial analysis to reconstruct reading order. It
identifies text blocks, sorts them by spatial position, and reads them
in the order a human would. For clinical guidelines, this preserves the
relationship between recommendations and their qualifying conditions.
