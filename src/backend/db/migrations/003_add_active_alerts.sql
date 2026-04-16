-- Migration 003: Active alerts table for Week 7 notification-ready intelligence
-- Stores triggered alerts from intelligence signals (patterns, risk thresholds)
-- that have been routed but not yet acknowledged or dismissed.

ALTER TABLE recommendations
    ADD COLUMN IF NOT EXISTS alert_source VARCHAR(50) DEFAULT NULL,  -- 'pattern', 'risk', 'brief'
    ADD COLUMN IF NOT EXISTS alert_severity VARCHAR(20) DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    ADD COLUMN IF NOT EXISTS triggered_by_event_ids JSONB DEFAULT '[]';

COMMENT ON COLUMN recommendations.alert_source IS 'Which intelligence system generated this alert';
COMMENT ON COLUMN recommendations.alert_severity IS 'Alert severity: low < medium < high < critical';
COMMENT ON COLUMN recommendations.triggered_by_event_ids IS 'Event IDs that caused this alert to fire';

-- Index for fetching unacknowledged alerts for a patient
CREATE INDEX IF NOT EXISTS idx_recommendations_active_alerts
    ON recommendations(patient_id, is_dismissed, is_acknowledged, alert_severity, created_at DESC)
    WHERE is_dismissed = FALSE
      AND is_acknowledged = FALSE
      AND alert_severity IS NOT NULL;
