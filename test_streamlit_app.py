from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).with_name("streamlit_app.py")


def test_empty_page_prompts_for_upload_without_exception():
    app = AppTest.from_file(str(APP)).run()

    assert not app.exception
    assert app.title[0].value == "热重曲线居里温度在线分析"
    assert "上传数据后" in app.info[0].value


def test_demo_runs_pipeline_and_displays_results():
    app = AppTest.from_file(str(APP)).run()
    app.button(key="run_demo").click().run(timeout=60)

    assert not app.exception
    assert "合成演示" in app.warning[0].value
    assert len(app.dataframe) == 1
    assert app.button(key="clear_results")

