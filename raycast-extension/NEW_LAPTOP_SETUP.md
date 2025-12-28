# New Laptop Setup Guide

Quick checklist to get the Investment Portfolio Raycast extension running on a new laptop.

## Prerequisites Checklist

Before setting up the extension, ensure you have:

- [ ] **Homebrew** installed

  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- [ ] **uv package manager** installed
  ```bash
  brew install uv
  ```
- [ ] **Node.js** (v18 or later) installed

  ```bash
  brew install node
  ```

- [ ] **Raycast** app installed
  - Download from: https://www.raycast.com/

## Setup Steps

### 1. Clone the Project

```bash
# Clone to your preferred location
git clone <your-repo-url> ~/Projects/investment-mcp
cd ~/Projects/investment-mcp
```

### 2. Set Up Python Backend

```bash
# Sync Python dependencies (this downloads Python 3.12 if needed)
uv sync

# Verify setup
uv run python check_setup.py
```

### 3. Configure Backend

Copy the example config and fill in your details:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your Google Sheets ID and ticker mappings
```

Add credentials to macOS Keychain:

```bash
# Google Sheets credentials (from service account JSON file)
security add-generic-password -a "mcp-portfolio-agent" \
  -s "google-sheets-credentials" \
  -w "$(cat path/to/service-account.json)" -U

# Alpha Vantage API key (for risk analysis)
security add-generic-password -a "mcp-portfolio-agent" \
  -s "alpha-vantage-api-key" \
  -w "YOUR_API_KEY" -U

# Fintel API key (for insider trading)
security add-generic-password -a "mcp-portfolio-agent" \
  -s "fintel-api-key" \
  -w "YOUR_API_KEY" -U
```

### 4. Set Up Raycast Extension

```bash
cd raycast-extension
npm install
npm run dev
```

You should see: `✓ Built extension successfully`

### 5. Configure Extension in Raycast

1. Open Raycast: `Cmd+Space`
2. Type "Portfolio Status" or "Upcoming Events"
3. Press `Cmd+,` to open preferences
4. Set **Project Root Path** to your project location:
   ```
   /Users/yourusername/Projects/investment-mcp
   ```
5. Press `Enter` to save

### 6. Test the Extension

Try running a command:

1. Open Raycast: `Cmd+Space`
2. Type "Portfolio Status"
3. Press `Enter`

**First run behavior:**

- **May take 2-3 minutes** if Python/dependencies need to be downloaded
- You might see "Request timed out" - just try again
- **Subsequent runs will be fast** (~2-3 seconds)

## Troubleshooting First Run

### Issue: "Python environment not found"

**Solution:**

```bash
# Verify uv is installed
which uv
# Should output: /opt/homebrew/bin/uv

# If not found, install:
brew install uv
```

### Issue: "Request timed out" on first run

**Cause:** Python 3.12 is being downloaded in the background (first time only)

**Solution:**

1. Wait 30 seconds
2. Try the command again
3. Repeat if necessary - downloads may take 2-3 minutes total
4. Once complete, all future runs will be fast

**Alternative (pre-download):**

```bash
cd ~/Projects/investment-mcp
uv sync  # Pre-downloads everything (takes 2-3 minutes)
```

### Issue: "Configuration file missing"

**Solution:**

```bash
# Ensure config.yaml exists
ls ~/Projects/investment-mcp/config.yaml

# If missing, copy from example
cd ~/Projects/investment-mcp
cp config.yaml.example config.yaml
# Edit with your settings
```

### Issue: "Failed to fetch data"

**Solution:**

```bash
# Run diagnostics
cd ~/Projects/investment-mcp
uv run python check_setup.py

# Common fixes:
# 1. Check Google Sheets credentials in Keychain
# 2. Verify service account has access to spreadsheet
# 3. Test internet connection
```

## Verification Checklist

Once setup is complete, verify everything works:

- [ ] `uv --version` shows version number
- [ ] `npm --version` shows version number
- [ ] `config.yaml` exists and is configured
- [ ] Credentials are in Keychain (check with Keychain Access app)
- [ ] `uv run python check_setup.py` passes all checks
- [ ] Extension appears in Raycast
- [ ] Portfolio Status command loads data (may be slow on first run)
- [ ] Upcoming Events command loads data
- [ ] Second run is fast (~2-3 seconds)

## Performance Notes

### First Run (One-Time Setup)

- **Time:** 2-3 minutes
- **Why:** Downloads Python 3.12 + all dependencies
- **Where:** Cached in `~/.local/share/uv/python/` and `.venv/`

### Subsequent Runs

- **Time:** 2-3 seconds
- **Why:** Everything is cached locally

### When Updates Happen

New downloads may occur when:

- Python version changes in `.python-version`
- Dependencies change in `pyproject.toml`
- Virtual environment is deleted (`.venv/`)

## Migration from Old Laptop

If transferring from an old laptop:

### What to Copy

- `config.yaml` (your configuration)
- Google Sheets service account JSON file
- API keys (or re-add to Keychain)

### What NOT to Copy

- `.venv/` directory (recreate with `uv sync`)
- `node_modules/` (recreate with `npm install`)
- `cache/` directory (auto-generated)
- `dashboards/` directory (auto-generated)

### Quick Migration

```bash
# On old laptop - backup config and credentials
cp config.yaml ~/Desktop/investment-mcp-backup.yaml
cp path/to/service-account.json ~/Desktop/gsheets-credentials.json

# On new laptop - restore
cp ~/Desktop/investment-mcp-backup.yaml ~/Projects/investment-mcp/config.yaml
# Re-add credentials to Keychain (see step 3 above)
```

## Need Help?

1. Check the main [README.md](README.md)
2. Review [QUICKSTART.md](QUICKSTART.md)
3. Run diagnostics: `uv run python check_setup.py`
4. Check Raycast console logs: `Cmd+Shift+D` in Raycast

---

**Setup complete! Your extension should now work seamlessly across laptops.**
