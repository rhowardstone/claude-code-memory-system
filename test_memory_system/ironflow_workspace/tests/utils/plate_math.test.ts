/**
 * Tests for plate math calculator
 */

import {
  calculatePlates,
  formatPlateCalculation,
  suggestNextWeight,
  calculateWarmupWeights,
  isWeightAchievable,
  STANDARD_PLATES_LBS,
  STANDARD_BAR_WEIGHT_LBS
} from '../../src/utils/plate_math';

describe('calculatePlates', () => {
  test('calculates exact weight with standard plates', () => {
    // 225 lbs = 45lb bar + 2x45 per side
    const result = calculatePlates(225, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBe(225);
    expect(result.difference).toBe(0);
    expect(result.platesPerSide).toEqual([
      { weight: 45, count: 2 }
    ]);
  });

  test('handles multiple plate combinations', () => {
    // 185 lbs = 45lb bar + 1x45 + 1x25 per side
    const result = calculatePlates(185, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBe(185);
    expect(result.difference).toBe(0);
    expect(result.platesPerSide).toContainEqual({ weight: 45, count: 1 });
    expect(result.platesPerSide).toContainEqual({ weight: 25, count: 1 });
  });

  test('uses fractional plates for precision', () => {
    // 147.5 lbs = 45lb bar + 1x45 + 1x5 + 1x2.5 per side
    const result = calculatePlates(147.5, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBe(147.5);
    expect(result.difference).toBe(0);
  });

  test('returns closest weight when exact match impossible', () => {
    // Try to hit 100 lbs with only 45lb plates
    const result = calculatePlates(100, 45, [45]);

    // Best we can do is 45lb bar alone (55 needed per side, but only 45lb plates)
    expect(result.totalWeight).toBe(45); // Just the bar
    expect(result.difference).toBe(55); // Can't add any plates
  });

  test('handles bar-only weight', () => {
    const result = calculatePlates(45, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBe(45);
    expect(result.platesPerSide).toEqual([]);
  });

  test('throws error when target less than bar weight', () => {
    expect(() => calculatePlates(20, 45, STANDARD_PLATES_LBS))
      .toThrow('Target weight (20) cannot be less than bar weight (45)');
  });

  test('throws error when no plates available', () => {
    expect(() => calculatePlates(100, 45, []))
      .toThrow('No plates available');
  });

  test('works with kg plates', () => {
    const KG_PLATES = [25, 20, 15, 10, 5, 2.5];
    // 100kg = 20kg bar + 2x20 + 2x10 + 2x5 per side
    const result = calculatePlates(100, 20, KG_PLATES);

    expect(result.totalWeight).toBe(100);
    expect(result.difference).toBe(0);
  });

  test('uses greedy algorithm efficiently', () => {
    // 315 lbs = 45lb bar + 3x45 per side
    const result = calculatePlates(315, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBe(315);
    expect(result.platesPerSide).toEqual([
      { weight: 45, count: 3 }
    ]);
  });

  test('handles unsorted plate array', () => {
    const unsortedPlates = [10, 45, 25, 5, 2.5];
    const result = calculatePlates(135, 45, unsortedPlates);

    expect(result.totalWeight).toBe(135);
    expect(result.difference).toBe(0);
  });
});

describe('formatPlateCalculation', () => {
  test('formats standard calculation correctly', () => {
    const calc = calculatePlates(225, 45, STANDARD_PLATES_LBS);
    const formatted = formatPlateCalculation(calc);

    expect(formatted).toBe('45lb bar + 2x45 per side = 225 lbs');
  });

  test('formats bar-only weight', () => {
    const calc = calculatePlates(45, 45, STANDARD_PLATES_LBS);
    const formatted = formatPlateCalculation(calc);

    expect(formatted).toBe('45lb bar only = 45 lbs');
  });

  test('shows difference when not exact match', () => {
    const calc = calculatePlates(100, 45, [45, 25]);
    const formatted = formatPlateCalculation(calc);

    expect(formatted).toContain('from target');
  });
});

describe('suggestNextWeight', () => {
  test('suggests next achievable weight', () => {
    const next = suggestNextWeight(135, 5, 45, STANDARD_PLATES_LBS);

    // From 135, next achievable with 2.5lb plates (5lb increment) should be 140
    expect(next).toBeGreaterThan(135);
    expect(isWeightAchievable(next, 45, STANDARD_PLATES_LBS)).toBe(true);
  });

  test('respects minimum increment', () => {
    const current = 225;
    const next = suggestNextWeight(current, 10, 45, STANDARD_PLATES_LBS);

    expect(next - current).toBeGreaterThanOrEqual(10);
  });

  test('uses smallest plate when minimum increment too small', () => {
    // With 2.5lb plates, smallest increment is 5lbs (both sides)
    const next = suggestNextWeight(135, 1, 45, STANDARD_PLATES_LBS);

    expect(next - 135).toBeGreaterThanOrEqual(5); // 2.5 * 2
  });
});

describe('calculateWarmupWeights', () => {
  test('generates three warmup sets at 40%, 60%, 80%', () => {
    const workingWeight = 225;
    const warmups = calculateWarmupWeights(workingWeight, 45, STANDARD_PLATES_LBS);

    expect(warmups).toHaveLength(3);

    // Should be approximately 90, 135, 180 lbs
    expect(warmups[0].totalWeight).toBeCloseTo(90, 0);
    expect(warmups[1].totalWeight).toBeCloseTo(135, 0);
    expect(warmups[2].totalWeight).toBeCloseTo(180, 0);
  });

  test('never suggests warmup below bar weight', () => {
    const workingWeight = 65; // Light weight
    const warmups = calculateWarmupWeights(workingWeight, 45, STANDARD_PLATES_LBS);

    warmups.forEach(warmup => {
      expect(warmup.totalWeight).toBeGreaterThanOrEqual(45);
    });
  });

  test('warmup weights are all achievable', () => {
    const warmups = calculateWarmupWeights(315, 45, STANDARD_PLATES_LBS);

    warmups.forEach(warmup => {
      expect(warmup.difference).toBe(0);
    });
  });
});

describe('isWeightAchievable', () => {
  test('returns true for achievable weights', () => {
    expect(isWeightAchievable(225, 45, STANDARD_PLATES_LBS)).toBe(true);
    expect(isWeightAchievable(135, 45, STANDARD_PLATES_LBS)).toBe(true);
    expect(isWeightAchievable(45, 45, STANDARD_PLATES_LBS)).toBe(true);
  });

  test('returns false for impossible weights', () => {
    // Can't achieve 100 lbs with only 45lb plates available
    expect(isWeightAchievable(100, 45, [45])).toBe(false);
  });

  test('returns false for weight less than bar', () => {
    expect(isWeightAchievable(30, 45, STANDARD_PLATES_LBS)).toBe(false);
  });
});

describe('edge cases', () => {
  test('handles very heavy weights', () => {
    const result = calculatePlates(1000, 45, STANDARD_PLATES_LBS);

    expect(result.totalWeight).toBeGreaterThan(0);
    expect(result.platesPerSide.length).toBeGreaterThan(0);
  });

  test('handles custom bar weights', () => {
    // 35lb bar (common for women's bars)
    const result = calculatePlates(135, 35, STANDARD_PLATES_LBS);

    expect(result.barWeight).toBe(35);
    expect(result.totalWeight).toBe(135);
  });

  test('handles limited plate availability', () => {
    // Only small plates available
    const result = calculatePlates(65, 45, [10, 5]);

    expect(result.totalWeight).toBe(65);
    expect(result.difference).toBe(0);
  });
});
