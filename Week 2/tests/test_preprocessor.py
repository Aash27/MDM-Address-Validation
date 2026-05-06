import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.encoding_fixer import fix_encoding
from utils.address_parser import parse_address
from utils.language_detector import expand_abbreviations, detect_language


def test_encoding_fixer():
    assert fix_encoding("JosÃ©")   == "José"
    assert fix_encoding("MÃ¡laga") == "Málaga"
    assert fix_encoding("BajÃ£Âo") == "Bajão"
    assert fix_encoding("Normal text") == "Normal text"
    assert fix_encoding(None) is None
    print("[PASS] test_encoding_fixer")


def test_address_parser_complete():
    result = parse_address("5460 Whispering Oaks Ln|#|#Fort Worth|#|#TX|#|#US|#|#76108")
    assert result['is_complete']   == True
    assert result['street']        == "5460 Whispering Oaks Ln"
    assert result['city']          == "Fort Worth"
    assert result['country']       == "US"
    assert result['flag_reason']   is None
    print("[PASS] test_address_parser_complete")


def test_address_parser_incomplete():
    result = parse_address("Waushara|#|#Berlin|#|#WI|#|#US|#|#54923")
    assert result['is_complete'] == False
    assert "street" in result['flag_reason']
    print("[PASS] test_address_parser_incomplete")


def test_address_parser_empty():
    result = parse_address("")
    assert result['is_complete']   == False
    assert result['clean_address'] is None
    print("[PASS] test_address_parser_empty")


def test_abbreviation_expansion():
    assert "Street" in expand_abbreviations("123 Main St")
    assert "Boulevard" in expand_abbreviations("456 Oak Blvd")
    assert "Avenue" in expand_abbreviations("789 Park Ave")
    assert "PO Box" in expand_abbreviations("Postfach 1234")
    print("[PASS] test_abbreviation_expansion")


def test_language_detection():
    lang = detect_language("Calle Mayor 123, Madrid")
    assert lang in ['es', 'ca']
    lang_en = detect_language("123 Main Street, Dallas")
    assert lang_en == 'en'
    print("[PASS] test_language_detection")


if __name__ == "__main__":
    print("\n===== RUNNING PRE-PROCESSING TESTS =====\n")
    test_encoding_fixer()
    test_address_parser_complete()
    test_address_parser_incomplete()
    test_address_parser_empty()
    test_abbreviation_expansion()
    test_language_detection()
    print("\n===== ALL TESTS PASSED =====")