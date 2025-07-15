from legend_data_monitor.utils import get_livetime


def test_get_livetime():
    # more than 1 year
    one_year_sec = 60 * 60 * 24 * 365.25
    livetime, unit = get_livetime(one_year_sec * 2)
    assert round(livetime, 2) == 2.0
    assert unit == " yr"

    # more than 1 day but less than 0.1 year
    livetime, unit = get_livetime(one_year_sec * 0.05)
    assert round(livetime, 2) == round((one_year_sec * 0.05) / (60 * 60 * 24), 2)
    assert unit == " days"

    # more than 1 hour but less than 1 day
    livetime, unit = get_livetime(3 * 60 * 60)
    assert round(livetime, 2) == 3.0
    assert unit == " hrs"

    # more than 1 minute but less than 1 hour
    livetime, unit = get_livetime(5 * 60)
    assert round(livetime, 2) == 5.0
    assert unit == " min"

    # less than 1 minute
    livetime, unit = get_livetime(30)
    assert livetime == 30
    assert unit == " sec"
