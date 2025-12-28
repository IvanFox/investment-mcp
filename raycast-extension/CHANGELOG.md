# Changelog

All notable changes to the Investment Portfolio Raycast Extension will be documented in this file.

## [1.0.0] - 2025-12-28

### Added
- Initial release of native Raycast extension
- **Portfolio Status** command with live data from Google Sheets
  - Categorized view of all positions
  - Searchable list with detail panels
  - Color-coded gains/losses
  - Actions: Copy name, copy value, refresh
- **Upcoming Events** command for earnings calendar
  - Time-based grouping (This Week, Next Week, Later)
  - Visual countdown with color coding
  - Yahoo Finance integration
  - Actions: Open on Yahoo Finance, copy ticker, refresh
- Smart uv executable detection
  - Automatically finds uv in common installation locations
  - Supports Homebrew (Apple Silicon & Intel), cargo, manual installs
  - Helpful error messages if uv not found
- Comprehensive error handling
  - User-friendly error messages
  - Actionable guidance for common issues
  - Retry functionality
- TypeScript utilities
  - Python executor with path detection
  - Data formatters (currency, dates, percentages)
  - Full type definitions for API responses
- Documentation
  - Complete README with usage guide
  - Quick Start guide
  - Troubleshooting section

### Fixed
- Resolved PATH issue where Raycast couldn't find uv executable
  - Now checks common installation paths: `/opt/homebrew/bin`, `/usr/local/bin`, `~/.cargo/bin`, `~/.local/bin`
  - Caches found path for better performance
  - Enhanced PATH environment for Python execution

### Technical Details
- TypeScript + React (Raycast API)
- Direct Python execution via Node.js child_process
- Reuses existing Python backend (agent/raycast_tools.py)
- JSON-based communication
- ~2-3s load time for Portfolio Status
- ~3-5s load time for Upcoming Events

### Known Limitations
- Requires uv package manager installed
- Requires valid config.yaml in project root
- No caching between command invocations (may add in future)
- Only 2 commands implemented (4 more from raycast-scripts available for future)

### Upgrading from Raycast Scripts
If you were using the bash-based Raycast scripts:
- Scripts in `raycast-scripts/` still work
- Extension provides better UI and UX
- Extension has same data source (Google Sheets + APIs)
- Both can coexist - use whichever you prefer
- Extension is recommended for daily use

---

## Future Roadmap

### Planned Features
- [ ] Add remaining commands (Quick Analysis, Winners/Losers, Insider Trades)
- [ ] Implement caching with configurable TTL
- [ ] "Open in Google Sheets" action with direct link
- [ ] Menu bar command for at-a-glance portfolio value
- [ ] Push notifications for upcoming earnings (within 24h)
- [ ] Export data to CSV/JSON
- [ ] Charts and visualizations (inline)
- [ ] Multi-portfolio support

### Performance Improvements
- [ ] Cache responses for 5 minutes (configurable)
- [ ] Background refresh
- [ ] Optimistic UI updates

### UX Enhancements
- [ ] Keyboard navigation shortcuts
- [ ] Favorites/pinned positions
- [ ] Custom sorting options
- [ ] Color theme customization
- [ ] Alternative layouts (compact, detailed)

---

For detailed installation and usage instructions, see [README.md](README.md).
