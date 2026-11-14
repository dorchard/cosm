import json
class Proc:
  fun = None

  def __init__(self, name_arg, fun_arg):
    self.fun  = fun_arg
    self.name = name_arg

  def __rshift__(self, other):
    if isinstance(other, Proc):
      return Proc(self.name + "_" + other.name, lambda x: other.run(self.run(x)))
    else:
      raise TypeError("Unsupported operand type for >>: 'Proc' and '{}'".format(type(other).__name__))

  def run(self, arg):
    with open(self.name + ".log", "a+") as f:
      f.seek(0)
      text = f.read()
    # read hash as JSON, treating an empty file as an empty hash
    hash_data = json.loads(text) if text.strip() else {}

    # JSON object keys are always strings, so key on the JSON encoding of arg
    key = json.dumps(arg)
    if key in hash_data:
      return hash_data[key]
    else:
      res = self.fun(arg)
      hash_data[key] = res
      with open(self.name + ".log", "w") as f:
        json.dump(hash_data, f)
      return res

# Example

f = Proc("f", lambda x: x + 1)
g = Proc("g", lambda x: x * 2)

p = f >> g
q = g >> f

print(p.run(42))
print(p.run(100))
print(p.run(42))
print(q.run(21))
