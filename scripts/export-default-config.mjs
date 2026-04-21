#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const runtimeSettingsPath = path.join(repoRoot, ".runtime-data", "settings.json");
const projectConfigPath = path.join(repoRoot, "auto-prompt.project.json");
const deployDir = path.join(repoRoot, ".deploy");
const deployEnvPath = path.join(deployDir, "default.env");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf-8");
}

if (!fs.existsSync(runtimeSettingsPath)) {
  console.error(`[export-default-config] missing ${runtimeSettingsPath}`);
  process.exit(1);
}

if (!fs.existsSync(projectConfigPath)) {
  console.error(`[export-default-config] missing ${projectConfigPath}`);
  process.exit(1);
}

const runtimeSettings = readJson(runtimeSettingsPath);
const projectConfig = readJson(projectConfigPath);

const mergedProjectConfig = {
  ...projectConfig,
  default_model_id: runtimeSettings.default_model_id ?? projectConfig.default_model_id,
  model_name: runtimeSettings.model_name ?? projectConfig.model_name,
  models: Array.isArray(runtimeSettings.models) ? runtimeSettings.models : projectConfig.models,
  god_prompt: runtimeSettings.god_prompt ?? projectConfig.god_prompt,
  extract_god_prompt: runtimeSettings.extract_god_prompt ?? projectConfig.extract_god_prompt,
  llm_timeout: runtimeSettings.llm_timeout ?? projectConfig.llm_timeout,
};

writeJson(projectConfigPath, mergedProjectConfig);

fs.mkdirSync(deployDir, { recursive: true });
const apiKey = String(runtimeSettings.api_key || "").trim();
fs.writeFileSync(
  deployEnvPath,
  `# Generated from .runtime-data/settings.json\nDASHSCOPE_API_KEY=${apiKey}\nOPENAI_API_KEY=${apiKey}\n`,
  "utf-8",
);

console.log("[export-default-config] updated auto-prompt.project.json");
console.log(`[export-default-config] wrote ${deployEnvPath}`);
