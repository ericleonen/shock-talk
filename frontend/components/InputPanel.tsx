'use client';

import InputTabs, { ActiveTab } from './InputTabs';
import ParameterConsole, { ParameterConfig, ShockConfig } from './ParameterConsole';

interface InputPanelProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  nlText: string;
  onNLChange: (text: string) => void;
  shocktalkText: string;
  onShockTalkChange: (text: string) => void;
  onConvert: () => void;
  isConverting: boolean;
  parameters: ParameterConfig[];
  shocks: ShockConfig[];
  onParameterChange: (name: string, value: number) => void;
  onShockChange: (name: string, value: number) => void;
  onSimulate: () => void;
  isSimulating: boolean;
  error: string | null;
  onDismissError: () => void;
}

export default function InputPanel({
  activeTab,
  onTabChange,
  nlText,
  onNLChange,
  shocktalkText,
  onShockTalkChange,
  onConvert,
  isConverting,
  parameters,
  shocks,
  onParameterChange,
  onShockChange,
  onSimulate,
  isSimulating,
  error,
  onDismissError,
}: InputPanelProps) {
  const canSimulate =
    !isSimulating && shocktalkText.trim().length > 0;

  return (
    <div className="flex flex-col gap-8">
      {/* Model input */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-sm font-semibold text-gray-900">Model Definition</h2>
          <p className="text-xs text-gray-500">
            Specify your DSGE model in natural language or directly in ShockTalk syntax.
          </p>
        </div>
        <InputTabs
          activeTab={activeTab}
          onTabChange={onTabChange}
          nlText={nlText}
          onNLChange={onNLChange}
          shocktalkText={shocktalkText}
          onShockTalkChange={onShockTalkChange}
          onConvert={onConvert}
          isConverting={isConverting}
        />
      </section>

      <div className="border-t border-gray-100" />

      {/* Parameter console */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-sm font-semibold text-gray-900">Parameter Console</h2>
          <p className="text-xs text-gray-500">
            Adjust structural parameters and shock sizes before simulating.
          </p>
        </div>
        <ParameterConsole
          parameters={parameters}
          shocks={shocks}
          onParameterChange={onParameterChange}
          onShockChange={onShockChange}
        />
      </section>

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span className="flex-1 leading-snug">{error}</span>
          <button
            onClick={onDismissError}
            className="shrink-0 text-red-400 hover:text-red-600 transition-colors text-base leading-none mt-0.5"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Simulate button */}
      <button
        onClick={onSimulate}
        disabled={!canSimulate}
        className="w-full rounded-md bg-green-600 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isSimulating ? (
          <>
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Simulating…
          </>
        ) : (
          'Simulate'
        )}
      </button>
    </div>
  );
}
