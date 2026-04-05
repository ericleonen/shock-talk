'use client';

export interface ParameterConfig {
  name: string;
  value: number;
  min: number;
  max: number;
  step: number;
  label: string;
}

export interface ShockConfig {
  name: string;
  value: number;
}

interface ParameterConsoleProps {
  parameters: ParameterConfig[];
  shocks: ShockConfig[];
  onParameterChange: (name: string, value: number) => void;
  onShockChange: (name: string, value: number) => void;
}

function SliderRow({
  name,
  label,
  value,
  min,
  max,
  step,
  onChange,
  displayValue,
}: {
  name: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  displayValue?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-sm font-mono font-medium text-gray-800">{name}</span>
          <span className="text-xs text-gray-500 leading-tight">{label}</span>
        </div>
        <span className="text-sm font-mono text-green-700 tabular-nums shrink-0">
          {displayValue ?? value.toFixed(3)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
    </div>
  );
}

export default function ParameterConsole({
  parameters,
  shocks,
  onParameterChange,
  onShockChange,
}: ParameterConsoleProps) {
  const isEmpty = parameters.length === 0 && shocks.length === 0;

  if (isEmpty) {
    return (
      <div className="flex flex-col gap-1 rounded-md border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-500">No model loaded</p>
        <p className="text-xs text-gray-400">
          Define a model above to configure parameters and shocks.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Parameters */}
      {parameters.length > 0 && (
        <div className="flex flex-col gap-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
            Parameters
          </h3>
          <div className="flex flex-col gap-5">
            {parameters.map((p) => (
              <SliderRow
                key={p.name}
                name={p.name}
                label={p.label}
                value={p.value}
                min={p.min}
                max={p.max}
                step={p.step}
                onChange={(v) => onParameterChange(p.name, v)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Shocks */}
      {shocks.length > 0 && (
        <div className="flex flex-col gap-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
            Shock Sizes
          </h3>
          <div className="flex flex-col gap-5">
            {shocks.map((s) => (
              <SliderRow
                key={s.name}
                name={s.name}
                label={`White-noise impulse for ${s.name.replace('e_', 'eps_')} process`}
                value={s.value}
                min={-0.1}
                max={0.1}
                step={0.001}
                onChange={(v) => onShockChange(s.name, v)}
                displayValue={s.value >= 0 ? `+${s.value.toFixed(3)}` : s.value.toFixed(3)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
