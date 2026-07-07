# Weight and Body Composition Tracking

This document explains the new weight and body composition tracking feature added to the Garmin to Notion integration.

## Overview

The weight tracking feature automatically syncs your Garmin weight and body composition data to a dedicated Notion database. This includes:

- **Weight (kg)** - Your body weight in kilograms
- **BMI** - Body Mass Index
- **Body Fat %** - Percentage of body fat (if available)
- **Muscle Mass (kg)** - Lean muscle mass (if available)
- **Bone Mass (kg)** - Bone mass (if available)
- **Water %** - Percentage of body water (if available)

## Files Added

### `src/workflows/weight-tracking.py`

The main workflow script that:
- Fetches weight and body composition data from Garmin (last 30 days)
- Formats the data consistently
- Checks if entries already exist in Notion
- Creates new entries or updates existing ones as needed
- Handles missing optional fields gracefully

**Key Functions:**
- `get_weight_data()` - Retrieves weight data from Garmin
- `format_weight_entry()` - Formats raw Garmin data
- `weight_entry_exists()` - Checks for existing Notion entries by date
- `weight_entry_needs_update()` - Compares old vs new data
- `create_weight_entry()` - Creates new Notion pages
- `update_weight_entry()` - Updates existing Notion pages

## Files Modified

### `src/helpers/_get_notion_client.py`

Added `weight` field to the `NotionDatabases` dataclass to support the new database ID:

```python
@dataclass(frozen=True)
class NotionDatabases:
    activities: str
    personal_records: str
    sleep: str
    daily_steps: str
    strength: str
    weight: str  # NEW
```

And added environment variable configuration:

```python
weight=os.getenv("NOTION_WEIGHT_DB_ID"),
```

### `.example.env`

Added new environment variables:

```env
# The ID of your Notion database for sleep data.
NOTION_SLEEP_DB_ID=CHANGEME
# The ID of your Notion database for strength training.
NOTION_STRENGTH_DB_ID=CHANGEME
# The ID of your Notion database for weight and body composition.
NOTION_WEIGHT_DB_ID=CHANGEME
```

## Setup Instructions

### Step 1: Create Notion Database

Create a new Notion database with the following properties:

| Property Name | Type | Notes |
|---|---|---|
| Date | Date | Primary key |
| Weight (kg) | Number | Required |
| BMI | Number | Required |
| Body Fat % | Number | Optional |
| Muscle Mass (kg) | Number | Optional |
| Bone Mass (kg) | Number | Optional |
| Water % | Number | Optional |

### Step 2: Add GitHub Secret

1. Copy your Notion database ID from the URL
2. Go to your repository Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. **Name:** `NOTION_WEIGHT_DB_ID`
5. **Value:** Your Notion database ID
6. Click "Add secret"

### Step 3: Update Local Environment

Add the following to your `.env` file:

```env
NOTION_WEIGHT_DB_ID=your_database_id_here
```

### Step 4: Run the Workflow

The weight tracking script runs automatically as part of the daily sync workflow. You can also manually trigger it:

```bash
uv run python -m src.workflows.weight-tracking
```

## Data Handling

### Missing Data

- **Critical fields** (Weight, BMI): Entries with missing values are skipped
- **Optional fields** (Body Fat %, Muscle Mass, etc.): Only included if available
- Empty Notion properties won't be created for missing data

### Updates

The script compares existing entries with new data:
- If any field has changed, the entry is updated
- If no changes detected, the entry is skipped
- Updates preserve the Date property

### Date Handling

Weight entries are keyed by date from Garmin. Only one entry per date is allowed. If multiple measurements occur on the same date, only the latest will be stored.

## Garmin Data

The script uses Garmin's `get_body_composition()` API method, which returns:
- Up to 30 days of historical data (configurable)
- Only measurements that have been recorded in Garmin Connect
- Data is automatically refreshed when you sync your Garmin device

## Troubleshooting

### No data syncing?

1. **Check Garmin data**: Ensure you have weight measurements recorded in Garmin Connect
2. **Verify database ID**: Confirm `NOTION_WEIGHT_DB_ID` is correct
3. **Check permissions**: Ensure your Notion integration has access to the database
4. **Run manually**: Execute `uv run python -m src.workflows.weight-tracking` and check for error messages

### Getting 401/403 errors?

These indicate authentication issues:
- Verify `NOTION_TOKEN` is correct and hasn't expired
- Verify `GARMIN_AUTH_TOKEN` is valid
- Check that the Notion integration is shared with your workspace

### Fields not showing up?

Optional fields (Body Fat %, Muscle Mass, etc.) only appear if:
1. Your Garmin device supports measuring them
2. You've recorded measurements with those metrics
3. Garmin is returning the data in the API response

## Future Enhancements

Potential improvements:
- Add weight trend analysis (weekly/monthly averages)
- Add goal tracking capabilities
- Add visual charts in Notion
- Support for multiple weight scale devices
- Historical data backfill option

