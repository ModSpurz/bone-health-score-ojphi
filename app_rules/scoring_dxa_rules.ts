/**
 * Bone Health Score and DXA consideration: isolated rule functions.
 * Adapted from the archived deployed calculations.ts (Oct–Dec 2025).
 * The clinical rules are unchanged. Supabase access and message rendering are
 * intentionally omitted to permit safe independent review.
 *
 * Application category labels are interface outputs, not validated risk strata.
 * The DXA prompt reflects selected implemented criteria, not full TOPF eligibility.
 */

export type FractureHistory = {
  hip?: boolean;
  spine?: boolean;
  wrist_shoulder?: boolean;
  other?: boolean;
};

export type BoneHealthInputs = {
  input_age: number;
  input_gender: 'Female' | 'Male' | string;
  input_weight_kg: number;
  input_height_cm: number;
  input_fracture_history: FractureHistory;
  input_diseases?: Record<string, boolean>;
  input_treatment_status?: string;
  input_fall_history: 'none' | '1_to_3' | '4_or_more';
  input_parent_fracture: boolean;
  input_smoking: boolean;
  input_alcohol: boolean;
  input_steroids: boolean;
  input_caffeine: boolean;
  input_exercise: 'less_than_1' | '1_2_times' | '3_plus_times';
  input_calcium: 'daily' | '2_3_weekly' | 'less_often';
  input_vitamin_d: 'supplement' | 'sun_exposure' | 'indoor';
  input_balance_exercise: boolean;
  input_menopause_before_45: 'yes' | 'no' | 'not_applicable';
};

export function boneHealthScore(inputs: BoneHealthInputs): number {
  let score = 100;
  const bmi = inputs.input_weight_kg / Math.pow(inputs.input_height_cm / 100, 2);
  if (bmi < 18.5) score -= 5;

  if (inputs.input_fracture_history.hip || inputs.input_fracture_history.spine) score -= 20;
  if (inputs.input_fracture_history.wrist_shoulder) score -= 10;
  if (inputs.input_fracture_history.other) score -= 5;

  // Included in archived calculation code; these fields were not displayed
  // in the study-period questionnaire, so they were not user entered.
  const diseaseCount = Object.values(inputs.input_diseases || {}).filter(Boolean).length;
  score -= diseaseCount * 5;
  if (inputs.input_treatment_status === 'treated_regularly') score += 5;
  if (inputs.input_treatment_status === 'treated_irregularly') score -= 10;

  if (inputs.input_fall_history === '1_to_3') score -= 10;
  else if (inputs.input_fall_history === '4_or_more') score -= 15;

  if (inputs.input_smoking) score -= 10;
  if (inputs.input_alcohol) score -= 10;
  if (inputs.input_steroids) score -= 15;
  if (inputs.input_caffeine) score -= 5;

  if (inputs.input_exercise === '3_plus_times') score += 15;
  else if (inputs.input_exercise === '1_2_times') score += 5;
  else score -= 5;

  if (inputs.input_calcium === 'daily') score += 10;
  else if (inputs.input_calcium === 'less_often') score -= 10;

  if (inputs.input_vitamin_d === 'supplement') score += 10;
  else if (inputs.input_vitamin_d === 'sun_exposure') score += 5;
  else score -= 5;

  if (inputs.input_balance_exercise) score += 5;
  return score;
}

export function scoreCategory(score: number): 'excellent' | 'good' | 'needs improvement' | 'high risk' {
  if (score > 125) return 'excellent';
  if (score >= 95) return 'good';
  if (score >= 70) return 'needs improvement';
  return 'high risk';
}

export function dxaConsiderationPrompt(inputs: BoneHealthInputs): boolean {
  const age = inputs.input_age;
  const female = inputs.input_gender === 'Female';
  const male = inputs.input_gender === 'Male';
  if (age <= 50) return false;

  const sexAgeThreshold = (female && age >= 65) || (male && age >= 70);
  if (sexAgeThreshold) return true;
  const belowSexAgeThreshold = (female && age < 65) || (male && age < 70);
  if (!belowSexAgeThreshold) return false;
  const bmi = inputs.input_weight_kg / Math.pow(inputs.input_height_cm / 100, 2);

  return (
    (female && inputs.input_menopause_before_45 === 'yes') ||
    inputs.input_steroids ||
    inputs.input_parent_fracture ||
    bmi < 20 ||
    Boolean(inputs.input_fracture_history.hip) ||
    Boolean(inputs.input_fracture_history.spine) ||
    Boolean(inputs.input_fracture_history.wrist_shoulder) ||
    Boolean(inputs.input_fracture_history.other)
  );
}
