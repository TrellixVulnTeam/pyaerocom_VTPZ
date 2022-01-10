from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd
import xarray as xr

from pyaerocom.griddeddata import GriddedData
from pyaerocom.io.cams2_83.models import ModelData, ModelName, RunType
from pyaerocom.units_helpers import UALIASES

"""
TODO:

As it is now, with e.g. leap = 3 and start date 01.12, 01.12 might not be used, since the leap shifts the date three days forward
This might have to be componsated for, with the filepath being for 3 days before 01.12 (the start date)(?)
"""

AEROCOM_NAMES = dict(
    co_conc="concco",
    no2_conc="concno2",
    o3_conc="conco3",
    pm10_conc="concpm10",
    pm2p5_conc="concpm25",
    so2_conc="concso2",
)


DATA_FOLDER_PATH = Path("/lustre/storeB/project/fou/kl/CAMS2_83/model")

logger = logging.getLogger(__name__)


def __model_path(
    name: str | ModelName, date: str | date | datetime, *, run: str | RunType = RunType.FC
) -> Path:
    if not isinstance(name, ModelName):
        name = ModelName[name]
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y%m%d").date()
    if isinstance(date, datetime):
        date = date.date()
    if not isinstance(run, RunType):
        run = RunType[run]
    return ModelData(name, run, date, DATA_FOLDER_PATH).path


def model_paths(
    model: str | ModelName, *dates: datetime | date | str, run: str | RunType = RunType.FC
) -> Iterator[Path]:
    for date in dates:
        path = __model_path(model, date, run=run)
        if not path.is_file():
            logger.warning(f"Could not find {path.name}. Skipping {date}")
            continue
        yield path


def parse_daterange(
    dates: pd.DatetimeIndex | list[datetime] | tuple[datetime, datetime]
) -> pd.DatetimeIndex:
    if isinstance(dates, pd.DatetimeIndex):
        return dates
    if len(dates) != 2:
        raise ValueError("need 2 datetime objets to define a date_range")
    return pd.date_range(*dates, freq="d")


def forecast_day(ds: xr.Dataset, *, day: int) -> xr.Dataset:
    data = ModelData.frompath(ds.encoding["source"])
    if not (0 <= day <= data.run.days):
        raise ValueError(f"{data} has no day #{day}")
    date = data.date + timedelta(days=day)
    ds = ds.sel(time=f"{date:%F}", level=0.0)
    ds.time.attrs["long_name"] = "time"
    ds.time.attrs["standard_name"] = "time"

    for var_name in ds.data_vars:
        ds[var_name].attrs["forecast_day"] = day
    return ds


def fix_coord(ds: xr.Dataset) -> xr.Dataset:
    lon = ds.longitude.data
    ds["longitude"] = np.where(lon > 180, lon - 360, lon)
    ds.longitude.attrs.update(
        long_name="longitude", standard_name="longitude", units="degrees_east"
    )
    ds.latitude.attrs.update(long_name="latitude", standard_name="latitude", units="degrees_north")
    return ds


def fix_names(ds: xr.Dataset) -> xr.Dataset:
    for var_name, aerocom_name in AEROCOM_NAMES.items():
        ds[var_name].attrs.update(long_name=aerocom_name)
    return ds.rename(AEROCOM_NAMES)


def read_dataset(paths: list[Path], *, day: int) -> xr.Dataset:
    def preprocess(ds: xr.Dataset) -> xr.Dataset:
        return ds.pipe(forecast_day, day=day)

    ds = xr.open_mfdataset(paths, preprocess=preprocess, parallel=False)
    return ds.pipe(fix_coord).pipe(fix_names)


class ReadCAMS2_83:
    FREQ_CODES = dict(hour="hourly", day="daily", month="monthly", fullrun="yearly")
    REVERSE_FREQ_CODES = {val: key for key, val in FREQ_CODES.items()}

    def __init__(
        self,
        data_id: str | None = None,
        data_dir: str | Path | None = None,
    ) -> None:

        self._filedata: Path | None = None
        self._filepaths: list[Path] | None = None
        self._data_dir: Path | None = None
        self._model: ModelName | None = None
        self._forecast_day: int | None = None
        self._data_id: str | None = None
        self._daterange: pd.DatetimeIndex | None = None

        if data_dir is not None:
            if isinstance(data_dir, str):
                data_dir = Path(data_dir)
            if not data_dir.is_dir():
                raise FileNotFoundError(f"{data_dir}")

            self.data_dir = data_dir

        self.data_id = data_id

    @property
    def data_dir(self) -> Path:
        """
        Directory containing netcdf files
        """
        if self._data_dir is None:
            raise AttributeError(f"data_dir needs to be set before accessing")
        return self._data_dir

    @data_dir.setter
    def data_dir(self, val: str | Path | None):
        if val is None:
            raise ValueError(f"Data dir {val} needs to be a dictionary or a file")
        if isinstance(val, str):
            val = Path(val)
        if not val.is_dir():
            raise FileNotFoundError(val)
        self._data_dir = val
        self._filedata = None

    @property
    def data_id(self):
        if self._data_id is None:
            raise AttributeError(f"data_id needs to be set before accessing")
        return self._data_id

    @data_id.setter
    def data_id(self, val):
        if val is None:
            raise ValueError(f"The data_id {val} can't be None")
        elif not isinstance(val, str):
            raise TypeError(f"The data_id {val} needs to be a string")

        self._data_id = val

        match = re.match(r"^CAMS2-83\.(.*)\.day(\d)$", val)
        if match is None:
            raise ValueError(f"The id {id} is not on the correct format")

        model, day = match.groups()
        self.model = model.casefold()
        self.forecast_day = int(day)

    @property
    def filepaths(self) -> list[Path]:
        """
        Path to data file
        """
        if self.data_dir is None and self._filepaths is None:  # type:ignore[unreachable]
            raise AttributeError("data_dir or filepaths needs to be set before accessing")
        if self._filepaths is None:
            paths = list(model_paths(self.model, *self.daterange))
            if not paths:
                raise ValueError(f"no files found for {self.model}")
            self._filepaths = paths
        return self._filepaths

    @filepaths.setter
    def filepaths(self, value: list[Path]):
        if not bool(list):
            raise ValueError("needs to be list of paths")
        if not isinstance(value, list):
            raise ValueError("needs to be list of paths")
        if all(isinstance(path, Path) for path in value):
            raise ValueError("needs to be list of paths")
        self._filepaths = value

    @property
    def filedata(self) -> xr.Dataset:
        """
        Loaded netcdf file (:class:`xarray.Dataset`)
        """
        if self._filedata is None:
            self._filedata = read_dataset(self.filepaths, day=self.forecast_day)
        return self._filedata

    @property
    def model(self) -> str:
        if self._model is None:
            raise ValueError(f"Model not set")
        return self._model

    @model.setter
    def model(self, val: str | ModelName):
        if not isinstance(val, ModelName):
            val = ModelName(val)
        self._model = val
        self._filedata = None

    @property
    def daterange(self) -> pd.DatetimeIndex:
        if self._daterange is None:
            raise ValueError("The date range is not set yet")
        return self._daterange

    @daterange.setter
    def daterange(self, dates: pd.DatetimeIndex | list[datetime] | tuple[datetime]):
        if not isinstance(dates, (pd.DatetimeIndex, list, tuple)):
            raise TypeError(f"{dates} need to be a pandas DatetimeIndex or 2 datetimes")

        self._daterange = parse_daterange(dates)
        self._filedata = None

    @property
    def forecast_day(self) -> int:
        if self._forecast_day is None:
            raise ValueError("forecast_day is not set")
        return self._forecast_day

    @forecast_day.setter
    def forecast_day(self, val: int):
        if not isinstance(val, int) or not (0 <= val <= 3):
            raise TypeError(f"forecast_day {val} is not a int between 0 and 3")
        self._forecast_day = val

    @staticmethod
    def has_var(var_name):
        """Check if variable is supported

        Parameters
        ----------
        var_name : str
            variable to be checked

        Returns
        -------
        bool
        """
        return var_name in AEROCOM_NAMES.values()

    def read_var(self, var_name: str, ts_type: str | None = None, **kwargs) -> GriddedData:
        """Load data for given variable.

        Parameters
        ----------
        var_name : str
            Variable to be read
        ts_type : str
            Temporal resolution of data to read. Supported are
            "hourly", "daily", "monthly" , "yearly".

        Returns
        -------
        GriddedData
        """
        if "daterange" in kwargs:
            self.daterange = kwargs["daterange"]
        if self._daterange is None:
            raise ValueError(f"No 'daterange' in kwargs={kwargs}")

        if ts_type != "hourly":
            raise ValueError(f"Only hourly ts_type is supported")

        cube = self.filedata[var_name].to_iris()

        gridded = GriddedData(
            cube,
            var_name=var_name,
            ts_type=ts_type,
            check_unit=True,
            convert_unit_on_init=True,
        )
        gridded.metadata["data_id"] = self.data_id

        return gridded


if __name__ == "__main__":
    from time import perf_counter

    data_dir = DATA_FOLDER_PATH
    data_id = "CAMS2-83.EMEP.day0"
    reader = ReadCAMS2_83(data_dir=data_dir, data_id=data_id)
    dates = ("2021-12-01", "2021-12-04")

    seconds = -perf_counter()
    print(reader.read_var("concno2", ts_type="hourly", daterange=dates))

    seconds += perf_counter()
    print(timedelta(seconds=int(seconds)))
