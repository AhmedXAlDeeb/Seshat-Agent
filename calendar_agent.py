from notion_client import Client
from datetime import date, timedelta
import os

notion_auth = os.getenv("NOTION_TOKEN")
notion = Client(auth=notion_auth)

DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


def get_todays_meetings():
    today = date.today()                # this is a date object
    tomorrow = today + timedelta(days=1)  # add timedelta to date object
    today_str = today.isoformat()         # convert to string when needed
    tomorrow_str = tomorrow.isoformat()

    # Notion date filter format requires ISO 8601 string
    filter_payload = {
        "filter": {
            "and": [
                {
                    "property": "Date",  # change to your calendar's date property name
                    "date": {
                        "on_or_after": today.isoformat()
                    }
                },
                {
                    "property": "Date",
                    "date": {
                        "before": tomorrow.isoformat()
                    }
                }
            ]
        }
    }

    response = notion.databases.query(database_id=DATABASE_ID, **filter_payload)
    return response.get("results", [])
def print_meetings(meetings):
    if not meetings:
        print("No meetings found for today.")
        return

    print(f"Meetings today ({len(meetings)} found):")
    for m in meetings:
        props = m["properties"]
        title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "No title"
        date_start = props["Date"]["date"]["start"]
        date_end = props["Date"]["date"].get("end", "N/A")
        print(f"- {title}: {date_start} to {date_end}")
        
# For quick test
if __name__ == "__main__":
    meetings = get_todays_meetings()
    print_meetings(meetings)