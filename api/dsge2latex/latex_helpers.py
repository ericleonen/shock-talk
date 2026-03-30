import re

GREEK = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho", "sigma",
    "tau", "upsilon", "phi", "chi", "psi", "omega",
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Pi", "Rho", "Sigma",
    "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega", "varepsilon"
]

# Sort longest-first so e.g. "epsilon" is replaced before "pi"
GREEK_SORTED = sorted(GREEK, key=len, reverse=True)


def _add_backslashes(s: str) -> str:
    """Scan left to right and prepend \\ to every known Greek symbol name."""
    for sym in GREEK_SORTED:
        s = re.sub(rf'(?<!\\)(?<![A-Za-z]){sym}(?![A-Za-z])', lambda _: rf'\{sym}', s)
    return s


def _var2latex(name: str, time: str = "t") -> str:
    """Render a variable name with a time subscript, e.g. pi -> pi_{t}."""
    return f"{name}_{{{time}}}"


def _shock2latex(name: str, time: str = "t") -> str:
    """Render a shock eps_x as varepsilon^{x}_{t}."""
    suffix = name[4:]  # strip "eps_"
    return f"varepsilon^{{{suffix}}}_{{{time}}}"
