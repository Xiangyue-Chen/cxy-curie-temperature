# 热重曲线居里温度在线分析

根据热重仪器 TXT 中的重量百分比–温度曲线，自动给出居里温度候选点并生成诊断图。网页支持批量 TXT/ZIP 上传、在线预览以及 CSV/ZIP 下载。

## 功能

- 自动定位温度列和重量百分比列。
- 只使用升温段，并跳过初始磁铁开启/稳定瞬态。
- 将数据重采样到 0.2 °C 等间距温度网格。
- 使用约 15 °C 的 Savitzky–Golay 窗口平滑。
- 在 80–580 °C 内，以 `d(重量%)/dT` 最小值作为自动居里温度候选点。
- 每个样品生成原始曲线、平滑曲线、导数曲线和叠加诊断图。
- 下载汇总 CSV 和包含全部图表、汇总及错误记录的 ZIP。
- 自带合成示例，可直接验证完整流程。

## 科学边界

自动结果是固定导数判据得到的候选温度，不替代人工判断。异常峰、基线漂移、实验场强、升温速率和样品状态都可能影响判温；正式使用前应核对原始曲线和实验记录。

## 在线部署

主入口为 `streamlit_app.py`，可直接部署到 Streamlit Community Cloud。

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 输入格式

TXT 中应包含类似 `min °C mg %` 的单位行；工具通过单位定位温度和重量百分比列，并读取其后的数值数据。

## 验证

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m py_compile streamlit_app.py curie_web.py curie_analysis.py
```


