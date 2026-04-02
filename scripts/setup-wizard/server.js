#!/usr/bin/env node
/**
 * Setup Wizard Server
 *
 * Minimal Node.js server with zero dependencies.
 * Provides API endpoints for the setup wizard UI.
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { exec, spawn } = require("child_process");
const { promisify } = require("util");

const execAsync = promisify(exec);
const PORT = 4321;
const ROOT = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(ROOT, "../..");

// MIME types for static files
const MIME_TYPES = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function commandExists(cmd) {
  try {
    await execAsync(`which ${cmd}`);
    return true;
  } catch {
    return false;
  }
}

async function getCommandVersion(cmd, versionFlag = "--version") {
  try {
    const { stdout } = await execAsync(`${cmd} ${versionFlag} 2>&1 | head -1`);
    return stdout.trim();
  } catch {
    return null;
  }
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error("Invalid JSON"));
      }
    });
    req.on("error", reject);
  });
}

function jsonResponse(res, data, status = 200) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function serveStatic(res, filePath) {
  const ext = path.extname(filePath);
  const mimeType = MIME_TYPES[ext] || "text/plain";

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": mimeType,
      "Cache-Control": "no-cache, no-store, must-revalidate",
      Pragma: "no-cache",
      Expires: "0",
    });
    res.end(data);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Input Validation (Security)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Validate GCP project ID format
 * Rules: 6-30 chars, lowercase letters, digits, hyphens, must start with letter
 */
function isValidGcpProjectId(projectId) {
  if (!projectId || typeof projectId !== "string") return false;
  return /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(projectId);
}

/**
 * Validate GCP service account email format
 */
function isValidServiceAccountEmail(email) {
  if (!email || typeof email !== "string") return false;
  return /^[a-z][a-z0-9-]*@[a-z][a-z0-9-]*\.iam\.gserviceaccount\.com$/.test(
    email,
  );
}

/**
 * Validate service account name format
 * Rules: 6-30 chars, lowercase letters, digits, hyphens
 */
function isValidServiceAccountName(name) {
  if (!name || typeof name !== "string") return false;
  return /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(name);
}

/**
 * Validate GCP region format
 */
function isValidGcpRegion(region) {
  if (!region || typeof region !== "string") return false;
  return /^[a-z]+-[a-z]+\d+$/.test(region);
}

/**
 * Validate that a path is within an allowed directory (prevent path traversal)
 */
function isPathWithinDir(filePath, allowedDir) {
  const resolvedPath = path.resolve(filePath);
  const resolvedDir = path.resolve(allowedDir);
  return (
    resolvedPath.startsWith(resolvedDir + path.sep) ||
    resolvedPath === resolvedDir
  );
}

/**
 * Validate features.json structure
 */
function isValidFeaturesStructure(features) {
  if (!features || typeof features !== "object") return false;

  const hasApp = features.app && typeof features.app === "object";
  const hasInfrastructure =
    features.infrastructure && typeof features.infrastructure === "object";
  const hasLlm = features.llm && typeof features.llm === "object";
  const hasIntegrations =
    features.integrations && typeof features.integrations === "object";

  return hasApp && hasInfrastructure && hasLlm && hasIntegrations;
}

/**
 * Generate a random 4-character suffix for app ID
 * Uses base36 (a-z, 0-9) for readability
 * Uses crypto.randomBytes for secure randomness
 */
function generateAppSuffix() {
  const crypto = require("crypto");
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = crypto.randomBytes(4);
  let suffix = "";
  for (let i = 0; i < 4; i++) {
    suffix += chars.charAt(bytes[i] % chars.length);
  }
  return suffix;
}

/**
 * Sanitize app name for use in IDs (lowercase, alphanumeric, hyphens)
 */
function sanitizeAppName(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/^-|-$/g, "")
    .replace(/-+/g, "-")
    .slice(0, 30);
}

// ─────────────────────────────────────────────────────────────────────────────
// API Endpoints
// ─────────────────────────────────────────────────────────────────────────────

async function checkPrereqs() {
  const checks = [
    { name: "docker", required: true },
    { name: "pnpm", required: true },
    { name: "gcloud", required: true },
    { name: "gh", required: false, label: "GitHub CLI" },
    { name: "git", required: true },
  ];

  const results = await Promise.all(
    checks.map(async (check) => {
      const exists = await commandExists(check.name);
      const version = exists ? await getCommandVersion(check.name) : null;
      return {
        name: check.name,
        label: check.label || check.name,
        exists,
        version,
        required: check.required,
      };
    }),
  );

  // Check if gcloud is authenticated
  let gcloudAuth = null;
  if (results.find((r) => r.name === "gcloud")?.exists) {
    try {
      const { stdout } = await execAsync(
        'gcloud config list account --format="value(core.account)"',
      );
      gcloudAuth = stdout.trim() || null;
    } catch {
      gcloudAuth = null;
    }
  }

  // Check for existing git remote
  let gitRemote = null;
  try {
    const { stdout } = await execAsync("git config --get remote.origin.url", {
      cwd: PROJECT_ROOT,
    });
    gitRemote = stdout.trim();
  } catch {
    gitRemote = null;
  }

  // Check for existing setup
  const hasExistingSetup = fs.existsSync(
    path.join(PROJECT_ROOT, "environment/.env.backend"),
  );

  return {
    checks: results,
    allRequired: results.filter((r) => r.required).every((r) => r.exists),
    gcloudAuth,
    gitRemote,
    hasExistingSetup,
  };
}

async function detectRepo() {
  try {
    const { stdout } = await execAsync("git config --get remote.origin.url", {
      cwd: PROJECT_ROOT,
    });
    const url = stdout.trim();

    // Parse GitHub URL
    let owner, repo;
    if (url.startsWith("git@github.com:")) {
      const match = url.match(/git@github\.com:(.+)\/(.+?)(?:\.git)?$/);
      if (match) [, owner, repo] = match;
    } else if (url.includes("github.com")) {
      const match = url.match(/github\.com\/(.+)\/(.+?)(?:\.git)?$/);
      if (match) [, owner, repo] = match;
    }

    return { url, owner, repo: repo?.replace(".git", "") };
  } catch {
    return { url: null, owner: null, repo: null };
  }
}

async function validateGcpProject(projectId) {
  // Validate project ID format to prevent command injection
  if (!isValidGcpProjectId(projectId)) {
    return {
      valid: false,
      error:
        "Invalid project ID format. Must be 6-30 lowercase letters, digits, or hyphens.",
    };
  }

  try {
    await execAsync(
      `gcloud projects describe ${projectId} --format="value(name)"`,
      { timeout: 10000 },
    );
    return { valid: true };
  } catch (e) {
    const msg = e.message || "";

    // Check for auth issues
    if (
      msg.includes("Reauthentication") ||
      msg.includes("auth tokens") ||
      msg.includes("Please run")
    ) {
      return {
        valid: false,
        error: "gcloud authentication expired. Please run: gcloud auth login",
        authExpired: true,
      };
    }

    // Check for permission issues
    if (msg.includes("PERMISSION_DENIED") || msg.includes("does not have")) {
      return {
        valid: false,
        error: `No access to project "${projectId}". Check the project ID or request access.`,
        permissionDenied: true,
      };
    }

    // Check for project not found
    if (msg.includes("NOT_FOUND") || msg.includes("not found")) {
      return {
        valid: false,
        error: `Project "${projectId}" not found. Check the project ID.`,
        notFound: true,
      };
    }

    return { valid: false, error: msg };
  }
}

async function writeEnvFiles(config) {
  const envDir = path.join(PROJECT_ROOT, "environment");

  // Backend .env
  const backendEnvPath = path.join(envDir, ".env.backend");
  const backendExamplePath = path.join(envDir, ".env.backend.example");

  // Start from existing .env if exists, otherwise use example, otherwise create new
  let backendContent = "";
  if (fs.existsSync(backendEnvPath)) {
    backendContent = fs.readFileSync(backendEnvPath, "utf8");
  } else if (fs.existsSync(backendExamplePath)) {
    backendContent = fs.readFileSync(backendExamplePath, "utf8");
  }

  // Calculate bucket name if we have the required info
  let gcsBucketName = config.gcsBucketName;
  if (!gcsBucketName && config.appName && config.gcpProjectId) {
    const crypto = require("crypto");
    const sanitizedAppName = config.appName
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 30);
    const hash = crypto
      .createHash("md5")
      .update(`${config.gcpProjectId}-${sanitizedAppName}`)
      .digest("hex")
      .slice(0, 4);
    gcsBucketName = `${sanitizedAppName}-dev-local-${hash}`;
  }

  // Replace/add values (these are active env vars for local dev)
  const backendVars = {
    DATABASE_URL: config.databaseUrl,
    NEON_API_KEY: config.neonApiKey,
    NEON_PROJECT_ID: config.neonProjectId,
    CLERK_SECRET_KEY: config.clerkSecretKey,
    CLERK_WEBHOOK_SECRET:
      config.clerkWebhookSecret ||
      "whsec_placeholder_update_me_after_deployment",
    OPENAI_API_KEY: config.openaiApiKey,
    ANTHROPIC_API_KEY: config.anthropicApiKey,
    GEMINI_API_KEY: config.geminiApiKey,
    LANGFUSE_PUBLIC_KEY: config.langfusePublicKey,
    LANGFUSE_SECRET_KEY: config.langfuseSecretKey,
    // Default to EU region if Langfuse keys provided but no host
    LANGFUSE_HOST:
      config.langfuseHost ||
      (config.langfusePublicKey ? "https://cloud.langfuse.com" : ""),
    GCP_PROJECT_ID: config.gcpProjectId,
    STORAGE_MODE: gcsBucketName ? "real" : config.storageMode || "fake",
    GCS_BUCKET_NAME: gcsBucketName,
  };

  // Handle service account JSON specially (contains special characters)
  if (config.googleServiceAccountJson) {
    // Compress JSON to single line
    try {
      const parsed = JSON.parse(config.googleServiceAccountJson);
      const compressed = JSON.stringify(parsed);
      backendVars.GOOGLE_SERVICE_ACCOUNT_JSON = `'${compressed}'`;
    } catch {
      // Use as-is if already compressed
      backendVars.GOOGLE_SERVICE_ACCOUNT_JSON = `'${config.googleServiceAccountJson}'`;
    }
  }

  for (const [key, value] of Object.entries(backendVars)) {
    if (!value) continue;
    // Match both commented (# KEY=) and uncommented (KEY=) lines
    const regex = new RegExp(`^#?\\s*${key}=.*$`, "m");
    if (regex.test(backendContent)) {
      backendContent = backendContent.replace(regex, `${key}=${value}`);
    } else {
      backendContent += `\n${key}=${value}`;
    }
  }

  // Write TEMPORAL_API_KEY as commented (for reference only - breaks local dev if active)
  // Local dev uses Docker Temporal which doesn't need auth
  if (config.temporalApiKey) {
    const commentedKey = `# TEMPORAL_API_KEY=${config.temporalApiKey}  # Uncomment only for Temporal Cloud, breaks local dev`;
    const regex = /^#?\s*TEMPORAL_API_KEY=.*$/m;
    if (regex.test(backendContent)) {
      backendContent = backendContent.replace(regex, commentedKey);
    } else {
      backendContent += `\n${commentedKey}`;
    }
  }

  fs.writeFileSync(backendEnvPath, backendContent.trim() + "\n");

  // Frontend .env
  const frontendEnvPath = path.join(envDir, ".env.frontend");
  const frontendExamplePath = path.join(envDir, ".env.frontend.example");

  // Start from existing .env if exists, otherwise use example
  let frontendContent = "";
  if (fs.existsSync(frontendEnvPath)) {
    frontendContent = fs.readFileSync(frontendEnvPath, "utf8");
  } else if (fs.existsSync(frontendExamplePath)) {
    frontendContent = fs.readFileSync(frontendExamplePath, "utf8");
  }

  if (config.clerkPublishableKey) {
    const regex = /^VITE_CLERK_PUBLISHABLE_KEY=.*$/m;
    if (regex.test(frontendContent)) {
      frontendContent = frontendContent.replace(
        regex,
        `VITE_CLERK_PUBLISHABLE_KEY=${config.clerkPublishableKey}`,
      );
    } else {
      frontendContent += `\nVITE_CLERK_PUBLISHABLE_KEY=${config.clerkPublishableKey}`;
    }
  }

  fs.writeFileSync(frontendEnvPath, frontendContent.trim() + "\n");

  return { success: true };
}

async function createLocalDevBucket(config) {
  const { appName, gcpProjectId, gcpRegion } = config;

  if (!appName || !gcpProjectId) {
    return { success: false, error: "Missing appName or gcpProjectId" };
  }

  // Validate inputs to prevent command injection
  if (!isValidGcpProjectId(gcpProjectId)) {
    return { success: false, error: "Invalid GCP project ID format" };
  }

  const region = gcpRegion || "asia-southeast1";
  if (!isValidGcpRegion(region)) {
    return { success: false, error: "Invalid GCP region format" };
  }

  try {
    // Sanitize app name for GCS (lowercase, alphanumeric and hyphens only)
    const sanitizedAppName = appName
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 30);

    // Calculate bucket hash (same as Terraform and old setup script)
    const crypto = require("crypto");
    const hash = crypto
      .createHash("md5")
      .update(`${gcpProjectId}-${sanitizedAppName}`)
      .digest("hex")
      .slice(0, 4);
    const bucketName = `${sanitizedAppName}-dev-local-${hash}`;

    // Check if bucket already exists
    try {
      await execAsync(`gsutil ls -b gs://${bucketName}`, { timeout: 10000 });
      console.log(`Local dev bucket already exists: ${bucketName}`);
      return { success: true, bucketName, alreadyExists: true };
    } catch {
      // Bucket doesn't exist, create it
    }

    // Create the bucket
    console.log(`Creating local dev bucket: ${bucketName}`);
    await execAsync(
      `gsutil mb -p ${gcpProjectId} -l ${region} gs://${bucketName}`,
      { timeout: 30000 },
    );
    console.log(`  ✓ Created bucket: ${bucketName}`);

    // Set CORS for browser uploads
    const corsConfig = JSON.stringify([
      {
        origin: ["*"],
        method: ["GET", "PUT", "POST", "DELETE", "OPTIONS"],
        responseHeader: ["*"],
        maxAgeSeconds: 3600,
      },
    ]);

    const corsFile = `/tmp/cors-${Date.now()}.json`;
    fs.writeFileSync(corsFile, corsConfig);

    try {
      await execAsync(`gsutil cors set ${corsFile} gs://${bucketName}`, {
        timeout: 10000,
      });
      console.log(`  ✓ Configured CORS for browser uploads`);
    } catch (e) {
      console.log(`  ⚠ Could not set CORS: ${e.message}`);
    } finally {
      try {
        fs.unlinkSync(corsFile);
      } catch {}
    }

    return { success: true, bucketName, created: true };
  } catch (e) {
    console.error(`Failed to create local dev bucket: ${e.message}`);
    return { success: false, error: e.message };
  }
}

async function setupGithubSecrets(config) {
  const secrets = {
    GCP_PROJECT_ID: config.gcpProjectId,
    TFSTATE_BUCKET: config.tfstateBucket,
    GOOGLE_CREDENTIALS: config.googleCredentials,
    CLERK_SECRET_KEY: config.clerkSecretKey,
    VITE_CLERK_PUBLISHABLE_KEY: config.clerkPublishableKey,
    CLERK_WEBHOOK_SECRET:
      config.clerkWebhookSecret ||
      "whsec_placeholder_update_me_after_deployment",
    OPENAI_API_KEY: config.openaiApiKey,
    ANTHROPIC_API_KEY: config.anthropicApiKey,
    GEMINI_API_KEY: config.geminiApiKey,
    LANGFUSE_PUBLIC_KEY: config.langfusePublicKey,
    LANGFUSE_SECRET_KEY: config.langfuseSecretKey,
    NEON_API_KEY: config.neonApiKey,
    NEON_PROJECT_ID: config.neonProjectId,
    TEMPORAL_API_KEY: config.temporalApiKey,
  };

  // Set non-sensitive config as variables (only include truthy values)
  const variables = {
    APP_NAME: config.appName,
    REGION: config.region,
    LANGFUSE_HOST: config.langfuseHost,
    TEMPORAL_REGION: config.temporalRegion,
  };

  const repo = `${config.repoOwner}/${config.repoName}`;
  const results = [];

  // Helper to set secret using a temp file (handles any content safely)
  async function setSecret(name, value, env = null) {
    if (!value) return;
    const displayName = env ? `${name} (${env})` : name;
    const tempFile = `/tmp/gh-secret-${Date.now()}-${Math.random().toString(36).slice(2)}.txt`;

    try {
      // Write value to temp file (handles any special characters)
      fs.writeFileSync(tempFile, value);

      const envFlag = env ? `--env ${env}` : "";
      const cmd = `gh secret set ${name} ${envFlag} --repo ${repo} < ${tempFile}`;
      console.log(`Setting secret: ${displayName}`);
      await execAsync(cmd, { cwd: PROJECT_ROOT });
      console.log(`  ✓ ${displayName} set successfully`);
      results.push({ name: displayName, success: true });
    } catch (e) {
      console.error(`  ✗ ${displayName} failed:`, e.message);
      results.push({ name: displayName, success: false, error: e.message });
    } finally {
      // Clean up temp file
      try {
        fs.unlinkSync(tempFile);
      } catch {}
    }
  }

  // Helper to set variable using a temp file
  async function setVariable(name, value) {
    if (!value) return;
    const displayName = `${name} (variable)`;
    const tempFile = `/tmp/gh-var-${Date.now()}-${Math.random().toString(36).slice(2)}.txt`;

    try {
      fs.writeFileSync(tempFile, value);
      const cmd = `gh variable set ${name} --repo ${repo} < ${tempFile}`;
      console.log(`Setting variable: ${name}`);
      await execAsync(cmd, { cwd: PROJECT_ROOT });
      console.log(`  ✓ ${name} set successfully`);
      results.push({ name: displayName, success: true });
    } catch (e) {
      console.error(`  ✗ ${name} failed:`, e.message);
      results.push({ name: displayName, success: false, error: e.message });
    } finally {
      try {
        fs.unlinkSync(tempFile);
      } catch {}
    }
  }

  console.log(`\n📦 Setting GitHub secrets for ${repo}...`);

  // Create environments first (required for environment-specific secrets)
  // Each service (backend, frontend, worker) gets its own environment for deployment protection
  const environments = [
    "prod",
    "prod-frontend",
    "prod-worker",
    "staging",
    "staging-frontend",
    "staging-worker",
  ];
  for (const env of environments) {
    try {
      console.log(`Creating environment: ${env}`);
      await execAsync(`gh api --method PUT repos/${repo}/environments/${env}`, {
        cwd: PROJECT_ROOT,
      });
      console.log(`  ✓ Environment ${env} created`);
    } catch (e) {
      // Environment might already exist, which is fine
      if (!e.message.includes("already exists")) {
        console.log(`  ⚠ Environment ${env}: ${e.message}`);
      }
    }
  }

  // Set all secrets
  for (const [name, value] of Object.entries(secrets)) {
    await setSecret(name, value);
  }

  // Environment-specific secrets (DATABASE_URL differs between prod/staging)
  // Set for both base env and worker env (worker needs DB access too)
  await setSecret("DATABASE_URL", config.databaseUrlProd, "prod");
  await setSecret("DATABASE_URL", config.databaseUrlProd, "prod-worker");
  await setSecret("DATABASE_URL", config.databaseUrlStaging, "staging");
  await setSecret("DATABASE_URL", config.databaseUrlStaging, "staging-worker");

  // Variables (from the variables object)
  for (const [name, value] of Object.entries(variables)) {
    await setVariable(name, value);
  }

  return { results };
}

async function runCommand(command, cwd = PROJECT_ROOT) {
  try {
    const { stdout, stderr } = await execAsync(command, {
      cwd,
      timeout: 60000,
    });
    return { success: true, stdout, stderr };
  } catch (e) {
    return {
      success: false,
      error: e.message,
      stdout: e.stdout,
      stderr: e.stderr,
    };
  }
}

async function startDocker() {
  return new Promise((resolve) => {
    const proc = spawn("pnpm", ["dev"], {
      cwd: PROJECT_ROOT,
      detached: true,
      stdio: "ignore",
    });
    proc.unref();

    // Give it a moment to start
    setTimeout(() => {
      resolve({ success: true, message: "Docker started in background" });
    }, 2000);
  });
}

async function checkHealth() {
  const checks = [];

  // Check backend
  try {
    const { stdout } = await execAsync("curl -s http://localhost:8080/health", {
      timeout: 5000,
    });
    checks.push({
      service: "backend",
      healthy: stdout.includes("ok") || stdout.includes("healthy"),
    });
  } catch {
    checks.push({ service: "backend", healthy: false });
  }

  // Check frontend
  try {
    await execAsync("curl -s http://localhost:3000", { timeout: 5000 });
    checks.push({ service: "frontend", healthy: true });
  } catch {
    checks.push({ service: "frontend", healthy: false });
  }

  return { checks };
}

async function createServiceAccount(config) {
  const { name, projectId } = config;

  // Validate inputs to prevent command injection
  if (!isValidServiceAccountName(name)) {
    return {
      success: false,
      error:
        "Invalid service account name format. Must be 6-30 lowercase letters, digits, or hyphens.",
    };
  }
  if (!isValidGcpProjectId(projectId)) {
    return { success: false, error: "Invalid GCP project ID format." };
  }

  const email = `${name}@${projectId}.iam.gserviceaccount.com`;

  try {
    // Check if service account exists
    try {
      await execAsync(
        `gcloud iam service-accounts describe ${email} --project=${projectId}`,
        { timeout: 10000 },
      );
    } catch {
      // Create it if it doesn't exist
      await execAsync(
        `gcloud iam service-accounts create ${name} --display-name="${name}" --project=${projectId}`,
        { timeout: 30000 },
      );
    }

    // Try to create a key
    const keyFile = `/tmp/sa-key-${Date.now()}.json`;
    try {
      await execAsync(
        `gcloud iam service-accounts keys create ${keyFile} --iam-account=${email} --project=${projectId}`,
        { timeout: 30000 },
      );
      const keyJson = fs.readFileSync(keyFile, "utf8");
      fs.unlinkSync(keyFile);

      return { success: true, email, keyJson };
    } catch (e) {
      const msg = e.message || "";

      if (msg.includes("PERMISSION_DENIED")) {
        return {
          success: false,
          error: `Permission denied. You need "Service Account Key Admin" role to create keys.`,
          email,
        };
      }

      if (msg.includes("10 keys")) {
        return {
          success: false,
          error: `Service account has reached the 10-key limit. Delete old keys in GCP Console.`,
          email,
        };
      }

      return { success: false, error: msg, email };
    }
  } catch (e) {
    return { success: false, error: e.message };
  }
}

async function readFile(filePath) {
  // Validate path is within project directory to prevent path traversal
  if (!isPathWithinDir(filePath, PROJECT_ROOT)) {
    return { success: false, error: "Path must be within project directory" };
  }

  try {
    const content = fs.readFileSync(filePath, "utf8");
    return { success: true, content };
  } catch (e) {
    return { success: false, error: `Cannot read file: ${e.message}` };
  }
}

async function getFeatures() {
  const featuresPath = path.join(PROJECT_ROOT, "features.json");
  try {
    const content = fs.readFileSync(featuresPath, "utf8");
    return JSON.parse(content);
  } catch (e) {
    // Return defaults if file doesn't exist or is invalid
    return {
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
    };
  }
}

/**
 * Generate an app ID from the app name
 * Format: {sanitized-name}-{4-char-suffix}
 * Example: invoicing-x7k2
 */
async function generateAppId(appName) {
  if (!appName || typeof appName !== "string") {
    return { success: false, error: "App name is required" };
  }

  const sanitized = sanitizeAppName(appName);
  if (!sanitized) {
    return { success: false, error: "App name must contain valid characters" };
  }

  const suffix = generateAppSuffix();
  const appId = `${sanitized}-${suffix}`;

  return { success: true, appId, name: sanitized };
}

/**
 * Parse a .env file into key-value pairs
 * Handles quoted values and multi-line JSON
 */
function parseEnvFile(content) {
  const result = {};
  if (!content) return result;

  const lines = content.split("\n");
  for (const line of lines) {
    // Skip comments and empty lines
    if (!line.trim() || line.trim().startsWith("#")) continue;

    const eqIndex = line.indexOf("=");
    if (eqIndex === -1) continue;

    const key = line.slice(0, eqIndex).trim();
    let value = line.slice(eqIndex + 1).trim();

    // Remove surrounding quotes if present
    if (
      (value.startsWith("'") && value.endsWith("'")) ||
      (value.startsWith('"') && value.endsWith('"'))
    ) {
      value = value.slice(1, -1);
    }

    result[key] = value;
  }

  return result;
}

/**
 * Load existing environment configuration from .env files
 */
async function loadExistingEnv() {
  const envDir = path.join(PROJECT_ROOT, "environment");
  const backendEnvPath = path.join(envDir, ".env.backend");
  const frontendEnvPath = path.join(envDir, ".env.frontend");

  const result = {
    exists: false,
    backend: {},
    frontend: {},
  };

  // Read backend .env
  if (fs.existsSync(backendEnvPath)) {
    result.exists = true;
    const content = fs.readFileSync(backendEnvPath, "utf8");
    result.backend = parseEnvFile(content);
  }

  // Read frontend .env
  if (fs.existsSync(frontendEnvPath)) {
    result.exists = true;
    const content = fs.readFileSync(frontendEnvPath, "utf8");
    result.frontend = parseEnvFile(content);
  }

  // Extract TEMPORAL_API_KEY from commented line (it's stored commented to not break local dev)
  let temporalApiKey = result.backend.TEMPORAL_API_KEY || "";
  if (!temporalApiKey && fs.existsSync(backendEnvPath)) {
    const content = fs.readFileSync(backendEnvPath, "utf8");
    const match = content.match(/^#\s*TEMPORAL_API_KEY=([^\s#]+)/m);
    if (match) {
      temporalApiKey = match[1];
    }
  }

  // Map to wizard fields
  const mapped = {
    exists: result.exists,
    databaseUrl: result.backend.DATABASE_URL || "",
    neonApiKey: result.backend.NEON_API_KEY || "",
    neonProjectId: result.backend.NEON_PROJECT_ID || "",
    clerkSecret: result.backend.CLERK_SECRET_KEY || "",
    clerkPublishable: result.frontend.VITE_CLERK_PUBLISHABLE_KEY || "",
    openaiKey: result.backend.OPENAI_API_KEY || "",
    anthropicKey: result.backend.ANTHROPIC_API_KEY || "",
    geminiKey: result.backend.GEMINI_API_KEY || "",
    langfusePublicKey: result.backend.LANGFUSE_PUBLIC_KEY || "",
    langfuseSecretKey: result.backend.LANGFUSE_SECRET_KEY || "",
    langfuseHost: result.backend.LANGFUSE_HOST || "",
    temporalApiKey: temporalApiKey,
    gcpProjectId: result.backend.GCP_PROJECT_ID || "",
    gcsBucketName: result.backend.GCS_BUCKET_NAME || "",
  };

  // Try to parse service account JSON if present
  if (result.backend.GOOGLE_SERVICE_ACCOUNT_JSON) {
    try {
      // It might be stored with surrounding quotes
      let json = result.backend.GOOGLE_SERVICE_ACCOUNT_JSON;
      if (json.startsWith("'") && json.endsWith("'")) {
        json = json.slice(1, -1);
      }
      // Validate it's valid JSON
      JSON.parse(json);
      mapped.serviceAccountJson = json;
    } catch {
      // Invalid JSON, skip
    }
  }

  return mapped;
}

async function writeFeatures(features) {
  // Validate features structure before writing
  if (!isValidFeaturesStructure(features)) {
    return {
      success: false,
      error:
        "Invalid features structure. Must have infrastructure, llm, and integrations.",
    };
  }

  const featuresPath = path.join(PROJECT_ROOT, "features.json");
  try {
    fs.writeFileSync(featuresPath, JSON.stringify(features, null, 2) + "\n");
    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

async function createKeyForExistingSa(config) {
  const { email } = config;

  // Validate email format to prevent command injection
  if (!isValidServiceAccountEmail(email)) {
    return {
      success: false,
      error:
        "Invalid service account email format. Must be: name@project.iam.gserviceaccount.com",
    };
  }

  try {
    // Extract project ID from email
    const match = email.match(/@(.+)\.iam\.gserviceaccount\.com$/);
    if (!match) {
      return { success: false, error: "Invalid service account email format" };
    }
    const projectId = match[1];

    // Verify the service account exists
    try {
      await execAsync(
        `gcloud iam service-accounts describe ${email} --project=${projectId}`,
        { timeout: 10000 },
      );
    } catch (e) {
      const msg = e.message || "";
      if (msg.includes("NOT_FOUND") || msg.includes("not found")) {
        return {
          success: false,
          error: `Service account "${email}" not found`,
        };
      }
      if (msg.includes("PERMISSION_DENIED")) {
        return {
          success: false,
          error: `Permission denied. Cannot access service account "${email}"`,
        };
      }
      return { success: false, error: `Cannot verify service account: ${msg}` };
    }

    // Create a new key
    const keyFile = `/tmp/sa-key-${Date.now()}.json`;
    try {
      await execAsync(
        `gcloud iam service-accounts keys create ${keyFile} --iam-account=${email} --project=${projectId}`,
        { timeout: 30000 },
      );
      const keyJson = fs.readFileSync(keyFile, "utf8");
      fs.unlinkSync(keyFile);

      return { success: true, email, keyJson };
    } catch (e) {
      const msg = e.message || "";

      if (msg.includes("PERMISSION_DENIED")) {
        return {
          success: false,
          error: `Permission denied. You need "Service Account Key Admin" role to create keys.`,
          email,
        };
      }

      if (msg.includes("10 keys")) {
        return {
          success: false,
          error: `Service account has reached the 10-key limit. Delete old keys in GCP Console.`,
          email,
        };
      }

      return { success: false, error: msg, email };
    }
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Router
// ─────────────────────────────────────────────────────────────────────────────

async function handleRequest(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const method = req.method;

  // CORS - restrict to localhost only (same-origin requests)
  const origin = req.headers.origin;
  if (
    origin &&
    (origin.startsWith("http://localhost:") ||
      origin.startsWith("http://127.0.0.1:"))
  ) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  }

  if (method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  try {
    // API Routes
    if (url.pathname === "/api/prereqs" && method === "GET") {
      const data = await checkPrereqs();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/detect-repo" && method === "GET") {
      const data = await detectRepo();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/validate-gcp" && method === "POST") {
      const body = await parseBody(req);
      const data = await validateGcpProject(body.projectId);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/write-env" && method === "POST") {
      const body = await parseBody(req);
      const data = await writeEnvFiles(body);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/github-secrets" && method === "POST") {
      const body = await parseBody(req);
      const data = await setupGithubSecrets(body);
      jsonResponse(res, data);
      return;
    }

    // DISABLED: /api/run-command - arbitrary command execution is a security risk
    // If needed, implement a whitelist of allowed commands
    if (url.pathname === "/api/run-command" && method === "POST") {
      jsonResponse(
        res,
        { success: false, error: "Endpoint disabled for security" },
        403,
      );
      return;
    }

    if (url.pathname === "/api/start-docker" && method === "POST") {
      const data = await startDocker();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/health" && method === "GET") {
      const data = await checkHealth();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/create-service-account" && method === "POST") {
      const body = await parseBody(req);
      const data = await createServiceAccount(body);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/read-file" && method === "POST") {
      const body = await parseBody(req);
      const data = await readFile(body.path);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/create-key-for-sa" && method === "POST") {
      const body = await parseBody(req);
      const data = await createKeyForExistingSa(body);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/create-local-bucket" && method === "POST") {
      const body = await parseBody(req);
      const data = await createLocalDevBucket(body);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/features" && method === "GET") {
      const data = await getFeatures();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/features" && method === "POST") {
      const body = await parseBody(req);
      const data = await writeFeatures(body);
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/load-env" && method === "GET") {
      const data = await loadExistingEnv();
      jsonResponse(res, data);
      return;
    }

    if (url.pathname === "/api/generate-app-id" && method === "POST") {
      const body = await parseBody(req);
      const data = await generateAppId(body.appName);
      jsonResponse(res, data);
      return;
    }

    // Static files - validate path to prevent traversal
    let filePath = url.pathname === "/" ? "/index.html" : url.pathname;
    const resolvedPath = path.resolve(ROOT, filePath.slice(1)); // Remove leading slash

    // Ensure resolved path is within ROOT directory
    if (!resolvedPath.startsWith(ROOT + path.sep) && resolvedPath !== ROOT) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isFile()) {
      serveStatic(res, resolvedPath);
      return;
    }

    res.writeHead(404);
    res.end("Not found");
  } catch (e) {
    console.error("Error:", e);
    jsonResponse(res, { error: e.message }, 500);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Server
// ─────────────────────────────────────────────────────────────────────────────

const server = http.createServer(handleRequest);

// Bind to localhost only for security (prevents network access)
server.listen(PORT, "127.0.0.1", () => {
  console.log(`
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   🚀 Setup Wizard running at http://localhost:${PORT}/setup   │
│                                                             │
│   Press Ctrl+C to stop                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
`);

  // Open browser
  const openCmd =
    process.platform === "darwin"
      ? "open"
      : process.platform === "win32"
        ? "start"
        : "xdg-open";
  exec(`${openCmd} http://localhost:${PORT}/`);
});
