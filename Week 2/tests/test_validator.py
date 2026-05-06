import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.stage2_address_validator import validate_address_azure, attempt_correction


def test_valid_address():
    result = validate_address_azure("1200 Schafer St, Bismarck, ND, US, 58506")
    assert result['validation_status'] in ['valid', 'low_confidence']
    assert result['formatted_address'] is not None
    print("[PASS] test_valid_address")


def test_empty_address():
    result = validate_address_azure("")
    assert result['validation_status'] == 'skipped'
    assert result['error_reason']      is not None
    print("[PASS] test_empty_address")


def test_none_address():
    result = validate_address_azure(None)
    assert result['validation_status'] == 'skipped'
    print("[PASS] test_none_address")


def test_correction_attempt():
    fake_row = {
        'street':  '1649 Horizon Pkwy',
        'city':    'Buford',
        'country': 'US'
    }
    result, fallback = attempt_correction(fake_row)
    assert fallback is not None
    assert result is not None
    print("[PASS] test_correction_attempt")


if __name__ == "__main__":
    print("\n===== RUNNING VALIDATOR TESTS =====\n")
    print("Note: These tests call Azure Maps API - make sure AZURE_MAPS_KEY is set\n")
    test_empty_address()
    test_none_address()
    test_correction_attempt()
    test_valid_address()
    print("\n===== ALL TESTS PASSED =====")