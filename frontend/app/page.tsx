'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import Header from '@/components/Header';
import InputPanel from '@/components/InputPanel';
import ResultsPanel from '@/components/ResultsPanel';
import { ActiveTab } from '@/components/InputTabs';
import { ParameterConfig, ShockConfig } from '@/components/ParameterConsole';
import { IRFDataPoint } from '@/components/IRFChart';

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = '/api';

// ─── Parameter metadata ───────────────────────────────────────────────────────

const PARAMETER_META: Record<string, { label: string; min: number; max: number; step: number }> = {
  sigma:   { label: 'Intertemporal elasticity of substitution', min: 0.1,  max: 5.0,   step: 0.01  },
  beta:    { label: 'Household discount factor',                min: 0.9,  max: 0.999, step: 0.001 },
  kappa:   { label: 'New Keynesian Phillips curve slope',       min: 0.01, max: 0.5,   step: 0.005 },
  phi_pi:  { label: 'Taylor rule coefficient on inflation',     min: 1.0,  max: 3.0,   step: 0.05  },
  phi_y:   { label: 'Taylor rule coefficient on output gap',    min: 0.0,  max: 2.0,   step: 0.05  },
  rho_d:   { label: 'Demand shock AR(1) persistence',           min: 0.0,  max: 0.99,  step: 0.01  },
  rho_u:   { label: 'Cost-push shock AR(1) persistence',        min: 0.0,  max: 0.99,  step: 0.01  },
  rho:     { label: 'Shock AR(1) persistence',                  min: 0.0,  max: 0.99,  step: 0.01  },
  delta:   { label: 'Capital depreciation rate',                min: 0.01, max: 0.1,   step: 0.001 },
  alpha:   { label: 'Capital share in production',              min: 0.2,  max: 0.5,   step: 0.01  },
  eta:     { label: 'Frisch elasticity of labor supply',        min: 0.1,  max: 5.0,   step: 0.1   },
};

function buildParameterConfig(name: string, value: number): ParameterConfig {
  const meta = PARAMETER_META[name] ?? {
    label: 'Model parameter',
    min: Math.min(0, value * 0.1),
    max: Math.max(2, value * 2),
    step: 0.01,
  };
  // Clamp value within [min, max] in case the API returns something outside the default range
  const clampedValue = Math.min(meta.max, Math.max(meta.min, value));
  return { name, value: clampedValue, ...meta };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Extract e_* shock input names from a list of ShockTalk equations. */
function extractShockNames(equations: string[]): string[] {
  const seen = new Set<string>();
  const re = /\beps_(\w+)\b/g;
  for (const eq of equations) {
    let m: RegExpExecArray | null;
    while ((m = re.exec(eq)) !== null) {
      seen.add(`e_${m[1]}`);
    }
  }
  return Array.from(seen);
}

/** Parse raw ShockTalk textarea text into an array of non-empty, non-comment law strings. */
function parseLaws(text: string): string[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'));
}

/** Convert the /simulate response data dict into IRFDataPoint[]. */
function responseToIRF(data: Record<string, number[]>): {
  points: IRFDataPoint[];
  variables: string[];
} {
  const variables = Object.keys(data);
  if (variables.length === 0) return { points: [], variables: [] };
  const T = data[variables[0]].length;
  const points: IRFDataPoint[] = Array.from({ length: T }, (_, t) => {
    const point: IRFDataPoint = { period: t };
    for (const v of variables) point[v] = data[v][t];
    return point;
  });
  return { points, variables };
}

// ─── Default NK model state ───────────────────────────────────────────────────

const DEFAULT_SHOCKTALK = `y   = F[y] - (1/sigma)*(r - F[pi]) + eps_d
pi  = beta*F[pi] + kappa*y + eps_u
r   = phi_pi*pi + phi_y*y`;

const DEFAULT_PARAMETERS: ParameterConfig[] = [
  buildParameterConfig('sigma',  1.0),
  buildParameterConfig('beta',   0.99),
  buildParameterConfig('kappa',  0.1),
  buildParameterConfig('phi_pi', 1.5),
  buildParameterConfig('phi_y',  0.5),
  buildParameterConfig('rho_d',  0.8),
  buildParameterConfig('rho_u',  0.5),
];

const DEFAULT_SHOCKS: ShockConfig[] = [
  { name: 'e_d', value: 0.01 },
  { name: 'e_u', value: 0.0  },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home() {
  // Input state
  const [activeTab, setActiveTab]         = useState<ActiveTab>('shocktalk');
  const [nlText, setNLText]               = useState('');
  const [shocktalkText, setShockTalkText] = useState(DEFAULT_SHOCKTALK);
  const [isConverting, setIsConverting]   = useState(false);

  // Parameter / shock state
  const [parameters, setParameters] = useState<ParameterConfig[]>(DEFAULT_PARAMETERS);
  const [shocks, setShocks]         = useState<ShockConfig[]>(DEFAULT_SHOCKS);

  // LaTeX state
  const [latex, setLatex]               = useState<string[]>([]);
  const [isLatexLoading, setLatexLoad]  = useState(false);
  const latexDebounce                   = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Results state
  const [isSimulating, setIsSimulating] = useState(false);
  const [irf, setIRF]                   = useState<IRFDataPoint[]>([]);
  const [variables, setVariables]       = useState<string[]>([]);
  const [hasResults, setHasResults]     = useState(false);

  // Error state
  const [error, setError] = useState<string | null>(null);

  // ── LaTeX fetch ─────────────────────────────────────────────────────────────

  const fetchLatex = useCallback(async (text: string) => {
    const laws = parseLaws(text);
    if (laws.length === 0) { setLatex([]); return; }
    setLatexLoad(true);
    try {
      const res = await fetch(`${API_BASE}/dsge2latex`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ laws }),
      });
      if (!res.ok) return;
      const body: { latex: string[] } = await res.json();
      setLatex(body.latex);
    } catch {
      // silently ignore — LaTeX preview is non-critical
    } finally {
      setLatexLoad(false);
    }
  }, []);

  // Debounce LaTeX re-render on every ShockTalk edit (500 ms)
  useEffect(() => {
    if (latexDebounce.current) clearTimeout(latexDebounce.current);
    latexDebounce.current = setTimeout(() => fetchLatex(shocktalkText), 500);
    return () => { if (latexDebounce.current) clearTimeout(latexDebounce.current); };
  }, [shocktalkText, fetchLatex]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleParameterChange = useCallback((name: string, value: number) => {
    setParameters((prev) => prev.map((p) => (p.name === name ? { ...p, value } : p)));
  }, []);

  const handleShockChange = useCallback((name: string, value: number) => {
    setShocks((prev) => prev.map((s) => (s.name === name ? { ...s, value } : s)));
  }, []);

  const handleConvert = useCallback(async () => {
    if (!nlText.trim()) return;
    setIsConverting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/talk2dsge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: nlText }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }
      const body: { equations: string[]; parameters: Record<string, number> } = await res.json();

      // Populate ShockTalk editor
      const equationText = body.equations.join('\n');
      setShockTalkText(equationText);
      setActiveTab('shocktalk');
      fetchLatex(equationText);

      // Rebuild parameter sliders from returned defaults
      setParameters(
        Object.entries(body.parameters).map(([name, value]) =>
          buildParameterConfig(name, value)
        )
      );

      // Infer shock inputs from the equations
      const shockNames = extractShockNames(body.equations);
      setShocks(shockNames.map((name) => ({ name, value: 0.01 })));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Conversion failed.');
    } finally {
      setIsConverting(false);
    }
  }, [nlText]);

  const handleSimulate = useCallback(async () => {
    const laws = parseLaws(shocktalkText);
    if (laws.length === 0) return;
    setIsSimulating(true);
    setError(null);
    try {
      const parametersDict = Object.fromEntries(
        parameters.map((p) => [p.name, p.value])
      );
      const shocksDict = Object.fromEntries(
        shocks.map((s) => [s.name, s.value])
      );

      const res = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          laws,
          parameters: parametersDict,
          shocks: shocksDict,
          T: 40,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }
      const body: { data: Record<string, number[]> } = await res.json();
      const { points, variables: vars } = responseToIRF(body.data);
      setIRF(points);
      setVariables(vars);
      setHasResults(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed.');
    } finally {
      setIsSimulating(false);
    }
  }, [shocktalkText, parameters, shocks]);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      <Header />
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">
        {/* Left — model builder */}
        <div className="overflow-y-auto border-b lg:border-b-0 lg:border-r border-gray-200 px-6 py-7">
          <InputPanel
            activeTab={activeTab}
            onTabChange={setActiveTab}
            nlText={nlText}
            onNLChange={setNLText}
            shocktalkText={shocktalkText}
            onShockTalkChange={setShockTalkText}
            onConvert={handleConvert}
            isConverting={isConverting}
            parameters={parameters}
            shocks={shocks}
            onParameterChange={handleParameterChange}
            onShockChange={handleShockChange}
            onSimulate={handleSimulate}
            isSimulating={isSimulating}
            error={error}
            onDismissError={() => setError(null)}
          />
        </div>

        {/* Right — results */}
        <div className="overflow-y-auto bg-gray-50 px-6 py-7">
          <ResultsPanel
            latex={latex}
            isLatexLoading={isLatexLoading}
            hasResults={hasResults}
            irf={irf}
            variables={variables}
          />
        </div>
      </main>
    </div>
  );
}
