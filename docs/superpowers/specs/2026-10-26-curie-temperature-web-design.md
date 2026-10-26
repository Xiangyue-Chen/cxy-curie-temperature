# Curie Temperature Web Design

## Intent

Turn the existing TGA-derived Curie-temperature analysis into a separate Streamlit app that accepts instrument exports and returns auditable results.

## Goals

- Upload one or more TGA TXT files, or a ZIP containing TXT files.
- Preserve the current heating-branch preprocessing, temperature-grid interpolation, Savitzky-Golay smoothing, and minimum-derivative criterion.
- Show a result table and per-sample four-panel diagnostic figure.
- Download a CSV summary and a ZIP containing all figures and results.
- Provide a synthetic demo for immediate online verification.

## Non-goals

- No claim that the automatically detected temperature replaces scientific review.
- No model fitting or long-term storage.
- No detailed tuning UI in the first upload.

## Approach

Extract the existing scientific functions into a side-effect-free Python module, render figures into memory, and add a bounded TXT/ZIP Streamlit adapter. Keep the current fixed search range and smoothing parameters visible in the UI and README.

