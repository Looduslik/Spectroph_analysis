"""
Построение калибровочной кривой (закон Бера-Ламберта: A = k*C + b)
по файлам вида cal_<концентрация>.txt
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np

from .io_utils import read_spectrum

# cal_5,0.txt / cal_10.txt / cal_0,25.txt
CAL_FILENAME_RE = re.compile(r"^cal_([0-9]+(?:,[0-9]+)?)\.txt$", re.IGNORECASE)


@dataclass
class CalibrationCurve:
    slope: float  # k
    intercept: float  # b
    r_squared: float
    concentrations: np.ndarray
    absorbances: np.ndarray
    wavelength_nm: float

    def concentration_from_absorbance(self, absorbance: float) -> float:
        return (absorbance - self.intercept) / self.slope

    def equation_str(self) -> str:
        sign = "+" if self.intercept >= 0 else "-"
        return f"A = {self.slope:.5g}*C {sign} {abs(self.intercept):.5g}   (R^2 = {self.r_squared:.4f})"


def _parse_concentration_from_filename(path: Path) -> float:
    m = CAL_FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(
            f"Имя файла калибровки '{path.name}' не соответствует формату "
            f"'cal_<концентрация>.txt' (например: cal_5,0.txt)"
        )
    return float(m.group(1).replace(",", "."))


def build_calibration_curve(calibration_folder: Union[str, Path], wavelength_nm: float) -> CalibrationCurve:
    folder = Path(calibration_folder)
    files = sorted(folder.glob("cal_*.txt"))
    if len(files) < 2:
        raise ValueError(
            f"В папке {folder} найдено {len(files)} калибровочных файлов "
            f"(cal_*.txt). Для построения прямой нужно минимум 2 разных концентрации."
        )

    concentrations = []
    absorbances = []
    for f in files:
        conc = _parse_concentration_from_filename(f)
        spec = read_spectrum(f)
        abs_value = spec.absorbance_at(wavelength_nm)
        concentrations.append(conc)
        absorbances.append(abs_value)

    conc_arr = np.array(concentrations)
    abs_arr = np.array(absorbances)

    slope, intercept = np.polyfit(conc_arr, abs_arr, 1)

    predicted = slope * conc_arr + intercept
    ss_res = np.sum((abs_arr - predicted) ** 2)
    ss_tot = np.sum((abs_arr - abs_arr.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return CalibrationCurve(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared),
        concentrations=conc_arr,
        absorbances=abs_arr,
        wavelength_nm=wavelength_nm,
    )
