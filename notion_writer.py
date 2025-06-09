from notion_client import Client
from datetime import datetime
import os
notion_auth = os.getenv("NOTION_TOKEN")
notion = Client(auth=notion_auth)

DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def create_meeting_page(meeting_data: dict, analysis: dict):
    """Push one meeting’s analysis into the Team-Meetings database."""
    title = meeting_data.get("title", "Untitled Meeting")
    date  = meeting_data.get("date", datetime.now().isoformat())

    page = notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": date}}
        },
        children=[
            _heading("📝 Summary"),
            _paragraph(analysis["summary"]),
            _heading("👥 Participants"),
            * _bulleted_list(analysis["participants"].split(", ")),   # ⬅️ unpack list
            _heading("✅ Tasks"),
            * _task_blocks(analysis["tasks"]),                        # ⬅️ unpack list
            _heading("📆 Deadlines & Reminders"),
            * _markdown_blocks(analysis["deadlines"]),                # ⬅️ unpack list
            _heading("📌 Key Decisions"),
            * _markdown_blocks(analysis["decisions"]),                # ⬅️ unpack list
            _heading("💡 Insights & Recommendations"),
            * _markdown_blocks(analysis["insights"])                  # ⬅️ unpack list
        ]
    )
    print(f"Notion page created: {page['url']}")
    return page


# ---------- helper block builders (unchanged) ----------

def _heading(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }

def _paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }

def _bulleted_list(items):
    return [
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": item}}]
            }
        }
        for item in items if item.strip()
    ]

def _task_blocks(markdown_text):
    lines = markdown_text.splitlines()
    blocks = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("* **", "- **")):
            blocks.append(_paragraph(stripped.strip("*- ").replace("**", "")))
        elif stripped.startswith(("*", "-")) and stripped[1:].strip():
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": stripped.lstrip('*- ').strip()}}],
                    "checked": False
                }
            })
    return blocks

def _markdown_blocks(markdown_text):
    blocks = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("*", "-")):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": stripped.lstrip('*- ').strip()}}]
                }
            })
        else:
            blocks.append(_paragraph(stripped))
    return blocks
if __name__ == "__main__":
    import json

    with open("analysis/sample_analysis.json", "r") as f:
        analysis = json.load(f)

    meeting_data = {
        "title": "Team Sync – June 7",
        "date": "2025-06-07"
    }

    create_meeting_page(meeting_data, analysis)