from maidenhead.cli import main


def test_cli_normalize(capsys):
    code = main(["normalize", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83ri"


def test_cli_validate_invalid(invalid_locators):
    for loc in invalid_locators:
        code = main(["validate", loc])
        assert code == 2


def test_cli_validate_valid_lengths(valid_locators):
    for loc in valid_locators:
        code = main(["validate", loc])
        assert code == 0
