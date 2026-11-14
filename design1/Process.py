"""
A process has a number of input ports and output ports, each of which
has an associated type (a subclass of PortType) and predicate (a sub
class of Predicate)
"""

from PortType import PortType
from Predicate import Predicate

class Process[T: PortType, P: Predicate]:
  def get_input_ports(self) -> list[tuple[str, T]]:
    pass
