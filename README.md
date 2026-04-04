# ShockTalk

ShockTalk is a natural-language interface for building and playing with Dynamic Stochastic General Equilibrium (DSGE) models. It is built on top of a Python library, also named `shocktalk`, that allows you to create simple, linear DSGE models in plain syntax.

---

## How It Works

1. **Natural language → ShockTalk syntax.** You describe the model in plain English (e.g. "Inflation today is driven by expected future inflation, the current output gap, and a cost-push shock."). A language model translates this into ShockTalk's equation syntax.
2. **ShockTalk syntax → econpizza YAML.** The equations are parsed, validated, and compiled into a [econpizza](https://github.com/gboehl/econpizza) YAML model definition.
3. **Simulation.** econpizza solves the rational-expectations equilibrium and returns impulse-response paths as a `pd.DataFrame`.

You can also skip step 1 and write ShockTalk syntax directly — see the example below.

---

## Supported Models

ShockTalk supports **log-linearized** models — a specific and widely-used approximation technique in macroeconomics.

### What log-linearization means

Most macroeconomic models are inherently nonlinear (e.g. a Cobb-Douglas production function $Y = K^\alpha N^{1-\alpha}$). Log-linearization approximates the model by replacing each variable with its **percentage deviation from steady state**:

$$\hat{x}_t = \frac{x_t - x^\ast}{x^\ast} \approx \log x_t - \log x^{*}$$

where $x^*$ is the steady-state level of $x$. The resulting equations are linear in the $\hat{x}_t$ terms, which makes the model tractable to solve analytically and simulate efficiently.

### Why all variables start at zero

Because every variable is expressed as a deviation from its own steady state, the steady state of the transformed system is exactly zero for every variable — by definition. A value of `0.01` in the simulation output means the variable is 1% above its steady-state level; `0` means it is exactly at steady state.

This has a convenient practical consequence: you never need to know or specify the actual steady-state levels ($Y^*$, $\Pi^*$, etc.). Those levels get divided out in the transformation, so only the **parameters governing dynamics** — how fast variables return to steady state, how they co-move — need to be supplied. Simulations always start from steady state, meaning all variables begin at zero before any shock is applied.

### Equation syntax

ShockTalk supports models where every equation is **linear** in the following terms:

| Term | Syntax | Meaning |
|------|--------|---------|
| Current variable | `x` | $x_t$ |
| Forward variable | `F[x]` | $E_t[x_{t+1}]$ |
| Lagged variable | `L[x]` | $x_{t-1}$ |
| Shock process | `eps_*` | AR(1) state, e.g. $\varepsilon^d_t$ |
| White noise | `e_*` | i.i.d. innovation to a shock process |

Equations must take the form of a single endogenous variable on the left-hand side, with a linear combination of the terms above on the right-hand side. Coefficients may be arbitrary (nonlinear) expressions in parameters (symbols that are neither variables nor shocks).

### Example

A standard three-equation New Keynesian model:

$$
\begin{aligned}
y_t      &= E_t[y_{t+1}] - \frac{1}{\sigma}(r_t - E_t[\pi_{t+1}]) + \varepsilon^d_t \\
\pi_t    &= \beta\, E_t[\pi_{t+1}] + \kappa\, y_t + \varepsilon^u_t \\
r_t      &= \phi_\pi \pi_t + \phi_y y_t
\end{aligned}
$$

```python
from dsge import DSGE

model = DSGE([
    "y  = F[y] - (1/sigma)*(r - F[pi]) + eps_d",
    "pi = beta*F[pi] + kappa*y + eps_u",
    "r  = phi_pi*pi + phi_y*y",
])

irf = model.simulate(
    parameters={
        "sigma": 1.0,  "beta": 0.99, "kappa": 0.1,
        "phi_pi": 1.5, "phi_y": 0.5,
        "rho_d": 0.8,  "rho_u": 0.8,
    },
    shocks={"e_d": 0.01},  # 1% demand shock in period 0
    T=40,
)
```

`simulate` returns a `pd.DataFrame` with `T + 1` rows (periods 0 … T) and one column per endogenous variable, in deviations from steady state:

```
        eps_d     eps_u        pi         r         y
period
0      0.0100    0.0000    0.0058    0.0116    0.0077
1      0.0080    0.0000    0.0046    0.0093    0.0055
2      0.0064    0.0000    0.0037    0.0074    0.0040
...
```

### What is Not Supported

- Nonlinear terms in endogenous variables (e.g. `y**2`, `y*pi`)
- Leads or lags beyond one period (e.g. `F[F[x]]`, `L[L[x]]`)
- Equations without a unique stable rational-expectations equilibrium (Blanchard-Kahn violations)
