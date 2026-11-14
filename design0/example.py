"""A toy cross-disciplinary chain: CO2 -> warming -> crop yield -> food price.

The numbers are illustrative only, not real estimates.
"""
from math import log2

from cosm import CompositionError, Normal, Uniform, model


@model(inputs={"co2": "ppm"}, outputs={"dT": "K"},
       params={"S": Normal(3.0, 0.5)},
       assumptions=["warming is logarithmic in CO2 concentration",
                    "equilibrium response: no time dynamics"],
       sources=["IPCC AR6 WG1 Ch.7: equilibrium climate sensitivity likely 2.5-4 K"])
def warming(co2, S):
    """Equilibrium warming at a given CO2 level; S is warming per doubling."""
    return {"dT": S * log2(co2 / 280)}


@model(inputs={"dT": "K"}, outputs={"yield_change": "%"},
       params={"beta": Normal(6.0, 2.0)},
       assumptions=["yield falls linearly with warming",
                    "no adaptation (e.g. new cultivars, planting dates)"],
       sources=["Zhao et al. (2017) PNAS: ~3-7% global yield loss per degree, by crop"],
       checks={"cannot lose more than 100% of yield": lambda yield_change: yield_change > -100})
def crop_yield(dT, beta):
    """Change in staple crop yield; beta is % yield lost per kelvin."""
    return {"yield_change": -beta * dT}


@model(inputs={"yield_change": "%"}, outputs={"price_change": "%"},
       params={"elasticity": Uniform(0.2, 0.6)},
       assumptions=["constant price elasticity of demand",
                    "no trade, stocks or substitution between foods"])
def food_price(yield_change, elasticity):
    """Change in food price from a supply shock."""
    return {"price_change": -yield_change / elasticity}


if __name__ == "__main__":
    food_security = warming >> crop_yield >> food_price

    print(food_security.explain())

    print("\n--- run ---")
    result = food_security.run(co2=Normal(560, 20), n=2000, seed=42)
    print(result.report())

    rerun = food_security.run(co2=Normal(560, 20), n=2000, seed=42)
    print("\nreproducible:", rerun.samples == result.samples)

    print("\n--- composition is checked ---")
    try:
        crop_yield >> warming
    except CompositionError as e:
        print("crop_yield >> warming:", e)

    print("\n--- audit trail (first step) ---")
    print(result.audit()[:600], "...")
