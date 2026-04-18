import pandas as pd
import requests
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY")
AZURE_MAPS_URL = "https://atlas.microsoft.com/search/address/json"


def validate_address_azure(clean_address):
    """
    Sends a clean address to Azure Maps API.
    Returns validation result with status and geocoded data.
    """
    if not clean_address or not isinstance(clean_address, str):
        return {
            "validation_status": "skipped",
            "confidence":        None,
            "formatted_address": None,
            "lat":               None,
            "lon":               None,
            "error_reason":      "No address to validate"
        }

    params = {
        "api-version":       "1.0",
        "subscription-key":  AZURE_MAPS_KEY,
        "query":             clean_address,
        "limit":             1
    }

    try:
        response = requests.get(AZURE_MAPS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            return {
                "validation_status": "invalid",
                "confidence":        None,
                "formatted_address": None,
                "lat":               None,
                "lon":               None,
                "error_reason":      "No results returned from Azure Maps"
            }

        top = results[0]
        score = top.get("score", 0)
        address = top.get("address", {})
        position = top.get("position", {})

        formatted = ", ".join(filter(None, [
            address.get("streetNameAndNumber"),
            address.get("municipality"),
            address.get("countrySubdivisionName"),
            address.get("country"),
            address.get("postalCode")
        ]))

        status = "valid" if score >= 8 else "low_confidence"

        return {
            "validation_status": status,
            "confidence":        round(score, 2),
            "formatted_address": formatted,
            "lat":               position.get("lat"),
            "lon":               position.get("lon"),
            "error_reason":      None if status == "valid" else "Low confidence score"
        }

    except requests.exceptions.Timeout:
        return {
            "validation_status": "error",
            "confidence":        None,
            "formatted_address": None,
            "lat":               None,
            "lon":               None,
            "error_reason":      "Request timed out"
        }
    except Exception as e:
        return {
            "validation_status": "error",
            "confidence":        None,
            "formatted_address": None,
            "lat":               None,
            "lon":               None,
            "error_reason":      str(e)
        }


def attempt_correction(row):
    """
    If address validation fails, tries to correct by
    building a simpler fallback query using just
    street + city + country and re-validating.
    """
    fallback_parts = [
        row.get('street'),
        row.get('city'),
        row.get('country')
    ]
    fallback = ", ".join([p for p in fallback_parts if p])

    if not fallback:
        return None, "Could not build fallback address"

    result = validate_address_azure(fallback)
    return result, fallback


def run_validator(input_path, output_path, flagged_path):
    """
    Full address validation pipeline.
    Step 1 - Validate every clean address via Azure Maps
    Step 2 - Attempt correction for failed records
    Step 3 - Flag records that fail after correction
    Step 4 - Save outputs
    """
    print("\n========== STAGE 2: ADDRESS VALIDATION ==========\n")

    df = pd.read_csv(input_path)
    total = len(df)
    print(f"Records loaded: {total}")

    validation_results = []
    print("\n[Step 1] Validating addresses via Azure Maps...")

    for idx, row in df.iterrows():
        result = validate_address_azure(row.get('clean_address'))
        validation_results.append(result)
        time.sleep(0.1)  # avoid hitting rate limits

        if (idx + 1) % 10 == 0:
            print(f"  Processed {idx + 1}/{total} records...")

    results_df = pd.DataFrame(validation_results)
    df['validation_status'] = results_df['validation_status'].values
    df['confidence']        = results_df['confidence'].values
    df['formatted_address'] = results_df['formatted_address'].values
    df['lat']               = results_df['lat'].values
    df['lon']               = results_df['lon'].values
    df['error_reason']      = results_df['error_reason'].values

    valid_count   = (df['validation_status'] == 'valid').sum()
    invalid_count = total - valid_count
    print(f"\n  Valid:   {valid_count}")
    print(f"  Invalid: {invalid_count}")

    # Step 2 - Attempt correction on failed records
    print("\n[Step 2] Attempting correction on failed records...")
    failed_mask = df['validation_status'].isin(['invalid', 'low_confidence', 'error'])
    failed_df   = df[failed_mask].copy()

    correction_results = []
    for idx, row in failed_df.iterrows():
        corrected_result, fallback_used = attempt_correction(row)
        if corrected_result:
            correction_results.append({
                "index":              idx,
                "correction_used":    fallback_used,
                "validation_status":  corrected_result['validation_status'],
                "confidence":         corrected_result['confidence'],
                "formatted_address":  corrected_result['formatted_address'],
                "lat":                corrected_result['lat'],
                "lon":                corrected_result['lon'],
                "error_reason":       corrected_result['error_reason']
            })
        time.sleep(0.1)

    # Apply corrections back to main dataframe
    for cr in correction_results:
        i = cr['index']
        if cr['validation_status'] == 'valid':
            df.at[i, 'validation_status'] = 'corrected'
            df.at[i, 'confidence']        = cr['confidence']
            df.at[i, 'formatted_address'] = cr['formatted_address']
            df.at[i, 'lat']               = cr['lat']
            df.at[i, 'lon']               = cr['lon']
            df.at[i, 'error_reason']      = None

    corrected_count = (df['validation_status'] == 'corrected').sum()
    print(f"  Successfully corrected: {corrected_count}")

    # Step 3 - Split validated vs still failed
    print("\n[Step 3] Splitting validated vs manual review records...")
    validated_df = df[df['validation_status'].isin(['valid', 'corrected'])].copy()
    manual_df    = df[~df['validation_status'].isin(['valid', 'corrected'])].copy()
    print(f"  Validated: {len(validated_df)}")
    print(f"  Needs manual review: {len(manual_df)}")

    # Step 4 - Save outputs
    print("\n[Step 4] Saving outputs...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(os.path.dirname(flagged_path), exist_ok=True)

    validated_df.to_csv(output_path, index=False)
    manual_df.to_csv(flagged_path,   index=False)

    print(f"  Validated records saved to:     {output_path}")
    print(f"  Manual review records saved to: {flagged_path}")

    print("\n========== ADDRESS VALIDATION COMPLETE ==========")
    print(f"  Total input:        {total}")
    print(f"  Valid:              {valid_count}")
    print(f"  Corrected:          {corrected_count}")
    print(f"  Manual review:      {len(manual_df)}")

    return validated_df, manual_df


if __name__ == "__main__":
    run_validator(
        input_path   = "data/intermediate/stage1_preprocessed.csv",
        output_path  = "data/intermediate/stage2_validated.csv",
        flagged_path = "data/output/manual_review_flags.csv"
    )