"""TGA-based automatic Curie-temperature estimation."""

import re
from io import BytesIO
from typing import NamedTuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter


T_MAX_SEARCH = 900.0
CURIE_SEARCH_MIN = 80.0
CURIE_SEARCH_MAX = 580.0
TEMP_GRID_STEP = 0.2
SMOOTH_WINDOW_C = 15.0
SMOOTH_POLYORDER = 3


class Detection(NamedTuple):
    temperature: float
    temperatures: np.ndarray
    weights_smooth: np.ndarray
    derivative: np.ndarray
    index: int


class CurieResult(NamedTuple):
    sample: str
    curie_temperature: float
    raw_temperatures: np.ndarray
    raw_weights: np.ndarray
    processed_temperatures: np.ndarray
    processed_weights: np.ndarray
    smooth_temperatures: np.ndarray
    smooth_weights: np.ndarray
    derivative: np.ndarray
    curie_index: int


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def parse_text(text: str) -> tuple[np.ndarray, np.ndarray]:
    """Locate the units header and parse temperature and weight-percent columns."""
    temperatures: list[float] = []
    weights: list[float] = []
    in_data = False
    temp_column = 1
    weight_column = 3
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^min\b", line, re.IGNORECASE) and ("°C" in line or "℃" in line) and "%" in line:
            units = line.split()
            temp_column = next(
                (index for index, item in enumerate(units) if "°C" in item or "℃" in item),
                1,
            )
            weight_column = next((index for index, item in enumerate(units) if "%" in item), 3)
            in_data = True
            continue
        if not in_data:
            continue
        parts = line.split()
        if len(parts) <= max(temp_column, weight_column):
            continue
        try:
            temperatures.append(_number(parts[temp_column]))
            weights.append(_number(parts[weight_column]))
        except ValueError:
            if temperatures:
                break
    if not in_data:
        raise ValueError("未找到包含 °C 和 % 的数据表头")
    if not temperatures:
        raise ValueError("数据表中没有可用的数值记录")
    return np.asarray(temperatures, dtype=float), np.asarray(weights, dtype=float)


def preprocess(
    temperatures: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Keep finite heating-branch data after the initial magnetic transient."""
    temperatures = np.asarray(temperatures, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if temperatures.shape != weights.shape:
        raise ValueError("温度与重量数组长度不一致")
    finite = np.isfinite(temperatures) & np.isfinite(weights)
    temperatures = temperatures[finite]
    weights = weights[finite]
    if not len(temperatures):
        return temperatures, weights
    maximum_index = int(np.argmax(temperatures))
    temperatures = temperatures[: maximum_index + 1]
    weights = weights[: maximum_index + 1]
    weight_peak_index = int(np.argmax(weights))
    start_temperature = temperatures[weight_peak_index]
    ramp = np.where(temperatures[weight_peak_index:] >= start_temperature + 5.0)[0]
    start_index = weight_peak_index + int(ramp[0]) if len(ramp) else weight_peak_index
    temperatures = temperatures[start_index:]
    weights = weights[start_index:]
    within_limit = temperatures <= T_MAX_SEARCH
    return temperatures[within_limit], weights[within_limit]


def find_curie_temperature(
    temperatures: np.ndarray, weights: np.ndarray
) -> Detection:
    """Estimate Curie temperature at the minimum smoothed d(weight%)/dT."""
    order = np.argsort(temperatures)
    sorted_temperatures = np.asarray(temperatures, dtype=float)[order]
    sorted_weights = np.asarray(weights, dtype=float)[order]
    finite = np.isfinite(sorted_temperatures) & np.isfinite(sorted_weights)
    sorted_temperatures = sorted_temperatures[finite]
    sorted_weights = sorted_weights[finite]
    unique_temperatures, inverse = np.unique(sorted_temperatures, return_inverse=True)
    weight_sums = np.zeros(len(unique_temperatures), dtype=float)
    counts = np.zeros(len(unique_temperatures), dtype=float)
    np.add.at(weight_sums, inverse, sorted_weights)
    np.add.at(counts, inverse, 1)
    if len(unique_temperatures) < 20:
        raise ValueError("没有足够的有效温度点用于平滑求导")
    unique_weights = weight_sums / counts
    start = np.ceil(unique_temperatures.min() / TEMP_GRID_STEP) * TEMP_GRID_STEP
    end = np.floor(unique_temperatures.max() / TEMP_GRID_STEP) * TEMP_GRID_STEP
    smooth_temperatures = np.arange(start, end + TEMP_GRID_STEP / 2, TEMP_GRID_STEP)
    grid_weights = np.interp(smooth_temperatures, unique_temperatures, unique_weights)
    window = max(int(round(SMOOTH_WINDOW_C / TEMP_GRID_STEP)), SMOOTH_POLYORDER + 2, 5)
    if window % 2 == 0:
        window += 1
    if window >= len(grid_weights):
        window = len(grid_weights) if len(grid_weights) % 2 else len(grid_weights) - 1
    if window <= SMOOTH_POLYORDER:
        raise ValueError("有效数据点太少，无法平滑求导")
    smooth_weights = savgol_filter(grid_weights, window_length=window, polyorder=SMOOTH_POLYORDER)
    derivative = np.gradient(smooth_weights, smooth_temperatures)
    search = (smooth_temperatures >= CURIE_SEARCH_MIN) & (
        smooth_temperatures <= CURIE_SEARCH_MAX
    )
    if not np.any(search):
        raise ValueError("居里温度搜索范围内没有有效数据点")
    search_indexes = np.where(search)[0]
    curie_index = int(search_indexes[np.argmin(derivative[search])])
    return Detection(
        float(smooth_temperatures[curie_index]),
        smooth_temperatures,
        smooth_weights,
        derivative,
        curie_index,
    )


def analyze_curve(
    sample: str, temperatures: np.ndarray, weights: np.ndarray
) -> CurieResult:
    """Preprocess and analyze one parsed curve."""
    raw_temperatures = np.asarray(temperatures, dtype=float)
    raw_weights = np.asarray(weights, dtype=float)
    raw_mask = (
        np.isfinite(raw_temperatures)
        & np.isfinite(raw_weights)
        & (raw_temperatures <= T_MAX_SEARCH)
    )
    processed_temperatures, processed_weights = preprocess(raw_temperatures, raw_weights)
    if len(processed_temperatures) < 20:
        raise ValueError("有效数据点太少")
    detection = find_curie_temperature(processed_temperatures, processed_weights)
    return CurieResult(
        sample,
        detection.temperature,
        raw_temperatures[raw_mask],
        raw_weights[raw_mask],
        processed_temperatures,
        processed_weights,
        detection.temperatures,
        detection.weights_smooth,
        detection.derivative,
        detection.index,
    )


def render_diagnostic_figure(result: CurieResult) -> bytes:
    """Render the raw, smoothed, derivative, and overlay diagnostics as PNG."""
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    raw, smooth, derivative_axis, overlay = axes.flat
    tc = result.curie_temperature
    raw.scatter(result.raw_temperatures, result.raw_weights, s=3, color="#4477AA", alpha=0.45)
    raw.axvline(tc, color="#CC3311", linestyle="--", linewidth=1.2)
    raw.set(title="Raw weight", xlabel="Temperature (°C)", ylabel="Weight (%)")
    smooth.plot(result.smooth_temperatures, result.smooth_weights, color="#0077BB", linewidth=1.5)
    smooth.axvline(tc, color="#CC3311", linestyle="--", linewidth=1.2)
    smooth.set(title="Smoothed curve", xlabel="Temperature (°C)", ylabel="Weight (%)")
    derivative_axis.axvspan(CURIE_SEARCH_MIN, CURIE_SEARCH_MAX, color="#BBBBBB", alpha=0.12)
    derivative_axis.plot(result.smooth_temperatures, result.derivative, color="#EE7733", linewidth=1.2)
    derivative_axis.scatter([tc], [result.derivative[result.curie_index]], color="#CC3311", s=45, zorder=5)
    derivative_axis.axvline(tc, color="#CC3311", linestyle="--", linewidth=1.2)
    derivative_axis.set(title="Derivative", xlabel="Temperature (°C)", ylabel="d(weight%)/dT")
    overlay.scatter(result.raw_temperatures, result.raw_weights, s=3, color="#4477AA", alpha=0.24)
    overlay.plot(result.smooth_temperatures, result.smooth_weights, color="#0077BB", linewidth=1.3)
    overlay.axvline(tc, color="#CC3311", linestyle="--", linewidth=1.2, label=f"Tc = {tc:.1f} °C")
    overlay.set(title="Raw + smooth + derivative", xlabel="Temperature (°C)", ylabel="Weight (%)")
    overlay_derivative = overlay.twinx()
    overlay_derivative.spines["top"].set_visible(False)
    overlay_derivative.plot(result.smooth_temperatures, result.derivative, color="#EE7733", linewidth=1.0)
    overlay_derivative.set_ylabel("d(weight%)/dT", color="#EE7733")
    overlay.legend(frameon=False, loc="best")
    fig.suptitle(f"{result.sample} — automatic Curie estimate: {tc:.1f} °C", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    stream = BytesIO()
    fig.savefig(stream, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return stream.getvalue()

