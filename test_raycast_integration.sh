#!/bin/bash
# Test script for Raycast integration

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🧪 Testing Raycast Integration..."
echo ""

# Test 1: Import raycast_tools
echo "1️⃣ Testing raycast_tools module import..."
cd "$SCRIPT_DIR"
uv run python -c "from agent import raycast_tools; print('   ✅ Module imported successfully')" || exit 1

# Test 2: Test JSON structure
echo ""
echo "2️⃣ Testing JSON function structure..."
uv run python -c "
from agent import raycast_tools
result = raycast_tools.get_winners_losers_json()
assert isinstance(result, dict)
assert 'success' in result
assert 'data' in result or 'error' in result
print('   ✅ JSON structure correct')
" || exit 1

# Test 3: Check all scripts are executable
echo ""
echo "3️⃣ Checking script permissions..."
for script in raycast-scripts/{portfolio-status,quick-analysis,portfolio-winners-losers,upcoming-events,insider-trades-portfolio,insider-trades-ticker}; do
    if [ ! -x "$script" ]; then
        echo "   ❌ $script is not executable"
        exit 1
    fi
done
echo "   ✅ All scripts are executable"

# Test 4: Verify Raycast metadata
echo ""
echo "4️⃣ Verifying Raycast metadata..."
grep -q "@raycast.schemaVersion" raycast-scripts/portfolio-status && \
grep -q "@raycast.title" raycast-scripts/portfolio-status && \
echo "   ✅ Raycast metadata present" || exit 1

# Test 5: Test actual script execution from different directory
echo ""
echo "5️⃣ Testing script execution from /tmp..."
cd /tmp
output=$("$SCRIPT_DIR/raycast-scripts/portfolio-status" 2>&1)
if echo "$output" | grep -q '"success": true'; then
    echo "   ✅ Portfolio Status script executed successfully from different directory"
else
    echo "   ❌ Portfolio Status script failed"
    echo "$output" | tail -10
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "📋 Next steps:"
echo "   1. Add raycast-scripts/ directory to Raycast:"
echo "      Raycast Settings → Extensions → Script Commands"
echo "      → Add Directory → $SCRIPT_DIR/raycast-scripts/"
echo ""
echo "   2. Open Raycast (Cmd+Space) and type 'Portfolio'"
echo ""
echo "   3. Scripts are now bash wrappers (no .py extension) that call Python implementations"
echo ""
