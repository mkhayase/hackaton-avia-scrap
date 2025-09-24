"""Утилиты для конвертации XLSX -> JSONL.
Каждый лист книги сериализуется в отдельную JSON-строку формата:
{"sheet_name": <str>, "rows": [ {col: value, ...}, ... ]}
"""
from __future__ import annotations
from dataclasses import dataclass
from json import JSONEncoder
from pathlib import Path
from typing import List, Dict, Optional, Iterable, Union
import json
import io
import os

import numpy as np
import pandas as pd

__all__ = [
    "XLSXtoJSONLConverter",
    "convert_xlsx_bytes_to_jsonl",
    "parse_excel_to_dict_list",
]

from click import DateTime


class CustomJSONEncoder(json.JSONEncoder):
    """Кастомный JSONEncoder для поддержки типов, не поддерживаемых по умолчанию.
    Реализовано: Datetime - to ISO format, str.
    """

    def default(self, obj):
        try:
            return super().default(obj)

        except TypeError:
            if type(obj) is DateTime:
                obj.isoformat()
            if isinstance(obj, np.integer):
                return int(obj)


@dataclass
class XLSXtoJSONLConverter:
    """Класс-конвертер XLSX -> JSONL.

    Параметры:
        include_sheet_name: включать ли имя листа в JSON (ключ sheet_name)
        orient: режим pandas DataFrame.to_dict (обычно 'records')
        skip_empty_sheets: пропускать полностью пустые листы (без данных)
    """
    include_sheet_name: bool = True
    orient: str = "records"
    skip_empty_sheets: bool = True

    def _sheet_to_record(self, df: pd.DataFrame, sheet_name: str) -> Optional[Dict]:
        # Если DataFrame пустой и нужно пропустить — возвращаем None
        if df.empty and self.skip_empty_sheets:
            return None
        # Заменяем NaN на None для корректного JSON
        df = df.where(pd.notna(df), None)
        data = df.to_dict(orient=self.orient)
        if self.include_sheet_name:
            return {"sheet_name": sheet_name, "rows": data}
        return {"rows": data}

    def iter_sheet_records(self, excel: Union[str, Path, io.BytesIO]) -> Iterable[Dict]:
        """Итерация по листам с возвратом JSON-совместимых dict."""
        with pd.ExcelFile(excel) as xls:
            for sheet in xls.sheet_names:
                df = xls.parse(sheet)
                rec = self._sheet_to_record(df, sheet)
                if rec is not None:
                    yield rec

    def _normalize_output_path(self, output_path: Union[str, Path, bytes, bytearray], default_filename: str) -> Path:
        """
        Гарантирует, что на выходе будет путь к файлу, а не к директории.
        Если передана директория — создаёт файл внутри неё.
        Если переданы bytes — декодирует как UTF-8.
        """
        if isinstance(output_path, (bytes, bytearray)):
            output_path = output_path.decode('utf-8')
        p = Path(output_path)
        # Если путь существует и это директория — используем default_filename внутри
        if p.exists() and p.is_dir():
            return p / default_filename
        # Если путь не существует, но заканчивается на разделитель (редко на Windows) — трактуем как директорию
        # Пользователь мог передать 'some_dir/' — Path('some_dir/') не существует, но мы можем создать и добавить имя
        if not p.suffix and (str(output_path).endswith(os.sep) or not p.name.count('.')):
            # нет расширения и нет файла с точкой в имени -> трактуем как директорию
            return p / default_filename
        return p

    def convert(self, input_path: Union[str, Path],
                output_path: Optional[Union[str, Path, bytes, bytearray]] = None) -> Path:
        """Конвертирует XLSX файл на диске в JSONL.

        Args:
            input_path: путь к исходному .xlsx
            output_path: путь к целевому .jsonl (если None, берётся тот же корень с расширением .jsonl)
        Returns:
            Path к созданному JSONL файлу.
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.with_suffix('.jsonl')
        # Если передали директорию как output_path — добавим имя по входному файлу
        output_path = self._normalize_output_path(output_path, input_path.with_suffix('.jsonl').name)
        # Создаём директории
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f_out:
            print(self.iter_sheet_records(input_path))
            for record in self.iter_sheet_records(input_path):
                f_out.write(json.dumps(record, ensure_ascii=False, cls=CustomJSONEncoder))
                f_out.write('\n')
        return output_path

    def convert_bytes(self, file_bytes: bytes, output_path: Union[str, Path, bytes, bytearray]) -> Path:
        """Конвертирует XLSX из набора байтов (например, загруженного файла) в JSONL.
        Дополнительно: если output_path указывает на директорию — будет создан файл output.jsonl внутри.
        """
        bio = io.BytesIO(file_bytes)
        output_path = self._normalize_output_path(output_path, 'output.jsonl')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f_out:
            for record in self.iter_sheet_records(bio):
                f_out.write(json.dumps(record, ensure_ascii=False))
                f_out.write('\n')
        return output_path


# Асинхронная обертка – может использоваться в хэндлерах
# TODO: use or remove
async def convert_xlsx_bytes_to_jsonl(file_bytes: bytes, output_path: Union[str, Path, bytes, bytearray]) -> Path:
    converter = XLSXtoJSONLConverter()
    return converter.convert_bytes(file_bytes, output_path)

# TODO: use or remove
# Сохранена и адаптирована из начального варианта – теперь читает любой лист (по имени)
def parse_excel_to_dict_list(filepath: str, sheet_name: str = 'Sheet1') -> List[Dict]:
    """Преобразует один лист Excel в список словарей (все NaN -> None)."""
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    if df.empty:
        return []
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient='records')

# TODO: use or remove
# Обратная совместимость имени (если ранее вызывали convert_xlsx_json)
async def convert_xlsx_json(file: bytes, output_path: Union[str, Path, bytes, bytearray]) -> Path:  # type: ignore
    """LEGACY: асинхронная функция для совместимости старого имени."""
    return await convert_xlsx_bytes_to_jsonl(file, output_path)
