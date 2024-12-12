import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

# Constants
API_VERSION = "v16.0"
API_URL = f"https://graph.facebook.com/{API_VERSION}"
LOG_FILE = "error_log.txt"

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def validate_access_token(access_token):
    """
    Validates the Facebook Access Token using the debug_token endpoint.

    Args:
        access_token (str): Facebook API Access Token.

    Returns:
        bool: True if valid, False otherwise.
    """
    url = f"{API_URL}/debug_token"
    params = {
        "input_token": access_token,
        "access_token": access_token,  # Typically, app access token should be used here
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        is_valid = data.get("data", {}).get("is_valid", False)
        if is_valid:
            print("Access Token is valid.")
            return True
        else:
            print("Invalid Access Token. Please check your credentials.")
            return False
    except requests.RequestException as e:
        logging.error(f"Error validating Access Token: {e}")
        print("Failed to validate Access Token. Check the error log for details.")
        return False


def get_group_members(group_id, access_token, batch_size=500):
    """
    Fetches members of the Facebook group using the Graph API with pagination.

    Args:
        group_id (str): Facebook Group ID.
        access_token (str): Facebook API Access Token.
        batch_size (int, optional): Number of members to fetch per request. Defaults to 500.

    Returns:
        list: List of group members.
    """
    url = f"{API_URL}/{group_id}/members"
    params = {"access_token": access_token, "limit": batch_size}
    members = []
    while url:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            members_batch = data.get("data", [])
            members.extend(members_batch)
            print(f"Fetched {len(members)} members so far...")
            url = data.get("paging", {}).get("next")
            params = {}  # Subsequent pages already include necessary parameters
        except requests.RequestException as e:
            logging.error(f"Error fetching group members: {e}")
            print("An error occurred while fetching group members. Check the error log for details.")
            break
    return members


def fetch_metadata_batch(member_ids, access_token):
    """
    Fetches metadata for a batch of member IDs using the Graph API.

    Args:
        member_ids (list): List of member IDs.
        access_token (str): Facebook API Access Token.

    Returns:
        dict: Metadata of members keyed by member ID.
    """
    ids = ",".join(member_ids)
    params = {
        "ids": ids,
        "fields": "id,name,location",
        "access_token": access_token,
    }
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching metadata batch: {e}")
        return {}


def filter_members_by_location(members, target_location, access_token, batch_size=50):
    """
    Filters members by a specified location using batch requests.

    Args:
        members (list): List of group members.
        target_location (str): Target location to filter members.
        access_token (str): Facebook API Access Token.
        batch_size (int, optional): Number of members per batch. Defaults to 50.

    Returns:
        list: Filtered list of members matching the target location.
    """
    filtered = []
    total_members = len(members)
    print(f"Filtering {total_members} members by location: {target_location}...")
    for i in range(0, total_members, batch_size):
        batch = members[i:i + batch_size]
        member_ids = [member["id"] for member in batch]
        metadata_batch = fetch_metadata_batch(member_ids, access_token)
        for member_id, metadata in metadata_batch.items():
            location = metadata.get("location", {}).get("name", "")
            if location.lower() == target_location.lower():
                filtered.append(metadata)
        print(f"Processed {min(i + batch_size, total_members)} / {total_members} members...")
    return filtered


def display_members_for_selection(members):
    """
    Displays the list of filtered members and allows the user to select members for removal.

    Args:
        members (list): List of filtered members.

    Returns:
        list: List of selected members to remove.
    """
    if not members:
        print("No members found matching the specified location.")
        return []

    print("\nFiltered Members:")
    for i, member in enumerate(members, start=1):
        name = member.get('name', 'Unknown')
        member_id = member.get('id', 'Unknown')
        location = member.get('location', {}).get('name', 'Unknown')
        print(f"{i}. Name: {name} | ID: {member_id} | Location: {location}")

    while True:
        selection = input(
            "\nSelect members to remove (e.g., 1,3,5 or 'all' to remove all, 'none' to cancel): "
        ).strip().lower()
        if selection == "all":
            return members
        elif selection == "none":
            return []
        else:
            try:
                indices = [int(index.strip()) - 1 for index in selection.split(",")]
                selected_members = [members[i] for i in indices if 0 <= i < len(members)]
                if selected_members:
                    return selected_members
                else:
                    print("No valid members selected. Please try again.")
            except (ValueError, IndexError):
                print("Invalid input. Please enter valid indices separated by commas, 'all', or 'none'.")


def remove_member(group_id, user_id, access_token):
    """
    Removes a member from the Facebook group.

    Args:
        group_id (str): Facebook Group ID.
        user_id (str): User ID of the member to remove.
        access_token (str): Facebook API Access Token.

    Returns:
        bool: True if removal was successful, False otherwise.
    """
    url = f"{API_URL}/{group_id}/members/{user_id}"
    try:
        response = requests.delete(url, params={"access_token": access_token})
        if response.status_code == 200:
            print(f"Successfully removed user {user_id}")
            return True
        else:
            logging.error(f"Error removing user {user_id}: {response.status_code} - {response.text}")
            return False
    except requests.RequestException as e:
        logging.error(f"Error during removal of user {user_id}: {e}")
        return False


def remove_members_concurrently(group_id, members_to_remove, access_token, max_workers=5):
    """
    Removes members concurrently using multi-threading.

    Args:
        group_id (str): Facebook Group ID.
        members_to_remove (list): List of members to remove.
        access_token (str): Facebook API Access Token.
        max_workers (int, optional): Number of threads. Defaults to 5.
    """
    total = len(members_to_remove)
    print(f"Initiating removal of {total} members...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_member = {
            executor.submit(remove_member, group_id, member["id"], access_token): member
            for member in members_to_remove
        }
        for future in as_completed(future_to_member):
            member = future_to_member[future]
            try:
                success = future.result()
                if not success:
                    print(f"Failed to remove user {member['id']}. Check the log for details.")
            except Exception as e:
                logging.error(f"Unhandled exception removing member {member['id']}: {e}")
                print(f"An error occurred while removing user {member['id']}. Check the log for details.")

    print("Member removal process completed.")


def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Manage Facebook group members.")
    parser.add_argument(
        "--group-id",
        required=True,
        help="Facebook Group ID",
    )
    parser.add_argument(
        "--access-token",
        required=True,
        help="Facebook API Access Token",
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Target location to filter members",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Validate Access Token
    if not validate_access_token(args.access_token):
        sys.exit(1)

    # Fetch group members
    print("Fetching group members...")
    members = get_group_members(args.group_id, args.access_token)
    if not members:
        print("No members fetched. Exiting.")
        sys.exit(1)
    print(f"Total members fetched: {len(members)}")

    # Filter members by location
    filtered_members = filter_members_by_location(members, args.location, args.access_token)
    print(f"Total filtered members: {len(filtered_members)}")

    # Display and select members for removal
    members_to_remove = display_members_for_selection(filtered_members)
    print(f"Selected {len(members_to_remove)} members for removal.")

    if not members_to_remove:
        print("No members selected for removal. Exiting.")
        sys.exit(0)

    # Remove selected members
    remove_members_concurrently(args.group_id, members_to_remove, args.access_token)


if __name__ == "__main__":
    main()
