from datetime import datetime, UTC, timedelta
import json

from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from src.helpers import get_garmin_client, get_notion_client


def get_weight_data(garmin_client: GarminClient, days: int = 30) -> list[dict]:
    """
    Get weight data from Garmin for the last n days.
    Returns a list of daily weight entries.
    """
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        print(f"Fetching weight data from {start_date} to {end_date}")
        response = garmin_client.get_body_composition(start_date, end_date)
        
        # The API returns a dict with "dateWeightList" containing the daily entries
        if isinstance(response, dict):
            weight_list = response.get("dateWeightList", [])
            
            if weight_list:
                print(f"Found {len(weight_list)} weight entries")
                return weight_list
            
            print("No weight entries found in dateWeightList")
            return []
        
        return []
    except Exception as e:
        print(f"Error fetching weight data: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_weight_entry(entry: dict) -> dict:
    """
    Format a raw Garmin weight entry into a structured format.
    Garmin returns weight/muscle/bone in grams, so convert to kg.
    """
    weight_grams = entry.get("weight")
    muscle_grams = entry.get("muscleMass")
    bone_grams = entry.get("boneMass")
    
    return {
        "date": entry.get("calendarDate"),
        "weight_kg": round(weight_grams / 1000, 2) if weight_grams else None,
        "bmi": entry.get("bmi"),
        "body_fat_percent": entry.get("bodyFat"),  # Already in percentage
        "muscle_mass_kg": round(muscle_grams / 1000, 2) if muscle_grams else None,
        "bone_mass_kg": round(bone_grams / 1000, 2) if bone_grams else None,
        "water_percent": entry.get("bodyWater"),  # Already in percentage
    }


def weight_entry_exists(
    notion_client: NotionClient,
    database_id: str,
    date: str,
) -> dict | None:
    """
    Check if a weight entry already exists in the Notion database for a given date.
    """
    query = notion_client.databases.query(
        database_id=database_id,
        filter={
            "property": "Date",
            "date": {"equals": date}
        }
    )
    results = query.get("results", [])
    return results[0] if results else None


def weight_entry_needs_update(existing: dict, new_data: dict) -> bool:
    """
    Compare existing weight data with new data to determine if an update is needed.
    """
    props = existing["properties"]
    
    # Check if any numeric fields have changed
    checks = [
        props.get("Weight (kg)", {}).get("number") != new_data["weight_kg"],
        props.get("BMI", {}).get("number") != new_data["bmi"],
    ]
    
    # Optional fields that may or may not exist
    if new_data["body_fat_percent"] is not None and new_data["body_fat_percent"] > 0:
        checks.append(
            props.get("Body Fat %", {}).get("number") != new_data["body_fat_percent"]
        )
    
    if new_data["muscle_mass_kg"] is not None and new_data["muscle_mass_kg"] > 0:
        checks.append(
            props.get("Muscle Mass (kg)", {}).get("number") != new_data["muscle_mass_kg"]
        )
    
    if new_data["bone_mass_kg"] is not None and new_data["bone_mass_kg"] > 0:
        checks.append(
            props.get("Bone Mass (kg)", {}).get("number") != new_data["bone_mass_kg"]
        )
    
    if new_data["water_percent"] is not None and new_data["water_percent"] > 0:
        checks.append(
            props.get("Water %", {}).get("number") != new_data["water_percent"]
        )
    
    return any(checks)


def create_weight_entry(
    notion_client: NotionClient,
    database_id: str,
    data: dict,
) -> None:
    """
    Create a new weight entry in the Notion database.
    """
    properties = {
        "Date": {"date": {"start": data["date"]}},
        "Weight (kg)": {"number": data["weight_kg"]},
        "BMI": {"number": data["bmi"]},
    }
    
    # Add optional fields if they have values (exclude 0 values which indicate missing data)
    if data["body_fat_percent"] is not None and data["body_fat_percent"] > 0:
        properties["Body Fat %"] = {"number": round(data["body_fat_percent"], 1)}
    
    if data["muscle_mass_kg"] is not None and data["muscle_mass_kg"] > 0:
        properties["Muscle Mass (kg)"] = {"number": data["muscle_mass_kg"]}
    
    if data["bone_mass_kg"] is not None and data["bone_mass_kg"] > 0:
        properties["Bone Mass (kg)"] = {"number": data["bone_mass_kg"]}
    
    if data["water_percent"] is not None and data["water_percent"] > 0:
        properties["Water %"] = {"number": round(data["water_percent"], 1)}
    
    try:
        notion_client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            icon={"emoji": "⚖️"}
        )
        print(f"Created weight entry for: {data['date']}")
    except Exception as e:
        print(f"Error creating weight entry: {e}")


def update_weight_entry(
    notion_client: NotionClient,
    existing: dict,
    new_data: dict,
) -> None:
    """
    Update an existing weight entry in the Notion database.
    """
    properties = {
        "Weight (kg)": {"number": new_data["weight_kg"]},
        "BMI": {"number": new_data["bmi"]},
    }
    
    # Add optional fields if they have values (exclude 0 values which indicate missing data)
    if new_data["body_fat_percent"] is not None and new_data["body_fat_percent"] > 0:
        properties["Body Fat %"] = {"number": round(new_data["body_fat_percent"], 1)}
    
    if new_data["muscle_mass_kg"] is not None and new_data["muscle_mass_kg"] > 0:
        properties["Muscle Mass (kg)"] = {"number": new_data["muscle_mass_kg"]}
    
    if new_data["bone_mass_kg"] is not None and new_data["bone_mass_kg"] > 0:
        properties["Bone Mass (kg)"] = {"number": new_data["bone_mass_kg"]}
    
    if new_data["water_percent"] is not None and new_data["water_percent"] > 0:
        properties["Water %"] = {"number": round(new_data["water_percent"], 1)}
    
    try:
        notion_client.pages.update(
            page_id=existing["id"],
            properties=properties
        )
        print(f"Updated weight entry for: {new_data['date']}")
    except Exception as e:
        print(f"Error updating weight entry: {e}")


def main():
    load_dotenv()

    # Initialize Garmin and Notion clients using environment variables
    garmin_client, _ = get_garmin_client()
    notion_client, notion_dbs = get_notion_client()

    database_id = notion_dbs.weight

    # Get weight data from the last 30 days
    weight_entries = get_weight_data(garmin_client, days=30)

    if not weight_entries:
        print("No weight data found for the last 30 days")
        return

    for entry in weight_entries:
        formatted_entry = format_weight_entry(entry)
        
        # Skip entries with missing critical data
        if formatted_entry["weight_kg"] is None or formatted_entry["bmi"] is None or formatted_entry["bmi"] == 0:
            print(f"Skipping entry for {formatted_entry['date']} - missing critical data")
            continue
        
        entry_date = formatted_entry["date"]
        existing_entry = weight_entry_exists(notion_client, database_id, entry_date)
        
        if existing_entry:
            if weight_entry_needs_update(existing_entry, formatted_entry):
                update_weight_entry(notion_client, existing_entry, formatted_entry)
        else:
            create_weight_entry(notion_client, database_id, formatted_entry)


if __name__ == "__main__":
    main()
