"""
Обработка кинетических данных десорбции с поправкой на невозвращаемые
аликвоты (объём аликвоты замещается чистым растворителем).

Идея поправки
-------------
Каждая аликвота "уносит" часть уже десорбировавшегося вещества
безвозвратно (на её место доливается чистый растворитель). Поэтому
измеренная концентрация в сосуде C_n (в момент взятия n-й аликвоты) —
это НЕ полное количество вещества, десорбировавшееся к этому моменту,
а только то, что осталось после всех предыдущих разбавлений.

Скорректированная (накопленная) концентрация для n-й аликвоты:

    C_corrected[n] = C_measured[n] + (V_аликвоты / V_общий) * sum(C_measured[1..n-1])

Это стандартная формула поправки на отбор проб с заменой объёма
(используется, например, в тестах на растворение — dissolution testing).
C_measured[i] для i < n — это измеренные (не скорректированные)
концентрации всех аликвот, отобранных раньше текущей.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd

from .calibration import CalibrationCurve
from .io_utils import read_spectrum

# "<образец>.<время_мин>.txt", например "5.120.txt" или "5.120,5.txt"
SAMPLE_FILENAME_RE = re.compile(
    r"^(?P<sample>[^.]+)\.(?P<time>[0-9]+(?:,[0-9]+)?)\.txt$", re.IGNORECASE
)


@dataclass
class SampleFileInfo:
    path: Path
    sample_id: str
    time_min: float


def _parse_sample_filename(path: Path) -> SampleFileInfo:
    m = SAMPLE_FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(
            f"Имя файла образца '{path.name}' не соответствует формату "
            f"'<номер_образца>.<время_в_минутах>.txt' (например: 5.120.txt)"
        )
    return SampleFileInfo(
        path=path,
        sample_id=m.group("sample"),
        time_min=float(m.group("time").replace(",", ".")),
    )


def collect_sample_files(samples_folder: Union[str, Path]) -> Dict[str, List[SampleFileInfo]]:
    """Группирует файлы образцов по sample_id и сортирует по времени.

    Порядковый номер аликвоты (1, 2, 3, ...) определяется именно этой
    сортировкой по времени — отдельно номер аликвоты в имени файла не нужен,
    предполагается, что аликвоты одного образца отбираются строго по порядку.

    Файлы, не соответствующие формату имени (например, служебный README.txt),
    пропускаются с предупреждением, а не приводят к падению программы.
    """
    folder = Path(samples_folder)
    files = sorted(folder.glob("*.txt"))

    groups: Dict[str, List[SampleFileInfo]] = {}
    for f in files:
        try:
            info = _parse_sample_filename(f)
        except ValueError:
            print(f"  [пропущен] {f.name} не похож на файл образца, игнорирую")
            continue
        groups.setdefault(info.sample_id, []).append(info)

    for sample_id in groups:
        groups[sample_id].sort(key=lambda info: info.time_min)

    return groups


def process_sample(
    sample_id: str,
    files: List[SampleFileInfo],
    calibration: CalibrationCurve,
    v_total: float,
    v_aliquot: float,
) -> pd.DataFrame:
    """Считает измеренную и скорректированную концентрацию для каждой аликвоты одного образца."""
    rows = []
    measured_history: List[float] = []

    for n, info in enumerate(files, start=1):
        spec = read_spectrum(info.path)
        abs_value = spec.absorbance_at(calibration.wavelength_nm)
        c_measured = calibration.concentration_from_absorbance(abs_value)

        prior_sum = sum(measured_history)  # сумма C_measured за все предыдущие аликвоты
        c_corrected = c_measured + (v_aliquot / v_total) * prior_sum

        rows.append(
            {
                "sample_id": sample_id,
                "aliquot_n": n,
                "time_min": info.time_min,
                "absorbance": abs_value,
                "c_measured": c_measured,
                "c_corrected": c_corrected,
                "source_file": info.path.name,
            }
        )
        measured_history.append(c_measured)

    return pd.DataFrame(rows)
