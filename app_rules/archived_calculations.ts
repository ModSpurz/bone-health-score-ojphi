import { UserInputs, Recommendation, CalculationResult, ScoreHistoryItem, TopfRecommendation } from '../types';
import { supabase } from './supabase';

export async function calculateBoneHealthScore(
  inputs: UserInputs,
  scoreHistory: ScoreHistoryItem[]
): Promise<CalculationResult> {
  let total_score = 100;
  const recommendations_list: Recommendation[] = [];

  const height_m = inputs.input_height_cm / 100;
  const bmi = inputs.input_weight_kg / (height_m * height_m);

  if (bmi < 18.5) {
    total_score -= 5;
    recommendations_list.push({
      points_lost: -5,
      text: 'ดัชนีมวลกาย (BMI) ของคุณต่ำกว่าเกณฑ์มาตรฐาน การรักษาน้ำหนักให้อยู่ในเกณฑ์ที่เหมาะสมมีความสำคัญต่อสุขภาพกระดูก'
    });
  }

  if (inputs.input_fracture_history.hip || inputs.input_fracture_history.spine) {
    total_score -= 20;
  }
  if (inputs.input_fracture_history.wrist_shoulder) {
    total_score -= 10;
  }
  if (inputs.input_fracture_history.other) {
    total_score -= 5;
  }

  const diseases = inputs.input_diseases;
  const diseaseCount = Object.values(diseases).filter(Boolean).length;
  if (diseaseCount > 0) {
      total_score -= diseaseCount * 5;
      recommendations_list.push({
        points_lost: -(diseaseCount * 5),
        text: `โรคประจำตัวที่คุณมี (${diseaseCount} โรค) เป็นปัจจัยเสี่ยงต่อสุขภาพกระดูก ควรปรึกษาแพทย์เพื่อดูแลอย่างใกล้ชิด`
      });
  }

  if (inputs.input_fall_history === '1_to_3') {
    total_score -= 10;
     recommendations_list.push({
      points_lost: -10,
      text: 'ประวัติการหกล้ม 1-3 ครั้งในปีที่ผ่านมาเป็นสัญญาณเตือนสำคัญ ควรฝึกการทรงตัวและจัดสภาพแวดล้อมในบ้านให้ปลอดภัย'
    });
  } else if (inputs.input_fall_history === '4_or_more') {
    total_score -= 15;
     recommendations_list.push({
      points_lost: -15,
      text: 'การล้มบ่อย (4 ครั้งขึ้นไป) เพิ่มความเสี่ยงกระดูกหักอย่างมีนัยสำคัญ ควรปรึกษาแพทย์เพื่อหาสาเหตุและป้องกัน'
    });
  }

  if (inputs.input_smoking) {
      total_score -= 10;
      recommendations_list.push({
          points_lost: -10,
          text: 'การสูบบุหรี่เป็นปัจจัยเสี่ยงสำคัญของการสูญเสียมวลกระดูก การเลิกสูบบุหรี่เป็นสิ่งที่ดีที่สุดที่คุณสามารถทำเพื่อกระดูกของคุณ'
      });
  }
  if (inputs.input_alcohol) {
      total_score -= 10;
      recommendations_list.push({
          points_lost: -10,
          text: 'การดื่มแอลกอฮอล์มากเกินไปรบกวนการดูดซึมแคลเซียมของร่างกาย พิจารณาลดปริมาณการดื่ม'
      });
  }
  if (inputs.input_steroids) {
      total_score -= 15;
      recommendations_list.push({
          points_lost: -15,
          text: 'การใช้สเตียรอยด์ระยะยาวเป็นปัจจัยเสี่ยงที่รุนแรงมากต่อโรคกระดูกพรุน โปรดปรึกษากับแพทย์ของคุณ'
      });
  }
  if (inputs.input_caffeine) {
      total_score -= 5;
      recommendations_list.push({
          points_lost: -5,
          text: 'การบริโภคคาเฟอีนสูงสามารถลดการดูดซึมแคลเซียมเล็กน้อย ตรวจสอบให้แน่ใจว่าได้รับแคลเซียมเพียงพอหรือพิจารณาลดคาเฟอีน'
      });
  }

  if (inputs.input_treatment_status === 'treated_regularly') {
      total_score += 5;
  } else if (inputs.input_treatment_status === 'treated_irregularly') {
      total_score -= 10;
      recommendations_list.push({
          points_lost: -10,
          text: 'คุณได้รับการวินิจฉัยแล้ว แต่ยังไม่ได้รับการรักษาอย่างสม่ำเสมอ โปรดปรึกษาแพทย์เพื่อจัดการปัจจัยเสี่ยงที่สำคัญนี้'
      });
  }

  if (inputs.input_exercise === '3_plus_times') {
      total_score += 15;
  } else if (inputs.input_exercise === '1_2_times') {
      total_score += 5;
  } else {
      total_score -= 5;
      recommendations_list.push({
          points_lost: -5,
          text: 'การออกกำลังกายแบบลงน้ำหนัก (เช่น เดิน วิ่ง หรือเต้นรำ) มีความสำคัญต่อการสร้างและรักษามวลกระดูก ตั้งเป้าอย่างน้อย 1-2 ครั้งต่อสัปดาห์'
      });
  }

  if (inputs.input_calcium === 'daily') {
      total_score += 10;
  } else if (inputs.input_calcium === 'less_often') {
      total_score -= 10;
      recommendations_list.push({
          points_lost: -10,
          text: 'แคลเซียมเป็นส่วนประกอบหลักของกระดูก รับประทานผลิตภัณฑ์นม ผักใบเขียว หรืออาหารเสริมแคลเซียมทุกวัน'
      });
  }

  if (inputs.input_vitamin_d === 'supplement') {
      total_score += 10;
  } else if (inputs.input_vitamin_d === 'sun_exposure') {
      total_score += 5;
  } else {
      total_score -= 5;
      recommendations_list.push({
          points_lost: -5,
          text: 'วิตามินดีมีความจำเป็นสำหรับการดูดซึมแคลเซียม หากคุณได้รับแสงแดดน้อย พิจารณาเสริมวิตามินดี'
      });
  }

  if (inputs.input_balance_exercise) {
      total_score += 5;
  }

  // --- TOPF Logic ---
  let meets_topf_criteria = false;
  if (inputs.input_age > 50) {
      if (
        (inputs.input_gender === 'Female' && inputs.input_age >= 65) ||
        (inputs.input_gender === 'Male' && inputs.input_age >= 70) ||
        (inputs.input_gender === 'Female' && inputs.input_menopause_before_45 === 'yes')
      ) {
        meets_topf_criteria = true;
      }

      const meetsAgeCriteria =
        (inputs.input_gender === 'Female' && inputs.input_age < 65) ||
        (inputs.input_gender === 'Male' && inputs.input_age < 70);

      if (meetsAgeCriteria) {
        if (
          inputs.input_steroids ||
          inputs.input_parent_fracture ||
          bmi < 20 ||
          inputs.input_fracture_history.hip ||
          inputs.input_fracture_history.spine ||
          inputs.input_fracture_history.wrist_shoulder ||
          inputs.input_fracture_history.other
        ) {
          meets_topf_criteria = true;
        }
      }
  }

  const topf_recommendation: TopfRecommendation = {
    meets_criteria: meets_topf_criteria,
    text: meets_topf_criteria
      ? "จากข้อมูลของคุณ ท่านมีข้อบ่งชี้ที่ควรเข้ารับการตรวจวัดความหนาแน่นของกระดูก (DEXA Scan) ตามคำแนะนำของมูลนิธิโรคกระดูกพรุนแห่งประเทศไทย (TOPF) ขอแนะนำให้ปรึกษาแพทย์เพื่อพิจารณาเพิ่มเติม"
      : "จากข้อมูลของคุณ ปัจจุบันยังไม่มีข้อบ่งชี้ที่จำเป็นต้องเข้ารับการตรวจวัดความหนาแน่นของกระดูก (DEXA Scan) ตามคำแนะนำของ TOPF ขอแนะนำให้ท่านดูแลสุขภาพกระดูกและประเมินพฤติกรรมอย่างสม่ำเสมอ",
  };
  // --- END TOPF Logic ---

  const final_score = total_score;

  // --- PRE-CALCULATE PERCENTILE AND LEVEL ---
  let percentile = 50;
  let total_users = 1;
  try {
    const { count: totalCount } = await supabase
      .from('scores')
      .select('*', { count: 'exact', head: true });

    const { count: lowerCount } = await supabase
      .from('scores')
      .select('*', { count: 'exact', head: true })
      .lt('final_score', final_score);

    if (totalCount && totalCount > 0) {
      total_users = totalCount;
      if (lowerCount !== null) {
        percentile = Math.round((lowerCount / totalCount) * 100);
      }
    } else {
        total_users = 1;
        percentile = 100;
    }
  } catch (err) {
    console.error('Error calculating percentile:', err);
  }

  let level_text = '';
  let level_color = '';
  if (final_score > 125) { level_text = 'ดีเยี่ยม'; level_color = '#166534'; }
  else if (final_score >= 95) { level_text = 'ดี'; level_color = '#22C55E'; }
  else if (final_score >= 70) { level_text = 'ควรปรับปรุง'; level_color = '#F97316'; }
  else { level_text = 'เสี่ยงสูง'; level_color = '#DC2626'; }

  recommendations_list.sort((a, b) => a.points_lost - b.points_lost);
  const top_recommendations = recommendations_list.slice(0, 3);

  // --- SINGLE INSERT OPERATION ---
  let scoreId = null;
  try {
    const { data, error } = await supabase.from('scores').insert({
      nickname: inputs.nickname,
      final_score,
      // Add all calculated fields here
      percentile,
      total_users,
      level_text,
      level_color,
      // Original input fields
      input_age: inputs.input_age,
      input_gender: inputs.input_gender,
      input_parent_fracture: inputs.input_parent_fracture,
      input_weight_kg: inputs.input_weight_kg,
      input_height_cm: inputs.input_height_cm,
      input_fracture_history: inputs.input_fracture_history,
      input_diseases: inputs.input_diseases,
      input_treatment_status: inputs.input_treatment_status,
      input_fall_history: inputs.input_fall_history,
      input_smoking: inputs.input_smoking,
      input_alcohol: inputs.input_alcohol,
      input_steroids: inputs.input_steroids,
      input_exercise: inputs.input_exercise,
      input_calcium: inputs.input_calcium,
      input_vitamin_d: inputs.input_vitamin_d,
      input_caffeine: inputs.input_caffeine,
      input_balance_exercise: inputs.input_balance_exercise,
      input_menopause_before_45: inputs.input_menopause_before_45
    }).select('id').single();

    if (error) throw error;
    if (data) scoreId = data.id;

  } catch (err) {
    console.error('Error saving to database:', err);
  }

  // The separate update call is now removed.

  return {
    scoreId,
    final_score,
    percentile,
    total_users,
    level_text,
    level_color,
    recommendations: top_recommendations,
    topf_recommendation,
    score_history: scoreHistory,
  };
}
