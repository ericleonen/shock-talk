from dsge2latex import dsge2latex


# ---------------------------------------------------------------------------
# 1. Greek letter handling
# ---------------------------------------------------------------------------

def test_greek_lhs_gets_backslash():
    result = dsge2latex(["pi = 0"])
    assert result[0] == r"\pi_{t} = 0"

def test_greek_rhs_coefficient_gets_backslash():
    result = dsge2latex(["y = beta*y"])
    assert result[0] == r"y_{t} = \beta y_{t}"

def test_multiple_greek_on_rhs():
    result = dsge2latex(["pi = alpha*y + sigma*r", "y = 0", "r = 0"])
    assert result == [
        r"\pi_{t} = \alpha y_{t} + \sigma r_{t}",
        r"y_{t} = 0",
        r"r_{t} = 0"
    ]

def test_uppercase_greek():
    result = dsge2latex(["Pi = Gamma*Y", "Y = 0"])
    assert result[0] == r"\Pi_{t} = \Gamma Y_{t}"

def test_greek_substring_not_double_replaced():
    # "epsilon" contains "pi" — make sure only \epsilon appears, not \epsi\pi on
    result = dsge2latex(["epsilon = 0"])
    assert r"\epsilon_{t}" in result[0]
    assert r"\pi" not in result[0]

def test_all_lowercase_greek_get_backslash():
    greek_names = [
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta",
        "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi",
        "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
    ]
    for name in greek_names:
        result = dsge2latex([f"{name} = 0"])
        assert rf"\{name}_{{t}}" in result[0], f"Missing backslash for {name}"

def test_non_greek_variable_no_backslash():
    result = dsge2latex(["y = 0"])
    # 'y' is not Greek — should not get a backslash
    assert r"\y" not in result[0]
    assert "y_{t}" in result[0]


# ---------------------------------------------------------------------------
# 2. Forwards and lags handling
# ---------------------------------------------------------------------------

def test_forward_becomes_expectation():
    result = dsge2latex(["pi = F[pi]"])
    assert r"E[\pi_{t+1}]" in result[0]

def test_lag_becomes_t_minus_1():
    result = dsge2latex(["pi = L[pi]"])
    assert r"\pi_{t-1}" in result[0]

def test_forward_non_greek():
    result = dsge2latex(["y = F[y]"])
    assert "E[y_{t+1}]" in result[0]

def test_lag_non_greek():
    result = dsge2latex(["y = L[y]"])
    assert "y_{t-1}" in result[0]

def test_forward_and_lag_same_law():
    result = dsge2latex(["pi = F[pi] + L[pi]"])
    assert r"E[\pi_{t+1}]" in result[0]
    assert r"\pi_{t-1}" in result[0]

def test_forward_shock():
    result = dsge2latex(["eps_d = F[eps_d]"])
    assert r"E[\varepsilon^{d}_{t+1}]" in result[0]

def test_lag_shock():
    result = dsge2latex(["eps_d = L[eps_d]"])
    assert r"\varepsilon^{d}_{t-1}" in result[0]


# ---------------------------------------------------------------------------
# 3. Time subscripts
# ---------------------------------------------------------------------------

def test_bare_variable_gets_t_subscript():
    result = dsge2latex(["y = c", "c = 0"])
    assert "y_{t}" in result[0]
    assert "c_{t}" in result[0]

def test_variable_inside_forward_gets_t_plus_1():
    result = dsge2latex(["pi = F[pi]"])
    assert r"\pi_{t+1}" in result[0]

def test_variable_inside_lag_gets_t_minus_1():
    result = dsge2latex(["pi = L[pi]"])
    assert r"\pi_{t-1}" in result[0]

def test_lhs_gets_t_subscript():
    result = dsge2latex(["y = 0"])
    assert result[0].startswith("y_{t}")

def test_multiple_variables_all_get_t():
    result = dsge2latex(["y = c + i + g", "c = 0", "i = 0", "g = 0"])
    for var in ["y_{t}", "c_{t}", "i_{t}", "g_{t}"]:
        assert var in result[0], f"{var} not found in: {result[0]}"

def test_subscripted_variable_name():
    # Variables like phi_pi are treated as a single token
    result = dsge2latex(["pi = phi_pi*L[pi]"])
    assert result[0] == r"\pi_{t} = \phi_\pi \pi_{t-1}"


# ---------------------------------------------------------------------------
# 4. Fractional coefficients handling
# ---------------------------------------------------------------------------

def test_simple_fraction():
    result = dsge2latex(["pi = 1/sigma"])
    assert r"\frac{1}{\sigma}" in result[0]

def test_fraction_with_expression_numerator():
    result = dsge2latex(["pi = (a+b)/c"])
    assert r"\frac" in result[0]
    # SymPy may reorder terms; just confirm it's a fraction
    assert "a" in result[0] and "b" in result[0] and "c" in result[0]

def test_fraction_with_expression_denominator():
    result = dsge2latex(["pi = 1/(sigma+eta)"])
    assert r"\frac{1}" in result[0]
    assert r"\sigma" in result[0]
    assert r"\eta" in result[0]

def test_fraction_both_expressions():
    result = dsge2latex(["pi = (alpha+beta)/(gamma+delta)"])
    assert r"\frac" in result[0]

def test_integer_fraction():
    result = dsge2latex(["pi = 1/2"])
    assert r"\frac{1}{2}" in result[0]

def test_fraction_coefficient_times_variable():
    # e.g.  1/sigma * y  ->  \frac{1}{\sigma} y_{t}
    result = dsge2latex(["pi = 1/sigma*y", "y = 0"])
    assert r"\frac{1}{\sigma}" in result[0]
    assert "y_{t}" in result[0]


# ---------------------------------------------------------------------------
# 5. Shocks handling
# ---------------------------------------------------------------------------

def test_bare_shock_on_rhs():
    result = dsge2latex(["pi = eps_d"])
    assert r"\varepsilon^{d}_{t}" in result[0]

def test_shock_lhs():
    result = dsge2latex(["eps_d = rho*L[eps_d]"])
    assert result[0].startswith(r"\varepsilon^{d}_{t}")

def test_shock_multi_character_suffix():
    result = dsge2latex(["eps_mp = 0"])
    assert r"\varepsilon^{mp}_{t}" in result[0]

def test_shock_in_forward():
    result = dsge2latex(["eps_d = F[eps_d]"])
    assert r"E[\varepsilon^{d}_{t+1}]" in result[0]

def test_shock_in_lag():
    result = dsge2latex(["eps_d = L[eps_d]"])
    assert r"\varepsilon^{d}_{t-1}" in result[0]

def test_multiple_shocks():
    result = dsge2latex(["pi = eps_d + eps_mp"])
    assert r"\varepsilon^{d}_{t}" in result[0]
    assert r"\varepsilon^{mp}_{t}" in result[0]

def test_shock_not_treated_as_plain_variable():
    # eps_d must render as varepsilon^{d}_{t}, not eps_d_{t}
    result = dsge2latex(["pi = eps_d"])
    assert "eps_d_{t}" not in result[0]