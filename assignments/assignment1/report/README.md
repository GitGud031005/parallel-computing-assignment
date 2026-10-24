# Assignment 1 report

[Read the English report](Assignment1_Report_EN.pdf).

The measurements come from the submitter's laptop (Intel Core i7-13620H, 6 performance + 4 efficiency cores, 16 logical CPUs, Windows 11, MinGW-w64 GCC 13.2) on 24 October 2026: run `run-laptop-02` with 711 configurations (P up to 14), plus the separate P=12-16 saturation run `saturation-laptop-01`.

The PDF is generated, not hand-edited. `scripts/create_report.py` reads the run directory, `results/processed/summary.csv`, the figures, the `checks.json` written by `scripts/verify.py`, and [notes.json](notes.json). The notes file holds the analysis paragraphs; every other number in the report comes from the data. After changing data or notes, regenerate from the repository root:

```bash
python assignments/assignment1/scripts/create_report.py --run-dir results-local/run-laptop-02 --summary assignments/assignment1/results/processed/summary.csv --saturation assignments/assignment1/results/processed/saturation/summary.csv --figures assignments/assignment1/results/figures --checks validation-local/check-laptop-02/checks.json --notes assignments/assignment1/report/notes.json --output assignments/assignment1/report
```

Before final submission, add the required student identity and verify the LMS closing time.
