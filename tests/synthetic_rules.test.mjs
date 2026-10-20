/** Synthetic only: no study participants or patient records. */
import assert from 'node:assert/strict';
import { boneHealthScore, scoreCategory, dxaConsiderationPrompt } from '../app_rules/scoring_dxa_rules.ts';

function sample(overrides = {}) {
  return {
    input_age: 51,
    input_gender: 'Female',
    input_weight_kg: 55,
    input_height_cm: 160,
    input_fracture_history: {hip: false, spine: false, wrist_shoulder: false, other: false},
    input_diseases: {},
    input_treatment_status: 'not_diagnosed',
    input_fall_history: 'none',
    input_parent_fracture: false,
    input_smoking: false,
    input_alcohol: false,
    input_steroids: false,
    input_caffeine: false,
    input_exercise: '1_2_times',
    input_calcium: '2_3_weekly',
    input_vitamin_d: 'sun_exposure',
    input_balance_exercise: false,
    input_menopause_before_45: 'no',
    ...overrides,
  };
}

let checks = 0;
function equals(got, expected, meaning) {
  assert.equal(got, expected, meaning);
  checks += 1;
}

equals(boneHealthScore(sample()), 110, 'baseline scoring');
equals(boneHealthScore(sample({input_smoking: true})), 100, 'smoking weight');
equals(boneHealthScore(sample({input_exercise: '3_plus_times'})), 120, 'exercise weight');
equals(boneHealthScore(sample({input_weight_kg: 40})), 105, 'low-BMI weight');
equals(boneHealthScore(sample({input_fracture_history: {hip: true}})), 90, 'hip fracture weight');
equals(scoreCategory(69), 'high risk', 'score below 70');
equals(scoreCategory(70), 'needs improvement', 'score at 70');
equals(scoreCategory(94), 'needs improvement', 'score at 94');
equals(scoreCategory(95), 'good', 'score at 95');
equals(scoreCategory(125), 'good', 'score at 125');
equals(scoreCategory(126), 'excellent', 'score at 126');
equals(dxaConsiderationPrompt(sample({input_age: 50, input_steroids: true})), false, 'age gate at 50');
equals(dxaConsiderationPrompt(sample({input_age: 51, input_steroids: true})), true, 'steroids at 51');
equals(dxaConsiderationPrompt(sample({input_age: 64})), false, 'woman 64 without criteria');
equals(dxaConsiderationPrompt(sample({input_age: 65})), true, 'woman age 65');
equals(dxaConsiderationPrompt(sample({input_gender: 'Male', input_age: 69})), false, 'man age 69');
equals(dxaConsiderationPrompt(sample({input_gender: 'Male', input_age: 70})), true, 'man age 70');
equals(dxaConsiderationPrompt(sample({input_age: 51, input_menopause_before_45: 'yes'})), true, 'early menopause after 50');
equals(dxaConsiderationPrompt(sample({input_age: 50, input_menopause_before_45: 'yes'})), false, 'no deployed early menopause exception at 50');
equals(dxaConsiderationPrompt(sample({input_age: 51, input_weight_kg: 40})), true, 'BMI under 20');
equals(dxaConsiderationPrompt(sample({input_age: 51, input_fracture_history: {hip: true}})), true, 'reported low trauma fracture');
equals(dxaConsiderationPrompt(sample({input_age: 70, input_gender: ''})), false, 'unrecorded sex');

console.log(`Synthetic scoring/DXA checks passed: ${checks}/${checks}`);
