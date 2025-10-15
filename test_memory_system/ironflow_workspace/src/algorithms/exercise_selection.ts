/**
 * Exercise Selection Algorithm
 *
 * Intelligently selects exercises based on:
 * - Muscle coverage requirements
 * - Volume remaining for the week
 * - Recovery/fatigue state
 * - Available equipment
 * - Movement pattern variety
 * - User preferences and history
 *
 * Goals:
 * - Ensure balanced muscle development
 * - Optimize time efficiency (prefer compounds when appropriate)
 * - Prevent overuse injuries through variation
 * - Match intensity to recovery state
 */

import {
  Exercise,
  MuscleGroup,
  MovementPattern,
  EquipmentType,
  SelectionCriteria,
  VolumeTarget,
  RecoveryScore
} from '../types';
import { identifyVolumePriorities } from './volume_targets';

/**
 * Exercise selection result
 */
export interface ExerciseSelection {
  exercises: Exercise[];
  musclesCovered: Map<MuscleGroup, number>; // Sets allocated per muscle
  reasoning: string[];
  estimatedDuration: number; // minutes
}

/**
 * Weights for exercise scoring
 */
const SCORING_WEIGHTS = {
  volumeNeed: 0.3,        // How much this exercise addresses volume gaps
  recovery: 0.25,         // Match to current recovery state
  efficiency: 0.2,        // Compound vs isolation
  variety: 0.15,          // Movement pattern variation
  equipment: 0.10         // Equipment availability
};

/**
 * Selects exercises for a workout based on criteria
 *
 * Strategy:
 * 1. Identify muscles needing volume
 * 2. Prioritize compound movements for efficiency
 * 3. Respect fatigue state (low recovery = lower fatigue exercises)
 * 4. Ensure movement pattern variety
 * 5. Fill remaining time with isolation work
 *
 * @param availableExercises - All exercises to choose from
 * @param criteria - Selection constraints and preferences
 * @param volumeTargets - Current volume status
 * @param recoveryScore - Current recovery state
 * @returns Selected exercises with reasoning
 */
export function selectExercises(
  availableExercises: Exercise[],
  criteria: SelectionCriteria,
  volumeTargets: VolumeTarget[],
  recoveryScore?: RecoveryScore
): ExerciseSelection {
  const reasoning: string[] = [];
  const selectedExercises: Exercise[] = [];
  const musclesCovered = new Map<MuscleGroup, number>();
  const usedMovementPatterns = new Set<MovementPattern>();

  // Filter by available equipment and exclusions
  const eligibleExercises = availableExercises.filter(ex => {
    if (criteria.excludeExercises.includes(ex.id)) return false;
    if (!criteria.availableEquipment.includes(ex.equipment)) return false;
    return true;
  });

  reasoning.push(`${eligibleExercises.length} exercises available with current equipment`);

  // Identify volume priorities
  const priorityMuscles = identifyVolumePriorities(volumeTargets, 0.7);
  reasoning.push(`Priority muscles: ${priorityMuscles.join(', ')}`);

  // Calculate fatigue budget based on recovery
  const fatigueLimit = calculateFatigueBudget(recoveryScore);
  let currentFatigue = criteria.currentFatigue;
  reasoning.push(`Fatigue budget: ${fatigueLimit - currentFatigue} remaining`);

  // Phase 1: Select primary compound movements
  const compounds = selectCompoundMovements(
    eligibleExercises,
    priorityMuscles,
    recoveryScore,
    usedMovementPatterns,
    Math.min(4, criteria.maxExercises)
  );

  for (const exercise of compounds) {
    if (currentFatigue + exercise.fatigueIndex > fatigueLimit) {
      reasoning.push(`Skipped ${exercise.name} - would exceed fatigue budget`);
      continue;
    }

    selectedExercises.push(exercise);
    currentFatigue += exercise.fatigueIndex;
    usedMovementPatterns.add(exercise.movementPattern);

    // Track muscle coverage (assume 3-4 sets per exercise)
    const setsPerExercise = 3;
    exercise.primaryMuscles.forEach(muscle => {
      const current = musclesCovered.get(muscle) || 0;
      musclesCovered.set(muscle, current + setsPerExercise);
    });

    reasoning.push(`Added ${exercise.name} (${exercise.movementPattern}) - targets ${exercise.primaryMuscles.join(', ')}`);
  }

  // Phase 2: Fill gaps with isolation exercises
  if (selectedExercises.length < criteria.maxExercises) {
    const isolations = selectIsolationExercises(
      eligibleExercises,
      priorityMuscles,
      musclesCovered,
      fatigueLimit - currentFatigue,
      criteria.maxExercises - selectedExercises.length
    );

    for (const exercise of isolations) {
      selectedExercises.push(exercise);
      currentFatigue += exercise.fatigueIndex;

      const setsPerExercise = 3;
      exercise.primaryMuscles.forEach(muscle => {
        const current = musclesCovered.get(muscle) || 0;
        musclesCovered.set(muscle, current + setsPerExercise);
      });

      reasoning.push(`Added ${exercise.name} for ${exercise.primaryMuscles.join(', ')}`);
    }
  }

  // Calculate estimated duration
  const estimatedDuration = estimateWorkoutDuration(selectedExercises);

  return {
    exercises: selectedExercises,
    musclesCovered,
    reasoning,
    estimatedDuration
  };
}

/**
 * Selects compound movements that provide most muscle coverage
 */
function selectCompoundMovements(
  exercises: Exercise[],
  priorityMuscles: MuscleGroup[],
  recoveryScore: RecoveryScore | undefined,
  usedPatterns: Set<MovementPattern>,
  maxExercises: number
): Exercise[] {
  // Filter for compound movements
  const compounds = exercises.filter(ex =>
    ex.movementPattern !== MovementPattern.ISOLATION &&
    ex.primaryMuscles.length >= 1
  );

  // Score each compound
  const scored = compounds.map(exercise => {
    let score = 0;

    // Bonus for targeting priority muscles
    const targetsPriority = exercise.primaryMuscles.some(m => priorityMuscles.includes(m));
    score += targetsPriority ? 30 : 0;

    // Bonus for multiple muscle groups (efficiency)
    score += (exercise.primaryMuscles.length + exercise.secondaryMuscles.length) * 5;

    // Penalty for already used movement pattern (variety)
    if (usedPatterns.has(exercise.movementPattern)) {
      score -= 15;
    }

    // Adjust for recovery state
    if (recoveryScore) {
      const muscleReadiness = exercise.primaryMuscles
        .map(m => recoveryScore.muscleReadiness.get(m) || 50)
        .reduce((a, b) => a + b, 0) / exercise.primaryMuscles.length;

      // If muscle not recovered, penalize high-fatigue exercises
      if (muscleReadiness < 60 && exercise.fatigueIndex > 7) {
        score -= 20;
      }
    }

    // Prefer moderate difficulty for main lifts
    if (exercise.difficulty >= 6 && exercise.difficulty <= 8) {
      score += 10;
    }

    return { exercise, score };
  });

  // Sort by score and select top exercises
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, maxExercises)
    .map(s => s.exercise);
}

/**
 * Selects isolation exercises to fill volume gaps
 */
function selectIsolationExercises(
  exercises: Exercise[],
  priorityMuscles: MuscleGroup[],
  currentCoverage: Map<MuscleGroup, number>,
  fatigueRemaining: number,
  maxExercises: number
): Exercise[] {
  // Filter for isolation movements
  const isolations = exercises.filter(ex =>
    ex.movementPattern === MovementPattern.ISOLATION &&
    ex.fatigueIndex <= fatigueRemaining
  );

  // Score each isolation exercise
  const scored = isolations.map(exercise => {
    let score = 0;

    // High priority for muscles not yet covered or priority muscles
    exercise.primaryMuscles.forEach(muscle => {
      const covered = currentCoverage.get(muscle) || 0;

      if (covered === 0) {
        score += 50; // Not covered at all
      } else if (covered < 6) {
        score += 30; // Undercovered
      }

      if (priorityMuscles.includes(muscle)) {
        score += 20;
      }
    });

    // Prefer lower fatigue for accessories
    score += (10 - exercise.fatigueIndex) * 2;

    return { exercise, score };
  });

  // Select top scored isolations
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, maxExercises)
    .map(s => s.exercise);
}

/**
 * Calculates fatigue budget based on recovery state
 *
 * High recovery = can handle more fatigue
 * Low recovery = limit fatigue accumulation
 */
function calculateFatigueBudget(recoveryScore?: RecoveryScore): number {
  if (!recoveryScore) return 60; // Default moderate budget

  // Scale fatigue budget with recovery: 40-80 range
  const baseBudget = 40;
  const recoveryBonus = (recoveryScore.overall / 100) * 40;

  return Math.round(baseBudget + recoveryBonus);
}

/**
 * Estimates workout duration based on exercises
 *
 * Assumptions:
 * - Compound: 5 min per set (including rest)
 * - Isolation: 3 min per set
 * - Warmup: 10 min
 * - Cooldown: 5 min
 */
function estimateWorkoutDuration(exercises: Exercise[]): number {
  let duration = 15; // Warmup + cooldown

  exercises.forEach(exercise => {
    const setsPerExercise = 3; // Average
    const timePerSet = exercise.movementPattern === MovementPattern.ISOLATION ? 3 : 5;
    duration += setsPerExercise * timePerSet;
  });

  return duration;
}

/**
 * Validates exercise selection meets minimum criteria
 *
 * Checks:
 * - All required muscles have coverage
 * - Movement patterns are balanced
 * - No excessive fatigue accumulation
 */
export function validateSelection(
  selection: ExerciseSelection,
  criteria: SelectionCriteria,
  volumeTargets: VolumeTarget[]
): { valid: boolean; warnings: string[] } {
  const warnings: string[] = [];

  // Check required muscles
  criteria.requiredMuscles.forEach(muscle => {
    const coverage = selection.musclesCovered.get(muscle) || 0;
    if (coverage === 0) {
      warnings.push(`Required muscle ${muscle} has no coverage`);
    }
  });

  // Check for movement pattern balance
  const patterns = new Map<MovementPattern, number>();
  selection.exercises.forEach(ex => {
    const count = patterns.get(ex.movementPattern) || 0;
    patterns.set(ex.movementPattern, count + 1);
  });

  // Warn if too many of same pattern
  patterns.forEach((count, pattern) => {
    if (count > 3) {
      warnings.push(`Too many ${pattern} exercises (${count}). Consider variety.`);
    }
  });

  // Check push/pull balance for upper body
  const pushCount = selection.exercises.filter(ex =>
    ex.movementPattern === MovementPattern.HORIZONTAL_PUSH ||
    ex.movementPattern === MovementPattern.VERTICAL_PUSH
  ).length;

  const pullCount = selection.exercises.filter(ex =>
    ex.movementPattern === MovementPattern.HORIZONTAL_PULL ||
    ex.movementPattern === MovementPattern.VERTICAL_PULL
  ).length;

  if (Math.abs(pushCount - pullCount) > 2) {
    warnings.push(`Push/pull imbalance: ${pushCount} push vs ${pullCount} pull exercises`);
  }

  return {
    valid: warnings.length === 0,
    warnings
  };
}

/**
 * Suggests exercise substitutions based on:
 * - Equipment availability
 * - Injury/preference
 * - Muscle targeting similarity
 */
export function suggestSubstitution(
  exercise: Exercise,
  allExercises: Exercise[],
  availableEquipment: EquipmentType[]
): Exercise[] {
  // Find exercises that target same primary muscles
  const substitutes = allExercises.filter(ex => {
    if (ex.id === exercise.id) return false;
    if (!availableEquipment.includes(ex.equipment)) return false;

    // Must target at least one same primary muscle
    const sharesPrimaryMuscle = exercise.primaryMuscles.some(m =>
      ex.primaryMuscles.includes(m)
    );

    // Similar movement pattern is a bonus
    const samePattern = ex.movementPattern === exercise.movementPattern;

    return sharesPrimaryMuscle || samePattern;
  });

  // Score substitutes by similarity
  const scored = substitutes.map(sub => {
    let score = 0;

    // Same primary muscles
    const sharedPrimary = exercise.primaryMuscles.filter(m =>
      sub.primaryMuscles.includes(m)
    ).length;
    score += sharedPrimary * 30;

    // Same movement pattern
    if (sub.movementPattern === exercise.movementPattern) {
      score += 25;
    }

    // Similar difficulty
    const difficultyDiff = Math.abs(sub.difficulty - exercise.difficulty);
    score += (10 - difficultyDiff) * 5;

    // Similar fatigue
    const fatigueDiff = Math.abs(sub.fatigueIndex - exercise.fatigueIndex);
    score += (10 - fatigueDiff) * 3;

    return { exercise: sub, score };
  });

  // Return top 5 substitutes
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map(s => s.exercise);
}

/**
 * Reorders exercises for optimal workout flow
 *
 * Best practices:
 * - Heaviest compounds first (when fresh)
 * - Alternate push/pull or upper/lower
 * - Isolations at the end
 * - Consider fatigue accumulation
 */
export function optimizeExerciseOrder(exercises: Exercise[]): Exercise[] {
  // Separate into categories
  const compounds: Exercise[] = [];
  const isolations: Exercise[] = [];

  exercises.forEach(ex => {
    if (ex.movementPattern === MovementPattern.ISOLATION) {
      isolations.push(ex);
    } else {
      compounds.push(ex);
    }
  });

  // Sort compounds by fatigue index (highest first - do when fresh)
  compounds.sort((a, b) => b.fatigueIndex - a.fatigueIndex);

  // Try to alternate movement patterns in compounds
  const optimizedCompounds: Exercise[] = [];
  const remaining = [...compounds];

  while (remaining.length > 0) {
    // Take the highest fatigue exercise remaining
    const next = remaining.shift()!;
    optimizedCompounds.push(next);

    // Try to find an exercise with different pattern for next
    if (remaining.length > 0) {
      const differentPatternIdx = remaining.findIndex(ex =>
        ex.movementPattern !== next.movementPattern
      );

      if (differentPatternIdx > 0) {
        // Swap to front
        const differentPattern = remaining.splice(differentPatternIdx, 1)[0];
        remaining.unshift(differentPattern);
      }
    }
  }

  // Append isolations (sorted by muscle group for super-setting potential)
  isolations.sort((a, b) => {
    const aMuscle = a.primaryMuscles[0];
    const bMuscle = b.primaryMuscles[0];
    return aMuscle.localeCompare(bMuscle);
  });

  return [...optimizedCompounds, ...isolations];
}
