"""cosm: a tiny seed for composing models.

A model maps named, unit-annotated inputs to named, unit-annotated outputs.
It carries its uncertain parameters, stated assumptions, sources and checks.
Models compose:

    a >> b   wire a's outputs into b's inputs (by port name)
    a | b    run a and b side by side (no wiring between them)

Composition is checked up front (units must agree, no dangling or backwards
wiring). Running a model propagates uncertainty by Monte Carlo sampling and
returns a Result that carries an audit trace of every step.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable


# Uncertainty -------------------------------------------------------------

@dataclass(frozen=True)
class Normal:
    mean: float
    sd: float

    def sample(self, rng: random.Random) -> float:
        return rng.gauss(self.mean, self.sd)


@dataclass(frozen=True)
class Uniform:
    lo: float
    hi: float

    def sample(self, rng: random.Random) -> float:
        return rng.uniform(self.lo, self.hi)


def _sampler(x) -> Callable[[random.Random], float]:
    """A plain number is a distribution with no spread."""
    return x.sample if hasattr(x, "sample") else (lambda rng: x)


# Models ------------------------------------------------------------------

class CompositionError(Exception):
    pass


@dataclass(frozen=True)
class Step:
    """One atomic model: a pointwise function plus everything a human needs
    to understand, question and audit it."""
    name: str
    fn: Callable[..., dict[str, float]]
    inputs: dict[str, str]          # port -> unit
    outputs: dict[str, str]         # port -> unit
    params: dict[str, object]       # name -> distribution or constant
    assumptions: tuple[str, ...]
    sources: tuple[str, ...]
    checks: dict[str, Callable]     # description -> predicate over ports
    doc: str
    version: str                    # hash of the model's source


def model(inputs, outputs, params=None, assumptions=(), sources=(), checks=None):
    """Decorator turning a pointwise function into a composable Model."""
    def wrap(fn):
        source = inspect.getsource(fn)
        return Model([Step(
            name=fn.__name__, fn=fn, inputs=dict(inputs), outputs=dict(outputs),
            params=dict(params or {}), assumptions=tuple(assumptions),
            sources=tuple(sources), checks=dict(checks or {}),
            doc=inspect.getdoc(fn) or "",
            version=hashlib.sha256(source.encode()).hexdigest()[:12],
        )])
    return wrap


class Model:
    """A pipeline of steps, ordered so every step's inputs are either free
    (supplied by the caller) or produced by an earlier step."""

    def __init__(self, steps: list[Step]):
        self.steps = steps

    @property
    def inputs(self) -> dict[str, str]:
        produced, free = set(), {}
        for s in self.steps:
            free.update({p: u for p, u in s.inputs.items() if p not in produced})
            produced |= s.outputs.keys()
        return free

    @property
    def outputs(self) -> dict[str, str]:
        return {p: u for s in self.steps for p, u in s.outputs.items()}

    def __rshift__(self, other: Model) -> Model:
        return _compose(self, other, parallel=False)

    def __or__(self, other: Model) -> Model:
        return _compose(self, other, parallel=True)

    def explain(self) -> str:
        """A plain-language account of what this model is and assumes."""
        ports = lambda d: ", ".join(f"{p} [{u}]" for p, u in d.items())
        lines = [f"needs: {ports(self.inputs)}"]
        for s in self.steps:
            lines.append(f"\n{s.name}  ({ports(s.inputs)} -> {ports(s.outputs)})")
            if s.doc:
                lines.append(f"  {s.doc}")
            lines += [f"  param   {k} ~ {d!r}" for k, d in s.params.items()]
            lines += [f"  assumes {a}" for a in s.assumptions]
            lines += [f"  checks  {c}" for c in s.checks]
            lines += [f"  source  {r}" for r in s.sources]
        return "\n".join(lines)

    def run(self, n: int = 1000, seed: int = 0, **given) -> Result:
        missing = self.inputs.keys() - given.keys()
        if missing:
            raise ValueError(f"missing inputs: {sorted(missing)}")

        # Each input and step gets its own seeded stream, so adding a step
        # elsewhere never changes the draws of an existing one.
        env = {}
        for p, v in given.items():
            rng, draw = random.Random(f"{seed}:input:{p}"), _sampler(v)
            env[p] = [draw(rng) for _ in range(n)]

        trace = []
        for s in self.steps:
            rng = random.Random(f"{seed}:{s.name}")
            draws = {k: [_sampler(d)(rng) for _ in range(n)] for k, d in s.params.items()}
            outs = {p: [] for p in s.outputs}
            for i in range(n):
                args = {p: env[p][i] for p in s.inputs} | {k: v[i] for k, v in draws.items()}
                result = s.fn(**args)
                if result.keys() != s.outputs.keys():
                    raise ValueError(f"{s.name} returned {sorted(result)}, "
                                     f"declared {sorted(s.outputs)}")
                for p in s.outputs:
                    outs[p].append(result[p])
            env.update(outs)
            trace.append({
                "model": s.name, "version": s.version,
                "inputs": s.inputs, "outputs": s.outputs,
                "params": {k: repr(d) for k, d in s.params.items()},
                "assumptions": list(s.assumptions), "sources": list(s.sources),
                "checks": {c: _pass_rate(pred, env, n) for c, pred in s.checks.items()},
            })

        units = self.inputs | self.outputs
        return Result(env, units, trace, seed, n, {p: repr(v) for p, v in given.items()})


def _pass_rate(pred: Callable, env: dict, n: int) -> float:
    ports = inspect.signature(pred).parameters
    return sum(bool(pred(**{p: env[p][i] for p in ports})) for i in range(n)) / n


def _compose(a: Model, b: Model, parallel: bool) -> Model:
    steps = a.steps + b.steps

    names = [s.name for s in steps]
    if len(set(names)) != len(names):
        raise CompositionError(f"duplicate model names in {names}")

    # Within a composite, a port name denotes one quantity with one unit.
    seen: dict[str, tuple[str, str]] = {}
    for s in steps:
        for p, u in (s.inputs | s.outputs).items():
            unit, owner = seen.setdefault(p, (u, s.name))
            if unit != u:
                raise CompositionError(
                    f"'{p}' is [{unit}] in {owner} but [{u}] in {s.name}")

    if both := a.outputs.keys() & b.outputs.keys():
        raise CompositionError(f"both sides produce {sorted(both)}")
    if back := a.inputs.keys() & b.outputs.keys():
        raise CompositionError(
            f"left side needs {sorted(back)}, produced by the right side; swap the order")
    if parallel and (fwd := b.inputs.keys() & a.outputs.keys()):
        raise CompositionError(f"'|' sides are wired together via {sorted(fwd)}; use '>>'")

    return Model(steps)


# Results -----------------------------------------------------------------

@dataclass
class Result:
    samples: dict[str, list[float]]
    units: dict[str, str]
    trace: list[dict]
    seed: int
    n: int
    given: dict[str, str] = field(default_factory=dict)

    def summary(self, port: str) -> tuple[float, float, float]:
        """Mean and 90% interval (5th, 95th percentiles)."""
        xs = self.samples[port]
        qs = statistics.quantiles(xs, n=20)
        return statistics.fmean(xs), qs[0], qs[-1]

    def report(self) -> str:
        lines = [f"seed={self.seed}  samples={self.n}"]
        for p, u in self.units.items():
            mean, lo, hi = self.summary(p)
            lines.append(f"  {p:>14} = {mean:8.2f} {u:<4} (90%: {lo:.2f} .. {hi:.2f})")
        for t in self.trace:
            for c, rate in t["checks"].items():
                flag = "ok  " if rate == 1 else "FAIL"
                lines.append(f"  [{flag}] {t['model']}: {c} ({rate:.1%} of samples)")
        return "\n".join(lines)

    def audit(self) -> str:
        """Everything needed to reproduce and scrutinise this run, as JSON."""
        return json.dumps({"seed": self.seed, "n": self.n, "given": self.given,
                           "trace": self.trace}, indent=2)
