/**
 * The six scenarios documented in docs/API_HANDOFF.md.
 * The backend has no scenario-list endpoint, so ids are taken from the
 * documented contract; labels here are UI copy only.
 */
export interface ScenarioInfo {
  id: string;
  title: string;
  description: string;
}

export const SCENARIOS: ScenarioInfo[] = [
  {
    id: "safe-normal-payment-001",
    title: "Routine vendor bill",
    description: "An unmodified, real-derived bill payment that should pass every check.",
  },
  {
    id: "semantic-duplicate-001",
    title: "Possible duplicate bill",
    description: "A second payment attempt that semantically matches an already-paid obligation.",
  },
  {
    id: "destination-change-001",
    title: "Vendor bank change",
    description: "The payment destination differs from previously verified beneficiaries.",
  },
  {
    id: "missing-context-001",
    title: "Unexplained cash movement",
    description: "An add-transaction proposal missing the facts needed to classify it.",
  },
  {
    id: "goal-mismatch-001",
    title: "Goal contradicts the proposal",
    description: "The agent's instruction says not to pay suppliers, yet it proposes a payment.",
  },
  {
    id: "high-amount-plausible-001",
    title: "Large but approved order",
    description: "A $50,000 payment that is plausible on paper but far outside the vendor's history.",
  },
];

/** Safe fallback while the health request is still loading. */
export const DEMO_PROVIDERS = ["rules", "gemini", "system_one", "openjev"] as const;
