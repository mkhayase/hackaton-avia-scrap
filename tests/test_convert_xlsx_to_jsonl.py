import json
from pathlib import Path
import pandas as pd
import os
from services.convert_from_xlsx_to_json import XLSXtoJSONLConverter, convert_xlsx_bytes_to_jsonl

"""
Соглашения pytest для автоматического обнаружения тестов:

Файлы с тестами: test_*.py или *_test.py.

Функции-тесты: имя начинается с test_.

Классы с тестами: имя начинается с Test, без метода __init__; внутри методы тоже test_....

Игнорируются: объекты, чьи имена начинаются с _.

Фикстуры: обычные функции (или другие фабрики) — имя произвольное; внедряются по совпадению имени параметра тестовой функции.

Спец-файл conftest.py: не содержит тестов, а предоставляет фикстуры/хуки по дереву каталогов.

Параметризация: @pytest.mark.parametrize — целевые функции всё равно должны называться test_*.

Плагины/хуки: функции формата pytest_* (например, pytest_configure) — специальная точка расширения, не тест.
"""


def _build_sample_xlsx(tmp_path: Path,
                       exist_file: Path = Path(__file__).resolve().parent / "payload") -> Path:
    if exist_file.exists():  # Проверяем, есть ли готовый файл в payload
        file_path = exist_file / "2024_уменьшенное.xlsx"
        return file_path
    file_path = tmp_path / "sample.xlsx"
    with pd.ExcelWriter(file_path) as writer:  # Создаём проверочный xlsx с тремя листами
        pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_excel(writer, sheet_name="Data", index=False)
        pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        pd.DataFrame({"col": [10]}).to_excel(writer, sheet_name="Meta", index=False)
    return file_path


def test_convert_path(tmp_path: Path):   # TODO: доделать проверки на тесте конвертации в JSONL
    xlsx = _build_sample_xlsx(tmp_path)  # Создаём\добавляем тестовый xlsx

    converter = XLSXtoJSONLConverter(skip_empty_sheets=True)  # Создаём экземпляр класса конвертера

    out_path = converter.convert(xlsx, None)  # Конвертируем в JSONL

    print(out_path)
    assert out_path.exists()  # Проверяем, что файл создан

    # lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    # # Должно быть 2 строки (Data, Meta) — Empty пропущен
    # assert len(lines) == 2
    # rec1 = json.loads(lines[0])
    # rec2 = json.loads(lines[1])
    # assert rec1["sheet_name"] == "Data"
    # assert rec2["sheet_name"] == "Meta"
    # assert rec1["rows"][0]["a"] == 1


def test_convert_bytes(tmp_path: Path):  # TODO: переделать тест потока байт
    xlsx = _build_sample_xlsx(tmp_path)
    file_bytes = xlsx.read_bytes()
    out_path = tmp_path / "from_bytes.jsonl"

    # Асинхронная функция обертка
    import asyncio
    asyncio.run(convert_xlsx_bytes_to_jsonl(file_bytes, out_path))

    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    sheets = [json.loads(l)["sheet_name"] for l in lines]
    assert set(sheets) == {"Data", "Meta"}


def test_output_path_directory(tmp_path: Path):
    xlsx = _build_sample_xlsx(tmp_path)
    target_dir = tmp_path / "nested" / "level"
    converter = XLSXtoJSONLConverter()
    result_path = converter.convert(xlsx, target_dir)  # передаём директорию
    assert result_path.parent == target_dir
    assert result_path.name.endswith('.jsonl')
    assert result_path.exists()


def test_output_path_bytes(tmp_path: Path):   # TODO: переделать тест пути потока байт
    xlsx = _build_sample_xlsx(tmp_path)
    file_bytes = xlsx.read_bytes()
    dir_bytes = (tmp_path / "bytes_dir").as_posix().encode('utf-8') + b'/'
    import asyncio
    result_path = asyncio.run(convert_xlsx_bytes_to_jsonl(file_bytes, dir_bytes))
    assert result_path.exists()
    assert result_path.name == 'output.jsonl'
