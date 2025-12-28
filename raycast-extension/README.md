# Investment Portfolio - Raycast Extension

A native Raycast extension for tracking your investment portfolio with live data and analytics.

## Features

### 💼 Portfolio Status

- **Live Data**: Fetches current portfolio positions directly from Google Sheets
- **Categorized View**: Positions organized by category (EU Stocks, US Stocks, etc.)
- **Detail Panel**: Full breakdown of each position with gain/loss information
- **Searchable**: Quick search across all positions
- **Sortable**: Categories and positions sorted by value (largest first)

### 📅 Upcoming Events

- **Earnings Calendar**: Shows upcoming earnings reports for all portfolio stocks
- **Time-Based Groups**: Events organized into "This Week", "Next Week", and "Later"
- **Countdown**: Visual countdown to each event with color coding
- **Detail View**: Full event information including estimates and dates
- **Quick Actions**: Open on Yahoo Finance, copy ticker, and more

## Prerequisites

Before using this extension, ensure you have:

1. **Python 3.12+** - Will be automatically downloaded by uv on first run
2. **uv package manager** installed:
   ```bash
   brew install uv
   ```
3. **investment-mcp project** set up with:
   - Valid `config.yaml` file
   - Google Sheets credentials in macOS Keychain
   - Dependencies will be installed automatically on first run

## New Laptop Setup

Setting up on a new laptop? See the **[New Laptop Setup Guide](NEW_LAPTOP_SETUP.md)** for a complete checklist.

**Quick version:**

1. Install prerequisites: `brew install uv node`
2. Clone project and configure `config.yaml`
3. Add credentials to macOS Keychain
4. Run `npm install && npm run dev` in `raycast-extension/`
5. Configure project path in Raycast preferences
6. First run may take 2-3 minutes (downloads Python automatically)
7. Subsequent runs are fast (~2-3 seconds)

## Installation

### Development Mode

1. **Clone or navigate to the project**:

   ```bash
   cd /Users/ivan.lissitsnoi/Projects/investment-mcp/raycast-extension
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Start development mode**:

   ```bash
   npm run dev
   ```

   The extension will automatically appear in Raycast with hot-reloading enabled.

4. **Configure extension preferences**:
   - Open Raycast (Cmd+Space)
   - Search for "Portfolio Status" or "Upcoming Events"
   - Press `Cmd+,` to open preferences
   - Set "Project Root Path" to: `/Users/ivan.lissitsnoi/Projects/investment-mcp`

### Production Build

To create a production build:

```bash
npm run build
```

The built extension will be in the `dist/` directory.

## Commands

### Portfolio Status

**Trigger**: Type "Portfolio Status" in Raycast

**Features**:

- View all current positions with live data
- Positions grouped by category
- Sortable by value
- Detailed view showing:
  - Current value and quantity
  - Purchase price and cost basis
  - Gain/Loss (EUR and %)
  - Category information

**Actions**:

- `Enter` - View position details
- `Cmd+C` - Copy asset name
- `Cmd+Shift+C` - Copy current value
- `Cmd+R` - Refresh data

**Performance**:

- First run: 2-3 minutes (downloads Python if needed)
- Subsequent runs: ~2-3 seconds (fetches live data from Google Sheets)

### Upcoming Events

**Trigger**: Type "Upcoming Events" in Raycast

**Features**:

- View upcoming earnings reports for portfolio stocks
- Events grouped by time period
- Color-coded countdown (red = within 3 days, orange = within 7 days)
- Detailed view showing:
  - Company name and ticker
  - Event type and date
  - Days until event
  - Earnings estimate (if available)

**Actions**:

- `Enter` - View event details
- `Cmd+Click` - Open on Yahoo Finance
- `Cmd+Shift+E` - Open earnings calendar
- `Cmd+C` - Copy ticker
- `Cmd+Shift+C` - Copy company name
- `Cmd+R` - Refresh data

**Performance**:

- First run: 2-3 minutes (downloads Python if needed)
- Subsequent runs: ~3-5 seconds (fetches data from Yahoo Finance API)

## Architecture

### Technology Stack

- **Frontend**: TypeScript + React (Raycast API)
- **Backend**: Python (existing `agent/raycast_tools.py`)
- **Integration**: Node.js `child_process` calling Python via `uv run`
- **Data Format**: JSON

### Project Structure

```
raycast-extension/
├── package.json              # Extension manifest & dependencies
├── tsconfig.json             # TypeScript configuration
├── src/
│   ├── portfolio-status.tsx  # Portfolio Status command
│   ├── upcoming-events.tsx   # Upcoming Events command
│   ├── utils/
│   │   ├── python-executor.ts   # Python script execution
│   │   ├── error-handler.tsx    # Error handling & UI
│   │   └── formatters.ts        # Data formatting utilities
│   └── types/
│       └── api.ts               # TypeScript interfaces
├── dist/                     # Build output
└── README.md                 # This file
```

### Data Flow

```
User
  ↓
Raycast Extension (TypeScript)
  ↓
python-executor.ts
  ↓
uv run python raycast-scripts/lib/<script>_impl.py
  ↓
agent/raycast_tools.py
  ↓
Google Sheets / APIs
  ↓
JSON Response
  ↓
TypeScript UI
  ↓
User
```

## Configuration

### Extension Preferences

- **Project Root Path** (required): Absolute path to the `investment-mcp` directory
  - Example: `/Users/ivan.lissitsnoi/Projects/investment-mcp`
  - Access: `Cmd+,` while viewing any command

### Python Backend Configuration

The extension uses the existing Python backend, which requires:

1. **config.yaml** in project root with:
   - `sheet_id`: Your Google Sheets spreadsheet ID
   - `ticker_mappings`: Stock ticker mappings

2. **Credentials** in macOS Keychain:
   - Google Sheets service account credentials
   - API keys for Yahoo Finance (if needed)

See the main project README for detailed setup instructions.

## Troubleshooting

### "Python environment not found"

**Problem**: Extension can't find Python or uv

**Solution**:

1. Install uv: `brew install uv`
2. Restart Raycast completely (Cmd+Q, then reopen)
3. Verify: `which uv` (should output `/opt/homebrew/bin/uv`)
4. Try the command again

### "Request timed out" on first run

**Problem**: First run takes longer than 3 minutes

**Cause**: Python 3.12 and dependencies are being downloaded automatically

**Solution**:

1. Wait 30 seconds and try again
2. This only happens once - Python is cached for future runs
3. Alternative: Pre-download by running `cd /path/to/investment-mcp && uv sync`
4. All subsequent runs will be fast (~2-3 seconds)

### "Configuration file missing"

**Problem**: config.yaml not found

**Solution**:

1. Check project root path in preferences
2. Ensure `config.yaml` exists in that directory
3. Copy from `config.yaml.example` if needed
4. Verify the path is absolute (not relative)

### "Failed to fetch data"

**Problem**: Can't retrieve data from Google Sheets or APIs

**Solution**:

1. Check internet connection
2. Verify Google Sheets credentials in Keychain
3. Ensure service account has access to spreadsheet
4. Check `uv run python check_setup.py` for configuration issues

### "Request timed out"

**Problem**: Operation took longer than 30 seconds

**Solution**:

1. Check internet connection
2. Try again in a few moments
3. Check if APIs are experiencing issues

### Build errors

**Problem**: TypeScript compilation errors

**Solution**:

```bash
cd raycast-extension
npm install  # Reinstall dependencies
npm run build  # Check for errors
```

## Development

### Running in Dev Mode

```bash
cd raycast-extension
npm run dev
```

Changes to source files will automatically reload in Raycast.

### Building

```bash
npm run build
```

### Linting

```bash
npm run lint          # Check for issues
npm run fix-lint      # Auto-fix issues
```

### Adding New Commands

1. Create a new file in `src/`: `src/my-command.tsx`
2. Add to `package.json` commands array:
   ```json
   {
     "name": "my-command",
     "title": "My Command",
     "description": "Description here",
     "mode": "view",
     "icon": "🎯"
   }
   ```
3. Implement the command (see existing commands as examples)
4. Run `npm run dev` to test

## Performance

### Initial Load Times

- **Portfolio Status**: ~2-3 seconds (live Google Sheets fetch)
- **Upcoming Events**: ~3-5 seconds (Yahoo Finance API calls)

### Optimization Tips

- Use `Cmd+R` to refresh instead of reopening the command
- Data is cached during the command's lifecycle
- Consider implementing caching in future versions (5-minute TTL)

## Future Enhancements

Potential features to add:

- [ ] Add remaining script commands (Quick Analysis, Winners/Losers, Insider Trades)
- [ ] Implement caching with `useCachedPromise` (5-minute TTL)
- [ ] Add "Open in Google Sheets" action with direct sheet link
- [ ] Support for multiple portfolios
- [ ] Charts and visualizations
- [ ] Push notifications for upcoming events
- [ ] Portfolio value trending graph
- [ ] Export data to CSV

## Support

For issues or questions:

1. Check this README first
2. Run `uv run python check_setup.py` in project root
3. Check console logs in Raycast Developer Tools
4. Review main project README for Python backend setup

## License

MIT License - See main project LICENSE file

---

**Enjoy tracking your portfolio! 💼📊**
