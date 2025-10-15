/**
 * Recovery Tracking Algorithm
 *
 * Calculates recovery readiness based on:
 * - Sleep quantity and quality
 * - Heart rate variability (HRV)
 * - Resting heart rate (RHR)
 * - Muscle soreness levels
 * - Stress and activity levels
 *
 * Uses a weighted formula to produce an overall recovery score (0-100)
 * and per-muscle readiness scores.
 */

import { RecoveryData, RecoveryScore, MuscleGroup } from '../types';

/**
 * Weights for recovery score components
 * These can be adjusted based on research or user preferences
 */
const RECOVERY_WEIGHTS = {
  sleep: 0.35,        // 35% - Sleep is crucial for recovery
  hrv: 0.25,          // 25% - HRV is strong indicator when available
  rhr: 0.15,          // 15% - Resting heart rate
  soreness: 0.15,     // 15% - Muscle soreness
  stress: 0.10        // 10% - Mental stress and activity
};

/**
 * Baseline values for normalization
 * These should ideally be personalized per user
 */
const BASELINES = {
  optimalSleep: 8,
  minSleep: 4,
  maxSleep: 10,
  optimalRHR: 60,
  rhrRange: 30,       // +/- 30 bpm from optimal
  optimalHRV: 65,
  hrvRange: 50,       // +/- 50ms from optimal
  optimalStress: 3,   // Low stress
  optimalActivity: 5  // Moderate activity
};

/**
 * Calculates overall recovery score from recovery data
 *
 * @param data - Recovery metrics for the day
 * @param userBaselines - Optional personalized baselines (uses defaults if not provided)
 * @returns RecoveryScore with overall score, readiness level, and recommendations
 */
export function calculateRecoveryScore(
  data: RecoveryData,
  userBaselines?: Partial<typeof BASELINES>
): RecoveryScore {
  const baselines = { ...BASELINES, ...userBaselines };

  // Calculate component scores (0-100 scale)
  const sleepScore = calculateSleepScore(data.sleepHours, data.sleepQuality, baselines);
  const hrvScore = data.hrv !== undefined
    ? calculateHRVScore(data.hrv, baselines)
    : 50; // Neutral if not available

  const rhrScore = data.restingHeartRate !== undefined
    ? calculateRHRScore(data.restingHeartRate, baselines)
    : 50; // Neutral if not available

  const sorenessScore = calculateSorenessScore(data.soreness);
  const stressScore = calculateStressActivityScore(data.stressLevel, data.activityLevel, baselines);

  // Weighted overall score
  const overall = Math.round(
    sleepScore * RECOVERY_WEIGHTS.sleep +
    hrvScore * RECOVERY_WEIGHTS.hrv +
    rhrScore * RECOVERY_WEIGHTS.rhr +
    sorenessScore * RECOVERY_WEIGHTS.soreness +
    stressScore * RECOVERY_WEIGHTS.stress
  );

  // Determine readiness level
  const readiness = getReadinessLevel(overall);

  // Generate recommendations
  const recommendations = generateRecommendations({
    overall,
    sleepScore,
    hrvScore,
    rhrScore,
    sorenessScore,
    stressScore,
    data
  });

  // Calculate per-muscle readiness
  const muscleReadiness = calculateMuscleReadiness(data.soreness, overall);

  return {
    overall,
    readiness,
    recommendations,
    muscleReadiness
  };
}

/**
 * Calculates sleep contribution to recovery (0-100)
 *
 * Formula combines quantity and quality:
 * - Optimal sleep hours = 100
 * - Quality multiplier adjusts based on sleep quality rating
 */
function calculateSleepScore(
  hours: number,
  quality: number,
  baselines: typeof BASELINES
): number {
  // Quantity score: bell curve around optimal sleep
  const hoursDiff = Math.abs(hours - baselines.optimalSleep);
  const quantityScore = Math.max(0, 100 - (hoursDiff / 2) * 25);

  // Quality multiplier: 1-10 scale to 0.5-1.0 multiplier
  const qualityMultiplier = 0.5 + (quality / 10) * 0.5;

  return Math.min(100, quantityScore * qualityMultiplier);
}

/**
 * Calculates HRV contribution to recovery (0-100)
 *
 * Higher HRV = better recovery (parasympathetic dominance)
 * Normalized around user baseline
 */
function calculateHRVScore(hrv: number, baselines: typeof BASELINES): number {
  const diff = hrv - baselines.optimalHRV;
  const normalizedDiff = diff / baselines.hrvRange;

  // Convert to 0-100 scale, higher HRV is better
  const score = 50 + (normalizedDiff * 50);
  return Math.max(0, Math.min(100, score));
}

/**
 * Calculates resting heart rate contribution to recovery (0-100)
 *
 * Lower RHR = better recovery
 * Elevated RHR suggests stress or incomplete recovery
 */
function calculateRHRScore(rhr: number, baselines: typeof BASELINES): number {
  const diff = baselines.optimalRHR - rhr; // Inverse: lower is better
  const normalizedDiff = diff / baselines.rhrRange;

  const score = 50 + (normalizedDiff * 50);
  return Math.max(0, Math.min(100, score));
}

/**
 * Calculates soreness contribution to recovery (0-100)
 *
 * Average soreness across all muscles, where:
 * - Low soreness (1-3) = good recovery
 * - High soreness (8-10) = poor recovery
 */
function calculateSorenessScore(soreness: Map<MuscleGroup, number>): number {
  if (soreness.size === 0) {
    return 100; // No soreness data = assume fully recovered
  }

  const sorenessValues = Array.from(soreness.values());
  const avgSoreness = sorenessValues.reduce((sum, val) => sum + val, 0) / sorenessValues.length;

  // Convert 1-10 scale to 100-0 (inverse: higher soreness = lower score)
  return Math.max(0, 100 - (avgSoreness - 1) * 11.1);
}

/**
 * Calculates stress and activity contribution to recovery (0-100)
 *
 * Combines mental stress and physical activity outside gym:
 * - Low stress + moderate activity = optimal
 * - High stress or very high activity = impaired recovery
 */
function calculateStressActivityScore(
  stress: number,
  activity: number,
  baselines: typeof BASELINES
): number {
  // Stress: 1-10 scale, lower is better
  const stressScore = Math.max(0, 100 - (stress - 1) * 11.1);

  // Activity: bell curve around optimal (moderate activity is good)
  const activityDiff = Math.abs(activity - baselines.optimalActivity);
  const activityScore = Math.max(0, 100 - activityDiff * 15);

  // Weight stress more heavily (70/30 split)
  return stressScore * 0.7 + activityScore * 0.3;
}

/**
 * Determines readiness level from overall score
 */
function getReadinessLevel(score: number): 'low' | 'medium' | 'high' {
  if (score >= 70) return 'high';
  if (score >= 50) return 'medium';
  return 'low';
}

/**
 * Generates actionable recommendations based on recovery metrics
 */
function generateRecommendations(context: {
  overall: number;
  sleepScore: number;
  hrvScore: number;
  rhrScore: number;
  sorenessScore: number;
  stressScore: number;
  data: RecoveryData;
}): string[] {
  const recommendations: string[] = [];

  // Sleep recommendations
  if (context.sleepScore < 60) {
    if (context.data.sleepHours < 7) {
      recommendations.push('Prioritize getting 7-9 hours of sleep tonight');
    }
    if (context.data.sleepQuality < 6) {
      recommendations.push('Focus on sleep quality: dark room, cool temperature, no screens before bed');
    }
  }

  // HRV/RHR recommendations
  if (context.hrvScore < 50 || context.rhrScore < 50) {
    recommendations.push('Elevated stress markers detected. Consider lighter training or active recovery');
  }

  // Soreness recommendations
  if (context.sorenessScore < 50) {
    recommendations.push('High soreness levels. Include mobility work and consider deload week');

    // Identify most sore muscles
    const soreMuscles = Array.from(context.data.soreness.entries())
      .filter(([_, level]) => level >= 7)
      .map(([muscle, _]) => muscle);

    if (soreMuscles.length > 0) {
      recommendations.push(`Avoid heavy training for: ${soreMuscles.join(', ')}`);
    }
  }

  // Stress recommendations
  if (context.stressScore < 60) {
    if (context.data.stressLevel >= 7) {
      recommendations.push('High stress detected. Consider meditation, walking, or reducing training volume');
    }
    if (context.data.activityLevel >= 8) {
      recommendations.push('High activity outside gym. Ensure adequate nutrition and hydration');
    }
  }

  // Overall readiness
  if (context.overall >= 80) {
    recommendations.push('Excellent recovery! Good day for high-intensity or heavy training');
  } else if (context.overall < 40) {
    recommendations.push('Poor recovery. Consider full rest day or light cardio only');
  }

  return recommendations;
}

/**
 * Calculates readiness score for each muscle group (0-100)
 *
 * Combines overall recovery with muscle-specific soreness
 */
function calculateMuscleReadiness(
  soreness: Map<MuscleGroup, number>,
  overallScore: number
): Map<MuscleGroup, number> {
  const muscleReadiness = new Map<MuscleGroup, number>();

  // Start with all muscles at overall recovery level
  Object.values(MuscleGroup).forEach(muscle => {
    muscleReadiness.set(muscle, overallScore);
  });

  // Adjust based on muscle-specific soreness
  soreness.forEach((sorenessLevel, muscle) => {
    const baseReadiness = overallScore;

    // Soreness penalty: 1 = no penalty, 10 = -50 points
    const sorenessPenalty = (sorenessLevel - 1) * 5.5;

    const muscleScore = Math.max(0, baseReadiness - sorenessPenalty);
    muscleReadiness.set(muscle, Math.round(muscleScore));
  });

  return muscleReadiness;
}

/**
 * Checks if a specific muscle group is ready for training
 *
 * @param muscle - Muscle group to check
 * @param recoveryScore - RecoveryScore from calculateRecoveryScore
 * @param threshold - Minimum readiness score (default 60)
 * @returns true if muscle is ready for training
 */
export function isMuscleReady(
  muscle: MuscleGroup,
  recoveryScore: RecoveryScore,
  threshold: number = 60
): boolean {
  const readiness = recoveryScore.muscleReadiness.get(muscle);
  return readiness !== undefined && readiness >= threshold;
}

/**
 * Suggests training intensity adjustment based on recovery
 *
 * @param recoveryScore - Overall recovery score
 * @returns Recommended intensity multiplier (0.5 - 1.0)
 */
export function suggestIntensityAdjustment(recoveryScore: RecoveryScore): number {
  if (recoveryScore.overall >= 80) return 1.0;   // Full intensity
  if (recoveryScore.overall >= 70) return 0.95;  // Slight reduction
  if (recoveryScore.overall >= 60) return 0.9;   // 10% reduction
  if (recoveryScore.overall >= 50) return 0.85;  // 15% reduction
  if (recoveryScore.overall >= 40) return 0.75;  // 25% reduction
  return 0.5; // 50% reduction or rest day
}

/**
 * Creates a recovery trend analysis from historical data
 *
 * @param recentScores - Array of recovery scores from recent days
 * @returns Trend indicator and recommendation
 */
export function analyzeRecoveryTrend(
  recentScores: Array<{ date: Date; score: number }>
): { trend: 'improving' | 'stable' | 'declining'; suggestion: string } {
  if (recentScores.length < 3) {
    return {
      trend: 'stable',
      suggestion: 'Need more data to identify trends'
    };
  }

  // Calculate moving average slope
  const recent = recentScores.slice(-7); // Last 7 days
  const avgFirst = recent.slice(0, 3).reduce((sum, r) => sum + r.score, 0) / 3;
  const avgLast = recent.slice(-3).reduce((sum, r) => sum + r.score, 0) / 3;
  const slope = avgLast - avgFirst;

  if (slope > 5) {
    return {
      trend: 'improving',
      suggestion: 'Recovery is improving. Consider gradually increasing training volume'
    };
  } else if (slope < -5) {
    return {
      trend: 'declining',
      suggestion: 'Recovery is declining. Consider deload week or check sleep/stress levels'
    };
  } else {
    return {
      trend: 'stable',
      suggestion: 'Recovery is stable. Maintain current training approach'
    };
  }
}
