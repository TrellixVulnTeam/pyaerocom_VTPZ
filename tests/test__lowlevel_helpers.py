import os

import numpy as np
import pytest
import simplejson

from pyaerocom import _lowlevel_helpers as mod


def test_round_floats():
    fl = float(1.12344567890)
    assert mod.round_floats(fl, precision=5) == 1.12345
    fl_list = [np.float_(2.3456789), np.float32(3.456789012)]
    tmp = mod.round_floats(fl_list, precision=3)
    assert tmp == [2.346, pytest.approx(3.457, 1e-3)]
    fl_tuple = (np.float128(4.567890123), np.float_(5.6789012345))
    tmp = mod.round_floats(fl_tuple, precision=5)
    assert isinstance(tmp, list)
    assert tmp == [pytest.approx(4.56789, 1e-5), 5.67890]
    fl_dict = {"bla": np.float128(0.1234455667), "blubb": int(1), "ha": "test"}
    tmp = mod.round_floats(fl_dict, precision=5)
    assert tmp["bla"] == pytest.approx(0.12345, 1e-5)
    assert tmp["blubb"] == 1
    assert isinstance(tmp["blubb"], int)
    assert isinstance(tmp["ha"], str)


@pytest.mark.parametrize("title", ["", "Bla", "Hello"])
@pytest.mark.parametrize("indent", [0, 4, 10])
def test_str_underline(title: str, indent: int):
    lines = mod.str_underline(title, indent).split("\n")
    assert len(lines) == 2
    assert len(lines[0]) == len(lines[1]) == len(title) + indent
    assert lines[0].endswith(title)
    assert lines[1].endswith("-" * len(title))
    assert lines[0][:indent] == lines[1][:indent] == " " * indent


class Constrainer(mod.ConstrainedContainer):
    def __init__(self):
        self.bla = 42
        self.blub = "str"
        self.opt = None


class NestedData(mod.NestedContainer):
    def __init__(self):
        self.bla = dict(a=1, b=2)
        self.blub = dict(c=3, d=4)
        self.d = 42


def test_read_json(tmpdir):
    data = {"bla": 42}
    path = os.path.join(tmpdir, "file.json")
    with open(path, "w") as f:
        simplejson.dump(data, f)
    assert os.path.exists(path)
    reload = mod.read_json(path)
    assert reload == data
    os.remove(path)


@pytest.mark.parametrize("data", [{"bla": 42}, {"bla": 42, "blub": np.nan}])
@pytest.mark.parametrize("kwargs", [dict(), dict(ignore_nan=True, indent=5)])
def test_write_json(tmpdir, data, kwargs):
    path = os.path.join(tmpdir, "file.json")
    mod.write_json(data, path, **kwargs)
    assert os.path.exists(path)
    os.remove(path)


def test_write_json_error(tmpdir):
    path = os.path.join(tmpdir, "file.json")
    with pytest.raises(TypeError) as e:
        mod.write_json({"bla": 42}, path, bla=42)
    assert str(e.value).endswith("unexpected keyword argument 'bla'")


def test_check_make_json(tmpdir):
    fp = os.path.join(tmpdir, "bla.json")
    val = mod.check_make_json(fp)
    assert os.path.exists(val)


def test_check_make_json_error(tmpdir):
    fp = os.path.join(tmpdir, "bla.txt")
    with pytest.raises(ValueError):
        mod.check_make_json(fp)


def test_invalid_input_err_str():
    st = mod.invalid_input_err_str("bla", "42", (42, 43))
    assert st == "Invalid input for bla (42), choose from (42, 43)"


@pytest.mark.parametrize("dir,val", [(".", True), ("/bla/blub", False), (42, False)])
def test_check_dir_access(dir, val):
    assert mod.check_dir_access(dir) == val


def test_Constrainer():
    cont = Constrainer()
    assert cont.bla == 42
    assert cont.blub == "str"
    assert cont.opt is None


def test_NestedData():
    cont = NestedData()
    assert cont.bla == dict(a=1, b=2)
    assert cont.blub == dict(c=3, d=4)


@pytest.mark.parametrize("kwargs", [dict(), dict(bla=400), dict(bla=45, opt={})])
def test_ConstrainedContainer_update(kwargs):
    cont = Constrainer()
    cont.update(**kwargs)
    for key, val in kwargs.items():
        assert cont[key] == val


@pytest.mark.parametrize("kwargs", [dict(blaaaa=400)])
def test_ConstrainedContainer_update_error(kwargs):
    cont = Constrainer()
    with pytest.raises(ValueError):
        cont.update(**kwargs)


def test_NestedData_keys_unnested():
    cont = NestedData()
    keys = cont.keys_unnested()
    assert sorted(keys) == ["a", "b", "bla", "blub", "c", "d", "d"]


def test_NestedData___getitem__():
    cont = NestedData()
    assert cont["d"] == 42


def test_NestedData___getitem___error():
    cont = NestedData()
    with pytest.raises(KeyError):
        cont["a"]


@pytest.mark.parametrize("kwargs", [dict(bla=42), dict(a=400), dict(d=400)])
def test_NestedData_update(kwargs):
    cont = NestedData()
    cont.update(**kwargs)
    for key, value in kwargs.items():
        if key in cont.__dict__:  # toplevel entry
            assert cont[key] == value
        for val in cont.values():
            if isinstance(val, dict) and key in val:
                assert val[key] == value


def test_NestedData_update_error():
    cont = NestedData()
    with pytest.raises(AttributeError) as e:
        cont.update(abc=400)
    assert str(e.value) == "invalid key abc"


@pytest.mark.parametrize("input", [{"b": 1, "a": 2, "kl": 42}])
@pytest.mark.parametrize(
    "pref_list,output_keys",
    [
        ([], ["a", "b", "kl"]),
        (["blaaa"], ["a", "b", "kl"]),
        (["kl"], ["kl", "a", "b"]),
        (["kl", "b"], ["kl", "b", "a"]),
    ],
)
def test_sort_dict_by_name(input, pref_list, output_keys):
    sorted = mod.sort_dict_by_name(input, pref_list)
    assert list(sorted.keys()) == output_keys
