interface ModelSummaryProps {
  hasResults: boolean;
}

export default function ModelSummary({ hasResults }: ModelSummaryProps) {
  if (!hasResults) {
    return (
      <div className="flex flex-col gap-1 rounded-md border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-500">No results yet</p>
        <p className="text-xs text-gray-400">
          Define a model and hit Simulate to see results here.
        </p>
      </div>
    );
  }

  // Placeholder — will be replaced with LLM-generated summary
  return (
    <div className="rounded-md border border-gray-200 bg-white p-5 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-900">Model Summary</h3>
        <span className="text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
          placeholder
        </span>
      </div>
      <div className="flex flex-col gap-3 text-sm text-gray-600 leading-relaxed">
        <p>
          <span className="font-medium text-gray-800">Model type:</span> Three-equation
          New Keynesian (NK) model with a demand shock and a cost-push shock.
        </p>
        <p>
          <span className="font-medium text-gray-800">Variables:</span>{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">y</code> (output gap),{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">pi</code> (inflation),{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">r</code> (nominal interest rate).
        </p>
        <p>
          <span className="font-medium text-gray-800">Shocks:</span>{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">e_d</code> (demand),{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">e_u</code> (cost-push).
          Both follow AR(1) processes with persistence parameters{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">ρ_d</code> and{' '}
          <code className="font-mono text-xs bg-gray-100 px-1 rounded">ρ_u</code>.
        </p>
        <p>
          <span className="font-medium text-gray-800">Blanchard–Kahn:</span>{' '}
          <span className="text-green-700 font-medium">Satisfied</span> — the model has a
          unique stable rational-expectations equilibrium.
        </p>
      </div>
    </div>
  );
}
