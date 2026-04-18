import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.encoding_fixer import fix_encoding_dataframe
from utils.address_parser import parse_address_dataframe
from utils.language_detector import process_language_dataframe


def run_preprocessor(input_path, output_path, flagged_path):
    """
    Full pre-processing pipeline.
    Step 1 - Fix encoding corruption
    Step 2 - Parse |#|# delimiter into clean address
    Step 3 - Detect language and translate non-English fields
    Step 4 - Flag incomplete addresses
    Step 5 - Save outputs
    """
    print("\n========== STAGE 1: PRE-PROCESSING ==========\n")

    # Load data
    df = pd.read_csv(input_path)
    total = len(df)
    print(f"Records loaded: {total}")

    # Step 1 - Fix encoding
    print("\n[Step 1] Fixing encoding corruption...")
    df = fix_encoding_dataframe(df, columns=['SOURCE_NAME', 'FULL_ADDRESS'])
    fixed_count = df['encoding_fixed'].sum()
    print(f"  Records with encoding fixed: {fixed_count}")

    # Step 2 - Parse address delimiter
    print("\n[Step 2] Parsing |#|# address delimiter...")
    df = parse_address_dataframe(df)
    complete_count   = df['is_complete'].sum()
    incomplete_count = total - complete_count
    print(f"  Complete addresses:   {complete_count}")
    print(f"  Incomplete addresses: {incomplete_count}")

    # Step 3 - Language detection and translation
    print("\n[Step 3] Detecting language and translating non-English fields...")
    df = process_language_dataframe(df)
    translated_count = df['was_translated'].sum()
    print(f"  Records translated: {translated_count}")

    # Step 4 - Split into clean and flagged
    print("\n[Step 4] Splitting complete vs flagged records...")
    clean_df   = df[df['is_complete'] == True].copy()
    flagged_df = df[df['is_complete'] == False].copy()
    print(f"  Clean records:   {len(clean_df)}")
    print(f"  Flagged records: {len(flagged_df)}")

    # Step 5 - Save outputs
    print("\n[Step 5] Saving outputs...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(os.path.dirname(flagged_path), exist_ok=True)

    clean_df.to_csv(output_path, index=False)
    flagged_df.to_csv(flagged_path, index=False)

    print(f"  Clean records saved to:   {output_path}")
    print(f"  Flagged records saved to: {flagged_path}")

    print("\n========== PRE-PROCESSING COMPLETE ==========")
    print(f"  Total input:    {total}")
    print(f"  Clean output:   {len(clean_df)}")
    print(f"  Flagged output: {len(flagged_df)}")

    return clean_df, flagged_df


if __name__ == "__main__":
    run_preprocessor(
        input_path  = "data/raw/100_sample_MDM.csv",
        output_path = "data/intermediate/stage1_preprocessed.csv",
        flagged_path= "data/output/manual_review_flags.csv"
    )