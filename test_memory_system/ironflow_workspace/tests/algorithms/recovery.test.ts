/**
 * Tests for recovery tracking algorithm
 */

import {
  calculateRecoveryScore,
  isMuscleReady,
  suggestIntensityAdjustment,
  analyzeRecoveryTrend
} from '../../src/algorithms/recovery';
import { RecoveryData, MuscleGroup } from '../../src/types';

describe('calculateRecoveryScore', () => {
  const baseRecoveryData: RecoveryData = {
    userId: 'test-user',
    date: new Date('2025-01-15'),
    sleepHours: 8,
    sleepQuality: 8,
    soreness: new Map(),
    stressLevel: 3,
    activityLevel: 5
  };

  test('calculates high recovery score with optimal metrics', () => {
    const result = calculateRecoveryScore(baseRecoveryData);

    expect(result.overall).toBeGreaterThanOrEqual(80);
    expect(result.readiness).toBe('high');
    expect(result.recommendations).toContain(
      expect.stringMatching(/excellent recovery/i)
    );
  });

  test('incorporates HRV into score when available', () => {
    const withHRV = {
      ...baseRecoveryData,
      hrv: 75 // High HRV
    };

    const withoutHRV = calculateRecoveryScore(baseRecoveryData);
    const withHRVScore = calculateRecoveryScore(withHRV);

    // High HRV should improve score
    expect(withHRVScore.overall).toBeGreaterThanOrEqual(withoutHRV.overall);
  });

  test('incorporates resting heart rate into score', () => {
    const goodRHR = {
      ...baseRecoveryData,
      restingHeartRate: 55 // Low RHR is good
    };

    const elevatedRHR = {
      ...baseRecoveryData,
      restingHeartRate: 75 // Elevated
    };

    const goodScore = calculateRecoveryScore(goodRHR);
    const elevatedScore = calculateRecoveryScore(elevatedRHR);

    expect(goodScore.overall).toBeGreaterThan(elevatedScore.overall);
  });

  test('penalizes poor sleep', () => {
    const poorSleep = {
      ...baseRecoveryData,
      sleepHours: 5,
      sleepQuality: 4
    };

    const result = calculateRecoveryScore(poorSleep);

    expect(result.overall).toBeLessThan(70);
    expect(result.recommendations).toContain(
      expect.stringMatching(/sleep/i)
    );
  });

  test('accounts for muscle soreness', () => {
    const highSoreness = new Map<MuscleGroup, number>([
      [MuscleGroup.CHEST, 8],
      [MuscleGroup.SHOULDERS, 7],
      [MuscleGroup.TRICEPS, 9]
    ]);

    const soreData = {
      ...baseRecoveryData,
      soreness: highSoreness
    };

    const result = calculateRecoveryScore(soreData);

    expect(result.overall).toBeLessThan(70);
    expect(result.recommendations.length).toBeGreaterThan(0);
  });

  test('accounts for high stress', () => {
    const highStress = {
      ...baseRecoveryData,
      stressLevel: 9
    };

    const result = calculateRecoveryScore(highStress);

    expect(result.overall).toBeLessThan(70);
    expect(result.recommendations).toContain(
      expect.stringMatching(/stress/i)
    );
  });

  test('calculates muscle-specific readiness', () => {
    const soreness = new Map<MuscleGroup, number>([
      [MuscleGroup.CHEST, 8],  // Very sore
      [MuscleGroup.BACK, 2]    // Not sore
    ]);

    const data = {
      ...baseRecoveryData,
      soreness
    };

    const result = calculateRecoveryScore(data);

    const chestReadiness = result.muscleReadiness.get(MuscleGroup.CHEST)!;
    const backReadiness = result.muscleReadiness.get(MuscleGroup.BACK)!;

    expect(chestReadiness).toBeLessThan(backReadiness);
    expect(chestReadiness).toBeLessThan(60); // Should be below threshold
  });

  test('generates specific recommendations for sore muscles', () => {
    const soreness = new Map<MuscleGroup, number>([
      [MuscleGroup.QUADS, 9],
      [MuscleGroup.HAMSTRINGS, 8]
    ]);

    const data = {
      ...baseRecoveryData,
      soreness
    };

    const result = calculateRecoveryScore(data);

    expect(result.recommendations).toContain(
      expect.stringMatching(/quads|hamstrings/i)
    );
  });

  test('handles missing optional data gracefully', () => {
    const minimalData: RecoveryData = {
      userId: 'test-user',
      date: new Date(),
      sleepHours: 7,
      sleepQuality: 7,
      soreness: new Map(),
      stressLevel: 5,
      activityLevel: 5
    };

    const result = calculateRecoveryScore(minimalData);

    expect(result.overall).toBeGreaterThan(0);
    expect(result.overall).toBeLessThanOrEqual(100);
    expect(result.readiness).toBeDefined();
  });

  test('uses custom baselines when provided', () => {
    const customBaselines = {
      optimalSleep: 9,
      optimalRHR: 50
    };

    const result = calculateRecoveryScore(baseRecoveryData, customBaselines);

    expect(result.overall).toBeGreaterThan(0);
    expect(result.overall).toBeLessThanOrEqual(100);
  });
});

describe('isMuscleReady', () => {
  test('returns true when muscle readiness above threshold', () => {
    const recoveryScore = calculateRecoveryScore({
      userId: 'test',
      date: new Date(),
      sleepHours: 8,
      sleepQuality: 8,
      soreness: new Map([[MuscleGroup.CHEST, 2]]),
      stressLevel: 3,
      activityLevel: 5
    });

    expect(isMuscleReady(MuscleGroup.CHEST, recoveryScore, 60)).toBe(true);
  });

  test('returns false when muscle very sore', () => {
    const recoveryScore = calculateRecoveryScore({
      userId: 'test',
      date: new Date(),
      sleepHours: 8,
      sleepQuality: 8,
      soreness: new Map([[MuscleGroup.CHEST, 9]]),
      stressLevel: 3,
      activityLevel: 5
    });

    expect(isMuscleReady(MuscleGroup.CHEST, recoveryScore, 60)).toBe(false);
  });

  test('respects custom threshold', () => {
    const recoveryScore = calculateRecoveryScore({
      userId: 'test',
      date: new Date(),
      sleepHours: 7,
      sleepQuality: 7,
      soreness: new Map([[MuscleGroup.BACK, 4]]),
      stressLevel: 5,
      activityLevel: 5
    });

    const highThreshold = isMuscleReady(MuscleGroup.BACK, recoveryScore, 90);
    const lowThreshold = isMuscleReady(MuscleGroup.BACK, recoveryScore, 50);

    expect(highThreshold).toBe(false);
    expect(lowThreshold).toBe(true);
  });
});

describe('suggestIntensityAdjustment', () => {
  test('suggests full intensity for high recovery', () => {
    const highRecovery = {
      overall: 85,
      readiness: 'high' as const,
      recommendations: [],
      muscleReadiness: new Map()
    };

    const adjustment = suggestIntensityAdjustment(highRecovery);
    expect(adjustment).toBeGreaterThanOrEqual(0.95);
  });

  test('suggests reduced intensity for low recovery', () => {
    const lowRecovery = {
      overall: 35,
      readiness: 'low' as const,
      recommendations: [],
      muscleReadiness: new Map()
    };

    const adjustment = suggestIntensityAdjustment(lowRecovery);
    expect(adjustment).toBeLessThanOrEqual(0.6);
  });

  test('provides graduated reductions based on recovery', () => {
    const scores = [90, 75, 65, 55, 45, 30];
    const adjustments = scores.map(score =>
      suggestIntensityAdjustment({
        overall: score,
        readiness: score >= 70 ? 'high' : score >= 50 ? 'medium' : 'low',
        recommendations: [],
        muscleReadiness: new Map()
      })
    );

    // Adjustments should decrease as recovery decreases
    for (let i = 1; i < adjustments.length; i++) {
      expect(adjustments[i]).toBeLessThanOrEqual(adjustments[i - 1]);
    }
  });
});

describe('analyzeRecoveryTrend', () => {
  test('identifies improving trend', () => {
    const improvingScores = [
      { date: new Date('2025-01-08'), score: 50 },
      { date: new Date('2025-01-09'), score: 55 },
      { date: new Date('2025-01-10'), score: 60 },
      { date: new Date('2025-01-11'), score: 65 },
      { date: new Date('2025-01-12'), score: 70 },
      { date: new Date('2025-01-13'), score: 75 },
      { date: new Date('2025-01-14'), score: 78 }
    ];

    const result = analyzeRecoveryTrend(improvingScores);

    expect(result.trend).toBe('improving');
    expect(result.suggestion).toContain('improving');
  });

  test('identifies declining trend', () => {
    const decliningScores = [
      { date: new Date('2025-01-08'), score: 80 },
      { date: new Date('2025-01-09'), score: 75 },
      { date: new Date('2025-01-10'), score: 70 },
      { date: new Date('2025-01-11'), score: 65 },
      { date: new Date('2025-01-12'), score: 60 },
      { date: new Date('2025-01-13'), score: 55 },
      { date: new Date('2025-01-14'), score: 50 }
    ];

    const result = analyzeRecoveryTrend(decliningScores);

    expect(result.trend).toBe('declining');
    expect(result.suggestion).toContain('declining');
  });

  test('identifies stable trend', () => {
    const stableScores = [
      { date: new Date('2025-01-08'), score: 70 },
      { date: new Date('2025-01-09'), score: 72 },
      { date: new Date('2025-01-10'), score: 69 },
      { date: new Date('2025-01-11'), score: 71 },
      { date: new Date('2025-01-12'), score: 70 },
      { date: new Date('2025-01-13'), score: 68 },
      { date: new Date('2025-01-14'), score: 71 }
    ];

    const result = analyzeRecoveryTrend(stableScores);

    expect(result.trend).toBe('stable');
    expect(result.suggestion).toContain('stable');
  });

  test('requires minimum data points', () => {
    const fewScores = [
      { date: new Date('2025-01-13'), score: 70 },
      { date: new Date('2025-01-14'), score: 72 }
    ];

    const result = analyzeRecoveryTrend(fewScores);

    expect(result.suggestion).toContain('more data');
  });
});

describe('edge cases and integration', () => {
  test('handles extreme values gracefully', () => {
    const extremeData: RecoveryData = {
      userId: 'test',
      date: new Date(),
      sleepHours: 2,
      sleepQuality: 1,
      restingHeartRate: 100,
      hrv: 20,
      soreness: new Map([
        [MuscleGroup.CHEST, 10],
        [MuscleGroup.BACK, 10],
        [MuscleGroup.LEGS, 10]
      ]),
      stressLevel: 10,
      activityLevel: 10
    };

    const result = calculateRecoveryScore(extremeData);

    expect(result.overall).toBeGreaterThanOrEqual(0);
    expect(result.overall).toBeLessThanOrEqual(100);
    expect(result.readiness).toBe('low');
    expect(result.recommendations.length).toBeGreaterThan(0);
  });

  test('comprehensive recovery workflow', () => {
    // Day 1: Poor recovery after hard training
    const day1: RecoveryData = {
      userId: 'test',
      date: new Date('2025-01-13'),
      sleepHours: 6,
      sleepQuality: 5,
      soreness: new Map([
        [MuscleGroup.CHEST, 8],
        [MuscleGroup.TRICEPS, 7]
      ]),
      stressLevel: 6,
      activityLevel: 7
    };

    const score1 = calculateRecoveryScore(day1);
    expect(score1.readiness).toBe('low');

    // Day 2: Improving with rest
    const day2: RecoveryData = {
      userId: 'test',
      date: new Date('2025-01-14'),
      sleepHours: 8,
      sleepQuality: 7,
      soreness: new Map([
        [MuscleGroup.CHEST, 5],
        [MuscleGroup.TRICEPS, 4]
      ]),
      stressLevel: 4,
      activityLevel: 4
    };

    const score2 = calculateRecoveryScore(day2);
    expect(score2.overall).toBeGreaterThan(score1.overall);

    // Trend analysis
    const trend = analyzeRecoveryTrend([
      { date: day1.date, score: score1.overall },
      { date: day2.date, score: score2.overall }
    ]);

    expect(trend.trend).toBe('stable'); // Need more data
  });
});
