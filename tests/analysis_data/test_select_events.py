import pandas as pd
import pytest
from legend_data_monitor.analysis_data import AnalysisData
from legend_data_monitor import utils

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "pulser": [True, False, False, True],
        "fc_bsln": [False, True, False, True],
        "muon": [False, False, True, False],
        "energy": [1400, 1450, 1500, 1600],
    })


plot_settings={'parameters': 'baseline', 'event_type': 'pulser', 'plot_structure': 'per string', 'resampled': 'only', 'plot_style': 'vs time', 'AUX_ratio': True, 'variation': True, 'time_window': '10T', 'range': [None, None], 'saving': 'append', 'plt_path': 'prova/tmp-auto/generated/plt/phy/p14/r005/l200-p14-r005-phy'}
dataset_info={'experiment': 'L200', 'period': 'p14', 'version': 'tmp-auto', 'path': '/global/cfs/cdirs/m2676/data/lngs/l200/public/prodenv/prod-blind/', 'type': 'phy', 'timestamps': ['20250619T213019Z']}

def test_select_events_pulser(sample_data):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    assert obj.data["flag_pulser"].all()

def test_select_events_fc_bsln(sample_data):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    assert obj.data["flag_fc_bsln"].all()

def test_select_events_muon(sample_data):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    assert obj.data["flag_muon"].all()

def test_select_events_phy(sample_data):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    # should keep events where *not* all of the flags are true
    assert ((~obj.data["flag_pulser"]) | (~obj.data["flag_fc_bsln"]) | (~obj.data["flag_muon"])).all()

def test_select_events_k_events(sample_data, monkeypatch):
    monkeypatch.setitem(utils.SPECIAL_PARAMETERS, "K_events", ["energy"])
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    assert obj.data["energy"].between(1430, 1575).all()

def test_select_events_all(sample_data):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    obj.select_events()
    assert len(obj.data) == len(sample_data)

def test_select_events_invalid(sample_data, caplog):
    obj = AnalysisData(selection=plot_settings | dataset_info, sub_data=sample_data.copy())
    result = obj.select_events()
    assert result == "bad"
    assert "Invalid event type!" in caplog.text
