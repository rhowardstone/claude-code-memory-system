/**
 * Volume Targeting System
 *
 * Implements evidence-based volume recommendations:
 * - Beginners: 8-12 sets per muscle per week
 * - Intermediate: 12-16 sets per muscle per week
 * - Advanced: 16-20 sets per muscle per week
 *
 * Adjusts based on:
 * - Recovery capacity
 * - Training frequency
 * - Exercise selection (compounds count for multiple muscles)
 * - Individual response (can be tuned over time)
 */

import {
  MuscleGroup,
  ExperienceLevel,
  VolumeTarget,
  Exercise,
  WorkoutExercise,
  RecoveryScore
} from '../types';

/**
 * Base volume ranges per experience level (sets per week)
 */
const VOLUME_RANGES = {
  [ExperienceLevel.BEGINNER]: { min: 8, optimal: 10, max: 12 },
  [ExperienceLevel.INTERMEDIATE]: { min: 12, optimal: 14, max: 16 },
  [ExperienceLevel.ADVANCED]: { min: 16, optimal: 18, max: 20 }
};

/**
 * Muscle group size modifiers
 * Larger muscles can handle more volume
 */
const MUSCLE_SIZE_MODIFIERS = {
  [MuscleGroup.CHEST]: 1.0,
  [MuscleGroup.BACK]: 1.1,      // Back is large, can handle more
  [MuscleGroup.SHOULDERS]: 0.9,
  [MuscleGroup.BICEPS]: 0.8,    // Smaller muscles need less volume
  [MuscleGroup.TRICEPS]: 0.8,
  [MuscleGroup.QUADS]: 1.1,     // Large muscle group
  [MuscleGroup.HAMSTRINGS]: 0.9,
  [MuscleGroup.GLUTES]: 1.0,
  [MuscleGroup.CALVES]: 0.7,    // Small muscle, but can handle frequency
  [MuscleGroup.ABS]: 0.7,
  [MuscleGroup.FOREARMS]: 0.6
};

/**
 * How much secondary muscle work counts toward volume
 * Secondary work is less fatiguing but still contributes
 */
const SECONDARY_WORK_MULTIPLIER = 0.5;

/**
 * Calculates target weekly volume for a muscle group
 *
 * @param muscle - Muscle group
 * @param experienceLevel - User's training experience
 * @param recoveryScore - Current recovery status (optional)
 * @param userPreference - Optional multiplier for user preference (0.8-1.2)
 * @returns Target sets per week
 */
export function calculateTargetVolume(
  muscle: MuscleGroup,
  experienceLevel: ExperienceLevel,
  recoveryScore?: RecoveryScore,
  userPreference: number = 1.0
): number {
  // Base volume from experience level
  const baseRange = VOLUME_RANGES[experienceLevel];
  const baseVolume = baseRange.optimal;

  // Adjust for muscle size
  const sizeModifier = MUSCLE_SIZE_MODIFIERS[muscle];
  let targetVolume = baseVolume * sizeModifier;

  // Adjust for recovery if available
  if (recoveryScore) {
    const recoveryAdjustment = getRecoveryVolumeAdjustment(recoveryScore.overall);
    targetVolume *= recoveryAdjustment;
  }

  // Apply user preference (allows personalization)
  targetVolume *= userPreference;

  // Round to nearest integer and clamp to range
  return Math.round(
    Math.max(baseRange.min, Math.min(baseRange.max, targetVolume))
  );
}

/**
 * Calculates volume adjustment based on recovery score
 *
 * - High recovery (80+): Can handle up to 110% volume
 * - Medium recovery (60-80): Standard volume
 * - Low recovery (<60): Reduce to 70-90% volume
 */
function getRecoveryVolumeAdjustment(recoveryScore: number): number {
  if (recoveryScore >= 80) return 1.1;
  if (recoveryScore >= 70) return 1.0;
  if (recoveryScore >= 60) return 0.95;
  if (recoveryScore >= 50) return 0.85;
  return 0.7;
}

/**
 * Counts sets performed for each muscle group from a workout
 *
 * Considers both primary and secondary muscle involvement
 *
 * @param workout - Array of exercises performed
 * @param exercises - Exercise definitions for lookup
 * @returns Map of muscle groups to set count
 */
export function countVolume(
  workout: WorkoutExercise[],
  exercises: Map<string, Exercise>
): Map<MuscleGroup, number> {
  const volumeCount = new Map<MuscleGroup, number>();

  workout.forEach(workoutExercise => {
    const exercise = exercises.get(workoutExercise.exerciseId);
    if (!exercise) return;

    // Count completed sets only
    const completedSets = workoutExercise.sets.filter(s => s.completed).length;

    // Add to primary muscles (full credit)
    exercise.primaryMuscles.forEach(muscle => {
      const current = volumeCount.get(muscle) || 0;
      volumeCount.set(muscle, current + completedSets);
    });

    // Add to secondary muscles (partial credit)
    exercise.secondaryMuscles.forEach(muscle => {
      const current = volumeCount.get(muscle) || 0;
      volumeCount.set(muscle, current + (completedSets * SECONDARY_WORK_MULTIPLIER));
    });
  });

  return volumeCount;
}

/**
 * Updates volume tracking for the current week
 *
 * @param currentTargets - Current volume targets for the week
 * @param workoutVolume - Volume from today's workout
 * @returns Updated volume targets
 */
export function updateVolumeTracking(
  currentTargets: VolumeTarget[],
  workoutVolume: Map<MuscleGroup, number>
): VolumeTarget[] {
  return currentTargets.map(target => {
    const additionalSets = workoutVolume.get(target.muscleGroup) || 0;

    return {
      ...target,
      currentSetsThisWeek: target.currentSetsThisWeek + additionalSets
    };
  });
}

/**
 * Calculates remaining volume needed for each muscle this week
 *
 * @param targets - Current volume targets
 * @param workoutsRemaining - Number of workouts left this week
 * @returns Map of muscles to recommended sets per remaining workout
 */
export function calculateRemainingVolume(
  targets: VolumeTarget[],
  workoutsRemaining: number
): Map<MuscleGroup, number> {
  const remainingVolume = new Map<MuscleGroup, number>();

  targets.forEach(target => {
    const setsNeeded = Math.max(0, target.targetSetsPerWeek - target.currentSetsThisWeek);

    // Distribute remaining sets across remaining workouts
    const setsPerWorkout = workoutsRemaining > 0
      ? Math.ceil(setsNeeded / workoutsRemaining)
      : 0;

    remainingVolume.set(target.muscleGroup, setsPerWorkout);
  });

  return remainingVolume;
}

/**
 * Identifies muscles that need volume and should be prioritized
 *
 * @param targets - Current volume targets
 * @param threshold - Percentage of target completed to be considered "needs work" (default 0.7)
 * @returns Array of muscle groups that need more volume
 */
export function identifyVolumePriorities(
  targets: VolumeTarget[],
  threshold: number = 0.7
): MuscleGroup[] {
  return targets
    .filter(target => {
      const percentComplete = target.currentSetsThisWeek / target.targetSetsPerWeek;
      return percentComplete < threshold;
    })
    .sort((a, b) => {
      // Sort by most behind on volume
      const aPercent = a.currentSetsThisWeek / a.targetSetsPerWeek;
      const bPercent = b.currentSetsThisWeek / b.targetSetsPerWeek;
      return aPercent - bPercent;
    })
    .map(target => target.muscleGroup);
}

/**
 * Distributes volume across workouts per week
 *
 * Research shows frequency of 2x per week is optimal for most muscles
 *
 * @param targetSets - Total sets per week for a muscle
 * @param workoutsPerWeek - Number of training sessions
 * @returns Array of sets per workout
 */
export function distributeVolumeAcrossWeek(
  targetSets: number,
  workoutsPerWeek: number
): number[] {
  if (workoutsPerWeek <= 0) return [];

  // Optimal frequency is 2-3x per week for most muscles
  const optimalFrequency = Math.min(workoutsPerWeek, 3);

  // Distribute sets evenly across optimal frequency
  const setsPerSession = Math.ceil(targetSets / optimalFrequency);
  const distribution: number[] = new Array(workoutsPerWeek).fill(0);

  // Assign sets to first N workouts (optimal frequency)
  let remainingSets = targetSets;
  for (let i = 0; i < optimalFrequency && remainingSets > 0; i++) {
    const sets = Math.min(setsPerSession, remainingSets);
    distribution[i] = sets;
    remainingSets -= sets;
  }

  return distribution;
}

/**
 * Checks if muscle group has received adequate volume stimulus
 *
 * @param target - Volume target for muscle
 * @returns Object with status and recommendation
 */
export function assessVolumeAdequacy(target: VolumeTarget): {
  status: 'under' | 'optimal' | 'over';
  recommendation: string;
} {
  const percentOfTarget = (target.currentSetsThisWeek / target.targetSetsPerWeek) * 100;

  if (percentOfTarget < 80) {
    return {
      status: 'under',
      recommendation: `Add ${Math.ceil(target.targetSetsPerWeek - target.currentSetsThisWeek)} more sets for ${target.muscleGroup} this week`
    };
  } else if (percentOfTarget <= 110) {
    return {
      status: 'optimal',
      recommendation: `Volume for ${target.muscleGroup} is in optimal range`
    };
  } else {
    return {
      status: 'over',
      recommendation: `Consider reducing volume for ${target.muscleGroup} to avoid overtraining`
    };
  }
}

/**
 * Progressive volume strategy for building work capacity
 *
 * Gradually increases volume over mesocycle (4-6 weeks)
 *
 * @param baseVolume - Starting weekly volume
 * @param weekNumber - Current week in mesocycle (1-based)
 * @param mesocycleLength - Total weeks in mesocycle
 * @returns Recommended volume for current week
 */
export function progressiveVolumeRamp(
  baseVolume: number,
  weekNumber: number,
  mesocycleLength: number = 6
): number {
  // Typical progression: increase ~5-10% per week, then deload
  if (weekNumber >= mesocycleLength) {
    // Deload week
    return Math.round(baseVolume * 0.6);
  }

  const weekMultiplier = 1 + ((weekNumber - 1) / mesocycleLength) * 0.3;
  return Math.round(baseVolume * weekMultiplier);
}

/**
 * Calculates Maximum Recoverable Volume (MRV) warning
 *
 * MRV is the max volume you can recover from
 * Warning signs: excessive soreness, performance decline, poor recovery
 *
 * @param targets - Volume targets
 * @param recoveryScores - Recent recovery scores
 * @returns Warning if approaching MRV
 */
export function checkMRVWarning(
  targets: VolumeTarget[],
  recoveryScores: number[]
): { warning: boolean; message?: string } {
  // Check if consistently hitting upper volume limits with declining recovery
  const avgRecovery = recoveryScores.reduce((a, b) => a + b, 0) / recoveryScores.length;

  const atMaxVolume = targets.some(t => {
    const percentOfMax = (t.currentSetsThisWeek / t.targetSetsPerWeek) * 100;
    return percentOfMax > 110;
  });

  if (atMaxVolume && avgRecovery < 60) {
    return {
      warning: true,
      message: 'High volume with poor recovery detected. Consider reducing volume or taking deload week.'
    };
  }

  return { warning: false };
}

/**
 * Initializes volume targets for a new week
 *
 * @param muscles - Muscle groups to track
 * @param experienceLevel - User experience level
 * @param lastWeekVolume - Volume from previous week (for reference)
 * @returns Array of volume targets
 */
export function initializeWeeklyTargets(
  muscles: MuscleGroup[],
  experienceLevel: ExperienceLevel,
  lastWeekVolume?: Map<MuscleGroup, number>
): VolumeTarget[] {
  return muscles.map(muscle => {
    const targetSets = calculateTargetVolume(muscle, experienceLevel);
    const lastWeek = lastWeekVolume?.get(muscle) || 0;

    return {
      muscleGroup: muscle,
      targetSetsPerWeek: targetSets,
      currentSetsThisWeek: 0,
      lastWeekVolume: lastWeek
    };
  });
}
