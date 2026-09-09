export function formatAttention(code) {
  const map = {
    normal_observation: "Normal observation",
    attention_recommended: "Attention recommended",
    caregiver_check_recommended: "Caregiver check recommended",
  };
  return map[code] || code;
}

export function attentionBadgeClass(code) {
  if (code === "caregiver_check_recommended") return "badge badge-alert";
  if (code === "attention_recommended") return "badge badge-warn";
  return "badge badge-ok";
}

export function countActionableAttention(counts = {}) {
  return (counts.attention_recommended || 0) + (counts.caregiver_check_recommended || 0);
}
