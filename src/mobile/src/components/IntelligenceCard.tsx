import React from 'react';
import { Card, CardContent } from './Card';
import { BrainIcon, AlertTriangleIcon, CheckCircleIcon, InfoIcon } from './Icons';
import type { RiskScore, DailyBrief, BaselineMetric } from '../types';

interface IntelligenceCardProps {
  risk: RiskScore | null;
  brief: DailyBrief | null;
  baselines: BaselineMetric[];
  patterns: Array<{ pattern_type: string; severity: number; confidence: number; reason: string }>;
  isLoading: boolean;
  hasSufficientData: boolean;
  isDegraded: boolean;
  isConfigured: boolean;
  onRefresh: () => void;
}

function RiskBadge({ level }: { level: string }) {
  const config: Record<string, { label: string; color: string; bg: string; text: string }> = {
    low: { label: 'Low Risk', color: '#16A34A', bg: '#DCFCE7', text: '#15803D' },
    medium: { label: 'Medium Risk', color: '#D97706', bg: '#FEF3C7', text: '#B45309' },
    high: { label: 'High Risk', color: '#DC2626', bg: '#FEE2E2', text: '#B91C1C' },
    critical: { label: 'Critical', color: '#7C3AED', bg: '#EDE9FE', text: '#6D28D9' },
  };
  const c = config[level] ?? config.low;

  return (
    <span
      className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {level === 'critical' || level === 'high' ? (
        <AlertTriangleIcon size={12} />
      ) : (
        <CheckCircleIcon size={12} />
      )}
      {c.label}
    </span>
  );
}

export const IntelligenceCard: React.FC<IntelligenceCardProps> = ({
  risk,
  brief,
  baselines,
  patterns,
  isLoading,
  hasSufficientData,
  isDegraded,
  isConfigured,
  onRefresh,
}) => {
  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5E7EB]" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-[#E5E7EB] rounded w-1/2" />
              <div className="h-3 bg-[#E5E7EB] rounded w-2/3" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Not configured: VITE_PATIENT_ID is not set — surface clearly, do not fabricate data
  if (!isConfigured) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#FEF3C7] flex items-center justify-center flex-shrink-0">
              <AlertTriangleIcon size={20} color="#D97706" />
            </div>
            <div>
              <p className="font-semibold text-[#1A1D21]">Intelligence Not Configured</p>
              <p className="text-sm text-[#8A8E97] mt-1">
                Set <code className="bg-[#F6F7F9] px-1 rounded text-xs">VITE_PATIENT_ID</code> in your <code className="bg-[#F6F7F9] px-1 rounded text-xs">.env</code> file to enable overnight intelligence. See the mobile README for setup instructions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!hasSufficientData) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F6F7F9] flex items-center justify-center flex-shrink-0">
              <InfoIcon size={20} color="#8A8E97" />
            </div>
            <div>
              <p className="font-semibold text-[#1A1D21]">Intelligence Building</p>
              <p className="text-sm text-[#8A8E97] mt-1">
                Not enough data yet. Keep logging — intelligence grows after a few days of entries.
              </p>
            </div>
          </div>
          <button
            onClick={onRefresh}
            className="mt-3 text-sm text-[#315BFF] font-medium"
          >
            Refresh
          </button>
        </CardContent>
      </Card>
    );
  }

  // We have data — show risk + brief summary
  const riskScore = risk?.risk_score ?? 0;
  const riskLevel = risk?.risk_level ?? 'low';

  // Build a short status line from baselines
  const avgGlucose = baselines.find(m => m.metric_type === 'overnight_average_glucose');
  const gapFreq = baselines.find(m => m.metric_type === 'coverage_gap_frequency');

  return (
    <Card variant="outlined">
      <CardContent>
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#F6F7F9] flex items-center justify-center flex-shrink-0">
            <BrainIcon size={20} color="#315BFF" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="font-semibold text-[#1A1D21]">Overnight Intelligence</p>
              {risk && <RiskBadge level={riskLevel} />}
              {isDegraded && (
                <span
                  title="Some intelligence data could not be loaded"
                  className="inline-flex items-center gap-0.5 text-xs text-[#D97706]"
                >
                  <AlertTriangleIcon size={12} /> partial
                </span>
              )}
            </div>
            {risk && (
              <p className="text-xs text-[#8A8E97] mt-0.5">
                Score {riskScore.toFixed(1)} · confidence {Math.round(risk.confidence * 100)}%
              </p>
            )}
          </div>
        </div>

        {isDegraded && (
          <div className="mb-3 p-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl flex items-start gap-2">
            <AlertTriangleIcon size={16} color="#D97706" className="flex-shrink-0 mt-0.5" />
            <p className="text-xs text-[#92400E]">
              <span className="font-semibold">Partial data — </span>
              Some intelligence endpoints failed to load. Results below may be incomplete.
            </p>
          </div>
        )}

        {brief && (
          <div className="mb-3 p-3 bg-[#F6F7F9] rounded-xl">
            <p className="text-sm font-medium text-[#1A1D21] mb-1">{brief.summary}</p>
            {brief.what_matters.length > 0 && (
              <p className="text-xs text-[#8A8E97] mt-2">
                <span className="font-medium">Matters: </span>
                {brief.what_matters[0]}
              </p>
            )}
            {brief.recommended_attention.length > 0 && (
              <p className="text-xs text-[#8A8E97] mt-1">
                <span className="font-medium">Tonight: </span>
                {brief.recommended_attention[0]}
              </p>
            )}
          </div>
        )}

        {avgGlucose && avgGlucose.value !== null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#8A8E97]">Avg overnight glucose</span>
            <span className="font-medium text-[#1A1D21]">{avgGlucose.value} mg/dL</span>
          </div>
        )}

        {gapFreq && gapFreq.value !== null && (
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-[#8A8E97]">Coverage gap frequency</span>
            <span className="font-medium text-[#1A1D21]">{Math.round(gapFreq.value * 100)}%</span>
          </div>
        )}

        {patterns.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-2">
              Detected Patterns
            </p>
            {patterns.slice(0, 3).map((p, i) => (
              <p key={i} className="text-xs text-[#8A8E97] mt-1">
                · {p.reason.length > 80 ? p.reason.slice(0, 80) + '…' : p.reason}
              </p>
            ))}
          </div>
        )}

        {risk && risk.factors.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-2">
              Active Factors
            </p>
            {risk.factors.slice(0, 2).map((f, i) => (
              <p key={i} className="text-xs text-[#8A8E97] mt-1">
                · {f.reason.length > 80 ? f.reason.slice(0, 80) + '…' : f.reason}
              </p>
            ))}
          </div>
        )}

        <button
          onClick={onRefresh}
          className="mt-3 text-sm text-[#315BFF] font-medium"
        >
          Refresh intelligence
        </button>
      </CardContent>
    </Card>
  );
};