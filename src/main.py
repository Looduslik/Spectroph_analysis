"""
Точка входа: строит калибровочную кривую и считает скорректированные
концентрации по кинетике десорбции для всех образцов.

Запуск (из корня проекта):
    python run.py
или
    python -m src.main --config config.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from .calibration import CalibrationCurve, build_calibration_curve
from .kinetics import collect_sample_files, process_sample


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ask_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            print("  Не похоже на число, попробуй ещё раз.")
            continue
        if value <= 0:
            print("  Значение должно быть положительным.")
            continue
        return value


def plot_calibration(calibration: CalibrationCurve, output_folder: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(calibration.concentrations, calibration.absorbances, label="Калибровочные точки")
    x_line = [calibration.concentrations.min(), calibration.concentrations.max()]
    y_line = [calibration.slope * x + calibration.intercept for x in x_line]
    ax.plot(x_line, y_line, "r--", label=calibration.equation_str())
    ax.set_xlabel("Концентрация")
    ax.set_ylabel(f"Поглощение (A) при {calibration.wavelength_nm:g} нм")
    ax.set_title("Калибровочная кривая")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_folder / "calibration_curve.png", dpi=150)
    plt.close(fig)


def plot_sample(sample_id: str, df, output_folder: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(df["time_min"], df["c_measured"], "o--", label="Измеренная (без поправки)")
    ax.plot(df["time_min"], df["c_corrected"], "o-", label="Скорректированная")
    ax.set_xlabel("Время, мин")
    ax.set_ylabel("Концентрация")
    ax.set_title(f"Образец {sample_id}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_folder / f"sample_{sample_id}_kinetics.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Обработка данных спектрофотометрии для кинетики десорбции")
    parser.add_argument("--config", default="config.yaml", help="Путь к config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)

    wavelength_nm = float(config["wavelength_nm"])
    calibration_folder = Path(config["calibration_folder"])
    samples_folder = Path(config["samples_folder"])
    output_folder = Path(config["output_folder"])
    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"Строю калибровочную кривую на λ = {wavelength_nm:g} нм...")
    calibration = build_calibration_curve(calibration_folder, wavelength_nm)
    print(f"  {calibration.equation_str()}")
    plot_calibration(calibration, output_folder)

    print()
    print("Укажи параметры эксперимента (одинаковые единицы объёма для обоих значений, например мл):")
    v_total = ask_float("  Полный объём раствора (V_общий): ")
    v_aliquot = ask_float("  Объём одной аликвоты (V_аликвоты): ")

    if v_aliquot >= v_total:
        raise SystemExit("Объём аликвоты не может быть больше или равен полному объёму раствора.")

    print()
    print(f"Ищу файлы образцов в {samples_folder} ...")
    groups = collect_sample_files(samples_folder)
    if not groups:
        raise SystemExit(f"В папке {samples_folder} не найдено ни одного файла образца.")

    for sample_id, files in groups.items():
        print(f"  Образец {sample_id}: {len(files)} точек по времени")
        df = process_sample(sample_id, files, calibration, v_total, v_aliquot)
        csv_path = output_folder / f"sample_{sample_id}_results.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        plot_sample(sample_id, df, output_folder)
        print(df.to_string(index=False))
        print(f"    -> сохранено в {csv_path}")
        print()

    print(f"Готово. Все результаты и графики — в папке {output_folder}/")


if __name__ == "__main__":
    main()
