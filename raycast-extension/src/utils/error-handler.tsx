import { Detail, ActionPanel, Action, openExtensionPreferences } from "@raycast/api";

/**
 * Error types that can occur in the extension
 */
export enum ErrorType {
  PYTHON_NOT_FOUND = "PYTHON_NOT_FOUND",
  CONFIG_MISSING = "CONFIG_MISSING",
  API_FAILURE = "API_FAILURE",
  INVALID_PATH = "INVALID_PATH",
  TIMEOUT = "TIMEOUT",
  UNKNOWN = "UNKNOWN",
}

/**
 * Categorize an error based on its message
 */
export function categorizeError(error: Error): ErrorType {
  const message = error.message.toLowerCase();
  
  if (message.includes("python") || message.includes("uv") || message.includes("enoent")) {
    return ErrorType.PYTHON_NOT_FOUND;
  }
  
  if (message.includes("config.yaml") || message.includes("configuration")) {
    return ErrorType.CONFIG_MISSING;
  }
  
  if (message.includes("fetch") || message.includes("api") || message.includes("network")) {
    return ErrorType.API_FAILURE;
  }
  
  if (message.includes("no such file") || message.includes("invalid path")) {
    return ErrorType.INVALID_PATH;
  }
  
  if (message.includes("timeout")) {
    return ErrorType.TIMEOUT;
  }
  
  return ErrorType.UNKNOWN;
}

/**
 * Get user-friendly error information based on error type
 */
export function getErrorInfo(errorType: ErrorType, originalError: Error): {
  title: string;
  message: string;
  markdown: string;
} {
  switch (errorType) {
    case ErrorType.PYTHON_NOT_FOUND:
      return {
        title: "Python Environment Not Found",
        message: "Please install the 'uv' package manager",
        markdown: `# Python Environment Not Found

The extension requires Python and the \`uv\` package manager to be installed.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

### Option 1: Install via Homebrew (Recommended)
\`\`\`bash
brew install uv
\`\`\`

### Option 2: Official Installer
\`\`\`bash
curl -LsSf https://astral.sh/uv/install.sh | sh
\`\`\`

### After Installing

1. **Restart Raycast** completely:
   - Quit Raycast: \`Cmd+Q\`
   - Reopen Raycast

2. **Or restart your computer** (ensures all environment variables are loaded)

3. Try running the command again

## What's Happening?

The extension looks for \`uv\` in these locations:
- \`/opt/homebrew/bin/uv\` (Homebrew on Apple Silicon)
- \`/usr/local/bin/uv\` (Homebrew on Intel)
- \`~/.cargo/bin/uv\` (Rust/Cargo install)
- \`~/.local/bin/uv\` (Manual install)

If you've installed uv but still see this error, try restarting Raycast or your computer.

For more information, visit: https://docs.astral.sh/uv/`,
      };
      
    case ErrorType.CONFIG_MISSING:
      return {
        title: "Configuration Missing",
        message: "config.yaml not found or invalid",
        markdown: `# Configuration Missing

The extension requires a valid \`config.yaml\` file in the project root.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

1. Ensure \`config.yaml\` exists in your project root
2. Copy from \`config.yaml.example\` if needed
3. Verify the project root path in extension preferences
4. Try running the command again`,
      };
      
    case ErrorType.API_FAILURE:
      return {
        title: "Failed to Fetch Data",
        message: "Could not retrieve portfolio data",
        markdown: `# Failed to Fetch Data

The extension could not retrieve data from the API or Google Sheets.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

1. Check your internet connection
2. Verify Google Sheets credentials are configured
3. Ensure the service account has access to your spreadsheet
4. Try refreshing the data`,
      };
      
    case ErrorType.INVALID_PATH:
      return {
        title: "Invalid Project Path",
        message: "Project directory not found",
        markdown: `# Invalid Project Path

The configured project root path does not exist or is invalid.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

1. Open Extension Preferences
2. Update the "Project Root Path" to the correct directory
3. The path should point to the \`investment-mcp\` directory
4. Try running the command again`,
      };
      
    case ErrorType.TIMEOUT:
      return {
        title: "Request Timed Out",
        message: "The operation took too long",
        markdown: `# Request Timed Out

The operation took longer than 30 seconds and was cancelled.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

1. Check your internet connection
2. Try again in a few moments
3. If the issue persists, the API may be experiencing issues`,
      };
      
    default:
      return {
        title: "An Error Occurred",
        message: "Something went wrong",
        markdown: `# An Error Occurred

An unexpected error occurred while running the command.

## Error Details
\`\`\`
${originalError.message}
\`\`\`

## How to Fix

1. Check the error details above
2. Verify your extension preferences
3. Try running the command again
4. If the issue persists, check the console logs`,
      };
  }
}

interface ErrorViewProps {
  error: Error;
  onRetry?: () => void;
}

/**
 * Render an error view with helpful actions
 */
export function ErrorView({ error, onRetry }: ErrorViewProps): JSX.Element {
  const errorType = categorizeError(error);
  const errorInfo = getErrorInfo(errorType, error);
  
  return (
    <Detail
      markdown={errorInfo.markdown}
      actions={
        <ActionPanel>
          {onRetry && (
            <Action
              title="Retry"
              onAction={onRetry}
              shortcut={{ modifiers: ["cmd"], key: "r" }}
            />
          )}
          <Action
            title="Open Extension Preferences"
            onAction={openExtensionPreferences}
            shortcut={{ modifiers: ["cmd"], key: "," }}
          />
        </ActionPanel>
      }
    />
  );
}
