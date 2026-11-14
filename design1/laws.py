"""Property-based laws that any instance of the Type interface should satisfy.

The laws only use ==, <=, * and +, so they apply equally to Predicate.

Usage: subclass TypeLaws in a pytest test module and set `elements` to a
Hypothesis strategy generating instances, e.g.

  class TestMyType(TypeLaws):
    elements = my_type_strategy()

Laws with premises (transitivity, congruence) are stated as implications, so
they hold vacuously when the premise fails. Strategies drawing from a small pool
of base types make the premises hold more often and the tests more meaningful.
"""

from hypothesis import given, strategies as st


def implies(p, q):
  return (not p) or q


class TypeLaws:
  elements: st.SearchStrategy

  def draw(self, data, n):
    return [data.draw(self.elements) for _ in range(n)]

  # == is an equivalence relation

  @given(st.data())
  def test_eq_reflexive(self, data):
    [a] = self.draw(data, 1)
    assert a == a

  @given(st.data())
  def test_eq_symmetric(self, data):
    a, b = self.draw(data, 2)
    assert implies(a == b, b == a)

  @given(st.data())
  def test_eq_transitive(self, data):
    a, b, c = self.draw(data, 3)
    assert implies(a == b and b == c, a == c)

  # <= is a preorder

  @given(st.data())
  def test_le_reflexive(self, data):
    [a] = self.draw(data, 1)
    assert a <= a

  @given(st.data())
  def test_le_transitive(self, data):
    a, b, c = self.draw(data, 3)
    assert implies(a <= b and b <= c, a <= c)

  # == is a congruence for * and +

  @given(st.data())
  def test_eq_congruence_mul(self, data):
    a, a2, b, b2 = self.draw(data, 4)
    assert implies(a == a2 and b == b2, a * b == a2 * b2)

  @given(st.data())
  def test_eq_congruence_add(self, data):
    a, a2, b, b2 = self.draw(data, 4)
    assert implies(a == a2 and b == b2, a + b == a2 + b2)

  # <= is a congruence (monotone) for * and +

  @given(st.data())
  def test_le_congruence_mul(self, data):
    a, a2, b, b2 = self.draw(data, 4)
    assert implies(a <= a2 and b <= b2, a * b <= a2 * b2)

  @given(st.data())
  def test_le_congruence_add(self, data):
    a, a2, b, b2 = self.draw(data, 4)
    assert implies(a <= a2 and b <= b2, a + b <= a2 + b2)

  # * and + are associative (up to ==)

  @given(st.data())
  def test_mul_associative(self, data):
    a, b, c = self.draw(data, 3)
    assert (a * b) * c == a * (b * c)

  @given(st.data())
  def test_add_associative(self, data):
    a, b, c = self.draw(data, 3)
    assert (a + b) + c == a + (b + c)
