import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import time
import math

# Constants
API_URL = "https://graph.facebook.com/v16.0"
LOG_FILE = "error_log.txt"

# Set up error logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def validate_access_token(access_token):
    """
    Validates the Facebook Access Token.
    """
    url = f"{API_URL}/debug_token"
    params = {"input_token": access_token, "access_token": access_token}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("data", {}).get("is_valid"):
            print("Access Token is valid.")
            return True
        else:
            print("Invalid Access Token. Check your credentials.")
            return False
    except requests.RequestException as e:
        logging.error(f"Error validating Access Token: {e}")
        print("Failed to validate Access Token. Check error log for details.")
        return False

def get_group_members(group_id, access_token, batch_size=500):
    """
    Fetches members of the Facebook group using Graph API with batching.
    """
    url = f"{API_URL}/{group_id}/members"
    params = {"access_token": access_token, "limit": batch_size}
    members = []
    while url:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            members.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
        except requests.RequestException as e:
            logging.error(f"Error fetching group members: {e}")
            break
    return members

def fetch_metadata_batch(member_ids, access_token):
    """
    Fetches metadata for a batch of member IDs using Graph API.
    """
    url = f"{API_URL}"
    ids = ",".join(member_ids)
    params = {
        "ids": ids,
        "fields": "id,name,location",
        "access_token": access_token
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching metadata batch: {e}")
        return {}

def filter_members_by_location(members, target_location, access_token, batch_size=50):
    """
    Filters members by location using batch requests.
    """
    filtered = []
    for i in range(0, len(members), batch_size):
        batch = members[i:i + batch_size]
        member_ids = [member["id"] for member in batch]
        metadata_batch = fetch_metadata_batch(member_ids, access_token)
        for member_id, metadata in metadata_batch.items():
            if metadata.get("location", {}).get("name") == target_location:
                filtered.append(metadata)
    return filtered

def display_members_for_selection(members):
    """
    Displays the list of members and allows the user to select members for removal.
    """
    print("\nFiltered Members:")
    for i, member in enumerate(members, start=1):
        print(f"{i}. Name: {member.get('name', 'Unknown')} | ID: {member['id']} | Location: {member.get('location', {}).get('name', 'Unknown')}")
    
    while True:
        selection = input("\nSelect members to remove (comma-separated indices, 'all' to remove all, or 'none'): ").strip()
        if selection.lower() == "all":
            return members
        elif selection.lower() == "none":
            return []
        else:
            try:
                indices = [int(index.strip()) - 1 for index in selection.split(",")]
                return [members[i] for i in indices if 0 <= i < len(members)]
            except (ValueError, IndexError):
                print("Invalid selection. Please try again.")

def remove_member(group_id, user_id, access_token):
    """
    Removes a member from the Facebook group.
    """
    url = f"{API_URL}/{group_id}/members/{user_id}"
    try:
        response = requests.delete(url, params={"access_token": access_token})
        if response.status_code == 200:
            print(f"Successfully removed user {user_id}")
        else:
            logging.error(f"Error removing user {user_id}: {response.status_code}, {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error during removal of user {user_id}: {e}")

def remove_members_concurrently(group_id, members_to_remove, access_token, batch_size=10):
    """
    Removes members concurrently using multi-threading and batching.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i in range(0, len(members_to_remove), batch_size):
            batch = members_to_remove[i:i + batch_size]
            for member in batch:
                futures.append(executor.submit(remove_member, group_id, member["id"], access_token))
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error removing member: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Facebook group members.")
    parser.add_argument("--group-id", required=True, help="Facebook Group ID")
    parser.add_argument("--access-token", required=True, help="Facebook API Access Token")
    parser.add_argument("--location", required=True, help="Target location to filter members")
    args = parser.parse_args()

    # Validate Access Token
    if not validate_access_token(args.access_token):
        sys.exit(1)

    # Fetch group members
    print("Fetching group members...")
    members = get_group_members(args.group_id, args.access_token)

    # Filter members by location
    print("Filtering members by location...")
    filtered_members = filter_members_by_location(members, args.location, args.access_token)
    print(f"Total filtered members: {len(filtered_members)}")

    # Display and select members for removal
    members_to_remove = display_members_for_selection(filtered_members)
    print(f"Selected {len(members_to_remove)} members for removal.")

    # Remove selected members
    print("Removing selected members...")
    remove_members_concurrently(args.group_id, members_to_remove, args.access_token)
    print("Task completed.")

