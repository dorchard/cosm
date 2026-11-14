"""Sanity checks for the TypeLaws harness, using toy instances."""

from hypothesis import strategies as st

from laws import TypeLaws


class FinSet:
  """Toy model: finite sets under subset, intersection and union."""

  def __init__(self, xs):
    self.xs = frozenset(xs)

  def __eq__(self, other):
    return self.xs == other.xs

  def __le__(self, other):
    return self.xs <= other.xs

  def __mul__(self, other):
    return FinSet(self.xs & other.xs)

  def __add__(self, other):
    return FinSet(self.xs | other.xs)

  def __repr__(self):
    return f"FinSet({set(self.xs)})"


class TestFinSetLaws(TypeLaws):
  elements = st.frozensets(st.integers(0, 3)).map(FinSet)
