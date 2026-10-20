from paketscope.exporting import csv_safe_record, csv_safe_value


def test_formula_like_cells_are_neutralized():
    for value in ("=1+1", "+SUM(A1:A2)", "-cmd", "@SUM(A1)", "  =1+1", "\t=1+1"):
        assert csv_safe_value(value).startswith("'")


def test_normal_values_are_not_modified():
    assert csv_safe_value("Firefox") == "Firefox"
    assert csv_safe_value("1.2.3") == "1.2.3"
    assert csv_safe_record({"name": "Firefox", "version": "1.2"}) == {
        "name": "Firefox",
        "version": "1.2",
    }
