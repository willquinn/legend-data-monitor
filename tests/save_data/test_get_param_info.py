from legend_data_monitor.save_data import get_param_info


def test_get_param_info():
    # unit_label is dict, param with '_var' suffix, unit_label is %
    plot_info_1 = {
        "unit_label": {"param": "%", "param_var": "%"},
        "unit": {"param": "unit1", "param_var": "unit1_var"},
        "label": {"param": "label1", "param_var": "label1_var"},
        "limits": {"param": (0, 1), "param_var": (0, 2)},
        "event_type": {"param": "type1", "param_var": "type1_var"},
        "title": "Original Title",
    }
    param_1 = "param_var"
    result_1 = get_param_info(param_1, plot_info_1)
    assert result_1["title"] == f"Plotting {param_1}"
    assert result_1["unit"] == "unit1_var"
    assert result_1["variation"] is True
    assert result_1["parameters"] == param_1
    assert result_1["param_mean"] == "param_mean"

    # unit_label is dict, param without '_var', unit_label not %
    plot_info_2 = {
        "unit_label": {"param": "mV"},
        "unit": {"param": "unit2"},
        "label": {"param": "label2"},
        "limits": {"param": (1, 10)},
        "event_type": {"param": "type2"},
        "title": "Original Title",
    }
    param_2 = "param"
    result_2 = get_param_info(param_2, plot_info_2)
    assert result_2["title"] == f"Plotting {param_2}"
    assert result_2["unit"] == "unit2"
    assert result_2["variation"] is False
    assert result_2["parameters"] == "param"
    assert result_2["param_mean"] == "param_mean"

    # unit_label is string %, param without '_var'
    plot_info_3 = {
        "unit_label": "%",
        "unit": "unit3",
        "label": "label3",
        "limits": (5, 15),
        "event_type": "type3",
        "title": "Original Title",
    }
    param_3 = "param"
    result_3 = get_param_info(param_3, plot_info_3)
    assert result_3["title"] == f"Plotting {param_3}_var"
    assert result_3["unit"] == "unit3"
    assert result_3["variation"] is True
    assert result_3["parameters"] == f"{param_3}_var"
    assert result_3["param_mean"] == f"{param_3}_mean"

    # unit_label is string not %, param without '_var'
    plot_info_4 = {
        "unit_label": "mV",
        "unit": "unit4",
        "label": "label4",
        "limits": (10, 20),
        "event_type": "type4",
        "title": "Original Title",
    }
    param_4 = "param"
    result_4 = get_param_info(param_4, plot_info_4)
    assert result_4["title"] == f"Plotting {param_4}"
    assert result_4["unit"] == "unit4"
    assert result_4["variation"] is False
    assert result_4["parameters"] == param_4
    assert result_4["param_mean"] == f"{param_4}_mean"
