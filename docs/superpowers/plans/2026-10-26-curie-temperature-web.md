# Curie Temperature Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a standalone Streamlit app for TGA-based Curie-temperature analysis.

**Architecture:** A side-effect-free scientific core parses, preprocesses, smooths, differentiates, detects, and plots each curve; a bounded upload adapter handles TXT/ZIP inputs and packages outputs; Streamlit provides upload, demo, preview, and downloads.

**Tech Stack:** Python 3.12, Streamlit 1.66.1, NumPy, SciPy, Matplotlib, pytest

**Spec:** `docs/superpowers/specs/2026-10-26-curie-temperature-web-design.md`

## Global Constraints

- Preserve `D:\VScode代码\处理热膨胀系数` unchanged.
- Process uploads only in temporary storage.
- Reject unsafe ZIP members and bound upload/member sizes.
- Label the detected Curie temperature as an automatic derivative-based estimate.

## Review Focus

- Header variants still locate temperature and weight-percent columns.
- Short or malformed files fail individually without stopping the batch.
- Heating/cooling cycles use only the heating branch.
- Boundary spikes outside 80–580 °C cannot become the reported estimate.
- Figure and CSV values agree exactly.

---

### Task 1: Side-effect-free Curie analysis core

**Files:**
- Create: `curie_analysis.py`
- Test: `test_curie_analysis.py`

**Interfaces:**
- Produces: `parse_text`, `preprocess`, `find_curie_temperature`, `analyze_curve`, `render_diagnostic_figure`

- [ ] Write synthetic detection, preprocessing, and malformed-input tests.
- [ ] Run focused tests and observe the expected missing-module failure.
- [ ] Implement the minimal analysis core from the existing script.
- [ ] Run focused tests to green.

### Task 2: Upload adapter and Streamlit UI

**Files:**
- Create: `curie_web.py`
- Create: `streamlit_app.py`
- Create: `test_curie_web.py`
- Create: `test_streamlit_app.py`

**Interfaces:**
- Consumes: Task 1 analysis functions.
- Produces: `process_uploads`, deployable Streamlit entry point.

- [ ] Write failing TXT/ZIP, package, demo, and UI smoke tests.
- [ ] Implement bounded batch processing and the upload/preview/download page.
- [ ] Run all tests to green.

### Task 3: Repository and deployment packaging

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `.gitignore`

- [ ] Add pinned cloud dependencies and scientific-boundary documentation.
- [ ] Run tests, compile checks, and `git diff --check`.
- [ ] Commit and push to `Xiangyue-Chen/cxy-curie-temperature`.
- [ ] Deploy and run the synthetic demo online.

