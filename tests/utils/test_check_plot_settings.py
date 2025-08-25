import pytest

from legend_data_monitor import plot_styles, plotting
from legend_data_monitor.utils import check_plot_settings


def test_check_plot_settings_valid_config():
    # pick any real valid keys from the repo
    plot_structure_key = next(iter(plotting.PLOT_STRUCTURE.keys()))
    plot_style_key = next(iter(plot_styles.PLOT_STYLE.keys()))

    conf = {
        "subsystems": {
            "subsys1": {
                "plot1": {
                    "parameters": "some_param",
                    "plot_structure": plot_structure_key,
                    "plot_style": plot_style_key,
                    "time_window": "1d",
                }
            }
        }
    }

    assert check_plot_settings(conf) is True


def test_check_plot_settings_missing_subsystems(caplog):
    # Config with no subsystems
    conf = {}
    with pytest.raises(SystemExit):
        check_plot_settings(conf)


def test_check_plot_settings_invalid_option(caplog):
    # Config with an invalid plot_style
    plot_structure_key = next(iter(plotting.PLOT_STRUCTURE.keys()))

    conf = {
        "subsystems": {
            "subsys1": {
                "plot1": {
                    "parameters": "param",
                    "plot_structure": plot_structure_key,
                    "plot_style": "not_a_real_style",
                }
            }
        }
    }

    result = check_plot_settings(conf)
    assert result is False
    assert any("does not exist" in rec.message for rec in caplog.records)


def test_check_plot_settings_exposure_invalid_event_type():
    # Exposure plots must use event_type pulser or all
    plot_structure_key = next(iter(plotting.PLOT_STRUCTURE.keys()))

    conf = {
        "subsystems": {
            "subsys1": {
                "plot1": {
                    "parameters": "exposure",
                    "plot_structure": plot_structure_key,
                    "plot_style": "whatever",
                    "event_type": "bad_event",
                }
            }
        }
    }

    result = check_plot_settings(conf)
    assert result is False


def test_check_plot_settings_vs_time_missing_time_window():
    # Plots with vs time style must provide time_window
    plot_structure_key = next(iter(plotting.PLOT_STRUCTURE.keys()))
    # find a style that equals 'vs time' if it exists
    if "vs time" in plot_styles.PLOT_STYLE:
        style_key = "vs time"
    else:
        pytest.skip("No 'vs time' style available in plot_styles.PLOT_STYLE")

    conf = {
        "subsystems": {
            "subsys1": {
                "plot1": {
                    "parameters": "param",
                    "plot_structure": plot_structure_key,
                    "plot_style": style_key,
                }
            }
        }
    }

    result = check_plot_settings(conf)
    assert result is False
