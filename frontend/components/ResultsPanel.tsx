import EquationsPanel from './EquationsPanel';
import ModelSummary from './ModelSummary';
import IRFChart, { IRFDataPoint } from './IRFChart';

interface ResultsPanelProps {
  latex: string[];
  isLatexLoading: boolean;
  hasResults: boolean;
  irf: IRFDataPoint[];
  variables: string[];
}

export default function ResultsPanel({
  latex,
  isLatexLoading,
  hasResults,
  irf,
  variables,
}: ResultsPanelProps) {
  return (
    <div className="flex flex-col gap-6">
      <EquationsPanel latex={latex} isLoading={isLatexLoading} />
      <ModelSummary hasResults={hasResults} />
      {hasResults && <IRFChart data={irf} variables={variables} />}
    </div>
  );
}
