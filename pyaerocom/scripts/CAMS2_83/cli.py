from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer

from pyaerocom.aeroval import EvalSetup
from pyaerocom.io.cams2_83.models import ModelName
from pyaerocom.scripts.CAMS2_83.config import CFG
from pyaerocom.scripts.CAMS2_83.processer import CAMS2_83_Processer

"""
TODO:
    - Add option for species
    - Add option for periodes [Done]
    - Add option for running only som observations/models/species
    - Add options with defaults for the different folders (data/coldata/cache)
"""


app = typer.Typer(add_completion=False)

DEFAULT_PATH = Path("/lustre/storeB/project/fou/kl/CAMS2_83/test_data")

state = {"verbose": False}


def make_period(
    start_date: datetime,
    end_date: datetime,
) -> str:
    start_yr = start_date.year
    end_yr = end_date.year

    if start_yr == end_yr:
        return f"{start_yr}"
    else:
        return f"{start_yr}-{end_yr}"


def make_model_entry(
    start_date: datetime,
    end_date: datetime,
    leap: int,
    path: str,
    model: ModelName,
) -> dict:

    return dict(
        model_id=f"CAMS2-83.{model.upper()}.day{leap}",
        model_data_dir=path,
        gridded_reader_id={"model": "ReadCAMS2_83"},
        model_kwargs=dict(
            cams2_83_daterange=[start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")],
        ),
    )


def make_config(
    start_date: datetime,
    end_date: datetime,
    leap: int,
    path: str,
    data_path: str,
    coldata_path: str,
    models: List[ModelName],
    id: str | None,
    name: str | None,
) -> dict:

    if state["verbose"]:
        typer.echo("Making the configuration")

    cfg = CFG

    model_cfg = {}

    if models == []:
        models = [m for m in ModelName]

    for model in models:
        model_cfg[f"CAMS2-83-{model}"] = make_model_entry(
            start_date,
            end_date,
            leap,
            path,
            model,
        )

    cfg["model_cfg"] = model_cfg

    cfg["periods"] = [
        make_period(
            start_date,
            end_date,
        )
    ]

    cfg["json_basedir"] = data_path
    cfg["coldata_basedir"] = coldata_path

    if not id is None:
        cfg["exp_id"] = id
    if not id is None:
        cfg["exp_name"] = name

    return CFG


def runner(cfg):
    if state["verbose"]:
        typer.echo("Running the evaluation for the config")
        typer.echo(cfg)

    stp = EvalSetup(**CFG)
    cams2_83_ana = CAMS2_83_Processer(stp)
    cams2_83_ana.run()

    # ana = ExperimentProcessor(stp)
    # res = ana.run()


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
    path: Path = typer.Option(
        DEFAULT_PATH,
        exists=True,
        readable=True,
        help="Path where the model data is found",
    ),
    data_path: Path = typer.Option(
        Path("../../data"),
        exists=True,
        readable=True,
        writable=True,
        help="Path where the results are stored",
    ),
    coldata_path: Path = typer.Option(
        Path("../../coldata"),
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Will only make and print the config without running the evaluation",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
    ),
):

    state["verbose"] = verbose

    cfg = make_config(
        start_date,
        end_date,
        leap,
        path,
        data_path,
        coldata_path,
        model,
        id,
        name,
    )

    if not dry_run:
        runner(cfg)
    else:
        typer.echo(cfg)


if __name__ == "__main__":
    app()
