# MDM Address Validation & Enrichment (Honeywell)

## Overview
This project is part of a Honeywell MDM initiative to address data quality issues in customer records that prevent successful enrichment. It focuses on cleaning, structuring, and validating data so that records can be reliably enriched with firmographic attributes.

---

## Problem Statement / Business Impact
Honeywell's MDM system contains ~5M Customer Master records. Enrichment is performed using Dun & Bradstreet (D&B), a third-party data provider. However, ~36K records fail to return enrichment due to poor source data quality, including:
- Malformed or incomplete addresses  
- Placeholder or dummy values  
- Alphanumeric codes in company names (e.g. "TJ Maxx 01607")  
- Multilingual inconsistencies (Chinese, Spanish, Russian, etc.)
- Encoding corruption (mojibake — e.g. "Málaga" → "MÃ¡laga")

As a result, these records lack critical firmographic attributes such as:
- Legal name  
- Corporate hierarchy (parent / domestic ultimate / global ultimate / HQ)
- Industry classifications (NAICS, SIC)  
- Website and domain  

This impacts overall data quality and downstream business processes (billing, analytics, revenue rollup).

---

## Project Overview
To address this issue, the project follows a two-step approach:

1. **Address Validation & Correction**
   - Use Azure Maps geolocation API to validate addresses  
   - Identify errors (missing components, mismatches, formatting issues)  
   - Generate corrected address suggestions through a 3-fallback cascade
2. **Company Verification & Enrichment**
   - Verify that the company exists at the validated address  
   - Use a 3-tier match strategy (Azure Fuzzy → Azure POI → GPT-4.1 web search)
   - Extract: legal name, full address, hierarchy, website, domain, NAICS/SIC, employee count, revenue, year established, industry

---

## Pipeline Architecture
The pipeline runs in 4 stages, with 15 parallel workers processing records end-to-end:

| Stage | Purpose | Key Operations |
|-------|---------|----------------|
| **1. Pre-Processing** | Clean & normalize raw data | Mojibake rescue, language detection + translation, abbreviation normalization, garbage street flagging |
| **2. Address Validation** | Verify physical existence | Azure Maps API call, score gate (≥0.85), 3-fallback cascade (drop street → drop state/zip → city only) |
| **3. Routing** | Decide downstream path | FULL_MATCH (strong address) / NAME_FIRST (weak address, strong name) / SKIP (neither) |
| **4. Match + Enrich** | Confirm company & pull firmographics | Tier 1 Azure Fuzzy → Tier 2 Azure POI → Tier 3 GPT-4.1 with web search; HQ hierarchy resolution |

---

## Source Data
- Total records (failing D&B enrichment): ~36K  
- POC dataset: 36,230 records  

### Fields
- **MDM_KEY** – unique identifier  
- **ROWID_SYSTEM** – row identifier  
- **SRC_KEY** – source system identifier  
- **SOURCE_NAME** – company name  
- **FULL_ADDRESS** – company address (delimited by `|#|#`)
- **name_category / sub_category** – metadata about name quality  
- **address_category / sub_category** – metadata about address quality  
- **name_reason / address_reason** – explanation of data condition  

---

## Results (POC Run on 36,230 records)

### Headline Outcomes
| Metric | Value |
|---|---|
| Records processed | 36,230 |
| Address validation pass rate | **96.8%** (35,074) |
| Companies verified | **75.2%** (27,261) |
| Fully enriched (all 6 core fields) | **55.1%** (19,954) |
| Partially enriched | **18.7%** (6,791) |
| Manual review queue (after cleanup) | **23.5%** (8,515) |
| End-to-end runtime | ~4.5 hours |


### Enrichment Breakdown
Of all 36,230 records, the final landing distribution:
- **19,954 fully enriched** (55.1%) — verified + all 6 core fields filled
- **6,791 partially enriched** (18.7%) — verified, some fields filled
- **516 verified, no enrichment** (1.4%)
- **8,969 not verified** (24.8%)

### Field Fill Rates (on 27,261 verified records)
| Field | Fill Rate |
|---|---|
| Headquarters Address | 96.4% |
| Legal Name | 90.0% |
| Industry | 87.9% |
| Email Domain | 81.3% |
| NAICS Code | 78.4% |
| SIC Code | 77.9% |
| Year Established | 76.7% |
| Employee Count Range | 73.3% |
| Revenue Range | 63.1% |
| Global Ultimate | 34.0% |
| Domestic Ultimate | 33.7% |
| Parent Company | 23.6% |

> Hierarchy fields (parent / ultimate) are weaker because most records in this dataset are standalone SMBs without public corporate hierarchy data — same gap D&B faces.

### Tier Distribution (Stage 4)
- Tier 1 Azure Fuzzy: 3,894 (10.7%)
- Tier 2 Azure POI: 1,348 (3.7%)
- Tier 3 GPT-4.1 web search: 30,988 (85.5%)

### Manual Review Cleanup
After running the cleanup script (`clean_manual_review_vscode.py`), the manual review queue dropped from **49.4% → 23.5%** via 4 targeted fixes:

| Fix | Records | What It Does |
|---|---|---|
| Fix B | 8,272 | DIFF_ADDR with verified `best_address` → `corrected_address` column added |
| Fix D | 1,088 | NOT_FOUND with HIGH/MEDIUM confidence + `best_address` → promoted to COMPANY_FOUND_DIFF_ADDR |
| Fix C | 19 | COMPANY_FOUND with HIGH confidence over-caught by filter → removed |
| Fix A | 8 | UNVERIFIED but company actually confirmed → relabelled (final tag count after Fix B overlap) |
| **Total removed** | **9,387** | |

---

## Verification & Anti-Hallucination Mechanisms
The pipeline has 5 built-in safeguards against AI errors:

1. **Verdict Rigor Guard** — If GPT-4.1 claims `address_match=CORRECT` but the MDM street number isn't in the AI's locations text, the verdict is auto-downgraded to PARTIAL + LOW confidence. Caught **8,026 overclaims** in this run.
2. **NAICS / SIC Format Validation** — Post-call regex enforces NAICS = 2–6 digits, SIC = 4 digits. Invalid codes are nulled.
3. **Deterministic-First Tiers** — Azure Fuzzy and POI run before AI. 14.4% of records resolved without any AI call.
4. **Source URL Citations** — Every AI call records the actual web URLs used (`sources_verify`, `sources_enrich`, `sources_hq` columns) for independent audit.
5. **Address Gate** — FULL_MATCH path requires score ≥ 0.85 AND match type = Point Address or Address Range (not just Street).

---

## Project Structure
```
mdm-address-validation/
├── pipeline/                    → main pipeline logic
│   └── mdmep_pipeline.py        → main pipeline (4 stages)
├── scripts/
│   └── clean_manual_review_vscode.py  → post-run manual review cleanup
├── utils/                       → helper modules (encoding, parsing, etc.)
├── tests/                       → unit tests
├── data/
│   ├── raw/                     → input CSV
│   ├── intermediate/
│   └── output/                  → final CSV + Excel reports
├── reports/                     → summary + narrative + xlsx workbook
├── .env                         → API keys (not committed)
├── requirements.txt
└── README.md
```

---

## How to Run

### Prerequisites
- Python 3.8+
- API keys for Azure Maps and OpenAI (set in `.env`):
```
  AZURE_MAPS_KEY=your_key_here
  OPENAI_API_KEY=your_key_here
```

### Setup
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate      # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline
```bash
# Full run on input CSV
python pipeline/mdmep_pipeline.py

# Test mode — process only first 10 records (verifies setup, parallelism)
python pipeline/mdmep_pipeline.py --test

# Custom input/output paths
python pipeline/mdmep_pipeline.py --input my_data.csv --output my_results.csv
```

The pipeline supports **resume** — if interrupted, it will pick up from the last completed record on restart.


---

### Key Output Columns
- **Identifiers**: `MDM_KEY`, `SOURCE_NAME`, `FULL_ADDRESS_RAW`, `country`
- **Address validation**: `addr_final_status`, `val_score`, `val_returned_freeform`
- **Company match**: `match_status`, `tier_used`, `canonical_name`, `company_exists`, `address_match`, `ai_confidence`, `confidence_score`
- **Enrichment**: `legal_name`, `parent_company`, `domestic_ultimate`, `global_ultimate`, `naics_code`, `sic_code`, `industry`, `headquarters_address`, `email_domain`
- **Audit**: `sources_verify`, `sources_enrich`, `sources_hq` (clickable URLs the AI grounded against)

---

## Performance & Cost
- **Throughput**: ~2.22 records/second with 15 parallel workers
- **End-to-end runtime**: ~4.5 hours for full 36,230 dataset
- **Caching**: name+country, enrichment, and HQ caches saved 4,281 API calls
---

## Known Limitations
- **Hierarchy data is sparse** — only 23–34% of records have parent/ultimate data because most are standalone SMBs without public corporate hierarchies. This is a data availability problem, not a pipeline limitation.
- **Truly stuck records (~3,716, 10.3% of total)** — small/local businesses with no web presence, dissolved companies, or generic code-like names. No automated process can resolve these. Recommendation: accept as UNVERIFIABLE in MDM, route to D&B Match API, or use the `mdm_address_occupant` field (Azure POI reverse-geocode of what's physically at the address).
- **Occasional OpenAI JSON parse errors** — affects ~1,394 records. Handled gracefully (record gets empty enrichment fields), but improving the JSON parser with truncation recovery would recover most.

---

## Roadmap / Next Steps
- [ ] Add local-language search prompt for non-English records (CN, ES, IT, MX, DE) — recover ~2,030 LOW confidence records. 
- [ ] Patch `_enforce_address_match_rigor()` to loosen street-number check for non-US countries — recover ~649 pipeline downgrade victims, no cost
- [ ] Re-run remaining 1,747 NOT_FOUND-with-best_address records with international prompt.
- [ ] Add JSON parse repair for truncated OpenAI responses (recovers ~1,394 records)
- [ ] Scale validation to full 36K dataset, then 5M MDM base

---

## Status
**POC Complete** — Pipeline tested end-to-end on 36,230 records. 55.1% fully enriched, 23.5% in genuine manual review, ~10% irreducibly stuck. Ready for review and decision on next-phase scaling.

---

## Summary
This project transforms unstructured, inconsistent MDM records into clean, validated, enrichment-ready data. By addressing data quality issues at the source, it enables reliable enrichment and improves the overall integrity of customer master data.

**75% of failed-enrichment records recovered. Manual review burden cut in half. Every AI claim is independently auditable via cited source URLs.**
