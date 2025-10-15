/**
 * Plate Math Calculator
 *
 * Calculates the optimal combination of weight plates to load on a barbell
 * to achieve a target weight. Uses a greedy algorithm to minimize plate changes.
 */

import { PlateCalculation } from '../types';

/**
 * Standard plate weights in pounds (can be customized per gym)
 */
export const STANDARD_PLATES_LBS = [45, 35, 25, 10, 5, 2.5, 1.25];
export const STANDARD_PLATES_KG = [25, 20, 15, 10, 5, 2.5, 1.25];

/**
 * Standard bar weights
 */
export const STANDARD_BAR_WEIGHT_LBS = 45;
export const STANDARD_BAR_WEIGHT_KG = 20;

/**
 * Calculates the plates needed on each side of the bar to reach target weight
 *
 * @param targetWeight - Total weight to achieve (including bar)
 * @param barWeight - Weight of the bar itself
 * @param availablePlates - Array of plate weights available (sorted descending is optimal)
 * @returns PlateCalculation with plates per side and actual total weight
 *
 * Algorithm: Greedy approach
 * 1. Subtract bar weight from target
 * 2. Divide remaining by 2 (plates go on both sides)
 * 3. Use largest plates first to minimize plate count
 * 4. Return closest achievable weight if exact match impossible
 */
export function calculatePlates(
  targetWeight: number,
  barWeight: number = STANDARD_BAR_WEIGHT_LBS,
  availablePlates: number[] = STANDARD_PLATES_LBS
): PlateCalculation {
  // Validate inputs
  if (targetWeight < barWeight) {
    throw new Error(`Target weight (${targetWeight}) cannot be less than bar weight (${barWeight})`);
  }

  if (availablePlates.length === 0) {
    throw new Error('No plates available');
  }

  // Sort plates descending for greedy algorithm
  const sortedPlates = [...availablePlates].sort((a, b) => b - a);

  // Weight needed on each side
  let remainingPerSide = (targetWeight - barWeight) / 2;

  // Track plates used per side
  const platesPerSide: Array<{ weight: number; count: number }> = [];
  const plateCounts = new Map<number, number>();

  // Greedy algorithm: use largest plates first
  for (const plateWeight of sortedPlates) {
    if (remainingPerSide < plateWeight) {
      continue; // Plate too heavy, skip
    }

    // How many of this plate can we use?
    const count = Math.floor(remainingPerSide / plateWeight);

    if (count > 0) {
      plateCounts.set(plateWeight, count);
      remainingPerSide -= plateWeight * count;
    }

    // Stop if we've achieved exact weight
    if (remainingPerSide === 0) {
      break;
    }
  }

  // Convert map to array format
  sortedPlates.forEach(weight => {
    const count = plateCounts.get(weight);
    if (count && count > 0) {
      platesPerSide.push({ weight, count });
    }
  });

  // Calculate actual total weight achieved
  const totalPlateWeight = platesPerSide.reduce(
    (sum, plate) => sum + (plate.weight * plate.count * 2), // *2 for both sides
    0
  );
  const totalWeight = barWeight + totalPlateWeight;
  const difference = targetWeight - totalWeight;

  return {
    targetWeight,
    barWeight,
    availablePlates: sortedPlates,
    platesPerSide,
    totalWeight,
    difference
  };
}

/**
 * Formats plate calculation into human-readable string
 * Example: "45lb bar + 2x45 + 1x25 + 1x10 per side = 205 lbs"
 */
export function formatPlateCalculation(calc: PlateCalculation): string {
  if (calc.platesPerSide.length === 0) {
    return `${calc.barWeight}lb bar only = ${calc.totalWeight} lbs`;
  }

  const platesStr = calc.platesPerSide
    .map(p => `${p.count}x${p.weight}`)
    .join(' + ');

  const diffStr = calc.difference !== 0
    ? ` (${calc.difference > 0 ? '+' : ''}${calc.difference.toFixed(2)} from target)`
    : '';

  return `${calc.barWeight}lb bar + ${platesStr} per side = ${calc.totalWeight} lbs${diffStr}`;
}

/**
 * Suggests the next achievable weight given current available plates
 * Useful for progression when exact weight isn't possible
 */
export function suggestNextWeight(
  currentWeight: number,
  minimumIncrement: number,
  barWeight: number = STANDARD_BAR_WEIGHT_LBS,
  availablePlates: number[] = STANDARD_PLATES_LBS
): number {
  const smallestPlate = Math.min(...availablePlates);
  const smallestIncrement = smallestPlate * 2; // plates on both sides

  // Try increments until we find one that's achievable
  let targetWeight = currentWeight + Math.max(minimumIncrement, smallestIncrement);

  for (let attempt = 0; attempt < 20; attempt++) {
    const calc = calculatePlates(targetWeight, barWeight, availablePlates);

    if (calc.difference === 0) {
      return calc.totalWeight;
    }

    targetWeight += smallestIncrement;
  }

  // Fallback: return current weight + smallest possible increment
  return currentWeight + smallestIncrement;
}

/**
 * Calculates warmup weights based on working weight
 * Uses standard progression: 40%, 60%, 80% of working weight
 */
export function calculateWarmupWeights(
  workingWeight: number,
  barWeight: number = STANDARD_BAR_WEIGHT_LBS,
  availablePlates: number[] = STANDARD_PLATES_LBS
): PlateCalculation[] {
  const percentages = [0.4, 0.6, 0.8];

  return percentages.map(pct => {
    const targetWeight = workingWeight * pct;
    // Ensure warmup weight is at least the bar weight
    const adjustedTarget = Math.max(targetWeight, barWeight);
    return calculatePlates(adjustedTarget, barWeight, availablePlates);
  });
}

/**
 * Validates if a weight is achievable with available plates
 */
export function isWeightAchievable(
  targetWeight: number,
  barWeight: number = STANDARD_BAR_WEIGHT_LBS,
  availablePlates: number[] = STANDARD_PLATES_LBS
): boolean {
  try {
    const calc = calculatePlates(targetWeight, barWeight, availablePlates);
    return calc.difference === 0;
  } catch {
    return false;
  }
}
