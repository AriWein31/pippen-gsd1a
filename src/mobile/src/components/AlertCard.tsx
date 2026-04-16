/**
 * AlertCard — displays a single active intelligence alert.
 *
 * Shows severity badge, title, description, and acknowledge/dismiss actions.
 * Severity colours:
 *   critical → red
 *   high     → orange
 *   medium   → amber
 *   low      → blue
 */

import type { Alert } from '../types';

interface AlertCardProps {
  alert: Alert;
  onAcknowledge: (alertId: string) => void;
  onDismiss: (alertId: string) => void;
}

const SEVERITY_COLOURS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-300', dot: 'bg-red-500' },
  high:     { bg: 'bg-orange-50', text: 'text-orange-800', border: 'border-orange-300', dot: 'bg-orange-500' },
  medium:   { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300', dot: 'bg-amber-500' },
  low:      { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-300', dot: 'bg-blue-500' },
};

const SOURCE_LABELS: Record<string, string> = {
  pattern: 'Pattern detected',
  risk: 'Risk alert',
  brief: 'Daily brief',
};

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoString;
  }
}

export function AlertCard({ alert, onAcknowledge, onDismiss }: AlertCardProps) {
  const colours = SEVERITY_COLOURS[alert.alert_severity] ?? SEVERITY_COLOURS.low;
  const sourceLabel = SOURCE_LABELS[alert.source] ?? alert.source;

  return (
    <div
      className={`rounded-xl border ${colours.border} ${colours.bg} p-4 flex flex-col gap-2`}
      role="alert"
      aria-label={`${alert.alert_severity} alert: ${alert.title}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${colours.dot} animate-pulse`} />
          <span className={`text-xs font-semibold uppercase tracking-wide ${colours.text}`}>
            {alert.alert_severity}
          </span>
          <span className={`text-xs ${colours.text} opacity-70`}>
            · {sourceLabel}
          </span>
        </div>
        <span className={`text-xs ${colours.text} opacity-60`}>
          {formatTime(alert.created_at)}
        </span>
      </div>

      {/* Title */}
      <p className={`font-semibold text-sm ${colours.text}`}>{alert.title}</p>

      {/* Description */}
      {alert.description && (
        <p className={`text-sm ${colours.text} opacity-80`}>{alert.description}</p>
      )}

      {/* Rationale (explainable threshold logic) */}
      {alert.rationale && (
        <details className="mt-1">
          <summary className={`text-xs cursor-pointer ${colours.text} opacity-60 hover:opacity-80`}>
            Why this alert fired
          </summary>
          <p className={`mt-1 text-xs ${colours.text} opacity-70 pl-2 border-l-2 ${colours.border}`}>
            {alert.rationale}
          </p>
        </details>
      )}

      {/* Confidence */}
      {alert.confidence > 0 && (
        <p className={`text-xs ${colours.text} opacity-60`}>
          Confidence: {Math.round(alert.confidence * 100)}%
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-1">
        <button
          onClick={() => onAcknowledge(alert.id)}
          className={`flex-1 text-xs font-medium py-1.5 px-3 rounded-lg border ${colours.border} ${colours.bg} ${colours.text} hover:opacity-80 transition-opacity`}
        >
          Acknowledge
        </button>
        <button
          onClick={() => onDismiss(alert.id)}
          className={`flex-1 text-xs font-medium py-1.5 px-3 rounded-lg border ${colours.border} ${colours.bg} ${colours.text} hover:opacity-80 transition-opacity`}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
