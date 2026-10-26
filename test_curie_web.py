from io import BytesIO
from zipfile import ZipFile

import pytest

from curie_web import ProcessingError, Upload, demo_uploads, process_uploads


def test_process_uploads_builds_figures_csv_and_zip_for_txt_and_archive():
    demo = demo_uploads()[0]
    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w") as archive:
        archive.writestr("folder/C54.txt", demo.data)

    result = process_uploads([demo, Upload("more.zip", archive_buffer.getvalue())])

    assert [item.sample for item in result.results] == ["C53-demo", "C54"]
    assert len(result.figures) == 2
    assert "居里温度" in result.summary_csv.decode("utf-8-sig")
    with ZipFile(BytesIO(result.archive)) as archive:
        assert "居里温度汇总.csv" in archive.namelist()
        assert len([name for name in archive.namelist() if name.endswith(".png")]) == 2


def test_process_uploads_rejects_zip_path_traversal():
    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w") as archive:
        archive.writestr("../../escape.txt", demo_uploads()[0].data)

    with pytest.raises(ProcessingError, match="不安全"):
        process_uploads([Upload("unsafe.zip", archive_buffer.getvalue())])


def test_process_uploads_rejects_batch_when_every_file_is_invalid():
    with pytest.raises(ProcessingError, match="没有成功分析"):
        process_uploads([Upload("bad.txt", b"not a TGA export")])

