'use client';

export type ActiveTab = 'nl' | 'shocktalk';

interface InputTabsProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  nlText: string;
  onNLChange: (text: string) => void;
  shocktalkText: string;
  onShockTalkChange: (text: string) => void;
  onConvert: () => void;
  isConverting: boolean;
}

const NL_PLACEHOLDER = `Describe your model in plain English. For example:

- Output equals expected future output minus the real interest rate scaled by the inverse of the intertemporal elasticity, plus a demand shock.
- Inflation equals discounted expected future inflation plus the New Keynesian Phillips curve slope times output, plus a cost-push shock.
- The central bank follows a Taylor rule responding to inflation and the output gap.`;

const SHOCKTALK_PLACEHOLDER = `Enter ShockTalk equations directly. For example:

y   = F[y] - (1/sigma)*(r - F[pi]) + eps_d
pi  = beta*F[pi] + kappa*y + eps_u
r   = phi_pi*pi + phi_y*y`;

export default function InputTabs({
  activeTab,
  onTabChange,
  nlText,
  onNLChange,
  shocktalkText,
  onShockTalkChange,
  onConvert,
  isConverting,
}: InputTabsProps) {
  return (
    <div className="flex flex-col">
      {/* Tab bar */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => onTabChange('nl')}
          className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'nl'
              ? 'border-green-600 text-green-700'
              : 'border-transparent text-gray-500 hover:text-gray-800'
          }`}
        >
          Natural Language
        </button>
        <button
          onClick={() => onTabChange('shocktalk')}
          className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'shocktalk'
              ? 'border-green-600 text-green-700'
              : 'border-transparent text-gray-500 hover:text-gray-800'
          }`}
        >
          ShockTalk Syntax
        </button>
      </div>

      {/* NL input */}
      {activeTab === 'nl' && (
        <div className="flex flex-col gap-3 pt-4">
          <textarea
            value={nlText}
            onChange={(e) => onNLChange(e.target.value)}
            placeholder={NL_PLACEHOLDER}
            rows={8}
            className="w-full resize-none rounded-md border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-100 font-sans leading-relaxed"
          />
          <button
            onClick={onConvert}
            disabled={isConverting || nlText.trim().length === 0}
            className="self-end flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isConverting ? (
              <>
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Converting…
              </>
            ) : (
              'Convert to ShockTalk'
            )}
          </button>
        </div>
      )}

      {/* ShockTalk input */}
      {activeTab === 'shocktalk' && (
        <div className="flex flex-col gap-3 pt-4">
          <textarea
            value={shocktalkText}
            onChange={(e) => onShockTalkChange(e.target.value)}
            placeholder={SHOCKTALK_PLACEHOLDER}
            rows={8}
            className="w-full resize-none rounded-md border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-100 font-mono leading-relaxed"
            spellCheck={false}
          />
          <p className="text-xs text-gray-400">
            Write one equation per line in the form{' '}
            <code className="font-mono bg-gray-100 px-1 rounded">variable = expression</code>.
            Shocks are prefixed <code className="font-mono bg-gray-100 px-1 rounded">eps_</code>,
            forward expectations use{' '}
            <code className="font-mono bg-gray-100 px-1 rounded">F[·]</code>.
          </p>
        </div>
      )}
    </div>
  );
}
