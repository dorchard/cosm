from abc import ABC

class Predicate(ABC):
  def __eq__(self, comparator : Predicate):
    """Predicate equality"""
    pass

  def __le__(self, comparator : Predicate):
    """Predicate inequality (implication)"""
    pass

  def __mul__(self, other):
    """Product composition of predicates"""
    pass

  def __add__(self, other):
    """Sum (alternation) composition of predicates"""
    pass
