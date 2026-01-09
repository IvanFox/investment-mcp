import { execFile } from "child_process";
import { promisify } from "util";
import { existsSync } from "fs";
import { homedir } from "os";
import { getPreferenceValues } from "@raycast/api";
import { Preferences } from "../types/api";

const execFileAsync = promisify(execFile);

/**
 * Cached uv executable path to avoid repeated filesystem checks
 */
let cachedUvPath: string | null = null;

/**
 * Find the uv executable by checking common installation locations
 *
 * @returns Absolute path to uv executable
 * @throws Error if uv is not found in any common location
 */
function findUvExecutable(): string {
  // Return cached path if already found
  if (cachedUvPath) {
    return cachedUvPath;
  }

  // Common installation paths for uv (in order of likelihood)
  const commonPaths = [
    "/opt/homebrew/bin/uv", // Homebrew on Apple Silicon (most common)
    "/usr/local/bin/uv", // Homebrew on Intel Macs
    `${homedir()}/.cargo/bin/uv`, // Installed via cargo/rustup
    `${homedir()}/.local/bin/uv`, // Manual install or pipx
  ];

  // Try each common path
  for (const path of commonPaths) {
    if (existsSync(path)) {
      console.log(`Found uv at: ${path}`);
      cachedUvPath = path;
      return path;
    }
  }

  // If not found in common locations, try just "uv" and let the system find it
  // This will work if uv is in the PATH (though unlikely in Raycast context)
  cachedUvPath = "uv";
  console.warn("uv not found in common locations, falling back to PATH lookup");
  return cachedUvPath;
}

/**
 * Execute a Python script from the raycast-scripts/lib directory
 *
 * @param scriptName - Name of the script (without _impl.py suffix)
 * @returns Parsed JSON response from the Python script
 * @throws Error if script execution fails or returns invalid JSON
 */
export async function executePythonScript<T>(scriptName: string): Promise<T> {
  const { projectRootPath } = getPreferenceValues<Preferences>();

  // Security: Validate that projectRootPath points to the legitimate investment-mcp project
  // This prevents execution of arbitrary Python scripts if preferences are compromised
  const configPath = `${projectRootPath}/config.yaml`;
  const pyprojectPath = `${projectRootPath}/pyproject.toml`;

  if (!existsSync(configPath) || !existsSync(pyprojectPath)) {
    throw new Error(
      `Invalid project root: Expected investment-mcp project structure not found.

The project root must contain both 'config.yaml' and 'pyproject.toml' files.
Current setting: ${projectRootPath}

Please verify your Raycast extension preferences point to the correct directory.`,
    );
  }

  const scriptPath = `${projectRootPath}/raycast-scripts/lib/${scriptName}_impl.py`;

  // Find uv executable
  const uvPath = findUvExecutable();

  try {
    const { stdout, stderr } = await execFileAsync(
      uvPath,
      ["run", "python", scriptPath],
      {
        cwd: projectRootPath,
        timeout: 180000, // 3 minute timeout (increased for first-run downloads)
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large responses
        env: {
          ...process.env,
          // Ensure common paths are in PATH as fallback
          // Include /usr/bin for macOS system commands like 'security'
          PATH: `/usr/bin:/opt/homebrew/bin:/usr/local/bin:${homedir()}/.local/bin:${homedir()}/.cargo/bin:${process.env.PATH}`,
        },
      },
    );

    // Log stderr if present (warnings, etc.)
    // Note: First-run downloads will show progress in stderr
    if (stderr && stderr.trim().length > 0) {
      // Check if stderr contains download/setup messages (expected on first run)
      const isSetupMessage =
        stderr.includes("Downloading") ||
        stderr.includes("Creating virtual environment") ||
        stderr.includes("Using CPython") ||
        stderr.includes("Installing") ||
        stderr.includes("Built") ||
        stderr.includes("Installed");

      if (isSetupMessage) {
        console.log("Python environment setup:", stderr);
      } else {
        console.error("Python stderr:", stderr);
      }
    }

    // Parse JSON response
    const result = JSON.parse(stdout);

    // Check if the Python script returned an error
    if (!result.success) {
      throw new Error(result.error || "Unknown error from Python script");
    }

    return result as T;
  } catch (error) {
    // Enhanced error messages for common issues
    if (error instanceof Error) {
      if (
        error.message.includes("ENOENT") ||
        error.message.includes("spawn uv")
      ) {
        // Clear cached path on failure so we retry next time
        cachedUvPath = null;

        throw new Error(
          `Python environment not found. Tried looking for 'uv' in common locations:
- /opt/homebrew/bin/uv
- /usr/local/bin/uv
- ~/.cargo/bin/uv
- ~/.local/bin/uv

Please install uv using one of these methods:
1. Homebrew: brew install uv
2. Official installer: curl -LsSf https://astral.sh/uv/install.sh | sh

After installing, restart Raycast or your computer.`,
        );
      }

      if (error.message.includes("timeout")) {
        throw new Error(
          `Request timed out after 3 minutes.

This might happen on first run if Python is being downloaded.
Please try again - subsequent runs will be much faster (2-3 seconds).`,
        );
      }

      if (error.message.includes("Unexpected token")) {
        throw new Error(
          "Invalid JSON response from Python script. Check the script output for errors.",
        );
      }

      if (error.message.includes("config.yaml")) {
        throw new Error(
          "Configuration file missing or invalid. Please ensure config.yaml exists in the project root.",
        );
      }

      // Re-throw with original message if not a known error type
      throw error;
    }

    throw new Error(
      "An unknown error occurred while executing the Python script",
    );
  }
}

/**
 * Get the currently cached or detected uv path (for debugging)
 *
 * @returns The uv executable path or null if not yet detected
 */
export function getUvPath(): string | null {
  return cachedUvPath;
}

/**
 * Clear the cached uv path (useful for testing or if path changes)
 */
export function clearUvCache(): void {
  cachedUvPath = null;
}
