-- IronFlow Initial Database Schema
-- Uses JSONB for flexible state management and offline-first architecture

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_level VARCHAR(20) NOT NULL CHECK (experience_level IN ('beginner', 'intermediate', 'advanced')),
    available_equipment JSONB NOT NULL DEFAULT '[]',
    injury_history JSONB NOT NULL DEFAULT '[]',
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- JSONB for flexible preference storage
    CONSTRAINT valid_preferences CHECK (
        jsonb_typeof(preferences) = 'object'
    )
);

-- Exercise definitions table
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL UNIQUE,
    primary_muscles JSONB NOT NULL,
    secondary_muscles JSONB NOT NULL DEFAULT '[]',
    movement_pattern VARCHAR(50) NOT NULL,
    equipment VARCHAR(50) NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 10),
    fatigue_index INTEGER NOT NULL CHECK (fatigue_index BETWEEN 1 AND 10),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Indexes for fast muscle group queries
    CONSTRAINT valid_muscles CHECK (
        jsonb_typeof(primary_muscles) = 'array' AND
        jsonb_typeof(secondary_muscles) = 'array'
    )
);

-- Create GIN indexes for JSONB columns
CREATE INDEX idx_exercises_primary_muscles ON exercises USING GIN (primary_muscles);
CREATE INDEX idx_exercises_secondary_muscles ON exercises USING GIN (secondary_muscles);
CREATE INDEX idx_exercises_equipment ON exercises (equipment);
CREATE INDEX idx_exercises_movement_pattern ON exercises (movement_pattern);

-- Workouts table with JSONB state
CREATE TABLE workouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    workout_date DATE NOT NULL,
    exercises JSONB NOT NULL DEFAULT '[]',
    duration INTEGER, -- minutes
    notes TEXT,
    state JSONB NOT NULL DEFAULT '{"completed": false, "syncStatus": "pending"}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Version for optimistic locking in offline sync
    version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT valid_exercises CHECK (jsonb_typeof(exercises) = 'array'),
    CONSTRAINT valid_state CHECK (jsonb_typeof(state) = 'object')
);

CREATE INDEX idx_workouts_user_id ON workouts (user_id);
CREATE INDEX idx_workouts_date ON workouts (workout_date);
CREATE INDEX idx_workouts_sync_status ON workouts ((state->>'syncStatus'));
CREATE INDEX idx_workouts_user_date ON workouts (user_id, workout_date DESC);

-- Volume tracking table
CREATE TABLE volume_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    muscle_group VARCHAR(50) NOT NULL,
    target_sets INTEGER NOT NULL,
    completed_sets INTEGER NOT NULL DEFAULT 0,
    previous_week_sets INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, week_start, muscle_group)
);

CREATE INDEX idx_volume_user_week ON volume_tracking (user_id, week_start);

-- Progression state table
CREATE TABLE progression_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    current_weight DECIMAL(10, 2) NOT NULL,
    current_reps INTEGER NOT NULL,
    target_reps INTEGER NOT NULL,
    sessions_at_current_load INTEGER NOT NULL DEFAULT 0,
    ready_to_progress BOOLEAN NOT NULL DEFAULT false,
    last_progression_date DATE,
    progression_history JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, exercise_id),
    CONSTRAINT valid_progression_history CHECK (jsonb_typeof(progression_history) = 'array')
);

CREATE INDEX idx_progression_user ON progression_state (user_id);
CREATE INDEX idx_progression_ready ON progression_state (user_id, ready_to_progress);

-- Recovery data table
CREATE TABLE recovery_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    sleep_hours DECIMAL(4, 2) NOT NULL,
    sleep_quality INTEGER NOT NULL CHECK (sleep_quality BETWEEN 1 AND 10),
    resting_heart_rate INTEGER,
    hrv INTEGER,
    soreness JSONB NOT NULL DEFAULT '{}',
    stress_level INTEGER NOT NULL CHECK (stress_level BETWEEN 1 AND 10),
    activity_level INTEGER NOT NULL CHECK (activity_level BETWEEN 1 AND 10),
    recovery_score JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date),
    CONSTRAINT valid_soreness CHECK (jsonb_typeof(soreness) = 'object'),
    CONSTRAINT valid_recovery_score CHECK (
        recovery_score IS NULL OR jsonb_typeof(recovery_score) = 'object'
    )
);

CREATE INDEX idx_recovery_user_date ON recovery_data (user_id, date DESC);

-- Sync queue for offline-first architecture
CREATE TABLE sync_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('workout', 'user_profile', 'progress', 'recovery')),
    entity_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('create', 'update', 'delete')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('synced', 'pending', 'conflict', 'error')),
    conflict_data JSONB,
    error_message TEXT,
    last_attempt TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_data CHECK (jsonb_typeof(data) = 'object')
);

CREATE INDEX idx_sync_status ON sync_queue (status, timestamp);
CREATE INDEX idx_sync_entity ON sync_queue (entity_type, entity_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workouts_updated_at BEFORE UPDATE ON workouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_volume_tracking_updated_at BEFORE UPDATE ON volume_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_progression_state_updated_at BEFORE UPDATE ON progression_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to increment version on workout updates (for optimistic locking)
CREATE OR REPLACE FUNCTION increment_workout_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_workout_version BEFORE UPDATE ON workouts
    FOR EACH ROW EXECUTE FUNCTION increment_workout_version();

-- Sample exercise data
INSERT INTO exercises (name, primary_muscles, secondary_muscles, movement_pattern, equipment, difficulty, fatigue_index) VALUES
-- Chest
('Barbell Bench Press', '["chest"]', '["shoulders", "triceps"]', 'horizontal_push', 'barbell', 7, 8),
('Dumbbell Bench Press', '["chest"]', '["shoulders", "triceps"]', 'horizontal_push', 'dumbbell', 6, 7),
('Incline Dumbbell Press', '["chest"]', '["shoulders", "triceps"]', 'horizontal_push', 'dumbbell', 6, 7),
('Cable Fly', '["chest"]', '[]', 'isolation', 'cable', 4, 3),
('Push-ups', '["chest"]', '["shoulders", "triceps"]', 'horizontal_push', 'bodyweight', 3, 4),

-- Back
('Barbell Deadlift', '["back", "glutes", "hamstrings"]', '["forearms"]', 'hinge', 'barbell', 9, 10),
('Pull-ups', '["back"]', '["biceps"]', 'vertical_pull', 'bodyweight', 7, 6),
('Barbell Row', '["back"]', '["biceps", "forearms"]', 'horizontal_pull', 'barbell', 7, 7),
('Lat Pulldown', '["back"]', '["biceps"]', 'vertical_pull', 'machine', 5, 5),
('Cable Row', '["back"]', '["biceps"]', 'horizontal_pull', 'cable', 5, 5),

-- Shoulders
('Overhead Press', '["shoulders"]', '["triceps"]', 'vertical_push', 'barbell', 7, 7),
('Dumbbell Shoulder Press', '["shoulders"]', '["triceps"]', 'vertical_push', 'dumbbell', 6, 6),
('Lateral Raise', '["shoulders"]', '[]', 'isolation', 'dumbbell', 4, 3),
('Face Pull', '["shoulders"]', '["back"]', 'horizontal_pull', 'cable', 4, 3),

-- Arms
('Barbell Curl', '["biceps"]', '["forearms"]', 'isolation', 'barbell', 4, 3),
('Hammer Curl', '["biceps", "forearms"]', '[]', 'isolation', 'dumbbell', 4, 3),
('Tricep Dips', '["triceps"]', '["chest", "shoulders"]', 'vertical_push', 'bodyweight', 6, 5),
('Cable Tricep Extension', '["triceps"]', '[]', 'isolation', 'cable', 4, 3),

-- Legs
('Barbell Squat', '["quads", "glutes"]', '["hamstrings"]', 'squat', 'barbell', 8, 9),
('Romanian Deadlift', '["hamstrings", "glutes"]', '["back"]', 'hinge', 'barbell', 7, 7),
('Bulgarian Split Squat', '["quads", "glutes"]', '[]', 'lunge', 'dumbbell', 6, 6),
('Leg Press', '["quads", "glutes"]', '[]', 'squat', 'machine', 5, 6),
('Leg Curl', '["hamstrings"]', '[]', 'isolation', 'machine', 4, 3),
('Calf Raise', '["calves"]', '[]', 'isolation', 'machine', 3, 3);

-- Create view for workout history with computed metrics
CREATE OR REPLACE VIEW workout_summary AS
SELECT
    w.id,
    w.user_id,
    w.workout_date,
    w.duration,
    jsonb_array_length(w.exercises) as exercise_count,
    (w.state->>'completed')::boolean as completed,
    w.state->>'syncStatus' as sync_status,
    w.version,
    w.created_at
FROM workouts w;

-- Comments for documentation
COMMENT ON TABLE user_profiles IS 'User profile data with flexible JSONB preferences';
COMMENT ON TABLE exercises IS 'Exercise library with muscle targeting and difficulty metrics';
COMMENT ON TABLE workouts IS 'Workout sessions with JSONB exercise data for flexible schema';
COMMENT ON TABLE volume_tracking IS 'Weekly volume targets and actuals per muscle group';
COMMENT ON TABLE progression_state IS 'Double progression tracking per exercise';
COMMENT ON TABLE recovery_data IS 'Daily recovery metrics for readiness assessment';
COMMENT ON TABLE sync_queue IS 'Offline-first sync queue with conflict detection';
COMMENT ON COLUMN workouts.version IS 'Optimistic locking version for conflict resolution';
