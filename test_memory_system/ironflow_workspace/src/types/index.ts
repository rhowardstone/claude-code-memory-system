/**
 * Core type definitions for IronFlow workout app
 */

// Muscle groups for exercise targeting
export enum MuscleGroup {
  CHEST = 'chest',
  BACK = 'back',
  SHOULDERS = 'shoulders',
  BICEPS = 'biceps',
  TRICEPS = 'triceps',
  QUADS = 'quads',
  HAMSTRINGS = 'hamstrings',
  GLUTES = 'glutes',
  CALVES = 'calves',
  ABS = 'abs',
  FOREARMS = 'forearms'
}

// Exercise movement patterns
export enum MovementPattern {
  HORIZONTAL_PUSH = 'horizontal_push',
  VERTICAL_PUSH = 'vertical_push',
  HORIZONTAL_PULL = 'horizontal_pull',
  VERTICAL_PULL = 'vertical_pull',
  SQUAT = 'squat',
  HINGE = 'hinge',
  LUNGE = 'lunge',
  ISOLATION = 'isolation'
}

// Equipment types
export enum EquipmentType {
  BARBELL = 'barbell',
  DUMBBELL = 'dumbbell',
  MACHINE = 'machine',
  CABLE = 'cable',
  BODYWEIGHT = 'bodyweight',
  BAND = 'band'
}

// Training experience levels
export enum ExperienceLevel {
  BEGINNER = 'beginner',      // 0-1 years
  INTERMEDIATE = 'intermediate', // 1-3 years
  ADVANCED = 'advanced'        // 3+ years
}

// Exercise definition
export interface Exercise {
  id: string;
  name: string;
  primaryMuscles: MuscleGroup[];
  secondaryMuscles: MuscleGroup[];
  movementPattern: MovementPattern;
  equipment: EquipmentType;
  difficulty: number; // 1-10 scale
  fatigueIndex: number; // 1-10, how taxing the exercise is
}

// Set tracking
export interface WorkoutSet {
  setNumber: number;
  targetReps: number;
  actualReps: number;
  weight: number;
  rpe?: number; // Rate of Perceived Exertion (1-10)
  completed: boolean;
  timestamp?: Date;
}

// Exercise instance in a workout
export interface WorkoutExercise {
  exerciseId: string;
  sets: WorkoutSet[];
  notes?: string;
}

// Complete workout session
export interface Workout {
  id: string;
  userId: string;
  date: Date;
  exercises: WorkoutExercise[];
  duration?: number; // minutes
  notes?: string;
  state: WorkoutState;
}

export interface WorkoutState {
  completed: boolean;
  startTime?: Date;
  endTime?: Date;
  syncStatus: SyncStatus;
}

// Sync queue for offline-first
export enum SyncStatus {
  SYNCED = 'synced',
  PENDING = 'pending',
  CONFLICT = 'conflict',
  ERROR = 'error'
}

export interface SyncQueueItem {
  id: string;
  entityType: 'workout' | 'user_profile' | 'progress';
  entityId: string;
  operation: 'create' | 'update' | 'delete';
  timestamp: Date;
  data: any; // JSONB in postgres
  retryCount: number;
  status: SyncStatus;
  conflictData?: any;
}

// User profile and progress tracking
export interface UserProfile {
  id: string;
  experienceLevel: ExperienceLevel;
  availableEquipment: EquipmentType[];
  injuryHistory: string[];
  preferences: UserPreferences;
  createdAt: Date;
  updatedAt: Date;
}

export interface UserPreferences {
  workoutsPerWeek: number;
  sessionDuration: number; // target minutes
  focusMuscles?: MuscleGroup[];
  avoidExercises?: string[]; // exercise IDs
}

// Volume tracking per muscle group
export interface VolumeTarget {
  muscleGroup: MuscleGroup;
  targetSetsPerWeek: number;
  currentSetsThisWeek: number;
  lastWeekVolume: number;
}

// Progression tracking
export interface ProgressionState {
  exerciseId: string;
  currentWeight: number;
  currentReps: number;
  targetReps: number;
  sessionsAtCurrentLoad: number;
  readyToProgress: boolean;
  lastProgressionDate?: Date;
}

// Recovery tracking
export interface RecoveryData {
  userId: string;
  date: Date;
  sleepHours: number;
  sleepQuality: number; // 1-10 scale
  restingHeartRate?: number;
  hrv?: number; // Heart Rate Variability
  soreness: Map<MuscleGroup, number>; // 1-10 scale
  stressLevel: number; // 1-10 scale
  activityLevel: number; // 1-10 scale (daily activity outside gym)
}

export interface RecoveryScore {
  overall: number; // 0-100
  readiness: 'low' | 'medium' | 'high';
  recommendations: string[];
  muscleReadiness: Map<MuscleGroup, number>; // 0-100 per muscle
}

// Exercise selection criteria
export interface SelectionCriteria {
  requiredMuscles: MuscleGroup[];
  excludeExercises: string[];
  availableEquipment: EquipmentType[];
  currentFatigue: number; // 0-100
  preferredMovementPatterns?: MovementPattern[];
  maxExercises: number;
}

// Plate calculation
export interface PlateCalculation {
  targetWeight: number;
  barWeight: number;
  availablePlates: number[]; // plate weights available
  platesPerSide: Array<{ weight: number; count: number }>;
  totalWeight: number;
  difference: number; // from target
}
