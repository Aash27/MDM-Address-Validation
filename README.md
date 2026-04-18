# MDM Address Validation & Enrichment (Honeywell)

## Overview
This project is part of a Honeywell MDM initiative to address data quality issues in customer records that prevent successful enrichment. It focuses on cleaning, structuring, and validating data so that records can be reliably enriched with firmographic attributes.

---

## Problem Statement / Business Impact

Honeywell’s MDM system contains ~5M Customer Master records. Enrichment is performed using Dun & Bradstreet (D&B), a third-party data provider. However, ~34K records fail to return enrichment due to poor source data quality, including:

- Malformed or incomplete addresses  
- Placeholder or dummy values  
- Alphanumeric codes in company names  
- Multilingual inconsistencies  

As a result, these records lack critical firmographic attributes such as:
- Legal name  
- Corporate hierarchy  
- Industry classifications (NAICS, SIC)  
- Website and domain  

This impacts overall data quality and downstream business processes.

---

## Project Overview

To address this issue, the project follows a two-step approach:

1. **Address Validation & Correction**
   - Use geolocation APIs to validate addresses  
   - Identify errors (missing components, mismatches, formatting issues)  
   - Generate corrected address suggestions  

2. **Company Verification & Enrichment**
   - Verify that the company exists at the validated address  
   - Use AI-assisted methods and APIs to extract:
     - Legal name  
     - Full address  
     - Corporate hierarchy (parent, domestic ultimate, global ultimate, HQ)  
     - Website and domain  
     - Industry codes (NAICS, SIC)  

---

## Source Data

- Total records (failing enrichment): ~34K  
- POC dataset: ~100 / ~3,400 records  

### Fields

- **MDM_KEY** – unique identifier  
- **ROWID_SYSTEM** – row identifier  
- **SRC_KEY** – source system identifier  
- **SOURCE_NAME** – company name  
- **FULL_ADDRESS** – company address  
- **name_category / sub_category** – metadata about name quality  
- **address_category / sub_category** – metadata about address quality  
- **name_reason / address_reason** – explanation of data condition  

---

## Goal

Recover ~34K customer records that fail enrichment by:

- Validating and correcting addresses  
- Verifying company existence at the given address  
- Enriching records with firmographic attributes  

Ultimately, the goal is to improve data quality and completeness across the 5M record MDM system.

---

## Project Direction

The solution is designed as a scalable pipeline:

Raw Data  
→ Preprocessing (cleaning, structuring, normalization)  
→ Address Validation & Correction  
→ Company-Address Verification  
→ AI-Assisted Enrichment  
→ Final Structured Output  

The pipeline is currently implemented on a ~10% sample (~3,400 records) as a proof of concept, with a design that scales to the full dataset.
 
---

## Project Structure

mdm-address-validation/

- pipeline/ → main pipeline logic  
- utils/ → helper modules (encoding, parsing, etc.)  
- tests/ → unit tests  
- data/  
  - raw/  
  - intermediate/  
  - output/  
- reports/  
- requirements.txt  

---

## How to Run

Activate environment:
.\.venv\Scripts\Activate.ps1  

Install dependencies:
pip install -r requirements.txt  

Run pipeline:
python pipeline/stage1_preprocessor.py  

Run tests:
python tests/test_preprocessor.py  

---

## Outputs

- `stage1_preprocessed.csv` → cleaned and structured data  
- `manual_review_flags.csv` → flagged records for review  

---

## Status
Work in progress — additional validation and enrichment steps will be added.

---

## Summary

This project transforms unstructured, inconsistent MDM records into clean, validated, and enrichment-ready data. By addressing data quality issues at the source, it enables reliable enrichment and improves the overall integrity of customer master data.
