/**
 * @deprecated Import from '@/shared/providers/FeaturesProvider' instead
 * This file re-exports for backwards compatibility
 */
export {
  useFeatures,
  type Features,
  type FeatureKey,
} from "../providers/FeaturesProvider";
export { clearFeaturesCache } from "../providers/FeaturesProvider";

// Re-export default for backwards compatibility
export { useFeatures as default } from "../providers/FeaturesProvider";
