# 04 — Clinical Workflows

## Who uses this system and how

The Clinical Protocol Assistant is designed for three personas who
operate at different points in the clinical workflow. Understanding
each persona's actual workflow — not an imagined version of it — is
what makes the system's design decisions defensible.

---

## Persona 1 — Utilization Management Nurse

### Who she is

A UM nurse works for a payer or health system reviewing prior
authorization requests submitted by providers. She receives a clinical
note from a provider requesting approval for a procedure — ACL
reconstruction, total knee arthroplasty, opioid continuation — and
must determine whether the submitted documentation meets the applicable
payer criteria.

She uses tools like InterQual, MCG, or payer-specific portals daily.
She reviews dozens of PA requests per shift. The bottleneck is not
clinical judgment — it is finding the relevant criteria in a 200-page
payer policy document and matching them against the submitted note.

### Her workflow without this system

1. Receive PA request with clinical note (fax, portal, or EHR message)
2. Identify the procedure and payer
3. Navigate to the correct Carelon / InterQual / MCG criteria
4. Manually read through the criteria to find the relevant section
5. Compare each criterion against the clinical note
6. If documentation is missing, contact the provider's office
7. Document the decision in the tracking system

Steps 3-5 take 15-25 minutes per request. A UM nurse reviewing 20-30
requests per shift spends 5+ hours on criteria lookup alone.

### Her workflow with this system

1. Receive PA request
2. Type the clinical scenario into the query interface:
   "Patient with ACL tear, failed 6 weeks PT, functional instability,
   positive Lachman. Requesting ACL reconstruction."
3. System returns in 30 seconds:
   - Relevant Carelon criteria with exact documentation requirements
   - AAOS clinical evidence supporting the indication
   - CMS LCD requirements for Medicare patients
   - Checklist of what is present and what is missing

The system does not make the PA decision — she does. But it eliminates
the lookup time and ensures she is comparing against the right criteria.

### What the system must do for this persona

- Return precise payer criteria, not clinical recommendations
  (she knows the clinical evidence; she needs the administrative rules)
- Cite sources so she can verify and document
- Handle specific clinical terms accurately — "failed conservative
  therapy" must retrieve criteria for what counts as adequate PT
- Refuse to answer when the question is outside the KB rather than
  generating a plausible-sounding but unsupported answer

---

## Persona 2 — Attending Physician at Point of Care

### Who she is

A physician seeing a patient in clinic who needs a quick answer from
a clinical guideline. She is not doing a systematic review — she needs
to know what the ACC/AHA says about starting beta blockers in a patient
with newly diagnosed HFrEF with LVEF 32%.

### Her workflow without this system

1. Open UpToDate or a clinical app
2. Search for "heart failure reduced ejection fraction treatment"
3. Read through a narrative summary
4. Find the specific recommendation she needs
5. Return to the patient

This takes 5-10 minutes of interrupted patient contact time.

### Her workflow with this system

1. Type "beta blocker initiation LVEF 32% newly diagnosed HFrEF"
2. System returns: Class I recommendation for beta blocker therapy in
   LVEF ≤40%, specific agents recommended, with ACC/AHA guideline
   citation and page number
3. 30 seconds, actionable, cited

### What the system must do for this persona

- Answer in under 60 seconds (rate limit permitting)
- Cite the specific guideline and page so she can show the patient or
  document in the chart
- Return a prose answer, not a list — she is in a clinical conversation
- Include the medical disclaimer so it is clear this is decision support,
  not a prescription

---

## Persona 3 — Clinical Researcher or Resident

### Who she is

A second-year resident or clinical researcher who needs to understand
what multiple guidelines say about a clinical question — not just
one answer, but the evidence landscape.

### Her workflow with this system

Types: "What are the recommendations for ACL reconstruction timing and
what evidence supports early vs delayed reconstruction?"

System returns a structured comparison pulling from the AAOS guideline
across multiple chunks, covering early reconstruction within 3-6 months,
delayed reconstruction risk at >1 year, and the evidence grade for
each recommendation.

### What the system must do for this persona

- Return structured LIST output when the query involves comparison
- Show evidence grades, not just recommendations
- Pull from multiple relevant sections of the guideline

---

## The query lifecycle — a concrete example

**Query:** "What documentation is required before ACL reconstruction
can be approved for a 28-year-old competitive soccer player?"

**Stage 1 — PII check:** No patient names, no DOBs, no MRNs. Passes.

**Stage 2 — Intent detection:** "documentation required before ACL
reconstruction" → SEARCH. A clinical administrative question.

**Stage 3 — Query rewrite:** Rewritten to "ACL reconstruction prior
authorization documentation requirements conservative therapy functional
instability"

**Stage 4 — Hybrid search:**
- Semantic search finds chunks about ACL indications, conservative
  management, and PA criteria
- BM25 finds chunks containing exact terms: "prior authorization",
  "documentation", "conservative therapy"
- RRF merges the lists — chunks that appear in both lists rank highest
- Top 5 chunks include: Carelon criteria for joint surgery PA,
  AAOS recommendation on failed conservative therapy, CMS LCD
  documentation requirements

**Stage 5 — Generation:**
The answer lists the documentation requirements: ICD code for ACL tear,
evidence of 6+ weeks conservative therapy (PT notes), functional
impairment score (KOOS or IKDC), imaging confirming ACL pathology,
patient age and activity level documented.

Sources cited: Carelon Joint Surgery Guidelines 2024 Page 14,
AAOS ACL CPG 2022 Page 34, CMS LCD Page 7.

**What makes this answer valuable:** It simultaneously answers the
clinical question (AAOS evidence) and the administrative question
(Carelon and CMS requirements). No single source in isolation gives
the complete answer.

---

## Clinical safety behaviors built into the workflow

### PII before everything

A UM nurse with 20 years of experience might instinctively type "patient
John Smith DOB 04/15/1978 ACL tear, requesting reconstruction." The
system catches this before any data leaves the server. The refusal
message explains how to rephrase in general clinical terms.

### Insufficient evidence is a valid answer

When the ibuprofen paediatric dosage question was asked, the system
returned "I cannot answer this based on the available guidelines" with
75% confidence. The CDC opioid guideline explicitly excludes paediatric
patients — the system retrieved that exclusion and correctly used it
as the answer. Refusing is not a failure mode; it is the correct
clinical safety behavior.

### The medical disclaimer on every answer

Every generated answer ends with:
"This response is generated from published clinical guidelines for
informational purposes only. It does not constitute medical advice and
should not replace clinical judgment."

This is not boilerplate — it is a clinical safety requirement. The
system is decision support, not a replacement for clinical judgment.
A clinician who acts on a generated answer without applying their
clinical expertise is misusing the tool.

### The hallucination check protects against over-confident generation

The language model will sometimes add claims that go beyond what the
source text says. In testing with the ACC/AHA heart failure guideline,
the model added "there is no specific threshold for beta blockers in
HFmrEF beyond Class 2b" — a reasonable inference, but not explicitly
stated in the retrieved text. The hallucination check removed it and
returned only what the source passages directly supported.

In a clinical context, the difference between "the guideline recommends"
and "I infer the guideline implies" is significant. The system only
returns the former.
