/**
 * Double Progression with Load Bias
 *
 * Progressive overload strategy that prioritizes adding weight over adding reps.
 *
 * How it works:
 * 1. Set a rep range (e.g., 6-10 reps)
 * 2. When you hit the top of the range for all sets, add weight
 * 3. "Load bias" means we progress weight more aggressively than traditional DP
 * 4. Track sessions at current load to ensure consistency before progressing
 *
 * Example progression:
 * - Week 1: 135lbs x 8,7,6
 * - Week 2: 135lbs x 9,8,7
 * - Week 3: 135lbs x 10,9,8 (not ready yet - didn't hit 10 on all sets)
 * - Week 4: 135lbs x 10,10,9 (almost ready)
 * - Week 5: 135lbs x 10,10,10 (PROGRESS!)
 * - Week 6: 140lbs x 7,6,6 (start cycle again)
 */

import { ProgressionState, WorkoutSet } from '../types';
import { calculatePlates, suggestNextWeight } from '../utils/plate_math';

/**
 * Configuration for double progression
 */
export interface ProgressionConfig {
  minReps: number;          // Bottom of rep range
  maxReps: number;          // Top of rep range (progression trigger)
  loadIncrement: number;    // How much weight to add (lbs/kg)
  sessionsRequired: number; // Sessions at current load before allowing progression
  rpeThreshold?: number;    // Optional: only progress if RPE is below this (e.g., 8)
}

/**
 * Standard progression configs for different rep ranges
 */
export const PROGRESSION_CONFIGS = {
  // Strength range (lower reps, bigger jumps)
  strength: {
    minReps: 3,
    maxReps: 5,
    loadIncrement: 10,
    sessionsRequired: 2,
    rpeThreshold: 8
  },
  // Hypertrophy range (moderate reps)
  hypertrophy: {
    minReps: 6,
    maxReps: 10,
    loadIncrement: 5,
    sessionsRequired: 2,
    rpeThreshold: 8.5
  },
  // Endurance range (higher reps, smaller jumps)
  endurance: {
    minReps: 12,
    maxReps: 15,
    loadIncrement: 2.5,
    sessionsRequired: 2,
    rpeThreshold: 9
  }
};

/**
 * Evaluates if ready to progress to heavier weight
 *
 * Criteria:
 * 1. Hit target reps on all sets (or majority with load bias)
 * 2. Completed minimum sessions at current load
 * 3. RPE is manageable (optional)
 *
 * Load bias: We allow progression if you hit target on 2/3 sets
 * This keeps weight progressing rather than getting stuck chasing perfect reps
 *
 * @param state - Current progression state
 * @param recentSets - Sets from most recent session
 * @param config - Progression configuration
 * @returns Object with readyToProgress flag and reasoning
 */
export function evaluateProgression(
  state: ProgressionState,
  recentSets: WorkoutSet[],
  config: ProgressionConfig
): {
  readyToProgress: boolean;
  reason: string;
  confidence: 'high' | 'medium' | 'low';
} {
  // Check 1: Minimum sessions at current load
  if (state.sessionsAtCurrentLoad < config.sessionsRequired) {
    return {
      readyToProgress: false,
      reason: `Need ${config.sessionsRequired - state.sessionsAtCurrentLoad} more session(s) at current weight`,
      confidence: 'low'
    };
  }

  // Check 2: Rep targets
  const completedSets = recentSets.filter(s => s.completed);
  if (completedSets.length === 0) {
    return {
      readyToProgress: false,
      reason: 'No completed sets in recent session',
      confidence: 'low'
    };
  }

  // Count sets that hit target reps
  const setsHittingTarget = completedSets.filter(s => s.actualReps >= config.maxReps).length;
  const totalSets = completedSets.length;

  // Load bias: require 2/3 of sets to hit target (more aggressive than 100%)
  const requiredSets = Math.ceil(totalSets * 0.66); // 66% threshold
  const hitEnoughSets = setsHittingTarget >= requiredSets;

  if (!hitEnoughSets) {
    return {
      readyToProgress: false,
      reason: `Hit target reps on ${setsHittingTarget}/${totalSets} sets. Need ${requiredSets}/${totalSets}`,
      confidence: 'medium'
    };
  }

  // Check 3: RPE check (if configured)
  if (config.rpeThreshold) {
    const avgRPE = completedSets
      .filter(s => s.rpe !== undefined)
      .reduce((sum, s) => sum + (s.rpe || 0), 0) / completedSets.length;

    if (avgRPE > config.rpeThreshold) {
      return {
        readyToProgress: false,
        reason: `RPE too high (${avgRPE.toFixed(1)}). Wait until below ${config.rpeThreshold}`,
        confidence: 'medium'
      };
    }
  }

  // All checks passed!
  return {
    readyToProgress: true,
    reason: `Hit ${setsHittingTarget}/${totalSets} sets at target reps. Ready to add weight!`,
    confidence: setsHittingTarget === totalSets ? 'high' : 'medium'
  };
}

/**
 * Calculates next weight for progression
 *
 * Uses plate math to ensure weight is achievable with available plates
 *
 * @param currentWeight - Current working weight
 * @param config - Progression config
 * @param availablePlates - Available plate weights
 * @param barWeight - Barbell weight
 * @returns Next weight to use
 */
export function calculateNextWeight(
  currentWeight: number,
  config: ProgressionConfig,
  availablePlates?: number[],
  barWeight?: number
): number {
  const targetWeight = currentWeight + config.loadIncrement;

  // If plate info provided, find nearest achievable weight
  if (availablePlates && barWeight) {
    return suggestNextWeight(currentWeight, config.loadIncrement, barWeight, availablePlates);
  }

  return targetWeight;
}

/**
 * Updates progression state after a workout
 *
 * @param state - Current progression state
 * @param sets - Sets completed in workout
 * @param config - Progression configuration
 * @returns Updated progression state
 */
export function updateProgressionState(
  state: ProgressionState,
  sets: WorkoutSet[],
  config: ProgressionConfig
): ProgressionState {
  const evaluation = evaluateProgression(state, sets, config);

  if (evaluation.readyToProgress) {
    // Progress to next weight
    const nextWeight = calculateNextWeight(state.currentWeight, config);

    return {
      ...state,
      currentWeight: nextWeight,
      currentReps: config.minReps, // Start at bottom of rep range
      targetReps: config.maxReps,
      sessionsAtCurrentLoad: 0, // Reset session counter
      readyToProgress: false,
      lastProgressionDate: new Date()
    };
  } else {
    // Stay at current weight, increment session counter
    return {
      ...state,
      sessionsAtCurrentLoad: state.sessionsAtCurrentLoad + 1,
      readyToProgress: evaluation.readyToProgress
    };
  }
}

/**
 * Handles deloads when progress stalls
 *
 * If stuck at same weight for too many sessions, reduce weight and build back up
 *
 * @param state - Current progression state
 * @param maxSessionsAtLoad - Max sessions before triggering deload (default 6)
 * @param deloadPercentage - How much to reduce weight (default 0.9 = 10% reduction)
 * @returns Updated state with deload applied if needed
 */
export function handleDeload(
  state: ProgressionState,
  maxSessionsAtLoad: number = 6,
  deloadPercentage: number = 0.9
): { state: ProgressionState; deloaded: boolean; reason?: string } {
  if (state.sessionsAtCurrentLoad < maxSessionsAtLoad) {
    return { state, deloaded: false };
  }

  // Apply deload
  const deloadedWeight = Math.round(state.currentWeight * deloadPercentage);

  return {
    state: {
      ...state,
      currentWeight: deloadedWeight,
      sessionsAtCurrentLoad: 0,
      readyToProgress: false
    },
    deloaded: true,
    reason: `Stalled for ${maxSessionsAtLoad} sessions. Deloading to ${deloadedWeight}lbs to rebuild`
  };
}

/**
 * Tracks long-term progression trends
 *
 * Analyzes progression history to identify patterns
 *
 * @param progressionHistory - Array of historical progression events
 * @returns Analysis of progression rate and trends
 */
export function analyzeProgressionTrend(
  progressionHistory: Array<{
    date: Date;
    weight: number;
    reps: number;
  }>
): {
  weightGainedPerWeek: number;
  progressionRate: 'fast' | 'normal' | 'slow' | 'stalled';
  recommendation: string;
} {
  if (progressionHistory.length < 4) {
    return {
      weightGainedPerWeek: 0,
      progressionRate: 'normal',
      recommendation: 'Keep tracking to establish baseline progression rate'
    };
  }

  // Calculate weight gained over time
  const recentHistory = progressionHistory.slice(-8); // Last 8 sessions
  const firstWeight = recentHistory[0].weight;
  const lastWeight = recentHistory[recentHistory.length - 1].weight;
  const weightGained = lastWeight - firstWeight;

  // Calculate time span in weeks
  const firstDate = new Date(recentHistory[0].date);
  const lastDate = new Date(recentHistory[recentHistory.length - 1].date);
  const weeksSpan = (lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24 * 7);

  const weightGainedPerWeek = weeksSpan > 0 ? weightGained / weeksSpan : 0;

  // Classify progression rate
  let progressionRate: 'fast' | 'normal' | 'slow' | 'stalled';
  let recommendation: string;

  if (weightGainedPerWeek >= 5) {
    progressionRate = 'fast';
    recommendation = 'Excellent progress! Maintain current approach and ensure recovery is adequate.';
  } else if (weightGainedPerWeek >= 2) {
    progressionRate = 'normal';
    recommendation = 'Good steady progress. This is sustainable long-term.';
  } else if (weightGainedPerWeek > 0) {
    progressionRate = 'slow';
    recommendation = 'Progress is slow. Consider increasing training frequency or volume.';
  } else {
    progressionRate = 'stalled';
    recommendation = 'No progress detected. Review form, recovery, and nutrition. Consider deload.';
  }

  return {
    weightGainedPerWeek,
    progressionRate,
    recommendation
  };
}

/**
 * Calculates estimated 1RM from working sets
 *
 * Uses Epley formula: 1RM = weight × (1 + reps/30)
 * Most accurate for reps between 3-10
 *
 * @param weight - Weight used
 * @param reps - Reps completed
 * @param rpe - Optional RPE (adjusts estimate)
 * @returns Estimated 1RM
 */
export function estimate1RM(weight: number, reps: number, rpe?: number): number {
  // Base Epley formula
  let e1RM = weight * (1 + reps / 30);

  // Adjust based on RPE if provided
  if (rpe !== undefined) {
    const repsInReserve = 10 - rpe; // RPE 8 = 2 RIR
    const totalReps = reps + repsInReserve;
    e1RM = weight * (1 + totalReps / 30);
  }

  return Math.round(e1RM);
}

/**
 * Suggests target weight based on percentage of 1RM
 *
 * Common training zones:
 * - 90-100%: Max strength
 * - 80-90%: Strength
 * - 70-80%: Hypertrophy/strength
 * - 60-70%: Hypertrophy
 *
 * @param e1RM - Estimated 1RM
 * @param percentage - Percentage of 1RM (0-1)
 * @returns Target working weight
 */
export function calculateTrainingWeight(e1RM: number, percentage: number): number {
  return Math.round(e1RM * percentage);
}

/**
 * Autoregulates intensity based on performance
 *
 * If consistently hitting top of rep range with low RPE, suggest weight increase
 * If struggling to hit bottom of range, suggest weight decrease
 *
 * @param recentSets - Last few sets performed
 * @param config - Progression config
 * @returns Suggested adjustment
 */
export function autoregulateLoad(
  recentSets: WorkoutSet[],
  config: ProgressionConfig
): {
  action: 'increase' | 'maintain' | 'decrease';
  reason: string;
  adjustmentAmount: number;
} {
  const completedSets = recentSets.filter(s => s.completed);
  if (completedSets.length === 0) {
    return {
      action: 'maintain',
      reason: 'No data to analyze',
      adjustmentAmount: 0
    };
  }

  // Check average reps and RPE
  const avgReps = completedSets.reduce((sum, s) => sum + s.actualReps, 0) / completedSets.length;
  const setsWithRPE = completedSets.filter(s => s.rpe !== undefined);
  const avgRPE = setsWithRPE.length > 0
    ? setsWithRPE.reduce((sum, s) => sum + (s.rpe || 0), 0) / setsWithRPE.length
    : null;

  // Case 1: Consistently exceeding top of range with low RPE
  if (avgReps >= config.maxReps + 1 && avgRPE && avgRPE < 7) {
    return {
      action: 'increase',
      reason: 'Consistently exceeding rep target with low effort',
      adjustmentAmount: config.loadIncrement * 1.5
    };
  }

  // Case 2: Hitting top of range easily
  if (avgReps >= config.maxReps && avgRPE && avgRPE < 7.5) {
    return {
      action: 'increase',
      reason: 'Hitting targets easily, ready for more weight',
      adjustmentAmount: config.loadIncrement
    };
  }

  // Case 3: Struggling to hit bottom of range
  if (avgReps < config.minReps) {
    return {
      action: 'decrease',
      reason: 'Failing to hit minimum rep target',
      adjustmentAmount: -config.loadIncrement
    };
  }

  // Case 4: In range, maintain
  return {
    action: 'maintain',
    reason: 'Performance is appropriate for current weight',
    adjustmentAmount: 0
  };
}
