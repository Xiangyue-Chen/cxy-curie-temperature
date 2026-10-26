from io import BytesIO

import pandas as pd
import streamlit as st

from curie_web import ProcessingError, Upload, demo_uploads, process_uploads


st.set_page_config(page_title="热重曲线居里温度在线分析", page_icon="🧲", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #fbfcfa; color: #17324d; }
    h1, h2, h3 { color: #17324d; }
    [data-testid="stMetric"] { background: white; border: 1px solid #dfe7e2; border-radius: 12px; padding: 12px; }
    .stButton button, .stDownloadButton button { border-radius: 9px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _clear() -> None:
    st.session_state.pop("result", None)
    st.session_state.pop("is_demo", None)


st.caption("TGA CURIE TEMPERATURE WORKBENCH")
st.title("热重曲线居里温度在线分析")
st.write("上传热重仪器导出的 TXT 或包含 TXT 的 ZIP，自动提取升温段、平滑求导并给出居里温度候选点。")
st.caption("当前自动搜索范围：80–580 °C；平滑窗口约 15 °C。结果必须结合原始曲线复核。")

st.subheader("01 · 选择数据")
uploaded_files = st.file_uploader(
    "上传 TXT 或 ZIP",
    type=["txt", "zip"],
    accept_multiple_files=True,
    help="文件仅用于本次会话的临时处理。",
)
process_column, demo_column, clear_column = st.columns(3)
if process_column.button("开始分析", disabled=not uploaded_files, key="process_uploads"):
    try:
        st.session_state.result = process_uploads(
            [Upload(item.name, item.getvalue()) for item in uploaded_files]
        )
        st.session_state.is_demo = False
    except ProcessingError as exc:
        _clear()
        st.error(str(exc))
if demo_column.button("运行合成示例", key="run_demo"):
    try:
        st.session_state.result = process_uploads(demo_uploads())
        st.session_state.is_demo = True
    except ProcessingError as exc:
        _clear()
        st.error(str(exc))
if clear_column.button(
    "清除当前结果", disabled="result" not in st.session_state, key="clear_results"
):
    _clear()
    st.rerun()

st.subheader("02 · 查看并下载")
result = st.session_state.get("result")
if result is None:
    st.info("上传数据后点击“开始分析”，或先运行合成示例查看页面效果。")
else:
    if st.session_state.get("is_demo"):
        st.warning("当前显示的是合成演示数据，仅用于验证处理流程，不代表真实实验精度。")
    columns = st.columns(4)
    columns[0].metric("TXT 文件", result.file_count)
    columns[1].metric("成功曲线", len(result.results))
    columns[2].metric("失败文件", len(result.errors))
    columns[3].metric("判温方法", "一阶导数最小值")
    summary_frame = pd.DataFrame(
        [
            {
                "样品": item.sample,
                "自动判定居里温度 (°C)": round(item.curie_temperature, 1),
                "有效温度点": len(item.processed_temperatures),
            }
            for item in result.results
        ]
    )
    st.dataframe(summary_frame, use_container_width=True, hide_index=True)
    if result.errors:
        error_frame = pd.DataFrame(result.errors, columns=["文件名", "错误"])
        st.dataframe(error_frame, use_container_width=True, hide_index=True)
    st.markdown("### 诊断图")
    selected = st.selectbox("选择样品", options=list(result.figures))
    st.image(result.figures[selected], use_column_width=True)
    download_csv, download_zip = st.columns(2)
    download_csv.download_button(
        "下载居里温度汇总 CSV",
        data=BytesIO(result.summary_csv),
        file_name="居里温度汇总.csv",
        mime="text/csv",
    )
    download_zip.download_button(
        "下载全部结果 ZIP",
        data=BytesIO(result.archive),
        file_name="居里温度分析结果.zip",
        mime="application/zip",
    )

st.caption("自动判温属于导数判据候选结果，不替代对原始曲线、实验条件和异常峰的人工判断。")

