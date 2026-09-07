"""
Утилиты для чтения "сырых" файлов спектрофотометра.

Формат файла (типичный для UV-VIS спектрофотометров):

    "имя_образца - RawData"
    "Wavelength nm." "Abs."
    190,00 0,797
    191,00 0,767
    ...

Особенности, которые приходится обрабатывать:
- Кодировка файла не всегда UTF-8 (часто cp1251, если имя образца
  на кириллице и файл сохранён на "русской" Windows) — определяется
  автоматически перебором нескольких вариантов.
- Десятичный разделитель — запятая, а не точка.
- Разделитель колонок — произвольное количество пробелов/табов.
- Первые две строки — служебная шапка, не данные.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import numpy as np

ENCODINGS_TO_TRY = ("utf-8-sig", "cp1251", "latin-1")
HEADER_LINES = 2


@dataclass
class Spectrum:
    """Спектр: массивы длин волн (нм) и поглощения (Abs.)."""

    wavelengths: np.ndarray
    absorbance: np.ndarray
    source_path: Path

    def absorbance_at(self, wavelength_nm: float, tol: float = 2.0) -> float:
        """
        Возвращает поглощение на заданной длине волны.

        Если такой длины волны нет в данных ровно, значение
        интерполируется линейно между соседними точками (обычный шаг
        сетки прибора — 1 нм, так что интерполяция практически незаметна).
        """
        wl = self.wavelengths
        if wavelength_nm < wl.min() - tol or wavelength_nm > wl.max() + tol:
            raise ValueError(
                f"Длина волны {wavelength_nm} нм вне диапазона данных "
                f"[{wl.min():.0f}, {wl.max():.0f}] нм в файле {self.source_path.name}"
            )
        return float(np.interp(wavelength_nm, wl, self.absorbance))


def _read_text_with_fallback_encoding(path: Path) -> List[str]:
    last_error = None
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError as e:
            last_error = e
            continue
    raise ValueError(
        f"Не удалось прочитать файл {path} ни в одной из кодировок {ENCODINGS_TO_TRY}"
    ) from last_error


def read_spectrum(path: Union[str, Path]) -> Spectrum:
    """Читает файл спектра прибора и возвращает Spectrum."""
    path = Path(path)
    lines = _read_text_with_fallback_encoding(path)

    data_lines = lines[HEADER_LINES:]

    wavelengths = []
    absorbance = []
    for i, raw_line in enumerate(data_lines, start=HEADER_LINES + 1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(f"{path.name}: не могу разобрать строку {i}: {raw_line!r}")
        try:
            wl = float(parts[0].replace(",", "."))
            ab = float(parts[1].replace(",", "."))
        except ValueError as e:
            raise ValueError(f"{path.name}: не могу разобрать числа в строке {i}: {raw_line!r}") from e
        wavelengths.append(wl)
        absorbance.append(ab)

    if not wavelengths:
        raise ValueError(f"{path.name}: в файле не найдено ни одной строки с данными")

    wl_arr = np.array(wavelengths)
    ab_arr = np.array(absorbance)

    order = np.argsort(wl_arr)
    return Spectrum(wavelengths=wl_arr[order], absorbance=ab_arr[order], source_path=path)
