from legend_data_monitor.utils import convert_to_camel_case


def test_convert_to_camel_case():
    result = convert_to_camel_case("hello_world_test", "_")
    assert result == "HelloWorldTest"

    result = convert_to_camel_case("convert-to-camel-case", "-")
    assert result == "ConvertToCamelCase"

    result = convert_to_camel_case("alreadyCamel", "_")
    assert result == "Alreadycamel"

    result = convert_to_camel_case("", "_")
    assert result == ""

    result = convert_to_camel_case("multiple__underscores", "_")
    assert result == "MultipleUnderscores"
