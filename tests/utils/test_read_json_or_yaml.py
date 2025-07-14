import json

import pytest
import yaml

from legend_data_monitor.utils import read_json_or_yaml


def test_read_json_or_yaml(tmp_path):
    # sample data
    sample_data = {"key": "value"}

    # yaml
    yaml_file = tmp_path / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_data, f)
    data = read_json_or_yaml(str(yaml_file))
    assert data == sample_data

    # json
    json_file = tmp_path / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_data, f)
    data = read_json_or_yaml(str(json_file))
    assert data == sample_data

    # other extension
    bad_file = tmp_path / "test.txt"
    bad_file.write_text("some content")
    with pytest.raises(SystemExit):
        read_json_or_yaml(str(bad_file))
