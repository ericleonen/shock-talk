import re
import sympy as sp
from typing import List
from .symbols import to_pizza, SYM_RE

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

# Matches any F[...] or L[...] bracket, capturing the full contents
_FL_ANY_RE = re.compile(r'\b([FL])\[([^\]]*)\]')
# A valid single-variable argument (bare identifier)
_FL_VAR_RE = re.compile(r'^[A-Za-z_]\w*$')


def validate_fl_arguments(laws: List[str]) -> None:
    """
    Verify that every F[...] and L[...] operator contains a single bare
    variable name — never an expression.

    E.g. ``F[beta*x]`` and ``L[x + y]`` are illegal; coefficients must
    appear *outside* the brackets: ``beta*F[x]``.
    """
    for i, law in enumerate(laws, 1):
        for m in _FL_ANY_RE.finditer(law):
            op  = m.group(1)   # 'F' or 'L'
            arg = m.group(2)
            if not _FL_VAR_RE.match(arg):
                raise ValueError(
                    f"Equation {i}: '{op}[{arg}]' — the argument to {op}[...] "
                    f"must be a single variable name, not an expression.\n"
                    f"  {law!r}\n"
                    f"Move any coefficients outside the brackets. "
                    f"For example, write 'beta*{op}[x]' instead of '{op}[beta*x]'."
                )


def validate_unique_lhs(laws: List[str]) -> None:
    """
    Verify that no variable appears as the left-hand side of more than one
    equation.
    """
    seen: dict[str, int] = {}
    for i, law in enumerate(laws, 1):
        if '=' not in law:
            continue   # validate_lhs will catch this
        lhs = law.split('=', 1)[0].strip()
        if lhs in seen:
            raise ValueError(
                f"Variable '{lhs}' is defined on the left-hand side of both "
                f"equation {seen[lhs]} and equation {i}.\n"
                f"Each variable must appear as the LHS of exactly one equation. "
                f"Merge the two equations into a single definition of '{lhs}'."
            )
        seen[lhs] = i


def validate_variable_names(laws: List[str]) -> None:
    """
    Check that LHS variable names do not use forbidden suffixes such as
    ``_next`` or ``_lag``.  These suffixes suggest the author intended a
    temporal reference, which must instead be expressed with ``F[x]`` / ``L[x]``.
    """
    for i, law in enumerate(laws, 1):
        if '=' not in law:
            continue   # validate_lhs will catch this
        lhs = law.split('=', 1)[0].strip()
        if lhs.endswith('_next'):
            base = lhs[:-5]
            raise ValueError(
                f"Equation {i}: '{lhs}' uses a '_next' suffix, which is not "
                f"valid ShockTalk syntax.\n"
                f"  {law!r}\n"
                f"To express next-period {base!r}, use 'F[{base}]' on the "
                f"right-hand side of the equation that defines '{base}'."
            )
        if lhs.endswith('_lag'):
            base = lhs[:-4]
            raise ValueError(
                f"Equation {i}: '{lhs}' uses a '_lag' suffix, which is not "
                f"valid ShockTalk syntax.\n"
                f"  {law!r}\n"
                f"To express last-period {base!r}, use 'L[{base}]' on the "
                f"right-hand side of the equation that defines '{base}'."
            )


def validate_lhs(laws: List[str]) -> None:
    """
    Verify that each equation has exactly one bare variable on the left-hand
    side (no operators, no F/L wrappers, no coefficients).
    """
    for i, law in enumerate(laws, 1):
        if '=' not in law:
            raise ValueError(
                f"Equation {i} has no '=' sign:\n  {law!r}\n"
                "Each equation must be of the form  variable = expression."
            )
        lhs_raw, _ = law.split('=', 1)
        lhs = lhs_raw.strip()
        if not re.fullmatch(r'[A-Za-z_]\w*', lhs):
            raise ValueError(
                f"Equation {i} has an invalid left-hand side: {lhs!r}\n"
                "The left-hand side must be a single bare variable name "
                "(e.g. 'y', 'pi', 'eps_d')."
            )


def validate_linearity(laws: List[str], endogenous: List[str]) -> None:
    """
    Verify that every equation is linear in all endogenous symbols (variables
    and shocks, in all their temporal forms: bare, Prime, Lag).

    Parameters
    ----------
    laws : list[str]
        Raw equation strings.
    endogenous : list[str]
        Base names of all endogenous quantities (variables + shocks).
    """
    # Build the full set of endogenous sympy Symbol objects
    endo_forms: set[str] = set()
    for v in endogenous:
        endo_forms |= {v, v + 'Prime', v + 'Lag'}

    for i, law in enumerate(laws, 1):
        pizza  = to_pizza(law)
        lhs, rhs = pizza.split('=', 1)

        # Collect all identifiers and build a sympy local namespace
        all_ids  = set(SYM_RE.findall(pizza))
        sym_dict = {name: sp.Symbol(name) for name in all_ids}
        endo_syms = {sym_dict[f] for f in endo_forms if f in sym_dict}

        try:
            expr = sp.sympify(
                f"({rhs}) - ({lhs})", locals=sym_dict
            )
        except Exception as exc:
            raise ValueError(
                f"Equation {i} could not be parsed as a mathematical "
                f"expression:\n  {law!r}\n"
                f"SymPy error: {exc}"
            ) from exc

        # 1. Check degree of each endogenous symbol
        for sym in endo_syms:
            try:
                deg = sp.Poly(expr, sym).degree()
            except sp.PolynomialError:
                # non-polynomial in this symbol → definitely nonlinear
                raise ValueError(
                    f"Equation {i} is nonlinear in '{sym}' "
                    f"(appears inside a non-polynomial expression):\n  {law!r}"
                )
            if deg > 1:
                raise ValueError(
                    f"Equation {i} is nonlinear in '{sym}' (degree {deg}):\n"
                    f"  {law!r}\n"
                    "All endogenous variables must appear with exponent 1."
                )

        # 2. Check for cross-products between endogenous symbols
        for term in sp.Add.make_args(sp.expand(expr)):
            endo_in_term = [s for s in term.free_symbols if s in endo_syms]
            if len(endo_in_term) > 1:
                raise ValueError(
                    f"Equation {i} contains a product of endogenous "
                    f"variables {[str(s) for s in endo_in_term]}:\n  {law!r}\n"
                    "Only linear combinations are allowed."
                )


def validate_shock_names(laws: List[str]) -> None:
    """
    Warn the user if they have written explicit ``e_*`` white-noise terms that
    look like they are meant to be shock processes (should start with ``eps_``).
    """
    for i, law in enumerate(laws, 1):
        lhs_raw, _ = law.split('=', 1)
        lhs = lhs_raw.strip()
        if lhs.startswith('e_') and not lhs.startswith('eps_'):
            raise ValueError(
                f"Equation {i} defines '{lhs}' on the left-hand side.  "
                "White-noise inputs start with 'e_' and are auto-generated — "
                "did you mean 'eps_" + lhs[2:] + "'?"
            )


def validate_equation_count(
    laws: List[str],
    variables: List[str],
    shocks: List[str],
) -> None:
    """
    Verify that the number of equations equals the number of endogenous
    quantities (variables + shocks).

    If shock AR(1) processes are not written explicitly they will be
    auto-generated, so we account for that here.
    """
    all_endo = variables + shocks
    n_endo   = len(all_endo)

    # Find which shocks already have an explicit AR(1) equation
    lhs_vars = {law.split('=')[0].strip() for law in laws}
    auto_generated = [s for s in shocks if s not in lhs_vars]
    n_effective = len(laws) + len(auto_generated)

    if n_effective != n_endo:
        raise ValueError(
            f"Model has {n_endo} endogenous quantities "
            f"({variables + shocks}) but {n_effective} equations "
            f"({len(laws)} explicit + {len(auto_generated)} auto-generated "
            f"AR(1) shock equations).  "
            "Add or remove equations so the counts match."
        )