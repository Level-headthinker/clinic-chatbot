export const PLANS = {
  starter: {
    label: "Starter",
    color: "#6b7280",
    features: {
      analytics: false,
      multi_branch: false,
      voice_agent: false,
    },
  },
  growth: {
    label: "Growth",
    color: "#2563eb",
    features: {
      analytics: true,
      multi_branch: true,
      voice_agent: false,
    },
  },
  enterprise: {
    label: "Enterprise",
    color: "#7c3aed",
    features: {
      analytics: true,
      multi_branch: true,
      voice_agent: true,
    },
  },
};

export const UPGRADE_MESSAGE = {
  analytics: { need: "Growth", reason: "Unlock analytics to track your clinic's performance." },
  multi_branch: { need: "Growth", reason: "Manage multiple branches from one account." },
  voice_agent: { need: "Enterprise", reason: "AI voice agent to handle patient calls automatically." },
};
