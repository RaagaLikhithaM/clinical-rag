# 08 — Cost and Infrastructure

## Cost per query — detailed breakdown

Every user query triggers up to five Mistral API calls. Here is the
exact cost breakdown based on Mistral's pricing at time of writing.
Verify current pricing at docs.mistral.ai/pricing.

### Cost model assumptions

- Intent detection input: ~100 tokens (query + prompt)
- Query rewrite input: ~150 tokens; output: ~60 tokens
- Query embedding: ~200 tokens
- Generation input: ~3,200 tokens (5 chunks × 512 tokens + prompt);
  output: ~600 tokens
- Hallucination check input: ~3,800 tokens; output: ~600 tokens

### Mistral pricing (approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| mistral-large-latest | $8.00 | $24.00 |
| mistral-small-latest | $1.00 | $3.00 |
| mistral-embed | $0.10 | N/A |

### Cost per query — current implementation (all mistral-large)

| Call | Input tokens | Output tokens | Cost |
|---|---|---|---|
| Intent detection | 100 | 5 | $0.0008 |
| Query rewrite | 150 | 60 | $0.0026 |
| Embedding | 200 | — | $0.00002 |
| Generation | 3,200 | 600 | $0.0400 |
| Hallucination check | 3,800 | 600 | $0.0456 |
| **Total** | **7,450** | **1,265** | **~$0.089** |

### Cost per query — optimised implementation

Using mistral-small for classification tasks (intent detection and
query rewrite) where full intelligence is not needed:

| Call | Model | Cost |
|---|---|---|
| Intent detection | mistral-small | $0.0001 |
| Query rewrite | mistral-small | $0.0003 |
| Embedding | mistral-embed | $0.00002 |
| Generation | mistral-large | $0.0400 |
| Hallucination check | mistral-large | $0.0456 |
| **Total** | | **~$0.086** |

The savings from switching classification tasks to mistral-small are
minimal in absolute terms because generation dominates the cost. The
real optimisation levers are caching and skipping the hallucination
check for high-confidence results.

### Cost at scale

| Usage | Queries/day | Cost/day | Cost/month |
|---|---|---|---|
| Demo | 10 | $0.89 | $26.70 |
| Small clinic (10 UM nurses) | 100 | $8.90 | $267 |
| Department (50 staff) | 500 | $44.50 | $1,335 |
| Health system (500 staff) | 5,000 | $445 | $13,350 |

At health system scale, the LLM API cost is the dominant operational
expense. For a 500-staff deployment at $13,350/month, cost optimisation
becomes a priority.

### Cost optimisation levers

**1. Query result caching**
If 20% of queries are the same PA criteria question, caching with
Redis TTL=1 hour eliminates those generation calls entirely.
Estimated savings: 15-20% of total cost.

```python
import hashlib
import redis

def get_cache_key(query: str) -> str:
    return f"query:{hashlib.md5(query.encode()).hexdigest()}"

async def query_with_cache(query: str) -> dict:
    key = get_cache_key(query)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    result = run_query(query)
    redis_client.setex(key, 3600, json.dumps(result))
    return result
```

**2. Skip hallucination check for high-confidence results**
When retrieval confidence is >0.90, the retrieved chunks are strongly
relevant and generation hallucination is less likely. Skipping the
check for these queries saves ~$0.046 per query.
Estimated savings: 30-40% of total cost.

**3. Batch similar queries**
For high-volume environments, batch similar queries and use a single
generation call. Requires a query clustering step.

**4. Local LLM for classification tasks**
Replace mistral-small intent detection and query rewrite with a
locally-hosted BERT-based classifier and T5-based rewriter. Eliminates
the API cost for these steps entirely. Setup cost: GPU infrastructure.

---

## Infrastructure cost

### Current deployment

| Component | Service | Cost |
|---|---|---|
| FastAPI backend | Railway free tier | $0 (until $5 credit runs out) |
| Streamlit frontend | Streamlit Cloud free tier | $0 |
| Database | SQLite on Railway filesystem | $0 |
| Total | | **$0/month** |

**Limitation:** Railway free tier has ephemeral storage (database resets
on restart) and $5 credit limit. After the credit runs out, either
add a credit card or the service sleeps.

### Production deployment — AWS

| Component | Service | Cost/month |
|---|---|---|
| FastAPI backend | ECS Fargate (0.5 vCPU, 1GB) | ~$30 |
| Load balancer | ALB | ~$18 |
| Database | RDS PostgreSQL t3.micro | ~$15 |
| Vector search | pgvector on RDS | $0 (extension) |
| Cache | ElastiCache Redis t3.micro | ~$15 |
| Storage | S3 for PDFs | ~$1 |
| API Gateway | AWS API Gateway | ~$3.50 per million requests |
| **Total infrastructure** | | **~$80/month** |

LLM API cost is separate and scales with usage as shown above.

### Production deployment — Azure (preferred for HIPAA)

Azure has HIPAA BAA available for Azure OpenAI Service and supporting
services.

| Component | Service | Cost/month |
|---|---|---|
| FastAPI backend | Azure Container Apps | ~$25 |
| Database | Azure Database for PostgreSQL | ~$25 |
| Cache | Azure Cache for Redis | ~$15 |
| Storage | Azure Blob Storage | ~$2 |
| API Management | Azure API Management | ~$50 |
| **Total infrastructure** | | **~$120/month** |

Azure is ~50% more expensive than AWS for equivalent infrastructure
but the HIPAA BAA coverage and integrated compliance tooling justify
the premium for a regulated healthcare deployment.

---

## Build vs buy analysis

For a health system considering whether to build this system or
purchase a commercial solution:

### Commercial alternatives

| Product | What it does | Approximate cost |
|---|---|---|
| InterQual (Change Healthcare) | UM criteria lookup | $500K-$2M/year enterprise license |
| MCG Health | Clinical guidelines + UM | $300K-$1M/year |
| UpToDate (Wolters Kluwer) | Clinical reference | $500-$800/clinician/year |
| Navina | AI-powered clinical summaries | Custom pricing |

### Build cost estimate (this architecture)

| Item | Estimated cost |
|---|---|
| Engineering development (3 months, 2 engineers) | $150K-$200K |
| Annual infrastructure (AWS/Azure) | $1,500-$5,000 |
| Annual LLM API (small health system) | $16,000-$50,000 |
| Annual maintenance (0.5 FTE) | $75K |
| **Total Year 1** | **~$250K-$325K** |
| **Total Year 2+** | **~$100K-$130K** |

**Build makes sense when:**
- The health system has specific workflows that commercial products
  don't cover (e.g., cross-domain PA assessment)
- Data sovereignty requirements prevent using external services
- The knowledge base needs to include proprietary internal protocols
  alongside public guidelines

**Buy makes sense when:**
- The use case is standard PA review that commercial products already
  cover
- The health system lacks engineering resources for maintenance
- The timeline is urgent (commercial products deploy in weeks, custom
  builds take months)

The architecture described in this documentation is closest to the
"build for specific workflows" scenario — particularly cross-domain
queries combining clinical guidelines with payer criteria, which no
commercial product currently does well.

---

## API key management

API keys must never appear in source code or version control. This
section describes the correct pattern for managing LLM API credentials
at each stage of deployment.

### Local development

Store the key in a `.env` file in the project root:

```
MISTRAL_API_KEY=your_key_here
```

Add `.env` to `.gitignore` so it is never committed. Load it at runtime
using `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
```

### Cloud deployment (Railway / Render)

Set the key as an environment variable in the hosting platform's
dashboard — never in the Procfile or any committed file. The running
container reads it from the environment at startup.

### Frontend deployment (Streamlit Cloud)

Store in `.streamlit/secrets.toml` — excluded from git via `.gitignore`.
Set via the Streamlit Cloud dashboard under App Settings → Secrets.

```toml
MISTRAL_API_KEY = "your_key_here"
API_BASE = "https://your-backend-url.railway.app"
```

### Production (enterprise)

API keys belong in a dedicated secrets manager:

| Cloud | Service |
|---|---|
| AWS | AWS Secrets Manager |
| Azure | Azure Key Vault |
| GCP | Google Secret Manager |
| Self-hosted | HashiCorp Vault |

**Key rotation policy for production:**
- Rotate every 90 days minimum
- One key per environment (dev / staging / prod)
- Revoke immediately if exposed in any log or commit
- All API calls logged with key identifier (not the key itself)
- Automated rotation scripts tied to CI/CD pipeline

### What happens if a key is accidentally committed

1. Revoke the key immediately in the provider's dashboard
2. Generate a new key
3. Run `git filter-branch` or BFG Repo Cleaner to remove the key
   from git history — `git rm` alone is not sufficient, the key
   remains in history
4. Force-push the cleaned history
5. Assume the key was compromised and audit all API usage logs

The `.gitignore` in this repository excludes `.env` and
`.streamlit/secrets.toml`. Run `git ls-files | grep -E "\.env|secrets"`
before any push to confirm no secrets are tracked.
