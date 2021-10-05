import pytest
import numpy as np
import pyaerocom.plot.plotscatter as mod
from matplotlib.axes import Axes
from ..conftest import does_not_raise_exception


def test_plot_scatter():
    val = mod.plot_scatter(np.ones(10), np.ones(10))
    assert isinstance(val,Axes)

@pytest.mark.parametrize('args,raises', [
    (dict(x_vals=np.ones(10), y_vals=np.ones(10)), does_not_raise_exception()),
    (dict(x_vals=np.arange(100),
          y_vals=np.arange(100)*2,
          var_name='od550aer',
          var_name_ref='bla',
          x_name='OBS',
          y_name='MODEL',
          start=np.datetime64('2010-01-01'),
          stop=np.datetime64('2010-12-31'),
          ts_type='monthly',
          unit='ONE',
          stations_ok=10,
          filter_name='BLAAAAA',
          lowlim_stats = 10,
          highlim_stats = 90,
          loglog=True,
          figsize=(30,30),
          fontsize_base=14,
          fontsize_annot= 13,
          marker='o',
          color='lime',
          alpha=0.1


          ), does_not_raise_exception()),

])
def test_plot_scatter_aerocom(args,raises):
    with raises:
        val = mod.plot_scatter_aerocom(**args)
        assert isinstance(val,Axes)