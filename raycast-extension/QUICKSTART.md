# Quick Start Guide - Investment Portfolio Raycast Extension

Get your Raycast extension up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd /Users/ivan.lissitsnoi/Projects/investment-mcp/raycast-extension
npm install
```

## Step 2: Start Development Mode

```bash
npm run dev
```

You should see:

```
✓ Built extension successfully
✓ Watching for changes...
```

## Step 3: Open Raycast

1. Open Raycast: `Cmd+Space`
2. Type "Portfolio Status" or "Upcoming Events"
3. You should see the commands appear

## Step 4: Configure Preferences (First Time Only)

1. Open any command (Portfolio Status or Upcoming Events)
2. Press `Cmd+,` to open preferences
3. Set **Project Root Path** to your project location (use absolute path):
   ```
   /Users/yourusername/Projects/investment-mcp
   ```
4. Press `Enter` to save

## Step 5: Test the Commands

### Portfolio Status

1. Type "Portfolio Status" in Raycast
2. Press `Enter`
3. **First run**: Wait 2-3 minutes (Python is being downloaded automatically)
   - If you see "Request timed out", wait 30 seconds and try again
   - This only happens once!
4. **Subsequent runs**: Wait 2-3 seconds for data to load
5. You should see:
   - List of positions grouped by category
   - Values and gain/loss percentages
   - Detail panel on the right

**Actions to try:**

- Search for a position
- Click a position to see details
- Press `Cmd+C` to copy asset name
- Press `Cmd+R` to refresh

### Upcoming Events

1. Type "Upcoming Events" in Raycast
2. Press `Enter`
3. **First run**: Wait 2-3 minutes (Python is being downloaded automatically)
   - If you see "Request timed out", wait 30 seconds and try again
   - This only happens once!
4. **Subsequent runs**: Wait 3-5 seconds for data to load
5. You should see:
   - Events grouped by "This Week", "Next Week", "Later"
   - Company names, tickers, and dates
   - Countdown to each event

**Actions to try:**

- Search for a company or ticker
- Click an event to see details
- Press `Enter` on an event to open Yahoo Finance
- Press `Cmd+C` to copy ticker

## Troubleshooting

### "Python environment not found"

**Fix:**

```bash
# Install uv if not already installed
brew install uv

# Restart Raycast completely
# Cmd+Q to quit, then reopen

# Verify installation
which uv
# Should output: /opt/homebrew/bin/uv
```

### "Request timed out" (first run only)

**This is normal on first run!** Python 3.12 is being downloaded automatically.

**Fix:**

1. Wait 30 seconds
2. Try the command again
3. Repeat if necessary (total download time: 2-3 minutes)
4. Once complete, all future runs will be fast (~2-3 seconds)

**Want to pre-download?** Run this before using the extension:

```bash
cd /path/to/investment-mcp
uv sync  # Downloads Python and all dependencies
```

### "Configuration file missing"

**Fix:**

1. Verify the project root path in preferences (must be absolute path)
2. Check that `config.yaml` exists:
   ```bash
   ls /path/to/investment-mcp/config.yaml
   ```
3. If missing, copy from example:
   ```bash
   cd /path/to/investment-mcp
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```
4. If missing, copy from example:
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

### "Failed to fetch data"

**Fix:**

1. Run the setup check:
   ```bash
   cd /path/to/investment-mcp
   uv run python check_setup.py
   ```
2. Fix any issues reported
3. Try the command again

### Extension doesn't appear in Raycast

**Fix:**

1. Make sure `npm run dev` is running
2. Restart Raycast: `Cmd+Q`, then reopen
3. Check the terminal for error messages

## Next Steps

- **Customize**: Modify the code to add new features
- **Hot Reload**: Make changes to `.tsx` files and see updates instantly
- **Add Commands**: See README.md for how to add more commands
- **Build**: Run `npm run build` to create a production build

## Keyboard Shortcuts

### Portfolio Status

- `Cmd+C` - Copy asset name
- `Cmd+Shift+C` - Copy current value
- `Cmd+R` - Refresh data
- `Cmd+,` - Open preferences

### Upcoming Events

- `Cmd+C` - Copy ticker
- `Cmd+Shift+C` - Copy company name
- `Cmd+Shift+E` - Open earnings calendar
- `Cmd+R` - Refresh data
- `Cmd+,` - Open preferences

## Development Tips

1. **Keep `npm run dev` running** - Changes auto-reload
2. **Check terminal** for error messages
3. **Use Raycast Developer Console** (`Cmd+Shift+D` in Raycast) for logs
4. **Test error states** by temporarily breaking config.yaml

## Success Checklist

- [ ] Dependencies installed (`npm install`)
- [ ] Dev mode running (`npm run dev`)
- [ ] Preferences configured (Project Root Path set)
- [ ] Portfolio Status command works
- [ ] Upcoming Events command works
- [ ] Can search and view details
- [ ] Actions work (copy, refresh, etc.)

## Need Help?

See the full documentation:

- [Extension README](README.md)
- [Main Project README](../README.md)
- [Raycast Scripts README](../raycast-scripts/README.md)

---

**You're all set! Enjoy tracking your portfolio! 💼📊**
