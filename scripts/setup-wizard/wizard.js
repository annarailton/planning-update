/**
 * Setup Wizard - Accordion-based UI
 * Fill sections in any order, complete when ready
 */

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// State
const state = {
  prereqs: null,
  repo: { owner: "", name: "", url: "" },
  appName: "",
  appId: "", // Generated unique ID for Redis namespace (e.g., "invoicing-x7k2")
  gcpProject: "development-403721",
  gcpRegion: "asia-southeast1",
  tfstateBucket: "singapore-terraform-state", // Default for Singapore
  gcpValidated: false,
  serviceAccountJson: "",
  serviceAccountMethod: "existing",
  serviceAccountName: "",
  serviceAccountEmail: "",
  databaseUrlProd: "",
  databaseUrlStaging: "",
  neonApiKey: "",
  neonProjectId: "",
  clerkSecret: "",
  clerkPublishable: "",
  openaiKey: "",
  anthropicKey: "",
  geminiKey: "",
  langfusePublicKey: "",
  langfuseSecretKey: "",
  langfuseHost: "https://cloud.langfuse.com", // Default to EU
  temporalApiKey: "",
  temporalRegion: "aws-ap-southeast-1",
  // Feature flags (categorized)
  features: {
    app: {
      name: "",
      id: "",
    },
    infrastructure: {
      redis: false,
      worker: false,
      temporal: false,
    },
    llm: {
      openai: true,
      anthropic: false,
      gemini: false,
    },
    integrations: {
      langfuse: false,
    },
  },
  featuresReviewed: false, // Tracks if user has reviewed features section
};

// Section completion rules
const sectionRules = {
  prereqs: () => state.prereqs?.allRequired && state.prereqs?.gcloudAuth,
  repo: () => state.repo.owner && state.repo.name && state.appName,
  features: () =>
    state.featuresReviewed &&
    (state.features.llm.openai ||
      state.features.llm.anthropic ||
      state.features.llm.gemini), // Reviewed + at least one LLM
  gcp: () => state.gcpProject && state.tfstateBucket && state.gcpValidated,
  serviceaccount: () => isValidServiceAccountJson(state.serviceAccountJson),
  database: () => state.databaseUrlProd && state.neonApiKey,
  auth: () => state.clerkSecret && state.clerkPublishable,
  ai: () => state.openaiKey || state.anthropicKey || state.geminiKey, // At least one LLM provider
  langfuse: () =>
    !state.features?.integrations?.langfuse ||
    (state.langfusePublicKey && state.langfuseSecretKey), // Complete if disabled OR configured
  temporal: () =>
    !state.features?.infrastructure?.temporal || state.temporalApiKey, // Complete if disabled OR configured
};

function isValidServiceAccountJson(json) {
  if (!json) return false;
  try {
    const parsed = JSON.parse(json);
    return (
      parsed.type === "service_account" &&
      parsed.private_key &&
      parsed.client_email
    );
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// API Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function api(endpoint, options = {}) {
  const res = await fetch(`/api${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return res.json();
}

/**
 * Generate a unique app ID from the app name
 * Format: {sanitized-name}-{4-char-suffix}
 * Example: invoicing-x7k2
 */
async function generateAppId(appName) {
  if (!appName) return;

  try {
    const data = await api("/generate-app-id", {
      method: "POST",
      body: { appName },
    });

    if (data.success) {
      state.appId = data.appId;
      state.features.app.name = data.name;
      state.features.app.id = data.appId;
      console.log(`Generated app ID: ${data.appId}`);
    }
  } catch (e) {
    console.error("Failed to generate app ID:", e);
  }
}

/**
 * Update the app ID display in the UI
 */
function updateAppIdDisplay() {
  const display = document.getElementById("app-id-display");
  const container = document.getElementById("app-id-container");
  if (display && state.appId) {
    display.textContent = state.appId;
    container?.classList.remove("hidden");
  } else if (container) {
    container.classList.add("hidden");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Accordion UI
// ─────────────────────────────────────────────────────────────────────────────

function toggleAccordion(section) {
  const item = document.querySelector(`[data-section="${section}"]`);
  if (!item) return;

  const wasExpanded = item.classList.contains("expanded");

  // Close all
  document.querySelectorAll(".accordion-item").forEach((el) => {
    el.classList.remove("expanded");
  });

  // Toggle clicked
  if (!wasExpanded) {
    item.classList.add("expanded");
  }

  // Save data when closing
  if (wasExpanded) {
    saveField(section);
    // Mark features as reviewed when closing the section
    if (section === "features") {
      state.featuresReviewed = true;
      updateSectionStatus("features");
      saveState();
    }
  }
}

function updateSectionStatus(section) {
  const item = document.querySelector(`[data-section="${section}"]`);
  if (!item) return;

  const isComplete = sectionRules[section]();
  item.classList.toggle("complete", isComplete);

  const status = item.querySelector(".accordion-status");
  if (status) {
    if (isComplete) {
      status.innerHTML = "✓";
    } else {
      // Get index among visible sections only
      const visibleSections = Array.from(
        document.querySelectorAll(".accordion-item:not(.hidden)"),
      );
      const index = visibleSections.indexOf(item);
      status.innerHTML = index >= 0 ? index + 1 : "";
    }
  }

  updateFooterStatus();
}

function updateFooterStatus() {
  // Only count visible sections
  const visibleSections = Array.from(
    document.querySelectorAll(".accordion-item:not(.hidden)"),
  )
    .map((el) => el.dataset.section)
    .filter((s) => s && sectionRules[s]);

  const complete = visibleSections.filter((s) => sectionRules[s]()).length;
  const total = visibleSections.length;

  const status = document.getElementById("footer-status");
  const btn = document.getElementById("complete-btn");

  if (complete === total) {
    status.textContent = "All sections complete! Ready to set up.";
    status.style.color = "var(--success)";
    btn.disabled = false;
  } else {
    status.textContent = `${complete}/${total} sections complete`;
    status.style.color = "var(--text-muted)";
    btn.disabled = false; // Allow partial setup
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Data Handling
// ─────────────────────────────────────────────────────────────────────────────

async function saveField(section) {
  switch (section) {
    case "repo":
      const repoUrl = document.getElementById("repo-url").value;
      const match = repoUrl.match(/github\.com[\/:](.+?)\/(.+?)(?:\.git)?$/);
      if (match) {
        state.repo.owner = match[1];
        state.repo.name = match[2].replace(".git", "");
        state.repo.url = repoUrl;
      }
      const newAppName = document.getElementById("app-name").value;

      // Generate app ID only once (never regenerate - it's used as Redis key prefix)
      if (newAppName && !state.appId) {
        await generateAppId(newAppName);
      }
      state.appName = newAppName;
      updateSaEmailPreview();
      updateAppIdDisplay();
      break;
    case "gcp":
      state.gcpProject = document.getElementById("gcp-project").value;
      state.gcpRegion = document.getElementById("gcp-region").value;
      state.tfstateBucket = document.getElementById("tfstate-bucket").value;
      updateSaEmailPreview();
      break;
    case "serviceaccount":
      state.serviceAccountMethod = document.getElementById("sa-method").value;
      state.serviceAccountName =
        document.getElementById("sa-name")?.value || "";
      state.serviceAccountEmail =
        document.getElementById("sa-email")?.value || "";
      const jsonEl = document.getElementById("sa-key-json");
      if (jsonEl && jsonEl.value) {
        state.serviceAccountJson = jsonEl.value.trim();
        validateServiceAccountJson();
      }
      break;
    case "database":
      state.databaseUrlProd = cleanDatabaseUrl(
        document.getElementById("db-url-prod").value,
      );
      state.databaseUrlStaging = cleanDatabaseUrl(
        document.getElementById("db-url-staging").value,
      );
      state.neonApiKey = document.getElementById("neon-api-key").value;
      state.neonProjectId = document.getElementById("neon-project-id").value;
      break;
    case "auth":
      state.clerkSecret = document.getElementById("clerk-secret").value;
      state.clerkPublishable =
        document.getElementById("clerk-publishable").value;
      break;
    case "ai":
      state.openaiKey = document.getElementById("openai-key").value;
      state.anthropicKey = document.getElementById("anthropic-key").value;
      state.geminiKey = document.getElementById("gemini-key").value;
      break;
    case "langfuse":
      state.langfusePublicKey = document.getElementById(
        "langfuse-public-key",
      ).value;
      state.langfuseSecretKey = document.getElementById(
        "langfuse-secret-key",
      ).value;
      state.langfuseHost = document.getElementById("langfuse-host").value;
      break;
    case "temporal":
      state.temporalApiKey = document.getElementById("temporal-api-key").value;
      state.temporalRegion = document.getElementById("temporal-region").value;
      break;
  }

  updateSectionStatus(section);
  sessionStorage.setItem("setupWizardState", JSON.stringify(state));
}

function loadSavedState() {
  const saved = sessionStorage.getItem("setupWizardState");
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      Object.assign(state, parsed);
      // Ensure features.app is synced with top-level appId
      if (state.appId && state.features?.app) {
        state.features.app.id = state.appId;
      }
    } catch (e) {
      console.error("Failed to load saved state:", e);
    }
  }
}

function restoreFormValues() {
  // Repo
  if (state.repo.url)
    document.getElementById("repo-url").value = state.repo.url;
  if (state.appName) document.getElementById("app-name").value = state.appName;
  if (state.appId) updateAppIdDisplay();

  // GCP
  if (state.gcpProject)
    document.getElementById("gcp-project").value = state.gcpProject;
  if (state.gcpRegion)
    document.getElementById("gcp-region").value = state.gcpRegion;
  // Set tfstate bucket from state or auto-fill from region
  if (state.tfstateBucket) {
    document.getElementById("tfstate-bucket").value = state.tfstateBucket;
  } else {
    updateTfstateBucket();
  }

  // Service Account
  if (state.serviceAccountMethod)
    document.getElementById("sa-method").value = state.serviceAccountMethod;
  if (state.serviceAccountJson)
    document.getElementById("sa-key-json").value = state.serviceAccountJson;
  if (state.serviceAccountName) {
    const nameEl = document.getElementById("sa-name");
    if (nameEl) nameEl.value = state.serviceAccountName;
  }
  if (state.serviceAccountEmail) {
    const emailEl = document.getElementById("sa-email");
    if (emailEl) emailEl.value = state.serviceAccountEmail;
  }
  updateSaMethod();
  updateSaEmailPreview();

  // Database
  if (state.databaseUrlProd)
    document.getElementById("db-url-prod").value = state.databaseUrlProd;
  if (state.databaseUrlStaging)
    document.getElementById("db-url-staging").value = state.databaseUrlStaging;
  if (state.neonApiKey)
    document.getElementById("neon-api-key").value = state.neonApiKey;
  if (state.neonProjectId)
    document.getElementById("neon-project-id").value = state.neonProjectId;

  // Auth
  if (state.clerkSecret)
    document.getElementById("clerk-secret").value = state.clerkSecret;
  if (state.clerkPublishable)
    document.getElementById("clerk-publishable").value = state.clerkPublishable;

  // AI
  if (state.openaiKey)
    document.getElementById("openai-key").value = state.openaiKey;
  if (state.anthropicKey)
    document.getElementById("anthropic-key").value = state.anthropicKey;
  if (state.geminiKey)
    document.getElementById("gemini-key").value = state.geminiKey;

  // Langfuse
  if (state.langfusePublicKey)
    document.getElementById("langfuse-public-key").value =
      state.langfusePublicKey;
  if (state.langfuseSecretKey)
    document.getElementById("langfuse-secret-key").value =
      state.langfuseSecretKey;
  if (state.langfuseHost)
    document.getElementById("langfuse-host").value = state.langfuseHost;

  // Temporal
  if (state.temporalApiKey)
    document.getElementById("temporal-api-key").value = state.temporalApiKey;
  if (state.temporalRegion)
    document.getElementById("temporal-region").value = state.temporalRegion;
}

function cleanDatabaseUrl(url) {
  if (!url) return "";
  url = url.replace(/^['"]|['"]$/g, "");
  url = url.replace(/^psql\s+['"]?/, "").replace(/['"]$/, "");
  if (url.startsWith("postgresql://")) {
    url = url.replace("postgresql://", "postgresql+asyncpg://");
  }
  url = url.replace(/[&?]channel_binding=require/, "");
  return url;
}

function resetWizard() {
  if (confirm("Clear all saved data and start fresh?")) {
    sessionStorage.removeItem("setupWizardState");
    location.reload();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Features
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Feature dependencies configuration.
 * Key: feature path (e.g., 'infrastructure.worker')
 * Value: array of feature paths that must be enabled for this feature
 */
const FEATURE_DEPS = {
  "infrastructure.worker": ["infrastructure.redis"],
  "infrastructure.temporal": ["infrastructure.worker"], // worker → redis is resolved recursively
  // Add future dependencies here, e.g.:
  // 'integrations.livekit': ['infrastructure.redis'],
};

/**
 * Get a feature value by dot-notation path
 */
function getFeatureValue(path) {
  const parts = path.split(".");
  let value = state.features;
  for (const part of parts) {
    value = value?.[part];
  }
  return value;
}

/**
 * Set a feature value by dot-notation path
 */
function setFeatureValue(path, value) {
  const parts = path.split(".");
  let obj = state.features;
  for (let i = 0; i < parts.length - 1; i++) {
    obj = obj[parts[i]];
  }
  obj[parts[parts.length - 1]] = value;
}

/**
 * Get the UI element ID for a feature path
 */
function getFeatureElementId(path) {
  const parts = path.split(".");
  if (parts[0] === "llm") {
    return `feature-llm-${parts[1]}`;
  }
  return `feature-${parts[parts.length - 1]}`;
}

/**
 * Update UI checkbox for a feature
 */
function updateFeatureUI(path, checked) {
  const el = document.getElementById(getFeatureElementId(path));
  if (el) el.checked = checked;
}

/**
 * Get all features that depend on the given feature
 */
function getDependents(featurePath) {
  return Object.entries(FEATURE_DEPS)
    .filter(([_, deps]) => deps.includes(featurePath))
    .map(([feature]) => feature);
}

/**
 * Resolve feature dependencies.
 * When enabling: auto-enable all dependencies
 * When disabling: auto-disable all dependents
 * Returns array of all affected feature paths
 * @param {string} featurePath - The feature being toggled
 * @param {boolean} enabling - Whether enabling or disabling
 * @param {Set} visited - Track visited nodes to prevent infinite loops
 */
function resolveDependencies(featurePath, enabling, visited = new Set()) {
  // Prevent circular dependency infinite loops
  if (visited.has(featurePath)) {
    console.warn(`Circular dependency detected: ${featurePath}`);
    return [];
  }
  visited.add(featurePath);

  const affected = [featurePath];

  if (enabling) {
    // Enable all dependencies recursively
    const deps = FEATURE_DEPS[featurePath] || [];
    for (const dep of deps) {
      if (!getFeatureValue(dep)) {
        setFeatureValue(dep, true);
        updateFeatureUI(dep, true);
        affected.push(dep);
        // Recursively enable dependencies of dependencies
        affected.push(...resolveDependencies(dep, true, visited).slice(1));
      }
    }
  } else {
    // Disable all dependents recursively
    const dependents = getDependents(featurePath);
    for (const dependent of dependents) {
      if (getFeatureValue(dependent)) {
        setFeatureValue(dependent, false);
        updateFeatureUI(dependent, false);
        affected.push(dependent);
        // Recursively disable dependents of dependents
        affected.push(
          ...resolveDependencies(dependent, false, visited).slice(1),
        );
      }
    }
  }

  return affected;
}

function updateFeature(feature) {
  const path = feature.split(".");

  // Mark features as reviewed when user interacts
  state.featuresReviewed = true;

  if (path[0] === "llm") {
    // Handle LLM provider checkboxes (no dependencies)
    state.features.llm[path[1]] = document.getElementById(
      `feature-llm-${path[1]}`,
    ).checked;
    validateLlmProviders();
    updateAiSectionVisibility();
  } else {
    // Handle infrastructure and integration toggles with dependency resolution
    const checked = document.getElementById(
      getFeatureElementId(feature),
    ).checked;
    setFeatureValue(feature, checked);

    // Resolve dependencies
    resolveDependencies(feature, checked);

    // Update all section visibilities
    updateAllSectionVisibilities();
  }

  updateSectionStatus("features");
  saveState();
}

function validateLlmProviders() {
  const hasLlm =
    state.features.llm.openai ||
    state.features.llm.anthropic ||
    state.features.llm.gemini;

  const warning = document.getElementById("llm-warning");
  if (warning) {
    warning.classList.toggle("hidden", hasLlm);
  }
}

function updateTemporalSectionVisibility() {
  const section = document.querySelector('[data-section="temporal"]');
  if (section) {
    section.classList.toggle("hidden", !state.features.infrastructure.temporal);
  }
}

function updateLangfuseSectionVisibility() {
  const section = document.querySelector('[data-section="langfuse"]');
  if (section) {
    section.classList.toggle("hidden", !state.features.integrations.langfuse);
  }
}

function updateAiSectionVisibility() {
  const openaiGroup = document.getElementById("ai-openai-group");
  const anthropicGroup = document.getElementById("ai-anthropic-group");
  const geminiGroup = document.getElementById("ai-gemini-group");
  const noProvidersWarning = document.getElementById("ai-no-providers");

  if (openaiGroup)
    openaiGroup.classList.toggle("hidden", !state.features.llm.openai);
  if (anthropicGroup)
    anthropicGroup.classList.toggle("hidden", !state.features.llm.anthropic);
  if (geminiGroup)
    geminiGroup.classList.toggle("hidden", !state.features.llm.gemini);

  // Show warning if no providers enabled
  const hasAnyProvider =
    state.features.llm.openai ||
    state.features.llm.anthropic ||
    state.features.llm.gemini;
  if (noProvidersWarning)
    noProvidersWarning.classList.toggle("hidden", hasAnyProvider);
}

function updateAllSectionVisibilities() {
  updateTemporalSectionVisibility();
  updateLangfuseSectionVisibility();
  updateAiSectionVisibility();
  updateSectionNumbers();
}

function updateSectionNumbers() {
  // Re-number visible sections
  const visibleSections = document.querySelectorAll(
    ".accordion-item:not(.hidden)",
  );
  visibleSections.forEach((section, index) => {
    const status = section.querySelector(".accordion-status");
    if (status && !section.classList.contains("complete")) {
      status.innerHTML = index + 1;
    }
  });
}

function restoreFeatureToggles() {
  // Infrastructure toggles
  const redisEl = document.getElementById("feature-redis");
  const workerEl = document.getElementById("feature-worker");
  const temporalEl = document.getElementById("feature-temporal");

  if (redisEl) redisEl.checked = state.features.infrastructure.redis;
  if (workerEl) workerEl.checked = state.features.infrastructure.worker;
  if (temporalEl) temporalEl.checked = state.features.infrastructure.temporal;

  // LLM provider checkboxes
  const openaiEl = document.getElementById("feature-llm-openai");
  const anthropicEl = document.getElementById("feature-llm-anthropic");
  const geminiEl = document.getElementById("feature-llm-gemini");

  if (openaiEl) openaiEl.checked = state.features.llm.openai;
  if (anthropicEl) anthropicEl.checked = state.features.llm.anthropic;
  if (geminiEl) geminiEl.checked = state.features.llm.gemini;

  // Integration toggles
  const langfuseEl = document.getElementById("feature-langfuse");
  if (langfuseEl) langfuseEl.checked = state.features.integrations.langfuse;

  // Update LLM warning visibility
  validateLlmProviders();

  // Update all section visibilities based on features
  updateAllSectionVisibilities();
}

async function loadFeatures() {
  try {
    const data = await api("/features");
    if (data && !data.error) {
      state.features = {
        app: {
          name: data.app?.name ?? "",
          id: data.app?.id ?? "",
        },
        infrastructure: {
          redis: data.infrastructure?.redis ?? false,
          worker: data.infrastructure?.worker ?? false,
          temporal: data.infrastructure?.temporal ?? false,
        },
        llm: {
          openai: data.llm?.openai ?? true,
          anthropic: data.llm?.anthropic ?? false,
          gemini: data.llm?.gemini ?? false,
        },
        integrations: {
          langfuse: data.integrations?.langfuse ?? false,
        },
      };

      // Restore app ID if it exists
      if (data.app?.id) {
        state.appId = data.app.id;
        state.appName = data.app.name || state.appName;
        updateAppIdDisplay();
      }

      restoreFeatureToggles();
      updateSectionStatus("features");
    }
  } catch (e) {
    console.error("Failed to load features:", e);
  }
}

/**
 * Load existing .env configuration and pre-populate form fields
 */
async function loadExistingEnv() {
  try {
    const data = await api("/load-env");
    if (!data.exists) return;

    console.log("Found existing .env configuration, pre-populating fields...");

    // Pre-populate state from existing env
    if (data.databaseUrl) state.databaseUrlProd = data.databaseUrl;
    if (data.neonApiKey) state.neonApiKey = data.neonApiKey;
    if (data.neonProjectId) state.neonProjectId = data.neonProjectId;
    if (data.clerkSecret) state.clerkSecret = data.clerkSecret;
    if (data.clerkPublishable) state.clerkPublishable = data.clerkPublishable;
    if (data.openaiKey) state.openaiKey = data.openaiKey;
    if (data.anthropicKey) state.anthropicKey = data.anthropicKey;
    if (data.geminiKey) state.geminiKey = data.geminiKey;
    if (data.langfusePublicKey)
      state.langfusePublicKey = data.langfusePublicKey;
    if (data.langfuseSecretKey)
      state.langfuseSecretKey = data.langfuseSecretKey;
    if (data.langfuseHost) state.langfuseHost = data.langfuseHost;
    if (data.temporalApiKey) state.temporalApiKey = data.temporalApiKey;
    if (data.gcpProjectId) state.gcpProject = data.gcpProjectId;
    if (data.serviceAccountJson)
      state.serviceAccountJson = data.serviceAccountJson;

    // Mark features as reviewed if we have existing config
    // (user has already gone through setup before)
    state.featuresReviewed = true;
  } catch (e) {
    console.error("Failed to load existing env:", e);
  }
}

function saveState() {
  sessionStorage.setItem("setupWizardState", JSON.stringify(state));
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Prerequisites
// ─────────────────────────────────────────────────────────────────────────────

async function checkPrereqs() {
  const list = document.getElementById("prereqs-list");
  const warning = document.getElementById("prereqs-warning");
  const gcloudWarning = document.getElementById("gcloud-auth-warning");

  list.innerHTML =
    '<li class="check-item"><div class="check-icon pending"></div><div class="check-details"><div class="check-name">Checking prerequisites...</div></div></li>';

  try {
    const data = await api("/prereqs");
    state.prereqs = data;

    list.innerHTML = data.checks
      .map(
        (check) => `
      <li class="check-item">
        <div class="check-icon ${check.exists ? "success" : "error"}">
          ${check.exists ? "✓" : "✗"}
        </div>
        <div class="check-details">
          <div class="check-name">${escapeHtml(check.label)}${check.required ? "" : " (optional)"}</div>
          <div class="check-version">${escapeHtml(check.version) || (check.exists ? "" : "Not installed")}</div>
        </div>
      </li>
    `,
      )
      .join("");

    warning.classList.toggle("hidden", data.allRequired);
    gcloudWarning.classList.toggle(
      "hidden",
      data.gcloudAuth || !data.checks.find((c) => c.name === "gcloud")?.exists,
    );

    updateSectionStatus("prereqs");
  } catch (e) {
    list.innerHTML =
      '<li class="check-item"><div class="check-icon error">✗</div><div class="check-details"><div class="check-name">Failed to check prerequisites</div></div></li>';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Repository
// ─────────────────────────────────────────────────────────────────────────────

async function detectRepo() {
  try {
    const data = await api("/detect-repo");
    if (data.owner && data.repo) {
      state.repo.owner = data.owner;
      state.repo.name = data.repo; // Server returns 'repo', state uses 'name'
      state.repo.url = data.url;
      document.getElementById("repo-detected").classList.remove("hidden");
      document.getElementById("repo-name-display").textContent =
        `${data.owner}/${data.repo}`;
      document.getElementById("repo-url").value = data.url || "";
      document.getElementById("app-name").value =
        state.appName ||
        data.repo
          .toLowerCase()
          .replace(/[^a-z0-9-]/g, "-")
          .slice(0, 30);
      state.appName = document.getElementById("app-name").value;
      updateSectionStatus("repo");
    }
  } catch (e) {
    console.error("Failed to detect repo:", e);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: GCP
// ─────────────────────────────────────────────────────────────────────────────

const TFSTATE_BUCKETS = {
  "asia-southeast1": "singapore-terraform-state",
  "australia-southeast1": "tomoro-tf-states",
  "europe-west2": "tomoro-tf-states",
};

// Map GCP regions to closest Temporal Cloud region
const TEMPORAL_REGION_MAP = {
  "asia-southeast1": "aws-ap-southeast-1", // Singapore -> Singapore
  "australia-southeast1": "aws-ap-southeast-2", // Sydney -> Sydney
  "europe-west2": "aws-eu-west-2", // London -> London
};

function updateTfstateBucket() {
  const regionEl = document.getElementById("gcp-region");
  if (!regionEl) return;

  const region = regionEl.value;
  const bucket = TFSTATE_BUCKETS[region];

  if (!bucket) {
    // Unknown region - clear bucket and let user input manually
    console.warn(`No default tfstate bucket for region: ${region}`);
  }

  const bucketEl = document.getElementById("tfstate-bucket");
  if (bucketEl) {
    bucketEl.value = bucket || "";
    state.tfstateBucket = bucket || "";
  }
}

function updateTemporalRegion() {
  const regionEl = document.getElementById("gcp-region");
  if (!regionEl) return;

  const region = regionEl.value;

  // Update Temporal region to match GCP region
  const temporalRegion = TEMPORAL_REGION_MAP[region] || "aws-ap-southeast-1";
  const temporalEl = document.getElementById("temporal-region");
  if (temporalEl) {
    temporalEl.value = temporalRegion;
  }
  state.temporalRegion = temporalRegion;
}

async function validateGcp() {
  const projectId = document.getElementById("gcp-project").value;
  const validationEl = document.getElementById("gcp-validation");
  const btn = document.getElementById("gcp-validate-btn");

  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> Validating...';
  validationEl.innerHTML =
    '<div class="alert alert-warning">Validating GCP project access...</div>';

  try {
    const data = await api("/validate-gcp", {
      method: "POST",
      body: { projectId },
    });

    if (data.valid) {
      validationEl.innerHTML =
        '<div class="alert alert-success">GCP project validated!</div>';
      state.gcpValidated = true;
    } else if (data.authExpired) {
      validationEl.innerHTML = `
        <div class="alert alert-error">
          <strong>gcloud authentication expired</strong><br>
          Run <code>gcloud auth login</code>, then try again.
        </div>
      `;
      state.gcpValidated = false;
    } else {
      validationEl.innerHTML = `<div class="alert alert-error">${escapeHtml(data.error)}</div>`;
      state.gcpValidated = false;
    }
  } catch (e) {
    validationEl.innerHTML =
      '<div class="alert alert-error">Failed to validate GCP project</div>';
    state.gcpValidated = false;
  }

  btn.disabled = false;
  btn.innerHTML = "Validate Access";
  saveField("gcp");
  updateSectionStatus("gcp");
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Service Account
// ─────────────────────────────────────────────────────────────────────────────

function updateSaMethod() {
  const method = document.getElementById("sa-method").value;
  document
    .querySelectorAll(".sa-method-section")
    .forEach((el) => el.classList.add("hidden"));

  const sectionMap = {
    existing: "sa-existing",
    "create-key": "sa-create-key",
    create: "sa-create",
    file: "sa-file",
  };
  const sectionId = sectionMap[method] || "sa-existing";
  document.getElementById(sectionId)?.classList.remove("hidden");

  state.serviceAccountMethod = method;
}

function updateSaEmailPreview() {
  const preview = document.getElementById("sa-email-preview");
  if (!preview) return;

  const name = state.appName || "app";
  const project = state.gcpProject || "project";
  preview.textContent = `${name}-deployer@${project}.iam.gserviceaccount.com`;

  const nameInput = document.getElementById("sa-name");
  if (nameInput && !nameInput.value) {
    nameInput.value = `${name}-deployer`;
  }
}

function validateServiceAccountJson() {
  const validationEl = document.getElementById("sa-validation");
  if (!validationEl) return;

  if (isValidServiceAccountJson(state.serviceAccountJson)) {
    try {
      const parsed = JSON.parse(state.serviceAccountJson);
      validationEl.classList.remove("hidden");
      validationEl.innerHTML = `<div class="alert alert-success">Valid service account: ${escapeHtml(parsed.client_email)}</div>`;
    } catch {
      validationEl.classList.add("hidden");
    }
  } else if (state.serviceAccountJson) {
    validationEl.classList.remove("hidden");
    validationEl.innerHTML =
      '<div class="alert alert-error">Invalid service account JSON. Must contain type, private_key, and client_email.</div>';
  } else {
    validationEl.classList.add("hidden");
  }

  updateSectionStatus("serviceaccount");
}

async function createServiceAccount() {
  const btn = document.getElementById("sa-create-btn");
  const statusEl = document.getElementById("sa-create-status");
  const name =
    document.getElementById("sa-name").value || `${state.appName}-deployer`;

  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> Creating...';
  statusEl.innerHTML =
    '<div class="alert alert-warning">Creating service account...</div>';

  try {
    const data = await api("/create-service-account", {
      method: "POST",
      body: {
        name,
        projectId: state.gcpProject,
      },
    });

    if (data.success) {
      state.serviceAccountJson = data.keyJson;
      document.getElementById("sa-key-json").value = data.keyJson;
      statusEl.innerHTML = `<div class="alert alert-success">Created: ${escapeHtml(data.email)}</div>`;

      // Switch to existing method to show the key
      document.getElementById("sa-method").value = "existing";
      updateSaMethod();
      validateServiceAccountJson();
    } else {
      statusEl.innerHTML = `<div class="alert alert-error">${escapeHtml(data.error)}</div>`;
    }
  } catch (e) {
    statusEl.innerHTML = `<div class="alert alert-error">Failed to create service account: ${escapeHtml(e.message)}</div>`;
  }

  btn.disabled = false;
  btn.innerHTML = "Create Service Account";
}

async function createKeyForExistingSa() {
  const btn = document.getElementById("sa-create-key-btn");
  const statusEl = document.getElementById("sa-create-key-status");
  const email = document.getElementById("sa-email").value.trim();

  if (!email) {
    statusEl.innerHTML =
      '<div class="alert alert-error">Please enter a service account email</div>';
    return;
  }

  // Validate email format
  if (!email.includes("@") || !email.includes(".iam.gserviceaccount.com")) {
    statusEl.innerHTML =
      '<div class="alert alert-error">Invalid service account email format. Should be: name@project.iam.gserviceaccount.com</div>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> Creating key...';
  statusEl.innerHTML =
    '<div class="alert alert-warning">Creating new key for existing service account...</div>';

  try {
    const data = await api("/create-key-for-sa", {
      method: "POST",
      body: { email },
    });

    if (data.success) {
      state.serviceAccountJson = data.keyJson;
      document.getElementById("sa-key-json").value = data.keyJson;
      statusEl.innerHTML = `<div class="alert alert-success">New key created for: ${escapeHtml(email)}</div>`;

      // Switch to existing method to show the key
      document.getElementById("sa-method").value = "existing";
      updateSaMethod();
      validateServiceAccountJson();
    } else {
      statusEl.innerHTML = `<div class="alert alert-error">${escapeHtml(data.error)}</div>`;
    }
  } catch (e) {
    statusEl.innerHTML = `<div class="alert alert-error">Failed to create key: ${escapeHtml(e.message)}</div>`;
  }

  btn.disabled = false;
  btn.innerHTML = "Create New Key";
}

async function loadSaFromFile() {
  const filePath = document.getElementById("sa-file-path").value;
  const statusEl = document.getElementById("sa-file-status");

  if (!filePath) return;

  try {
    const data = await api("/read-file", {
      method: "POST",
      body: { path: filePath },
    });

    if (data.success) {
      state.serviceAccountJson = data.content;
      document.getElementById("sa-key-json").value = data.content;
      statusEl.innerHTML =
        '<div class="alert alert-success">Loaded service account key</div>';
      validateServiceAccountJson();
    } else {
      statusEl.innerHTML = `<div class="alert alert-error">${escapeHtml(data.error)}</div>`;
    }
  } catch (e) {
    statusEl.innerHTML = `<div class="alert alert-error">Failed to read file: ${escapeHtml(e.message)}</div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Complete Setup
// ─────────────────────────────────────────────────────────────────────────────

async function completeSetup() {
  const outputEl = document.getElementById("setup-output");
  const btn = document.getElementById("complete-btn");

  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> Setting up...';

  const steps = [];
  const addStatus = (message, success = null) => {
    const icon = success === null ? "⏳" : success ? "✓" : "✗";
    const color =
      success === null
        ? "var(--warning)"
        : success
          ? "var(--success)"
          : "var(--error)";
    steps.push({ message, icon, color });
    outputEl.innerHTML = `
      <div class="card" style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; margin-top: 1rem;">
        <h3 style="margin-bottom: 0.5rem; font-size: 1rem;">Setup Progress</h3>
        ${steps
          .map(
            (s) => `
          <div class="status-line" style="color: ${s.color}">
            <span>${s.icon}</span>
            <span>${s.message}</span>
          </div>
        `,
          )
          .join("")}
      </div>
    `;
  };

  try {
    // 0. Generate app ID if we don't have one yet
    if (!state.appId && state.appName) {
      addStatus("Generating app ID...");
      await generateAppId(state.appName);
      steps[steps.length - 1] = {
        message: `Generated app ID: ${state.appId}`,
        icon: "✓",
        color: "var(--success)",
      };
    }

    // Ensure app section is populated
    state.features.app = {
      name: state.appName || state.features.app?.name || "",
      id: state.appId || state.features.app?.id || "",
    };

    // 1. Write features.json
    addStatus("Saving feature configuration...");
    const featuresResult = await api("/features", {
      method: "POST",
      body: state.features,
    });
    if (featuresResult.success) {
      steps[steps.length - 1] = {
        message: "Feature configuration saved",
        icon: "✓",
        color: "var(--success)",
      };
    } else {
      steps[steps.length - 1] = {
        message: `Feature config failed: ${featuresResult.error}`,
        icon: "✗",
        color: "var(--error)",
      };
    }

    // 1. Create local dev bucket (if gsutil available)
    addStatus("Creating local development bucket...");
    const bucketResult = await api("/create-local-bucket", {
      method: "POST",
      body: {
        appName: state.appName,
        gcpProjectId: state.gcpProject,
        gcpRegion: state.gcpRegion,
      },
    });

    if (bucketResult.success) {
      if (bucketResult.alreadyExists) {
        steps[steps.length - 1] = {
          message: `Local bucket exists: ${bucketResult.bucketName}`,
          icon: "✓",
          color: "var(--success)",
        };
      } else {
        steps[steps.length - 1] = {
          message: `Created bucket: ${bucketResult.bucketName}`,
          icon: "✓",
          color: "var(--success)",
        };
      }
    } else {
      steps[steps.length - 1] = {
        message: `Bucket creation skipped: ${bucketResult.error || "gsutil not available"}`,
        icon: "⚠",
        color: "var(--warning)",
      };
    }

    // 2. Write local .env files
    addStatus("Writing local environment files...");
    await api("/write-env", {
      method: "POST",
      body: {
        databaseUrl: state.databaseUrlProd,
        neonApiKey: state.neonApiKey,
        neonProjectId: state.neonProjectId,
        clerkSecretKey: state.clerkSecret,
        clerkPublishableKey: state.clerkPublishable,
        openaiApiKey: state.openaiKey,
        anthropicApiKey: state.anthropicKey,
        geminiApiKey: state.geminiKey,
        langfusePublicKey: state.langfusePublicKey,
        langfuseSecretKey: state.langfuseSecretKey,
        langfuseHost: state.langfuseHost,
        temporalApiKey: state.temporalApiKey,
        gcpProjectId: state.gcpProject,
        googleServiceAccountJson: state.serviceAccountJson,
        appName: state.appName,
        gcsBucketName: bucketResult.success ? bucketResult.bucketName : null,
      },
    });
    steps[steps.length - 1] = {
      message: "Local environment files created",
      icon: "✓",
      color: "var(--success)",
    };

    // 3. Setup GitHub secrets (creates environments first)
    if (
      state.prereqs?.checks.find((c) => c.name === "gh")?.exists &&
      state.repo.owner
    ) {
      addStatus("Setting up GitHub secrets...");
      const ghResult = await api("/github-secrets", {
        method: "POST",
        body: {
          repoOwner: state.repo.owner,
          repoName: state.repo.name,
          gcpProjectId: state.gcpProject,
          tfstateBucket: state.tfstateBucket,
          googleCredentials: state.serviceAccountJson,
          clerkSecretKey: state.clerkSecret,
          clerkPublishableKey: state.clerkPublishable,
          openaiApiKey: state.openaiKey,
          anthropicApiKey: state.anthropicKey,
          geminiApiKey: state.geminiKey,
          langfusePublicKey: state.langfusePublicKey,
          langfuseSecretKey: state.langfuseSecretKey,
          langfuseHost: state.langfuseHost,
          neonApiKey: state.neonApiKey,
          neonProjectId: state.neonProjectId,
          databaseUrlProd: state.databaseUrlProd,
          databaseUrlStaging: state.databaseUrlStaging,
          appName: state.appName,
          region: state.gcpRegion,
          temporalApiKey: state.temporalApiKey,
          temporalRegion: state.temporalRegion,
        },
      });

      const successCount = ghResult.results.filter((r) => r.success).length;
      const failCount = ghResult.results.filter((r) => !r.success).length;

      if (failCount === 0) {
        steps[steps.length - 1] = {
          message: `GitHub secrets configured (${successCount} secrets)`,
          icon: "✓",
          color: "var(--success)",
        };
      } else {
        steps[steps.length - 1] = {
          message: `GitHub secrets: ${successCount} ok, ${failCount} failed`,
          icon: "⚠",
          color: "var(--warning)",
        };
      }
    } else {
      addStatus(
        "GitHub secrets skipped (gh CLI not available or no repo)",
        false,
      );
      steps[steps.length - 1].icon = "⚠";
      steps[steps.length - 1].color = "var(--warning)";
    }

    // 4. Done
    addStatus("Setup complete!", true);
    sessionStorage.removeItem("setupWizardState");

    outputEl.innerHTML += `
      <div class="card" style="background: var(--bg-card); border: 1px solid var(--success); border-radius: 12px; padding: 1rem; margin-top: 1rem;">
        <h3 style="margin-bottom: 0.5rem; font-size: 1rem; color: var(--success);">Next Steps</h3>
        <div class="code-block">
          <div>1. Start local development:</div>
          <div style="color: var(--primary); margin-left: 1rem;">pnpm dev</div>
          <div style="margin-top: 0.5rem;">2. Open your app:</div>
          <div style="color: var(--primary); margin-left: 1rem;">http://localhost:3000</div>
          <div style="margin-top: 0.5rem;">3. Deploy to production:</div>
          <div style="color: var(--primary); margin-left: 1rem;">git push origin main</div>
        </div>
      </div>
    `;

    btn.innerHTML = "✓ Complete";
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-secondary");
  } catch (e) {
    addStatus(`Error: ${e.message}`, false);
    btn.disabled = false;
    btn.innerHTML = "Retry";
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Initialize
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  // Load existing .env files first (base config from disk)
  await loadExistingEnv();

  // Then load sessionStorage (overrides with in-progress changes)
  loadSavedState();

  restoreFormValues();

  // Load features from features.json
  await loadFeatures();

  // Check prereqs first
  await checkPrereqs();

  // Auto-detect repo
  await detectRepo();

  // Update all section statuses
  Object.keys(sectionRules).forEach(updateSectionStatus);

  // Always expand features section - it's the most important config
  toggleAccordion("features");
});
