"""Refresh sources explicitly, then execute the model chain with HTTP disabled.

Run from any directory: python scripts/refresh_model.py [--refresh]
"""

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

from istat_source import ROOT, istat_data, worldbank_fertility, population_history

CHAIN = ("14", "30", "40", "45", "63", "70", "73", "84", "86")
NOTEBOOKS = ROOT / "notebooks"


def path_for(prefix):
    return next(NOTEBOOKS.glob(f"{prefix}_*.ipynb"))


def download_sources():
    population_history()
    # Literal source filters live in the notebooks, so retrieval and analysis agree.
    for prefix in ("14", "30", "40", "45", "70"):
        notebook = nbformat.read(path_for(prefix), as_version=4)
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            for node in ast.walk(ast.parse(cell.source)):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "istat_data":
                    query = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
                    frame = istat_data(**query)
                    print(query["resource_id"], len(frame), frame.TIME_PERIOD.min(), frame.TIME_PERIOD.max(), flush=True)
    worldbank_fertility()


def execute_offline(path, discovery=False):
    # A venv using system packages also needs the base installation's Jupyter
    # templates/kernels; they are data files rather than Python imports.
    jupyter_data = str(Path(sys.base_prefix) / "share" / "jupyter")
    search_paths = [p for p in os.environ.get("JUPYTER_PATH", "").split(os.pathsep) if p]
    if jupyter_data not in search_paths:
        os.environ["JUPYTER_PATH"] = os.pathsep.join(search_paths + [jupyter_data])
    for variable, directory in (("IPYTHONDIR", "ipython"), ("MPLCONFIGDIR", "matplotlib"), ("JUPYTER_RUNTIME_DIR", "jupyter")):
        cache = ROOT / ".cache" / directory
        cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(variable, str(cache))
    notebook = nbformat.read(path, as_version=4)
    preserved = notebook.cells[3:] if discovery else []
    if discovery:
        notebook.cells = notebook.cells[:3]
    # Fail closed if any forgotten HTTP path remains in the maintained notebooks.
    guard = nbformat.v4.new_code_cell(
        "import requests\n"
        "def _offline_http(*args, **kwargs):\n"
        "    raise RuntimeError('HTTP is disabled during model execution; refresh sources separately')\n"
        "requests.adapters.HTTPAdapter.send = _offline_http\n"
    )
    notebook.cells.insert(0, guard)
    print(f"Executing offline: {path.name}", flush=True)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv[0] = sys.executable
    NotebookClient(
        notebook, timeout=1800, km=manager,
        resources={"metadata": {"path": str(NOTEBOOKS)}},
    ).execute(cleanup_kc=True)
    notebook.cells.pop(0)
    for cell in notebook.cells:
        if cell.cell_type == "code" and cell.execution_count:
            cell.execution_count -= 1
            for output in cell.get("outputs", []):
                if output.get("execution_count"):
                    output.execution_count -= 1
    notebook.cells.extend(preserved)
    nbformat.write(notebook, path)
    subprocess.run([sys.executable, "-m", "nbmirror.cli", "build", str(path), "--repo-root", str(ROOT)], check=True)
    exported = ROOT / "notebooks_html" / f"{path.stem}.html"
    # nbconvert carries code-line padding and blank JS lines into HTML.
    exported.write_text("\n".join(
        line.rstrip() if "<span" in line or not line.strip() else line
        for line in exported.read_text().splitlines()
    ) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh selected sources: ISTAT for the core model, Open-Meteo with --heatwaves")
    parser.add_argument("--download-only", action="store_true", help="Save source snapshots without running notebooks")
    parser.add_argument("--heatwaves", action="store_true", help="Run supplementary notebook 53 only; --refresh downloads Open-Meteo, never ISTAT")
    parser.add_argument("--from-notebook", choices=CHAIN, default="14", help="Resume offline execution at a notebook")
    parser.add_argument("--through-notebook", choices=CHAIN, default="86", help="Stop after this notebook")
    args = parser.parse_args()
    if args.heatwaves:
        if args.refresh:
            from weather_source import analysis_period, load_weather
            import pandas as pd

            years = pd.read_csv(ROOT / "data" / "ccr_by_age_year.csv", nrows=0).columns[1:]
            os.environ["WEATHER_REFRESH"] = "1"
            load_weather(*analysis_period(years))
        if args.download_only:
            return
        os.environ.pop("WEATHER_REFRESH", None)
        os.environ.pop("ISTAT_REFRESH", None)
        execute_offline(path_for("53"))
        return
    if args.refresh:
        os.environ["ISTAT_REFRESH"] = "1"
        download_sources()
    if args.download_only:
        return
    os.environ.pop("ISTAT_REFRESH", None)
    if args.from_notebook == "14":
        execute_offline(path_for("00"), discovery=True)
    start, stop = CHAIN.index(args.from_notebook), CHAIN.index(args.through_notebook)
    if start > stop:
        parser.error("--from-notebook must not follow --through-notebook")
    for prefix in CHAIN[start:stop + 1]:
        execute_offline(path_for(prefix))
    if args.through_notebook != "86":
        return
    from validate_model import validate

    report = validate()
    (ROOT / "data" / "refresh_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
