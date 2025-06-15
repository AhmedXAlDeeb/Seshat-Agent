# Voice2Notion (Backend)

The Python backend for Voice2Notion, a tool designed to automate the creation of meeting notes from audio recordings directly into your Notion workspace. It processes audio files, transcribes them, extracts summaries and action items using AI, and then populates a Notion database with structured notes.

Core capabilities include:
*   Processes a folder of audio recordings.
*   Transcribes audio using configurable services (OpenAI Whisper, Google Cloud Speech-to-Text).
*   Summarizes content and extracts action items using Google Gemini.
*   Creates new pages in a specified Notion database.

## Features

*   **Batch Processing:** Efficiently handles multiple audio files from a specified folder.
*   **Multiple Transcription Services:** Supports OpenAI Whisper (built-in, local processing) and Google Cloud Speech-to-Text. Easily extensible for more services.
*   **AI-Powered Analysis:** Leverages Google Gemini for intelligent summarization and action item extraction from transcripts.
*   **Direct Notion Integration:** Creates well-structured pages in your Notion database via the official Notion API.
*   **Flexible Configuration:** Settings are managed via a JSON file (`~/.voice2notion/settings.json`), allowing customization of API keys, service choices, and model parameters.
*   **Command-Line Interface:** Provides a CLI for initiating processing and managing settings.
*   **Designed for UI Integration:** Can be easily called and controlled by a separate user interface application.

## How it Works (Backend Flow)

1.  **Input:** The application takes a path to a folder containing audio files as input.
2.  **Iteration:** It iterates through each supported audio file in the folder.
3.  **Processing Per File:**
    *   **Transcription:** The audio is transcribed to text using the selected transcription service (e.g., Whisper).
    *   **Analysis:** The transcript is then sent to Google Gemini to generate a concise summary and a list of action items.
    *   **Notion Page Creation:** A new page is created in the configured Notion database.
        *   The **title** of the page is derived from the audio filename.
        *   The **date** property is set based on the audio file's modification date (this can be overridden).
        *   The page **content** includes the generated summary, a checklist of action items, and the full transcript within a toggle block.

## System Requirements

*   **Python:** Version 3.8 or higher.
*   **`ffmpeg`:** Must be installed and accessible in your system's PATH. This is crucial for audio format conversion, primarily used by the Whisper transcriber.
*   **Service-Specific Dependencies:**
    *   **OpenAI Whisper:** No additional external service setup beyond `ffmpeg` and Python dependencies.
    *   **Google Cloud Speech-to-Text:** Requires a Google Cloud Platform project with the Speech-to-Text API enabled and a service account key JSON file.
    *   **Google Gemini:** Requires a Google API Key with the Gemini API enabled.

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/voice2notion-backend.git # Replace with actual URL
    cd voice2notion-backend
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration (`~/.voice2notion/settings.json`)

The application stores its configuration in a JSON file located at `~/.voice2notion/settings.json`.
If this file or directory does not exist, the application will attempt to create it with default values when `orchestrator.py` is run or certain configuration commands are used.

**Example `settings.json` structure:**
(Note: The `orchestrator.py` currently uses a flat structure for `whisper_model_size` and `google_stt_api_key_path`. The nested `transcription_settings` is a suggested improvement for future config structure.)
```json
{
    "notion_api_key": "YOUR_NOTION_INTEGRATION_TOKEN",
    "notion_database_id": "YOUR_NOTION_DATABASE_ID",
    "gemini_api_key": "YOUR_GEMINI_API_KEY",
    "transcription_service": "OpenAI Whisper", // or "Google Cloud Speech-to-Text"
    "whisper_model_size": "base", // tiny, base, small, medium, large
    "google_stt_api_key_path": "/path/to/your/google_cloud_credentials.json",
    "google_stt_language_code": "en-US", // Example for Google STT
    "audio_input_folder": "/path/to/your/default/audio_files_folder",
    "default_audio_formats": [ // UI hint, not directly used by current backend logic
        ".m4a",
        ".mp3",
        ".wav",
        ".aac",
        ".flac",
        ".opus",
        ".ogg"
    ]
}
```

**Key Configuration Fields:**

*   `notion_api_key`: Your Notion integration token.
*   `notion_database_id`: The ID of your Notion database where pages will be created.
*   `gemini_api_key`: Your API key for Google Gemini (e.g., from Google AI Studio).
*   `transcription_service`: Choose between `"OpenAI Whisper"` or `"Google Cloud Speech-to-Text"`.
*   `whisper_model_size`: (For "OpenAI Whisper") Specifies the model size.
*   `google_stt_api_key_path`: (For "Google Cloud Speech-to-Text") Path to your Google Cloud service account JSON key file.
*   `google_stt_language_code`: (For "Google Cloud Speech-to-Text") Language code for transcription.
*   `audio_input_folder`: (Optional) A default folder to scan if no path is provided via CLI.


**Note on API Keys:**
*   **Notion:** Create an internal integration in Notion and get the "Internal Integration Token". Share your target database with this integration. The database ID can be extracted from the database URL.
*   **Gemini:** Obtain your API key from Google AI Studio (formerly MakerSuite).
*   **Google STT:** Follow Google Cloud documentation to set up a project, enable the Speech-to-Text API, and download a service account key.

## Usage (CLI)

The primary way to run the backend is through `orchestrator.py`.

**Main command:**
```bash
python orchestrator.py /path/to/your/audio/folder
```
If `/path/to/your/audio/folder` is omitted, it will try to use `audio_input_folder` from settings, or default to the current directory.

**Optional arguments to override settings:**
*   `--notion-api-key YOUR_KEY`: Overrides the Notion API key from settings.
*   `--notion-db-id YOUR_DB_ID`: Overrides the Notion Database ID.
*   `--gemini-api-key YOUR_GEMINI_KEY`: Overrides the Gemini API key.
*   `--whisper-model MODEL_NAME`: Overrides the Whisper model size (e.g., `base`).
*   `--help`: Shows all available command-line options.

**Example Output (Conceptual):**
```
--- Voice2Notion Initializing ---
Using audio input folder from CLI argument: recordings/
Initializing services...
OpenAI Whisper initialized.
SummarizerService (Gemini) initialized.
NotionHandler initialized.
Service initialization complete.

--- Starting to process folder: recordings/ ---
Found audio file: Meeting_2023-10-26.m4a
--- Processing audio file: Meeting_2023-10-26.m4a ---
Using file metadata date for Meeting_2023-10-26.m4a: 2023-10-26 (from modification date)
Starting transcription for Meeting_2023-10-26.m4a using OpenAI Whisper...
Transcription successful for Meeting_2023-10-26.m4a. Length: 15032 chars.
Starting analysis for transcript of Meeting_2023-10-26.m4a...
Analysis successful for Meeting_2023-10-26.m4a.
Creating Notion page for Meeting_2023-10-26.m4a with title 'Meeting_2023-10-26' and date '2023-10-26'...
Successfully created Notion page: https://www.notion.so/your-workspace/Meeting-2023-10-26-xxxxxxxxxxxxxxxxxxxx
Success for Meeting_2023-10-26.m4a: Successfully processed and uploaded to Notion: https://www.notion.so/your-workspace/Meeting-2023-10-26-xxxxxxxxxxxxxxxxxxxx
... (more files) ...
--- Finished processing folder: recordings/ ---

--- Overall Results ---
File: recordings/Meeting_2023-10-26.m4a
  Status: success
  Message: Successfully processed and uploaded to Notion: https://www.notion.so/your-workspace/Meeting-2023-10-26-xxxxxxxxxxxxxxxxxxxx
  URL: https://www.notion.so/your-workspace/Meeting-2023-10-26-xxxxxxxxxxxxxxxxxxxx
...
Processing complete. X file(s) uploaded successfully to Notion.
--- Voice2Notion Finished ---
```

## For Native UI Integration

This backend is designed to be callable by a native UI (e.g., built with Electron, Tauri, Qt, etc.). The UI would typically:
1.  Execute the `orchestrator.py` script as a child process.
2.  Pass necessary parameters (folder path, API key overrides if managed by UI) via command-line arguments.
3.  Capture and parse `stdout` from `orchestrator.py` for real-time progress updates and final results. The backend prints status messages that can be used by the UI.

**Utility commands for UI interaction (Conceptual - these need to be implemented in `orchestrator.py`'s `main()` if desired):**

*   `python orchestrator.py --get-settings-json`: Prints the current settings as a JSON string.
    *   *Implementation Detail:* `config_manager.load_settings()` then `json.dumps()`.
*   `python orchestrator.py --save-settings-json "{...json_string...}"`: Takes a JSON string and saves it as the new settings.
    *   *Implementation Detail:* `json.loads()` then `config_manager.save_settings()`.
*   `python orchestrator.py --list-transcription-services`: Prints a JSON representation of available transcription services and their configuration schemas.
    *   *Implementation Detail:* Iterate through known `TranscriptionService` subclasses, call their `get_config_schema()` and `name` property.

## Modules Overview

*   **`orchestrator.py`**: The main entry point and coordinator. Handles CLI arguments, initializes services, and manages the overall workflow of processing audio files and folders.
*   **`input_manager.py`**: Provides functions for finding audio files in folders and extracting file metadata.
*   **`config_manager.py`**: Manages loading and saving of application settings from/to `~/.voice2notion/settings.json`.
*   **`summarizer_service.py`**: Contains `SummarizerService` (using Google Gemini) for generating summaries and action items.
*   **`notion_handler.py`**: Includes `NotionHandler` for all interactions with the Notion API.
*   **`transcription_services/`** (directory):
    *   `transcription_service_interface.py`: Defines the `TranscriptionService` abstract base class.
    *   `whisper_transcriber.py`: Implements transcription using OpenAI's Whisper model.
    *   `google_stt_transcriber.py`: Implements transcription using Google Cloud Speech-to-Text.

## License

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
