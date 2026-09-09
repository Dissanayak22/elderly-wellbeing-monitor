import { describe, expect, it } from "vitest";
import { attentionBadgeClass, countActionableAttention, formatAttention } from "../src/utils/labels";

describe("attention labels", () => {
  it("formats caregiver attention indicators", () => {
    expect(formatAttention("normal_observation")).toBe("Normal observation");
    expect(formatAttention("attention_recommended")).toBe("Attention recommended");
  });

  it("maps badge classes", () => {
    expect(attentionBadgeClass("caregiver_check_recommended")).toContain("badge-alert");
  });

  it("counts only actionable attention indicators", () => {
    expect(
      countActionableAttention({
        normal_observation: 20,
        attention_recommended: 3,
        caregiver_check_recommended: 2,
      })
    ).toBe(5);
  });
});
