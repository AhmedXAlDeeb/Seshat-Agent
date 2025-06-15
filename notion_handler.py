import os
from datetime import datetime

# Attempt to import Notion client, provide guidance if not installed
try:
    from notion_client import Client, APIErrorCode, APIResponseError
except ImportError:
    print("Error: The 'notion-client' library is not installed. Please install it by running: pip install notion-client")
    Client = None # Set to None for conditional checks
    APIErrorCode = None
    APIResponseError = None

class NotionHandler:
    """
    Handles interactions with the Notion API to create pages.
    """

    def __init__(self, api_key: str, database_id: str):
        """
        Initializes the NotionHandler.

        Args:
            api_key: The Notion integration token (API key).
            database_id: The ID of the Notion database where pages will be created.

        Raises:
            ValueError: If api_key or database_id is not provided.
            RuntimeError: If the Notion client library is not installed or fails to initialize.
        """
        if not Client: # Check if import failed
            raise RuntimeError(
                "Notion client library (notion-client) is not installed. "
                "Please install it: pip install notion-client"
            )
        if not api_key:
            raise ValueError("Notion API key not provided.")
        if not database_id:
            raise ValueError("Notion Database ID not provided.")

        self.api_key = api_key
        self.database_id = database_id
        try:
            self.notion = Client(auth=self.api_key)
            # Test connection by trying to retrieve the database (optional, but good for early feedback)
            self.notion.databases.retrieve(database_id=self.database_id)
            print("Notion client initialized and database connection verified successfully.")
        except APIResponseError as e:
            if e.code == APIErrorCode.Unauthorized:
                raise RuntimeError(f"Notion API Error: Unauthorized. Check your API key. Details: {e}") from e
            elif e.code == APIErrorCode.ObjectNotFound:
                 raise RuntimeError(f"Notion API Error: Database not found. Check your Database ID '{self.database_id}'. Details: {e}") from e
            else:
                raise RuntimeError(f"Notion API Error during initialization. Details: {e}") from e
        except Exception as e: # Catch other potential errors like network issues during client init
            raise RuntimeError(f"Failed to initialize Notion client: {e}") from e

    # --- Notion Block Helper Methods ---
    def _rich_text_object(self, text_content: str, link_url: str = None) -> list:
        obj = {"type": "text", "text": {"content": text_content}}
        if link_url:
            obj["text"]["link"] = {"url": link_url}
        return [obj]

    def _heading(self, level: int, text_content: str) -> dict:
        if level not in [1, 2, 3]:
            raise ValueError("Heading level must be 1, 2, or 3.")
        return {
            f"heading_{level}": {
                "rich_text": self._rich_text_object(text_content),
                "color": "default"
            }
        }

    def _paragraph(self, text_content: str, link_url: str = None) -> dict:
        if not text_content: # Notion API errors if text content is empty for a paragraph
             return { "paragraph": {"rich_text": [{"type": "text", "text": {"content": " "}}]}} # Send a space
        return {
            "paragraph": {
                "rich_text": self._rich_text_object(text_content, link_url),
                "color": "default"
            }
        }

    def _todo_item(self, text_content: str, checked: bool = False) -> dict:
        return {
            "to_do": {
                "rich_text": self._rich_text_object(text_content),
                "checked": checked,
                "color": "default"
            }
        }

    def _bulleted_list_item(self, text_content: str) -> dict:
        return {
            "bulleted_list_item": {
                "rich_text": self._rich_text_object(text_content),
                "color": "default"
            }
        }

    def _split_text_into_chunks(self, text: str, chunk_size: int = 2000) -> list[str]:
        """Splits text into chunks for Notion's block limits."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _toggle_block_with_text_content(self, heading_text: str, content_text: str) -> dict:
        """Creates a toggle block with potentially long text content split into multiple paragraph blocks."""
        content_chunks = self._split_text_into_chunks(content_text)
        if not content_chunks: # if content_text is empty
            content_chunks = [" "] # Add a space to avoid empty children array

        children_blocks = [{"paragraph": {"rich_text": self._rich_text_object(chunk)}} for chunk in content_chunks]

        return {
            "toggle": {
                "rich_text": self._rich_text_object(heading_text),
                "color": "default",
                "children": children_blocks
            }
        }

    def create_notion_page(
        self,
        title: str,
        date_iso: str,
        summary: str,
        action_items: list[str],
        transcript: str,
        source_filename: str
    ) -> str:
        """
        Creates a new page in the configured Notion database.

        Args:
            title: The title of the Notion page.
            date_iso: The date for the 'Date' property (ISO 8601 string, e.g., "YYYY-MM-DD").
            summary: The summary text.
            action_items: A list of action item strings.
            transcript: The full transcript text.
            source_filename: The name of the source audio file.

        Returns:
            The URL of the created Notion page, or an error message string if creation fails.
        """
        print(f"Attempting to create Notion page titled: '{title}'")

        page_properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": date_iso}}, # Assumes 'Date' is a Date type property
            "Source File": {"rich_text": [{"text": {"content": source_filename}}]} # Assumes 'Source File' is a Rich Text or Text type property
            # Add other properties as needed, ensuring they match your Notion DB schema
        }

        # Construct page content blocks
        page_content_blocks = []

        # Summary
        page_content_blocks.append(self._heading(2, "Summary"))
        page_content_blocks.append(self._paragraph(summary if summary else "No summary generated."))

        # Action Items
        page_content_blocks.append(self._heading(2, "Action Items"))
        if action_items:
            for item in action_items:
                page_content_blocks.append(self._todo_item(item))
        else:
            page_content_blocks.append(self._paragraph("No action items identified."))

        # Transcript
        page_content_blocks.append(self._heading(2, "Transcript"))
        page_content_blocks.append(self._toggle_block_with_text_content(
            "Full Transcript",
            transcript if transcript else "Transcript not available."
        ))

        try:
            created_page = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=page_properties,
                children=page_content_blocks
            )
            page_url = created_page.get("url", "URL not found in response")
            print(f"Successfully created Notion page: {page_url}")
            return page_url
        except APIResponseError as e:
            error_msg = f"Notion API Error while creating page: {e.code} - {e.body}"
            print(error_msg)
            # You could parse e.body for more specific messages if needed
            return error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred while creating Notion page: {e}"
            print(error_msg)
            return error_msg


if __name__ == "__main__":
    print("--- Testing NotionHandler ---")

    # These tests require NOTION_API_KEY and NOTION_DATABASE_ID environment variables.
    # The database should have at least:
    # - 'Name' (Title property)
    # - 'Date' (Date property)
    # - 'Source File' (Text or Rich Text property)

    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_api_key or not notion_database_id:
        print("Skipping NotionHandler live tests: NOTION_API_KEY or NOTION_DATABASE_ID environment variables not set.")
        print("Please set these variables to run these tests:")
        print("  export NOTION_API_KEY='your_notion_api_key'")
        print("  export NOTION_DATABASE_ID='your_notion_database_id'")
    else:
        print(f"Using Notion API Key (last 5 chars): ...{notion_api_key[-5:]}")
        print(f"Using Notion Database ID (last 5 chars): ...{notion_database_id[-5:]}")

        handler = None
        # Test 1: Initialization
        print("\n1. Test Initialization")
        try:
            handler = NotionHandler(api_key=notion_api_key, database_id=notion_database_id)
            print("NotionHandler initialized successfully.")
        except Exception as e:
            print(f"Initialization failed: {e}")
            # If init fails, handler remains None, subsequent tests will be skipped.

        if handler:
            # Test 2: Create a Notion Page
            print("\n2. Test Create Notion Page")
            try:
                # Get current date for the 'Date' property
                current_date_iso = datetime.now().strftime("%Y-%m-%d")

                page_title = f"Test Note - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                summary_text = "This is a test summary generated by the NotionHandler automated test."
                action_items_list = [
                    "Follow up on Test Action 1.",
                    "Complete Test Task B before EOD.",
                    "Review the test document."
                ]
                transcript_text = "This is the full transcript of the test meeting. " * 50 # Make it a bit long for toggle
                transcript_text += "\nAnother paragraph in the transcript." * 30
                source_file = "test_audio_sample.mp3"

                page_url_or_error = handler.create_notion_page(
                    title=page_title,
                    date_iso=current_date_iso,
                    summary=summary_text,
                    action_items=action_items_list,
                    transcript=transcript_text,
                    source_filename=source_file
                )

                if "https://" in page_url_or_error:
                    print(f"Page created successfully! URL: {page_url_or_error}")
                    # You would typically go to the URL to verify.
                    # For automated tests, you might use the Notion API to retrieve the page and check its content,
                    # but that's more involved.
                else:
                    print(f"Page creation failed: {page_url_or_error}")

                assert "https://" in page_url_or_error, f"Page creation seems to have failed. Response: {page_url_or_error}"

            except Exception as e:
                print(f"An unexpected error occurred during page creation test: {e}")

            # Test 3: Create a page with minimal data (e.g., no action items)
            print("\n3. Test Create Notion Page with Minimal Data")
            try:
                current_date_iso = datetime.now().strftime("%Y-%m-%d")
                page_title_minimal = f"Minimal Test Note - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

                page_url_minimal = handler.create_notion_page(
                    title=page_title_minimal,
                    date_iso=current_date_iso,
                    summary="Minimal summary.",
                    action_items=[], # No action items
                    transcript="Short transcript.",
                    source_filename="minimal_test.wav"
                )
                if "https://" in page_url_minimal:
                    print(f"Minimal page created successfully! URL: {page_url_minimal}")
                else:
                    print(f"Minimal page creation failed: {page_url_minimal}")
                assert "https://" in page_url_minimal, f"Minimal page creation failed. Response: {page_url_minimal}"

            except Exception as e:
                print(f"An unexpected error occurred during minimal page creation test: {e}")

    # Test 4: Initialization with missing credentials
    print("\n4. Test Initialization with Missing Credentials")
    try:
        NotionHandler(api_key="", database_id="fakedbid")
        print("ERROR: NotionHandler initialized with empty API key (unexpected).")
    except ValueError as e:
        print(f"Caught expected ValueError for empty API key: {e}")
    except Exception as e:
        print(f"Caught unexpected error for empty API key test: {e}")

    try:
        NotionHandler(api_key="fakekey", database_id="")
        print("ERROR: NotionHandler initialized with empty Database ID (unexpected).")
    except ValueError as e:
        print(f"Caught expected ValueError for empty Database ID: {e}")
    except Exception as e:
        print(f"Caught unexpected error for empty Database ID test: {e}")

    print("\n--- NotionHandler tests finished ---")
