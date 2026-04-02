import { useMemo } from "react";
import { ShowcaseHeader } from "../shared/components/showcase/ShowcaseHeader";
import { ShowcaseComponentCard } from "../shared/components/showcase/ShowcaseComponentCard";
import { showcaseComponents } from "../shared/data/showcaseComponents";
import { useFeatures } from "../shared/providers/FeaturesProvider";

export function ComponentShowcasePage() {
  const { isFeatureEnabled } = useFeatures();

  const filteredComponents = useMemo(() => {
    return showcaseComponents.filter((component) => {
      if (!component.requiresFeature) return true;
      return isFeatureEnabled(component.requiresFeature);
    });
  }, [isFeatureEnabled]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white">
      <ShowcaseHeader />

      <div className="max-w-7xl mx-auto px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-8">
          {filteredComponents.map((component, index) => (
            <ShowcaseComponentCard
              key={component.id}
              {...component}
              index={index}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default ComponentShowcasePage;
