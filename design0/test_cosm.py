import pytest

from cosm import CompositionError, Normal, model


@model(inputs={"x": "m"}, outputs={"y": "m"}, params={"k": Normal(2.0, 0.1)})
def double(x, k):
    return {"y": k * x}


@model(inputs={"y": "m"}, outputs={"z": "m"})
def inc(y):
    return {"z": y + 1}


@model(inputs={"y": "km"}, outputs={"w": "km"})
def in_km(y):
    return {"w": y}


@model(inputs={"a": "s"}, outputs={"b": "s"})
def other(a):
    return {"b": a}


def test_sequential_wires_by_name():
    m = double >> inc
    assert m.inputs == {"x": "m"}
    assert m.outputs == {"y": "m", "z": "m"}
    r = m.run(x=1.0, n=500)
    mean, lo, hi = r.summary("z")
    assert lo < 3.0 < hi


def test_unit_mismatch_rejected():
    with pytest.raises(CompositionError, match="'y'"):
        double >> in_km


def test_backwards_wiring_rejected():
    with pytest.raises(CompositionError, match="swap"):
        inc >> double


def test_parallel():
    m = double | other
    assert m.inputs == {"x": "m", "a": "s"}
    with pytest.raises(CompositionError):
        double | inc


def test_reproducible_and_stable_under_extension():
    a = double.run(x=1.0, seed=7).samples["y"]
    assert double.run(x=1.0, seed=7).samples["y"] == a
    assert (double >> inc).run(x=1.0, seed=7).samples["y"] == a
    assert double.run(x=1.0, seed=8).samples["y"] != a


def test_missing_input():
    with pytest.raises(ValueError, match="missing"):
        double.run()
