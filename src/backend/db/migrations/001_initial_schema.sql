-- Pippen Database Schema
-- Phase 1, Week 1: Foundation Data Layer
-- PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Patients table
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    gsd1a_diagnosis_date DATE,
    care_protocol JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Caregivers (emergency contacts with escalation order)
CREATE TABLE caregivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    relationship VARCHAR(100) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    telegram_id VARCHAR(100),
    escalation_order INTEGER NOT NULL DEFAULT 1,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    notify_warning BOOLEAN NOT NULL DEFAULT TRUE,
    notify_alarm BOOLEAN NOT NULL DEFAULT TRUE,
    notify_escalation BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_caregivers_patient_id ON caregivers(patient_id);
CREATE INDEX idx_caregivers_escalation ON caregivers(patient_id, escalation_order);

-- Care team members (clinical staff)
CREATE TABLE care_team_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    specialty VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    is_on_call BOOLEAN NOT NULL DEFAULT FALSE,
    notify_updates BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_care_team_patient_id ON care_team_members(patient_id);

-- ============================================================
-- EVENT-SOURCED CORE (Immutable)
-- ============================================================

-- Events table - APPEND ONLY, never UPDATE or DELETE
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'manual', 'sensor', 'api', 'system'
    source_id VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Immutable: no updated_at column
    -- Links to amending event if this is superseded
    amended_by UUID REFERENCES events(id),
    amends UUID REFERENCES events(id),
    
    -- Note: Immutability enforced by application layer (no UPDATE/DELETE on events table)
    -- The amended_by and amends columns support the amendment workflow
);

CREATE INDEX idx_events_patient_id ON events(patient_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_occurred_at ON events(occurred_at);
CREATE INDEX idx_events_patient_time ON events(patient_id, occurred_at DESC);
CREATE INDEX idx_events_source ON events(source_type, source_id);

-- Event type enum values for reference:
-- glucose_reading, cornstarch_dose, meal, symptom, coverage_course_start,
-- coverage_course_end, alarm_triggered, alarm_acknowledged, alarm_escalated,
-- notification_sent, pattern_detected, baseline_updated

-- ============================================================
-- COVERAGE COURSES (Critical for GSD1A timing)
-- ============================================================

CREATE TABLE coverage_courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    trigger_event_id UUID REFERENCES events(id),
    trigger_type VARCHAR(100) NOT NULL,  -- 'cornstarch', 'meal', 'manual', 'sensor'
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expected_end_at TIMESTAMPTZ NOT NULL,
    actual_end_at TIMESTAMPTZ,
    
    -- For course chaining
    previous_course_id UUID REFERENCES coverage_courses(id),
    next_course_id UUID REFERENCES coverage_courses(id),
    
    -- Course metadata
    duration_minutes INTEGER NOT NULL,
    is_bedtime_dose BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    
    -- Computed fields
    gap_minutes INTEGER,  -- Gap from previous course
    overlap_minutes INTEGER,  -- Overlap with previous course
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_courses_patient_id ON coverage_courses(patient_id);
CREATE INDEX idx_courses_status ON coverage_courses(status);
CREATE INDEX idx_courses_active ON coverage_courses(patient_id, status) WHERE status = 'active';
CREATE INDEX idx_courses_time ON coverage_courses(patient_id, started_at DESC);

-- ============================================================
-- PATIENT LEARNING LAYER
-- ============================================================

-- Learned patterns
CREATE TABLE patient_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_key VARCHAR(255) NOT NULL,
    pattern_value JSONB NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    sample_count INTEGER NOT NULL DEFAULT 0,
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(patient_id, pattern_type, pattern_key)
);

CREATE INDEX idx_patterns_patient_id ON patient_patterns(patient_id);
CREATE INDEX idx_patterns_type ON patient_patterns(pattern_type);

-- Computed baselines (normal values)
CREATE TABLE patient_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL,  -- 'glucose', 'dose_timing', 'coverage_duration'
    metric_value JSONB NOT NULL,  -- {"mean": 120, "std": 15, "p25": 105, "p75": 135}
    computed_from_events JSONB NOT NULL DEFAULT '[]',  -- Event IDs used
    sample_count INTEGER NOT NULL DEFAULT 0,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    
    UNIQUE(patient_id, metric_type)
);

CREATE INDEX idx_baselines_patient_id ON patient_baselines(patient_id);

-- ============================================================
-- RESEARCH LAYER
-- ============================================================

-- Tracked research sources
CREATE TABLE research_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50) NOT NULL,  -- 'pubmed', 'clinicaltrials', 'web', 'community'
    source_url VARCHAR(1000) NOT NULL UNIQUE,
    source_name VARCHAR(255) NOT NULL,
    trust_tier INTEGER NOT NULL DEFAULT 3,  -- 1=highest (peer-reviewed), 4=lowest
    last_fetched_at TIMESTAMPTZ,
    last_etag VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_type ON research_sources(source_type);
CREATE INDEX idx_sources_active ON research_sources(is_active) WHERE is_active = TRUE;

-- Extracted claims from research
CREATE TABLE research_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES research_sources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    claim_summary TEXT,
    topic_tags TEXT[] DEFAULT '{}',
    relevance_score FLOAT,
    patient_relevance JSONB DEFAULT '{}',  -- Which patients this applies to
    embedding_id VARCHAR(255),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by VARCHAR(255),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claims_source ON research_claims(source_id);
CREATE INDEX idx_claims_tags ON research_claims USING GIN(topic_tags);
CREATE INDEX idx_claims_relevance ON research_claims(relevance_score DESC);

-- Clinical trials being tracked
CREATE TABLE tracked_trials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id VARCHAR(255) NOT NULL UNIQUE,  -- NCT number
    source_url VARCHAR(1000) NOT NULL,
    trial_name VARCHAR(500),
    phase VARCHAR(50),
    status VARCHAR(100),
    recruiting BOOLEAN,
    locations TEXT[],
    conditions TEXT[],
    interventions TEXT[],
    contact_info JSONB DEFAULT '{}',
    last_checked_at TIMESTAMPTZ,
    last_status_change TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trials_status ON tracked_trials(status) WHERE recruiting = TRUE;
CREATE INDEX idx_trials_nct ON tracked_trials(trial_id);

-- ============================================================
-- INTELLIGENCE & RECOMMENDATIONS
-- ============================================================

-- Generated recommendations
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    recommendation_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',  -- 'low', 'medium', 'high', 'urgent'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    rationale TEXT,
    action_url VARCHAR(500),
    confidence FLOAT NOT NULL DEFAULT 0.0,
    based_on_events JSONB DEFAULT '[]',
    is_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendations_patient ON recommendations(patient_id);
CREATE INDEX idx_recommendations_active ON recommendations(patient_id, is_dismissed, is_acknowledged) 
    WHERE is_dismissed = FALSE AND is_acknowledged = FALSE;
CREATE INDEX idx_recommendations_priority ON recommendations(priority, created_at DESC);

-- Active hypotheses / open questions
CREATE TABLE open_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    question_type VARCHAR(100) NOT NULL,  -- 'pattern', 'anomaly', 'research'
    question_text TEXT NOT NULL,
    hypothesis TEXT,
    relevant_events JSONB DEFAULT '[]',
    relevance_score FLOAT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- 'active', 'investigating', 'resolved', 'dismissed'
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_questions_patient ON open_questions(patient_id);
CREATE INDEX idx_questions_status ON open_questions(status) WHERE status = 'active';

-- ============================================================
-- DAILY BRIEFS & NOTIFICATIONS
-- ============================================================

-- Daily intelligence snapshots
CREATE TABLE daily_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    brief_date DATE NOT NULL,
    summary TEXT,
    key_insights JSONB DEFAULT '[]',
    risk_alerts JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    coverage_summary JSONB DEFAULT '{}',  -- {"courses_completed": 5, "gaps": 2, "average_gap_minutes": 45}
    research_highlights JSONB DEFAULT '[]',
    generated_by VARCHAR(100) NOT NULL DEFAULT 'system',
    confidence FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(patient_id, brief_date)
);

CREATE INDEX idx_briefs_patient_date ON daily_briefs(patient_id, brief_date DESC);

-- Notification log
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    notification_type VARCHAR(100) NOT NULL,  -- 'warning', 'alarm', 'escalation', 'info'
    channel VARCHAR(50) NOT NULL,  -- 'telegram', 'push', 'sms', 'email'
    recipient_id UUID,  -- caregiver_id or device_token
    recipient_address VARCHAR(255),  -- phone, email, telegram_id
    message_text TEXT NOT NULL,
    message_payload JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'sent', 'delivered', 'failed'
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_patient ON notification_log(patient_id);
CREATE INDEX idx_notifications_type ON notification_log(notification_type);
CREATE INDEX idx_notifications_status ON notification_log(status);
CREATE INDEX idx_notifications_time ON notification_log(created_at DESC);

-- ============================================================
-- NIGHT ALARM STATE MACHINE
-- ============================================================

CREATE TABLE night_alarm_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES coverage_courses(id),
    
    -- State machine status
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- 'active', 'warning_sent', 'expired', 'alarmed', 'escalated', 'resolved', 'superseded'
    
    -- Timing
    course_expected_end TIMESTAMPTZ NOT NULL,
    warning_sent_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    alarmed_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    
    -- Who received what
    warning_recipients JSONB DEFAULT '[]',
    alarm_recipients JSONB DEFAULT '[]',
    escalation_recipients JSONB DEFAULT '[]',
    
    -- Context
    last_patient_event_id UUID REFERENCES events(id),
    last_acknowledged_by UUID REFERENCES caregivers(id),
    last_acknowledged_at TIMESTAMPTZ,
    
    -- Resolution
    resolution VARCHAR(100),  -- 'patient_logged', 'caregiver_checked', 'false_alarm', 'timeout'
    resolution_notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alarm_state_patient ON night_alarm_state(patient_id);
CREATE INDEX idx_alarm_state_status ON night_alarm_state(status);
CREATE INDEX idx_alarm_state_active ON night_alarm_state(patient_id, status) 
    WHERE status IN ('active', 'warning_sent', 'expired', 'alarmed');
CREATE INDEX idx_alarm_state_course ON night_alarm_state(course_id);

-- ============================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_caregivers_updated_at
    BEFORE UPDATE ON caregivers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_care_team_updated_at
    BEFORE UPDATE ON care_team_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recommendations_updated_at
    BEFORE UPDATE ON recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_questions_updated_at
    BEFORE UPDATE ON open_questions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alarm_state_updated_at
    BEFORE UPDATE ON night_alarm_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();