import json
import icechunk
import zarr

# A single Icechunk repository holds the hash for every Proc: one Zarr group
# per Proc name, with the hash kept in the group's attributes.
repo = icechunk.Repository.open_or_create(
  icechunk.local_filesystem_storage("hashcons.icechunk"))

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
    # read the hash from the latest snapshot, treating a missing group (or a
    # fresh repository with no root group yet) as an empty hash
    session = repo.readonly_session(branch="main")
    try:
      hash_data = dict(zarr.open_group(session.store, mode="r")[self.name].attrs)
    except (zarr.errors.GroupNotFoundError, KeyError):
      hash_data = {}

    # Zarr attributes are JSON, whose object keys are always strings, so key on
    # the JSON encoding of arg
    key = json.dumps(arg)
    if key in hash_data:
      print(f"[{self.name}]: hashed {key} = {hash_data[key]}")
      return hash_data[key]
    else:
      print(f"[{self.name}]: computing {key}")
      res = self.fun(arg)
      session = repo.writable_session("main")
      root = zarr.open_group(session.store, mode="a")
      root.require_group(self.name).attrs[key] = res
      session.commit(f"{self.name}({key}) = {json.dumps(res)}")
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
