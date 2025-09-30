# MCP Agent Plan: Portfolio Monitoring & Performance Analysis

**Objective:** Create an automated system to fetch portfolio data from Google Sheets, generate weekly performance snapshots, compare them, and report on changes, including new/sold positions and realized gains/losses.

**Technical Stack:**
- **Executor:** `fastmcp`
- **Language:** Python
- **Data Persistence:** Single `portfolio_history.json` file
- **Package Manager:** `uv`

**Credentials**
- See credentials.json for API key to query google spreadsheet API and sheet-details.json to get spreadsheet id and gid
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit?gid=SHEET_ID#gid=SHEET_ID

## **Project Structure**

Create the following file structure for the project:

 /mcp-portfolio-agent/
|-- .venv/
|-- agent/
|   |-- init.py
|   |-- main.py             # Main entrypoint for the fastmcp agent
|   |-- sheets_connector.py # Module for all Google Sheets API interactions
|   |-- analysis.py         # Module for all data processing and comparison logic
|   |-- storage.py          # Module for reading/writing to the JSON file
|   |-- reporting.py        # Module for formatting the final output report
|
|-- credentials.json        # Google Cloud Service Account key
|-- portfolio_history.json  # Data store for weekly snapshots
 

## **Phase 2: Google Sheets Data Extraction Module**

**File:** `agent/sheets_connector.py`

This module is solely responsible for connecting to the Google Sheets API, fetching, and normalizing the raw portfolio data.

### **Constants**

```python
# The name of the sheet that contains the current year's portfolio data.
ACTIVE_SHEET_NAME = '2025'

# Define the specific cell ranges for each asset category to be fetched.
# Ensure the ranges capture all necessary columns, especially 'Name', 'Qty', 'Purchase Price', and 'Current Value'.
# Example:
ASSET_RANGES = {
    'stocks_us': f'{ACTIVE_SHEET_NAME}!A5:L20',
    'stocks_eu': f'{ACTIVE_SHEET_NAME}!A25:L35',
    'etfs': f'{ACTIVE_SHEET_NAME}!A40:L45',
}

# Define the cells containing currency conversion rates.
RATES_RANGE = f'{ACTIVE_SHEET_NAME}!B2:B3' # Assuming GBP/EUR is B2, USD/EUR is B3
 Functions to Implement
1. ⁠get_sheets_service()
	•	Purpose: Authenticates with the Google API using ⁠credentials.json and returns a service object. 	•	Parameters: None. 	•	Returns: ⁠googleapiclient.discovery.Resource object. 	•	Details: This function should handle the boilerplate authentication flow.
2. ⁠fetch_portfolio_data()
	•	Purpose: Fetches all required raw data from the spreadsheet. 	•	Parameters: None. 	•	Returns: ⁠dict containing the raw values for rates and assets.
	▪	Example Return:
 {
  "rates": [[1.1589], [0.8490]], # Raw values from RATES_RANGE
  "assets": {
    "stocks_us": [["Wise", "10003", ...], ["Intel Corp", "55", ...]], # Raw values from stocks_us range
    "stocks_eu": [["Artea bank", "2100", ...]]
  }
}
 
3. ⁠parse_and_normalize_data(raw_data: dict)
	•	Purpose: Takes the raw data from ⁠fetch_portfolio_data and transforms it into a clean, standardized list of asset dictionaries. This is the primary data cleaning and structuring step. 	•	Parameters: ⁠raw_data (the dictionary returned by ⁠fetch_portfolio_data). 	•	Returns: ⁠list[dict] 	•	Logic:
	a.	Extract the currency rates. 	b.	Iterate through each asset category in ⁠raw_data['assets']. 	c.	For each row (asset), parse the columns into a structured dictionary. 	d.	Crucially, perform currency conversion on the purchase price and current value, standardizing both to EUR. 	e.	Handle potential errors like empty rows or non-numeric values gracefully. 	f.	Skip any rows where the asset name is blank. 	•	Output Asset Dictionary Schema:
 {
  "name": str,          # e.g., "Intel Corp"
  "quantity": float,    # e.g., 55.0
  "purchase_price_total_eur": float, # Total cost at purchase in EUR
  "current_value_eur": float, # Total current value in EUR
  "category": str       # e.g., "Tech", "Finance"
}
 
Phase 3: Core Analysis & Snapshot Logic
File: ⁠agent/analysis.py
This module contains the business logic for creating snapshots and comparing them.
Data Schemas
Snapshot JSON Schema
This is the structure of the object that will be saved to ⁠portfolio_history.json each week.
 {
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "total_value_eur": 123456.78,
  "assets": [
    {
      "name": "Intel Corp",
      "quantity": 55,
      "purchase_price_total_eur": 2335.71,
      "current_value_eur": 1050.27,
      "category": "Tech"
    }
  ]
}
 Functions to Implement
1. ⁠create_portfolio_snapshot(normalized_data: list[dict])
	•	Purpose: Creates a complete snapshot of the portfolio at a single point in time. 	•	Parameters: ⁠normalized_data (the list of asset dictionaries from ⁠parse_and_normalize_data). 	•	Returns: ⁠dict that conforms to the Snapshot JSON Schema. 	•	Logic:
	a.	Generate a current UTC timestamp in ISO 8601 format. 	b.	Calculate ⁠total_value_eur by summing the ⁠current_value_eur of all assets in the input list. 	c.	Construct and return the final dictionary.
2. ⁠compare_snapshots(current_snapshot: dict, previous_snapshot: dict)
	•	Purpose: Performs the week-over-week comparison and generates a structured report object. 	•	Parameters: ⁠current_snapshot and ⁠previous_snapshot dictionaries. 	•	Returns: ⁠dict containing the full analysis. 	•	Logic:
	a.	Create sets of asset names from both snapshots for efficient comparison. 	b.	Identify Held, New, and Sold asset names using set operations. 	c.	Analyze Held Assets:
	▪	Iterate through the held names. 	▪	For each asset, find its corresponding data in both snapshots. 	▪	Calculate the change in ⁠current_value_eur. 	▪	Store these changes. 	▪	Sort the results to find the top 3 gainers and top 3 losers (by absolute EUR change).
	d.	Analyze New Assets:
	▪	For each new asset name, extract its full data object from the ⁠current_snapshot.
	e.	Analyze Sold Assets:
	▪	For each sold asset name, find its data in the ⁠previous_snapshot. 	▪	Calculate ⁠realized_gain_loss = previous_snapshot.current_value_eur - previous_snapshot.purchase_price_total_eur. This represents the gain/loss at the time of sale (approximated by the last snapshot's value).
	f.	Calculate Totals: Calculate the change in ⁠total_value_eur for the entire portfolio. 	g.	Construct and return a single dictionary containing all of this analyzed data. 	•	Output Report Data Schema:
 {
  "total_value_change_eur": float,
  "total_value_change_percent": float,
  "top_movers": [{"name": str, "change_eur": float}, ...],
  "bottom_movers": [{"name": str, "change_eur": float}, ...],
  "new_positions": [{"name": str, "quantity": float, "current_value_eur": float}, ...],
  "sold_positions": [{"name": str, "realized_gain_loss_eur": float}, ...]
}

Phase 4: Data Persistence in JSON
File: ⁠agent/storage.py
This module handles all file I/O for ⁠portfolio_history.json.
Functions to Implement
1. ⁠save_snapshot(snapshot_data: dict)
	•	Purpose: Appends a new snapshot to the ⁠portfolio_history.json file. 	•	Parameters: ⁠snapshot_data (a dictionary conforming to the Snapshot JSON Schema). 	•	Returns: ⁠None. 	•	Logic:
	a.	Read the entire ⁠portfolio_history.json file into a list. 	b.	If the file is empty or doesn't exist, initialize an empty list. 	c.	Append the new ⁠snapshot_data to this list. 	d.	Write the entire list back to the file, overwriting it.
2. ⁠get_latest_snapshot()
	•	Purpose: Retrieves the most recent snapshot from the history file. 	•	Parameters: None. 	•	Returns: ⁠dict (the latest snapshot object) or ⁠None if the file is empty. 	•	Logic:
	a.	Read the ⁠portfolio_history.json file into a list. 	b.	If the list is not empty, return the last element (⁠list[-1]). 	c.	If the list is empty, return ⁠None.
Phase 5: Automation and Reporting
File: ⁠agent/reporting.py
This module is responsible for creating the human-readable report.
Functions to Implement
1. ⁠format_report_markdown(report_data: dict, current_total_value: float)
	•	Purpose: Converts the analysis data object into a formatted Markdown string. 	•	Parameters:
	▪	⁠report_data: The dictionary returned by ⁠analysis.compare_snapshots. 	▪	⁠current_total_value: The total value from the current snapshot. 	•	Returns: ⁠str (a single multi-line string in Markdown format). 	•	Details: Use the data to construct a string identical to the example in the previous plan, using f-strings and proper formatting for currency and percentages.
File: ⁠agent/main.py
This is the main entry point where the ⁠fastmcp agent is defined and the scheduled task is orchestrated.
Main Workflow to Implement
	1.	Define an MCP Agent using ⁠fastmcp. 	2.	Create a Scheduled Function (⁠run_weekly_analysis) that will be decorated to run on a schedule (e.g., every Friday at 23:00 Europe/Tallinn). 	3.	Implement the ⁠run_weekly_analysis function:
	▪	Log the start of the process. 	▪	Call ⁠storage.get_latest_snapshot() to get the previous state. 	▪	Call ⁠sheets_connector.fetch_portfolio_data() and then ⁠sheets_connector.parse_and_normalize_data() to get the current state. 	▪	Call ⁠analysis.create_portfolio_snapshot() to create the new snapshot object. 	▪	Call ⁠storage.save_snapshot() to persist the new snapshot immediately. 	▪	Conditional Logic: If ⁠get_latest_snapshot returned data (i.e., this is not the first run):
	◦	Call ⁠analysis.compare_snapshots() with the new and previous snapshots. 	◦	Call ⁠reporting.format_report_markdown() with the result of the comparison. 	◦	Print the formatted Markdown report to the console/log. 	▪	If this is the first run, log a message indicating that the first snapshot has been created and the analysis will run next week. 	▪	Log the completion of the process.
