import { useAuth } from "../context/AuthContext";
import { PLANS } from "../config/plans";

export function usePlan() {
  const { user } = useAuth();
  const plan = user?.plan || "starter";
  const planConfig = PLANS[plan] || PLANS.starter;

  const can = (feature) => !!planConfig.features[feature];

  return { plan, planConfig, can };
}
