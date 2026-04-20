# 07 — Clinical Domains

## How the knowledge base maps to clinical practice

The Clinical Protocol Assistant covers three clinical domains. This
document explains each domain, the clinical problems the system can
and cannot answer, and how the domains connect to each other in
real patient care pathways.

---

## Domain 1 — Musculoskeletal (MSK)

### The clinical landscape

MSK conditions are the most common reason for prior authorization
requests in commercial insurance. ACL reconstruction, total knee
arthroplasty, total hip arthroplasty, and rotator cuff repair together
account for a disproportionate share of PA volume relative to their
total cost because payers have high denial rates for these procedures
when documentation is incomplete.

The specific statistic that motivates the MSK focus: the average denial
rate for joint surgery PA is 15-22% on first submission. Of those
denials, approximately 70% are overturned on appeal. This means the
majority of denials are documentation failures — the clinical indication
existed, but the note didn't prove it. This is the problem the system
addresses.

### What the system knows about MSK

**From AAOS ACL CPG 2022:**

The guideline covers ACL injuries in adults from initial evaluation
through surgical management and return to sport. Key clinical knowledge:

*Diagnosis:* The Lachman test has sensitivity 85% and specificity 94%
for ACL tears. The pivot shift test is highly specific. MRI has 92%
sensitivity and 95% specificity. The system can explain why imaging is
recommended before surgery and what imaging findings support the
indication.

*Treatment decision:* There is no universal recommendation for surgical
vs non-surgical management — the decision depends on patient age,
activity level, concomitant injuries, and patient preference. The
system can explain all of these decision points with citations.

*Timing:* Early reconstruction (within 3-6 months) is associated with
lower risk of secondary meniscal damage. Delayed reconstruction (>1 year)
in older patients is associated with higher osteoarthritis risk. These
are specific, answerable questions.

*Evidence grades:* The system retrieves not just the recommendation but
its evidence grade. A Strong recommendation from AAOS has multiple
high-quality RCTs behind it. A Limited recommendation has only
retrospective case series. A clinician or UM nurse can assess the
strength of the evidence, not just the conclusion.

**From Carelon Joint Surgery Guidelines 2024:**

This is the payer-side document. It specifies what documentation a
UM nurse must see before approving joint surgery. Key content:

- ICD code for the primary diagnosis
- Duration and type of conservative therapy attempted
- Functional impairment score (KOOS, IKDC, or equivalent)
- Imaging findings that confirm the pathology
- Provider specialty (orthopaedic surgeon attestation)

The system can explain each requirement and why payers have it —
understanding the rationale helps providers submit better documentation
on the first attempt.

**From CMS LCD (Local Coverage Determination):**

For Medicare and Medicare Advantage patients, CMS sets the legal floor
for coverage criteria. All MA plans must align to the LCD. The system
can answer questions about what CMS requires specifically for Medicare
patients, which is often different from commercial payer criteria.

**From VA/DoD Knee OA Guideline 2020:**

Covers the conservative management phase. A veteran or active duty
patient with knee pain and early OA will typically go through:
- Weight management counselling
- Physical therapy (6-12 weeks)
- NSAIDs or topical agents
- Intra-articular injections
- Activity modification

Documentation of this pathway is what makes the PA record complete.
The system can explain each step and what documentation proves adequate
conservative management was attempted.

### What the system does NOT know about MSK

- Specific surgical technique details — which graft type (autograft vs
  allograft, patellar tendon vs hamstring)
- Post-operative rehabilitation protocols
- Specific implant selection criteria for joint replacement
- Cost-effectiveness data comparing surgical approaches
- Paediatric MSK — most guidelines in the KB explicitly exclude patients
  under 18

---

## Domain 2 — Cardiovascular

### Why cardiovascular is in an MSK-focused system

Two reasons:

**Clinical reason:** Cardiovascular comorbidities directly affect
surgical candidacy for MSK procedures. A patient requesting total knee
arthroplasty with LVEF 28% and decompensated heart failure may not be
appropriate for elective surgery. The ACC/AHA perioperative cardiac
risk guidelines (not currently in the KB but a natural addition)
connect the cardiovascular and MSK domains.

**Architectural reason:** Having a second clinical domain in the
knowledge base proves the pipeline is domain-agnostic. The same
retrieval logic that finds ACL reconstruction criteria also finds
beta blocker initiation thresholds. No domain-specific code anywhere.

### What the system knows about cardiovascular

**From ACC/AHA/HFSA Heart Failure Guideline 2022:**

*LVEF classification:*
- HFrEF: LVEF ≤40% — systolic dysfunction, most evidence for treatment
- HFmrEF: LVEF 41-49% — mildly reduced, emerging evidence
- HFpEF: LVEF ≥50% — preserved, limited proven treatments

*GDMT (Guideline-Directed Medical Therapy) for HFrEF:*
The four drug classes with Class I recommendations:
1. ACE inhibitor or ARB or ARNI (sacubitril/valsartan)
2. Beta blocker (carvedilol, metoprolol succinate, or bisoprolol)
3. Mineralocorticoid receptor antagonist (spironolactone or eplerenone)
4. SGLT2 inhibitor (dapagliflozin or empagliflozin)

*Device therapy:*
- ICD indicated for LVEF ≤35% despite 3 months GDMT
- CRT-D indicated for LVEF ≤35% with LBBB and QRS ≥150ms

The system can answer questions about all of these thresholds with
specific citations.

### The hallucination check example from this domain

During testing, a query about "recommended ejection fraction threshold
for initiating beta blocker therapy" returned an answer that included:
"There is no specific ejection fraction threshold for initiating beta
blockers in HFmrEF, but evidence supports their use in select cases."

The hallucination check removed this claim because:
- The source passage stated only the Class 2b recommendation for HFmrEF
- The model had added an interpretation ("evidence supports their use")
  that went beyond the literal source text

This is the clinical safety behavior the system is designed for. The
model is instructed to cite every claim. The hallucination check
verifies that every cited claim is directly supported by the source.

---

## Domain 3 — Pain Management

### The clinical landscape

Pain management intersects with both MSK and cardiovascular care. Post-
operative pain after joint surgery requires opioid management. Chronic
MSK pain in patients with cardiovascular disease limits NSAID use.
The opioid crisis has created a complex regulatory environment around
opioid prescribing that both providers and payers navigate.

### What the system knows about pain management

**From CDC Clinical Practice Guideline for Prescribing Opioids 2022:**

This is the federal-level guidance that replaced the 2016 version. Key
changes in 2022:
- Removed the hard 90 MME/day threshold (replaced with clinical judgment)
- Emphasised individualised care based on patient circumstances
- Clarified that the guideline does not apply to cancer pain, palliative
  care, or end-of-life care
- Explicitly excluded patients under 18

*For acute pain:*
- Prescribe the lowest effective dose for the shortest duration
- For most non-traumatic, non-surgical acute pain: a few days or less
- Evaluate at least every 2 weeks if continuing
- Prescribe a taper if continuous use exceeds a few days

*Taper schedules the system can retrieve:*
- Used continuously >3 days but <1 week: reduce daily dose by 50% for 2 days
- Used continuously ≥1 week but <1 month: reduce by ~20% every 2 days
- Used >1 month: slower taper with individualised schedule

**From APA Clinical Practice Guideline for Chronic MSK Pain 2024:**

*Non-pharmacological interventions the system knows:*
- Cognitive-behavioural therapy (CBT) — strong evidence for chronic pain
- Acceptance and Commitment Therapy (ACT) — emerging evidence
- Mindfulness-based stress reduction (MBSR)
- Exercise therapy — must be documented for PA purposes
- Biofeedback

Payers increasingly require documentation of non-pharmacological
interventions before approving opioid continuation. The APA guideline
provides the clinical evidence base for why these interventions are
recommended and what documentation of them should include.

---

## Cross-domain queries — the most valuable use case

The system's highest-value queries involve multiple domains simultaneously.

**Example 1 — Cardiovascular comorbidity affecting MSK surgical candidacy:**

"My patient needs total knee replacement but has HFrEF with LVEF 32%
and is on carvedilol. What are the considerations?"

The system retrieves:
- Carelon criteria for joint arthroplasty (MSK domain)
- ACC/AHA recommendations on cardiac risk for non-cardiac surgery
  (cardiovascular domain)

These two sources answer different parts of the question — the payer
will want the cardiac comorbidity documented and cleared, and the
ACC/AHA guideline defines what "cleared" means.

**Example 2 — Pain management following MSK procedure:**

"What opioid prescribing duration is appropriate for post-ACL
reconstruction pain management?"

The system retrieves:
- CDC guideline on post-surgical opioid prescribing
- AAOS guideline on ACL reconstruction recovery timeline

Together they provide: the clinical recovery timeline that justifies
the duration, and the federal guideline that defines appropriate
prescribing within that timeline.

**Example 3 — Conservative therapy documentation for PA:**

"What evidence of conservative therapy is required before knee
arthroplasty PA will be approved?"

The system retrieves:
- Carelon criteria specifying required PT documentation
- VA/DoD guideline defining adequate conservative management

One answers what the payer requires; the other defines what adequate
treatment looks like — the complete picture for preparing a PA submission.

---

## Future domains — natural extensions

**Oncology:**
NCCN guidelines for NSCLC, breast cancer, colorectal cancer. The
oncology PA domain has the highest denial rate (41% for immunotherapy)
and the highest clinical urgency (27-day delays correlate with tumor
progression). This is the prior-auth-rag project.

**Diabetes / endocrinology:**
ADA Standards of Medical Care 2024. GLP-1 receptor agonist PA criteria
(the highest-volume PA category in primary care). The semaglutide
demo scenario from earlier sessions fits here.

**Infectious disease:**
IDSA guidelines for sepsis, pneumonia, antimicrobial stewardship.
MIMIC-IV contains extensive ICU data that could combine with IDSA
guidelines for a research-grade system.

**Obstetrics:**
ACOG Practice Bulletins for preeclampsia, gestational hypertension,
caesarean delivery criteria. Relevant to maternal mortality research
and to high-volume obstetric PA requests.
