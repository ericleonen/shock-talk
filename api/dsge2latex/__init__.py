import re
from typing import List, Set

from .fractions import _convert_fractions
from .latex_helpers import _add_backslashes, _var2latex, _shock2latex


def dsge2latex(laws: List[str]) -> List[str]:
    """
    Converts DSGE laws into LaTeX law equations (for pretty rendering). Specifically, this method:
    - Turns divisions into fractions (e.g. `1/sigma` -> `\frac{1}{\sigma}`, `(a+b)/c` -> `\frac{a+b}{c}`)
    - Formats forwards as expectations (e.g. `F[pi]` -> `E[pi_{t+1}]`)
    - Formats variables with a time subscript (e.g. `pi` -> `pi_{t}`)
    - Formats lags (e.g. `L[pi]` -> `pi_{t-1}`)
    - Removes the `*` between a coefficient and a variable (e.g. `beta*pi` -> `beta pi_{t}`)
    - Formats shocks (e.g. `eps_d` -> `varepsilon^{d}_{t}`)

    For laws that do not strictly follow DSGE law syntax, there are no guarantees.
    """
    # Collect variable and shock names from LHS and F[]/L[] occurrences
    variables: Set[str] = set()
    shocks: Set[str] = set()

    for law in laws:
        lhs = law.split("=", 1)[0].strip()
        (shocks if lhs.startswith("eps_") else variables).add(lhs)

    for law in laws:
        for m in re.finditer(r'[FL]\[(\w+)\]', law):
            name = m.group(1)
            (shocks if name.startswith("eps_") else variables).add(name)

    def convert(law: str) -> str:
        lhs_raw, rhs = law.split("=", 1)
        lhs_name = lhs_raw.strip()

        # 0. Convert divisions to \frac{}{} on raw RHS (tokens still plain)
        rhs = _convert_fractions(rhs)

        # 1. F[var] -> E[\var_{t+1}]
        def repl_forward(m: re.Match) -> str:
            n = m.group(1)
            inner = _shock2latex(n, "t+1") if n.startswith("eps_") else _var2latex(n, "t+1")
            return f"E[{inner}]"
        rhs = re.sub(r'F\[(\w+)\]', repl_forward, rhs)

        # 2. L[var] -> \var_{t-1}
        def repl_lag(m: re.Match) -> str:
            n = m.group(1)
            return _shock2latex(n, "t-1") if n.startswith("eps_") else _var2latex(n, "t-1")
        rhs = re.sub(r'L\[(\w+)\]', repl_lag, rhs)

        # 3. Bare variable names -> var_{t}
        # Sort longest-first to avoid partial replacements (e.g. phi_pi before phi)
        for var in sorted(variables, key=len, reverse=True):
            rhs = re.sub(rf'\b{re.escape(var)}\b', _var2latex(var), rhs)

        # 4. Bare eps_x -> varepsilon^{x}_{t} (after variable substitution so
        #    the shock suffix is never mistaken for a bare variable)
        rhs = re.sub(r'\beps_(\w+)\b', lambda m: _shock2latex("eps_" + m.group(1)), rhs)

        # 5. Remove * between terms (coeff*token -> coeff token)
        rhs = re.sub(r'\*', ' ', rhs)

        # 6. Convert LHS
        lhs_latex = (
            _shock2latex(lhs_name) if lhs_name.startswith("eps_") else _var2latex(lhs_name)
        )

        result = f"{lhs_latex} = {rhs.strip()}"
        return _add_backslashes(result)

    return [convert(law) for law in laws]
