from pathlib import Path

from browser_controller import BrowserController


def test_url_validation():
    browser = BrowserController(Path(".jarvis-test-browser"))
    assert browser._validate_url("https://www.youtube.com/").startswith("https://")
    try:
        browser._validate_url("javascript:alert(1)")
    except ValueError:
        pass
    else:
        raise AssertionError("URL javascript: deveria ser rejeitada")
