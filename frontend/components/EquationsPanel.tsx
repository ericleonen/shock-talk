'use client';

import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface EquationsPanelProps {
  latex: string[];
  isLoading: boolean;
}

function renderLatex(src: string): string {
  try {
    return katex.renderToString(src, { displayMode: true, throwOnError: false });
  } catch {
    return `<span class="text-red-500 text-xs font-mono">${src}</span>`;
  }
}

export default function EquationsPanel({ latex, isLoading }: EquationsPanelProps) {
  const rendered = useMemo(() => latex.map(renderLatex), [latex]);

  const showSkeleton = isLoading && latex.length === 0;

  if (!isLoading && latex.length === 0) return null;

  return (
    <div className="rounded-md border border-gray-200 bg-white p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900">Model Equations</h3>
        {isLoading && (
          <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-gray-500" />
            Rendering…
          </span>
        )}
      </div>

      {showSkeleton ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 rounded bg-gray-100 animate-pulse" style={{ width: `${60 + i * 10}%` }} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-gray-100">
          {rendered.map((html, i) => (
            <div
              key={i}
              className="py-2 overflow-x-auto [&_.katex-display]:my-0"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
