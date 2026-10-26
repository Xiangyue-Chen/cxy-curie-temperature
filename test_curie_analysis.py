from io import BytesIO

import numpy as np
from PIL import Image

from curie_analysis import (
    analyze_curve,
    find_curie_temperature,
    parse_text,
    preprocess,
    render_diagnostic_figure,
)


def synthetic_curve(center: float = 320.0) -> tuple[np.ndarray, np.ndarray]:
    temperatures = np.linspace(20.0, 700.0, 3401)
    magnetic_drop = 2.0 / (1.0 + np.exp(-(temperatures - center) / 8.0))
    weights = 100.0 - magnetic_drop - 0.0002 * temperatures
    weights[temperatures >= 650.0] -= (temperatures[temperatures >= 650.0] - 650.0) * 0.08
    return temperatures, weights


def test_parse_text_locates_temperature_and_weight_percent_columns():
    text = "\n".join(
        [
            "Instrument export",
            "Time Temperature Mass Weight",
            "min °C mg %",
            "0.0 20.0 10.0 100.0",
            "0.1 20.2 9.9 99.9",
        ]
    )

    temperatures, weights = parse_text(text)

    assert temperatures.tolist() == [20.0, 20.2]
    assert weights.tolist() == [100.0, 99.9]


def test_parse_text_rejects_file_without_data_header():
    try:
        parse_text("no instrument data here")
    except ValueError as exc:
        assert "表头" in str(exc)
    else:
        raise AssertionError("malformed input must be rejected")


def test_preprocess_keeps_only_heating_branch():
    heating_temps, heating_weights = synthetic_curve()
    temperatures = np.concatenate([heating_temps, heating_temps[-2::-1]])
    weights = np.concatenate([heating_weights, heating_weights[-2::-1]])

    processed_temps, processed_weights = preprocess(temperatures, weights)

    assert processed_temps[-1] == 700.0
    assert len(processed_temps) < len(temperatures)
    assert len(processed_temps) == len(processed_weights)


def test_find_curie_temperature_ignores_large_drop_above_search_range():
    temperatures, weights = synthetic_curve(center=320.0)

    detection = find_curie_temperature(temperatures, weights)

    assert abs(detection.temperature - 320.0) <= 0.5
    assert 80.0 <= detection.temperature <= 580.0


def test_analyze_curve_and_figure_report_same_temperature():
    temperatures, weights = synthetic_curve(center=365.0)
    result = analyze_curve("C53", temperatures, weights)
    png = render_diagnostic_figure(result)

    assert result.sample == "C53"
    assert abs(result.curie_temperature - 365.0) <= 0.5
    image = Image.open(BytesIO(png))
    assert image.format == "PNG"
    assert image.width >= 1000
    assert image.height >= 700

