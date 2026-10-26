"""Bounded upload adapter for TGA Curie-temperature analysis."""

import csv
import math
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from typing import NamedTuple
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from curie_analysis import CurieResult, analyze_curve, parse_text, render_diagnostic_figure


MAX_UPLOADS = 50
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_ZIP_MEMBERS = 200


class ProcessingError(Exception):
    pass


class Upload(NamedTuple):
    name: str
    data: bytes


class FileError(NamedTuple):
    file_name: str
    message: str


class BatchResult(NamedTuple):
    results: list[CurieResult]
    errors: list[FileError]
    figures: dict[str, bytes]
    summary_csv: bytes
    archive: bytes
    file_count: int


def _decode(data: bytes) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"无法识别文本编码: {last_error}")


def _safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.name:
        raise ProcessingError(f"ZIP 中包含不安全路径：{name}")
    return path


def _extract_text_files(uploads: list[Upload]) -> list[tuple[str, bytes]]:
    if not uploads:
        raise ProcessingError("请上传至少一个 TXT 或 ZIP 文件。")
    if len(uploads) > MAX_UPLOADS:
        raise ProcessingError(f"每次最多上传 {MAX_UPLOADS} 个文件。")
    files: list[tuple[str, bytes]] = []
    total_size = 0
    for upload in uploads:
        if len(upload.data) > MAX_FILE_BYTES:
            raise ProcessingError(f"文件过大：{upload.name}")
        suffix = PurePosixPath(upload.name).suffix.lower()
        if suffix == ".txt":
            total_size += len(upload.data)
            files.append((PurePosixPath(upload.name.replace("\\", "/")).name, upload.data))
            continue
        if suffix != ".zip":
            raise ProcessingError(f"不支持的文件类型：{upload.name}")
        try:
            with ZipFile(BytesIO(upload.data)) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                if len(members) > MAX_ZIP_MEMBERS:
                    raise ProcessingError(f"ZIP 文件数量超过 {MAX_ZIP_MEMBERS}：{upload.name}")
                for member in members:
                    path = _safe_member(member.filename)
                    if member.flag_bits & 1:
                        raise ProcessingError(f"不支持加密 ZIP：{upload.name}")
                    if path.suffix.lower() != ".txt":
                        continue
                    if member.file_size > MAX_FILE_BYTES:
                        raise ProcessingError(f"ZIP 内文件过大：{member.filename}")
                    total_size += member.file_size
                    if total_size > MAX_TOTAL_BYTES:
                        raise ProcessingError("解压后的 TXT 总大小超过限制。")
                    files.append((path.as_posix(), archive.read(member)))
        except BadZipFile as exc:
            raise ProcessingError(f"无法读取 ZIP：{upload.name}") from exc
    if not files:
        raise ProcessingError("上传内容中没有找到 TXT 文件。")
    if total_size > MAX_TOTAL_BYTES:
        raise ProcessingError("TXT 总大小超过限制。")
    return files


def _safe_plot_name(sample: str, index: int) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_." else "_" for character in sample)
    return f"{index:02d}_{cleaned[:80] or 'sample'}_居里温度.png"


def _summary_bytes(results: list[CurieResult]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["样品", "自动判定居里温度 (°C)", "判定方法"])
    for result in results:
        writer.writerow([result.sample, f"{result.curie_temperature:.1f}", "平滑重量百分比曲线的一阶导数最小值"])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def process_uploads(uploads: list[Upload]) -> BatchResult:
    files = _extract_text_files(uploads)
    results: list[CurieResult] = []
    errors: list[FileError] = []
    figures: dict[str, bytes] = {}
    for file_name, data in files:
        try:
            temperatures, weights = parse_text(_decode(data))
            result = analyze_curve(PurePosixPath(file_name).stem, temperatures, weights)
            results.append(result)
            figures[_safe_plot_name(result.sample, len(results))] = render_diagnostic_figure(result)
        except (UnicodeError, ValueError, OverflowError) as exc:
            errors.append(FileError(file_name, str(exc)))
    if not results:
        details = "；".join(error.message for error in errors)
        raise ProcessingError(f"没有成功分析任何曲线。{details}".rstrip("。"))
    summary = _summary_bytes(results)
    archive_stream = BytesIO()
    with ZipFile(archive_stream, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("居里温度汇总.csv", summary)
        for name, data in figures.items():
            archive.writestr(name, data)
        if errors:
            error_stream = StringIO(newline="")
            writer = csv.writer(error_stream)
            writer.writerow(["文件名", "错误"])
            writer.writerows(errors)
            archive.writestr("未处理文件.csv", "\ufeff" + error_stream.getvalue())
    return BatchResult(results, errors, figures, summary, archive_stream.getvalue(), len(files))


def demo_uploads() -> list[Upload]:
    lines = ["Synthetic TGA export", "Time Temperature Mass Weight", "min °C mg %"]
    for index in range(1361):
        temperature = 20.0 + index * 0.5
        drop = 2.0 / (1.0 + math.exp(-(temperature - 340.0) / 8.0))
        weight = 100.0 - drop - 0.0002 * temperature
        if temperature >= 650.0:
            weight -= (temperature - 650.0) * 0.08
        lines.append(f"{index / 10:.1f} {temperature:.2f} 10.0 {weight:.6f}")
    return [Upload("C53-demo.txt", "\n".join(lines).encode("utf-8"))]

