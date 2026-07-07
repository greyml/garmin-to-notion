from datetime import datetime, UTC

from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from src.helpers import get_garmin_client, get_notion_client


def get_weight_data(garmin_client: GarminClient, days: int = 30) -> list[dict]:
    """
    Get weight data from Garmin for the last n days.
    """
    try:
        weight_data = garmin_client.get_body_composition(days)
        return weight_data if weight_data else []
    except Exception as e:
        print(f"Error fetching weight data: {e}")
        return []


def format_weight_entry(entry: dict) -> dict:
    """
    Format a raw Garmin weight entry into a structured format.
    """
    return {
        "date": entry.get("date"),
        "weight_kg": entry.get("weight"),
        "bmi": entry.get("bmi"),
        "body_fat_percent": entry.get("bodyFatPercent"),
        "muscle_mass_kg": entry.get("muscleMass"),
        "bone_mass_kg": entry.get("boneMass"),
        "water_percent": entry.get("waterPercent"),
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
    if new_data["body_fat_percent"] is not None:
        checks.append(
            props.get("Body Fat %", {}).get("number") != new_data["body_fat_percent"]
        )
    
    if new_data["muscle_mass_kg"] is not None:
        checks.append(
            props.get("Muscle Mass (kg)", {}).get("number") != new_data["muscle_mass_kg"]
        )
    
    if new_data["bone_mass_kg"] is not None:
        checks.append(
            props.get("Bone Mass (kg)", {}).get("number") != new_data["bone_mass_kg"]
        )
    
    if new_data["water_percent"] is not None:
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
    
    # Add optional fields if they have values
    if data["body_fat_percent"] is not None:
        properties["Body Fat %"] = {"number": round(data["body_fat_percent"], 1)}
    
    if data["muscle_mass_kg"] is not None:
        properties["Muscle Mass (kg)"] = {"number": round(data["muscle_mass_kg"], 2)}
    
    if data["bone_mass_kg"] is not None:
        properties["Bone Mass (kg)"] = {"number": round(data["bone_mass_kg"], 2)}
    
    if data["water_percent"] is not None:
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
    
    # Add optional fields if they have values
    if new_data["body_fat_percent"] is not None:
        properties["Body Fat %"] = {"number": round(new_data["body_fat_percent"], 1)}
    
    if new_data["muscle_mass_kg"] is not None:
        properties["Muscle Mass (kg)"] = {"number": round(new_data["muscle_mass_kg"], 2)}
    
    if new_data["bone_mass_kg"] is not None:
        properties["Bone Mass (kg)"] = {"number": round(new_data["bone_mass_kg"], 2)}
    
    if new_data["water_percent"] is not None:
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

    for entry in weight_entries:
        formatted_entry = format_weight_entry(entry)
        
        # Skip entries with missing critical data
        if formatted_entry["weight_kg"] is None or formatted_entry["bmi"] is None:
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
