
A Python tool was built for my bachelor's thesis project. It builds a
calibration curve from standard solutions of known concentration, then uses
it to compute substance concentration over time in a desorption experiment —
correcting for the fact that each sampled aliquot is permanently removed and
replaced with fresh solvent rather than returned to the vessel.


## How it works

1. **Calibration** Spectra of calibration solutions (with known concntration) are loaded.  choose wavelenght manually. Datatype: wavelenght - absorbance.Calibration line  `A = k·C + b` is fitted by least squares..
2. **Kinetics** FOr each samples, a series of spectra is loaded — one spectrum per aliquot taken, ordered by time. For each aliquot, the calibration line converts absorbance into concentration.
3. **Correction for aloquot removal** Because each aliquot is not returned, but replaced with fresh solvent aplplied a correction:

   ```
   C_corrected[n] = C_measured[n] + (V_aliquot / V_total) * Σ C_measured[1..n-1]
   ```

  whre the sum runs over all aliquots taken before the current one.
 
## Структура проекта

```
spectro-diploma/
├── config.yaml              # wavelength, paths to data folders
├── run.py                   
├── requirements.txt
├── src/
│   ├── io_utils.py          # reading raw  files
│   ├── calibration.py       # calibration curve fittin
│   ├── kinetics.py          # kinetics calculation with aliquot correction
│   └── main.py            
├── data/
│   ├── calibration/         # ut cal_<concentration>.txt files here
│   ├── samples/              # сput <sample>.<time_min>.txt files here
│   └── raw_examples/         # sample raw files as exported by the instrument
└── results/                 # output CSVs and plots are saved here
```

## input file format

Instrument output file from UV-1800, Shimadzu (used as-is, no manual edits needed):
```
"имя_образца - RawData"
"Wavelength nm." "Abs."
190,00 0,797
191,00 0,767
...
```



### Calibration solutions → `data/calibration/`

```
cal_<concentration>.txt
```

Дробная часть концентрации — через запятую. Примеры:

- `cal_5,0.txt` → concentration 5.0 %
- `cal_10.txt` → concentration 10 %
- `cal_0,25.txt` → concentration 0.25 %

Concentration units can be anything (mg/L, µM, etc.) as long as they're
consistent across all calibration solutions. Output values (`c_measured`,
`c_corrected`) will be in the same units.


### Samples → `data/samples/`

```
<sample_id>.<time_in_min>.txt
```

examples:

- `5.120.txt` → sample 5, time point  at 120min



## CHoosing a wavelenght for calibration

Enter the choosen value in `config.yaml`:

```yaml
wavelength_nm: 270
```

## Running

Из корня проекта:

```bash
python run.py
```

Программа:

The program will:
build the calibration curve and print its equation and R²
(the plot is saved to `results/calibration_curve.png`);
prompt for `V_total` and `V_aliquot` in the terminal (same volume units,
e.g. mL);
process every sample in `data/samples/` and save, for each one:
`results/sample_<id>_results.csv` — a table of all aliquots (time,
absorbance, measured and corrected concentration);
`results/sample_<id>_kinetics.png` — a concentration-vs-time plot.
A different config file can be specified:
```bash
python run.py --config other_config.yaml
```

## Publishing on GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <(https://github.com/Looduslik/Spectroph_analysis)>
git push -u origin main
```

