from abc import ABC

class PortType(ABC):
  def __eq__(self, comparator : PortType):
    """Type equality"""
    pass

  def __le__(self, comparator : PortType):
    """Type inequality (subtyping)"""
    pass

  def __mul__(self, other):
    """Product composition of types"""
    pass

  def __add__(self, other):
    """Sum (alternation) composition of types"""
    pass