import { PolicyEngine, evaluateRisk, canExecuteImmediately } from "../src/core/policy-engine";
import { RiskLevel } from "../src/types/core";

describe("PolicyEngine", () => {
  const engine = new PolicyEngine();

  describe("R0_READ_ONLY", () => {
    const risk: RiskLevel = "R0_READ_ONLY";

    it("should allow without approval", () => {
      const decision = engine.evaluate(risk);
      expect(decision.allowed).toBe(true);
      expect(decision.requiresApproval).toBe(false);
    });

    it("should auto-execute", () => {
      expect(engine.canAutoExecute(risk)).toBe(true);
    });
  });

  describe("R3_FINANCIAL_IMPACT", () => {
    const risk: RiskLevel = "R3_FINANCIAL_IMPACT";

    it("should allow with approval", () => {
      const decision = engine.evaluate(risk);
      expect(decision.allowed).toBe(true);
      expect(decision.requiresApproval).toBe(true);
    });

    it("should not auto-execute", () => {
      expect(engine.canAutoExecute(risk)).toBe(false);
    });
  });

  describe("R4_DESTRUCTIVE", () => {
    const risk: RiskLevel = "R4_DESTRUCTIVE";

    it("should require double approval", () => {
      expect(engine.requiresDoubleApproval(risk)).toBe(true);
    });
  });

  describe("evaluateRisk helper", () => {
    it("should return policy decision", () => {
      const decision = evaluateRisk("R1_SAFE_WRITE");
      expect(decision.allowed).toBe(true);
      expect(decision.riskLevel).toBe("R1_SAFE_WRITE");
    });
  });

  describe("canExecuteImmediately helper", () => {
    it("should return true for R0", () => {
      expect(canExecuteImmediately("R0_READ_ONLY")).toBe(true);
    });

    it("should return false for R3", () => {
      expect(canExecuteImmediately("R3_FINANCIAL_IMPACT")).toBe(false);
    });
  });
});
