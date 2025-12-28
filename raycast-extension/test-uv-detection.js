/**
 * Simple test script to verify uv detection works
 * Run with: node test-uv-detection.js
 */

const { execFileSync } = require("child_process");
const { existsSync } = require("fs");
const { homedir } = require("os");

console.log("Testing uv detection...\n");

// Common installation paths for uv (in order of likelihood)
const commonPaths = [
  "/opt/homebrew/bin/uv", // Homebrew on Apple Silicon (most common)
  "/usr/local/bin/uv", // Homebrew on Intel Macs
  `${homedir()}/.cargo/bin/uv`, // Installed via cargo/rustup
  `${homedir()}/.local/bin/uv`, // Manual install or pipx
];

let uvFound = false;
let uvPath = null;

console.log("Checking common paths:");
for (const path of commonPaths) {
  const exists = existsSync(path);
  console.log(`  ${exists ? "✅" : "❌"} ${path}`);
  if (exists && !uvFound) {
    uvFound = true;
    uvPath = path;
  }
}

if (uvFound) {
  console.log(`\n✅ Found uv at: ${uvPath}`);
  
  // Try to execute uv --version
  try {
    const version = execFileSync(uvPath, ["--version"], { encoding: "utf8" });
    console.log(`✅ uv is executable: ${version.trim()}`);
    
    // Try uv run python --version
    try {
      const pythonVersion = execFileSync(
        uvPath,
        ["run", "python", "--version"],
        { encoding: "utf8", cwd: process.env.HOME }
      );
      console.log(`✅ uv can run python: ${pythonVersion.trim()}`);
      console.log("\n🎉 All checks passed! The extension should work.");
    } catch (pythonError) {
      console.error(`\n❌ Error running python with uv:`);
      console.error(pythonError.message);
      console.log("\nℹ️  This might not be a problem if Python is installed via uv in the project directory.");
    }
  } catch (execError) {
    console.error(`\n❌ Error executing uv:`);
    console.error(execError.message);
  }
} else {
  console.log("\n❌ uv not found in any common location");
  console.log("\nPlease install uv using one of these methods:");
  console.log("1. Homebrew: brew install uv");
  console.log("2. Official installer: curl -LsSf https://astral.sh/uv/install.sh | sh");
}

console.log("\n---");
console.log("Current PATH:", process.env.PATH);
