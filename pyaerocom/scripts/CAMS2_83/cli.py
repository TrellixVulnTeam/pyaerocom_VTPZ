from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from pprint import pformat
from reprlib import repr
from typing import List, Optional

import typer

from pyaerocom import change_verbosity, const
from pyaerocom.aeroval import EvalSetup, ExperimentProcessor
from pyaerocom.io.cams2_83.models import ModelName
from pyaerocom.io.cams2_83.reader import DATA_FOLDER_PATH as DEFAULT_MODEL_PATH

from .config import CFG
from .processer import CAMS2_83_Processer

"""
TODO:
    - Add option for species
    - Add option for periodes [Done]
    - Add option for running only som observations/models/species
    - Add options with defaults for the different folders (data/coldata/cache)
"""


DEFAULT_OBS_PATH = DEFAULT_MODEL_PATH.with_name("obs")

app = typer.Typer(add_completion=False)
logger = logging.getLogger(__name__)


def make_period(
    start_date: datetime,
    end_date: datetime,
) -> List[str]:
    start_yr = start_date.year
    end_yr = end_date.year

    if start_yr == end_yr:
        return [f"{start_yr}"]

    return [f"{start_yr}-{end_yr}", f"{start_yr}", f"{end_yr}"]


def make_model_entry(
    start_date: datetime,
    end_date: datetime,
    leap: int,
    model_path: Path,
    obs_path: Path,
    model: ModelName,
) -> dict:

    return dict(
        model_id=f"CAMS2-83.{model.name}.day{leap}",
        model_data_dir=str(model_path),
        gridded_reader_id={"model": "ReadCAMS2_83"},
        model_kwargs=dict(
            cams2_83_daterange=[f"{start_date:%F}", f"{end_date:%F}"],
        ),
    )


def make_config(
    start_date: datetime,
    end_date: datetime,
    leap: int,
    model_path: Path,
    obs_path: Path,
    data_path: Path,
    coldata_path: Path,
    models: List[ModelName],
    id: str | None,
    name: str | None,
) -> dict:

    logger.info("Making the configuration")

    if not models:
        models = list(ModelName)

    cfg = deepcopy(CFG)
    cfg.update(
        model_cfg={
            f"{model.name}": make_model_entry(
                start_date,
                end_date,
                leap,
                model_path,
                obs_path,
                model,
            )
            for model in models
        },
        periods=make_period(start_date, end_date),
        json_basedir=str(data_path),
        coldata_basedir=str(coldata_path),
    )

    if id is not None:
        cfg["exp_id"] = id
    if name is not None:
        cfg["exp_name"] = name

    return cfg


def runner(
    cfg: dict,
    cache: str | Path | None,
    *,
    dry_run: bool = False,
    quiet: bool = False,
):
    logger.info(f"Running the evaluation for the config\n{pformat(cfg)}")
    if dry_run:
        return

    if cache is not None:
        const.CACHEDIR = cache

    if quiet:
        const.QUIET = True

    stp = EvalSetup(**cfg)

    ana_cams2_83 = CAMS2_83_Processer(stp)
    ana = ExperimentProcessor(stp)

    logger.info(f"Running Rest of Statistics")
    ana.run()

    logger.info(f"Running CAMS2_83 Spesific Statistics")
    ana_cams2_83.run()


@app.command()
def main(
    start_date: datetime = typer.Argument(
        ...,
        formats=["%Y-%m-%d", "%Y%m%d"],
        help="Start date for the evaluation",
    ),
    end_date: datetime = typer.Argument(
        ...,
        formats=["%Y-%m-%d", "%Y%m%d"],
        help="End date for the evaluation",
    ),
    leap: int = typer.Argument(
        0,
        min=0,
        max=3,
        help="Which forecast day to use",
    ),
    model_path: Path = typer.Option(
        DEFAULT_MODEL_PATH,
        exists=True,
        readable=True,
        help="Path where the model data is found",
    ),
    obs_path: Path = typer.Option(
        DEFAULT_OBS_PATH,
        exists=True,
        readable=True,
        help="Path where the obs data is found",
    ),
    data_path: Path = typer.Option(
        Path("../../data").resolve(),
        exists=True,
        readable=True,
        writable=True,
        help="Path where the results are stored",
    ),
    coldata_path: Path = typer.Option(
        Path("../../coldata").resolve(),
        exists=True,
        readable=True,
        writable=True,
        help="Path where the coldata are stored",
    ),
    model: List[ModelName] = typer.Option(
        [],
        case_sensitive=False,
        help="Which model to use. All is used if none is given",
    ),
    id: Optional[str] = typer.Option(
        None,
        help="Experiment name. If none are given, the id from the default config is used",
    ),
    name: Optional[str] = typer.Option(
        None,
        help="Experiment name. If none are given, the name from the default config is used",
    ),
    cache: Optional[Path] = typer.Option(
        None,
        help="Optional path to cache. If nothing is given, the default pyaerocom cache is used",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Will only make and print the config without running the evaluation",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):

    if verbose or dry_run:
        change_verbosity(logging.INFO)

    cfg = make_config(
        start_date, end_date, leap, model_path, obs_path, data_path, coldata_path, model, id, name
    )

    quiet = not verbose
    runner(cfg, cache, dry_run=dry_run, quiet=quiet)
