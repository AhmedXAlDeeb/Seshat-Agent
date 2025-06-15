import argparse
import os
from pathlib import Path
from typing import Optional, Type

# Configuration and Input Management
import config_manager
import input_manager

# Core Services
# Assuming transcription_services is a subdirectory or on Python path
# If not, these imports will need adjustment (e.g., if files are in the same root directory)
try:
    from transcription_services.transcription_service_interface import TranscriptionService
    from transcription_services.whisper_transcriber import WhisperTranscriber
    from transcription_services.google_stt_transcriber import GoogleSTTTranscriber
except ImportError as e:
    print(f"Error importing transcription services: {e}. Please ensure they are in the 'transcription_services' subdirectory or your PYTHONPATH is configured correctly.")
    # Define placeholders if import fails, so the rest of the file can be parsed
    TranscriptionService = type('TranscriptionService', (object,), {})
    WhisperTranscriber = type('WhisperTranscriber', (TranscriptionService,), {'get_config_schema': staticmethod(lambda: {})})
    GoogleSTTTranscriber = type('GoogleSTTTranscriber', (TranscriptionService,), {'get_config_schema': staticmethod(lambda: {})})


from summarizer_service import SummarizerService
from notion_handler import NotionHandler


class Orchestrator:
    def __init__(self, settings: dict):
        self.settings = settings
        self.transcription_service: Optional[TranscriptionService] = None
        self.summarizer_service: Optional[SummarizerService] = None
        self.notion_handler: Optional[NotionHandler] = None

        self._initialize_services()

    def _initialize_services(self):
        """Initializes all necessary services based on settings."""
        print("Initializing services...")

        # 1. Transcription Service
        service_name = self.settings.get("transcription_service", "OpenAI Whisper")
        print(f"Selected transcription service: {service_name}")

        transcription_config = {}
        service_class: Optional[Type[TranscriptionService]] = None

        if service_name == "OpenAI Whisper":
            service_class = WhisperTranscriber
            transcription_config = {"model_size": self.settings.get("whisper_model_size", "base")}
        elif service_name == "Google Cloud Speech-to-Text":
            service_class = GoogleSTTTranscriber
            transcription_config = {
                "api_key_path": self.settings.get("google_stt_api_key_path"),
                "language_code": self.settings.get("google_stt_language_code", "en-US") # Example language code
            }
            if not transcription_config["api_key_path"]:
                print("Warning: Google STT selected, but 'google_stt_api_key_path' is not set in settings.")
                # service_class = None # Prevent initialization if key is missing
        else:
            print(f"Warning: Unknown transcription service '{service_name}' specified in settings. No transcription service will be loaded.")

        if service_class:
            try:
                self.transcription_service = service_class(config=transcription_config)
                print(f"{service_class.name if hasattr(service_class, 'name') else service_name} initialized.")
            except Exception as e:
                print(f"Error initializing {service_name}: {e}")
                self.transcription_service = None # Ensure it's None if init fails

        # 2. Summarizer Service (Gemini)
        gemini_api_key = self.settings.get("gemini_api_key")
        if gemini_api_key:
            try:
                self.summarizer_service = SummarizerService(api_key=gemini_api_key)
                print("SummarizerService (Gemini) initialized.")
            except Exception as e:
                print(f"Error initializing SummarizerService: {e}")
                self.summarizer_service = None
        else:
            print("Warning: Gemini API key not found in settings. SummarizerService will not be available.")

        # 3. Notion Handler
        notion_api_key = self.settings.get("notion_api_key")
        notion_database_id = self.settings.get("notion_database_id")
        if notion_api_key and notion_database_id:
            try:
                self.notion_handler = NotionHandler(api_key=notion_api_key, database_id=notion_database_id)
                print("NotionHandler initialized.")
            except Exception as e:
                print(f"Error initializing NotionHandler: {e}")
                self.notion_handler = None
        else:
            print("Warning: Notion API key or Database ID not found in settings. NotionHandler will not be available.")

        print("Service initialization complete.")

    def process_single_audio_file(self, audio_path: Path, notion_date_iso: str) -> dict:
        """
        Processes a single audio file: transcribes, analyzes, and creates a Notion page.
        """
        print(f"\n--- Processing audio file: {audio_path.name} ---")
        result = {"file": str(audio_path), "status": "pending", "message": "", "url": ""}

        # 1. Transcription
        if not self.transcription_service:
            result["status"] = "error"
            result["message"] = "Transcription service not available or failed to initialize."
            print(f"Error for {audio_path.name}: {result['message']}")
            return result

        transcript_text = ""
        try:
            print(f"Starting transcription for {audio_path.name} using {self.transcription_service.name}...")
            transcript_text = self.transcription_service.transcribe(audio_path)
            if not transcript_text or not transcript_text.strip():
                 result["status"] = "error"
                 result["message"] = "Transcription resulted in empty text."
                 print(f"Error for {audio_path.name}: {result['message']}")
                 return result
            print(f"Transcription successful for {audio_path.name}. Length: {len(transcript_text)} chars.")
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Transcription failed: {e}"
            print(f"Error for {audio_path.name}: {result['message']}")
            return result

        # 2. Summarization and Analysis
        summary_data = {"summary": "", "action_items": []}
        if not self.summarizer_service:
            print("Warning: Summarizer service not available. Skipping analysis.")
            # Proceed without summary if summarizer is not available
        else:
            try:
                print(f"Starting analysis for transcript of {audio_path.name}...")
                summary_data = self.summarizer_service.analyze_transcript(transcript_text, audio_path.name)
                print(f"Analysis successful for {audio_path.name}.")
            except Exception as e:
                # Log error but proceed with creating Notion page with transcript only if summarization fails
                print(f"Warning: Summarization/analysis failed for {audio_path.name}: {e}. Proceeding without summary/action items.")
                summary_data["summary"] = f"[Analysis failed: {e}]" # Add error to summary for visibility

        # 3. Create Notion Page
        if not self.notion_handler:
            result["status"] = "error"
            result["message"] = "NotionHandler not available or failed to initialize. Cannot create page."
            print(f"Error for {audio_path.name}: {result['message']}")
            return result

        try:
            page_title = audio_path.stem # Use filename without extension as title
            print(f"Creating Notion page for {audio_path.name} with title '{page_title}' and date '{notion_date_iso}'...")

            page_url_or_error = self.notion_handler.create_notion_page(
                title=page_title,
                date_iso=notion_date_iso,
                summary=summary_data.get("summary", "Summary not available."),
                action_items=summary_data.get("action_items", []),
                transcript=transcript_text,
                source_filename=audio_path.name
            )

            if "https://" in page_url_or_error:
                result["status"] = "success"
                result["url"] = page_url_or_error
                result["message"] = f"Successfully processed and uploaded to Notion: {page_url_or_error}"
                print(f"Success for {audio_path.name}: {result['message']}")
            else:
                result["status"] = "error"
                result["message"] = f"Failed to create Notion page: {page_url_or_error}"
                print(f"Error for {audio_path.name}: {result['message']}")
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Failed to create Notion page due to unexpected error: {e}"
            print(f"Error for {audio_path.name}: {result['message']}")

        return result

    def process_folder(self, folder_path_str: str, date_mapping: Optional[dict[str, str]] = None) -> list[dict]:
        """
        Processes all supported audio files in a given folder.
        """
        print(f"\n--- Starting to process folder: {folder_path_str} ---")
        if not self.transcription_service and not self.notion_handler and not self.summarizer_service:
             print("Error: No services (Transcription, Notion, Summarizer) are initialized. Aborting folder processing.")
             return [{"file": "", "status": "error", "message": "All services failed to initialize.", "url": ""}]

        audio_files = input_manager.get_audio_files(folder_path_str)
        if not audio_files:
            print(f"No audio files found in {folder_path_str}.")
            return []

        results = []
        for audio_file_path in audio_files:
            # Determine date for Notion page
            notion_page_date_iso = ""
            if date_mapping and audio_file_path.name in date_mapping:
                notion_page_date_iso = date_mapping[audio_file_path.name]
                print(f"Using provided date mapping for {audio_file_path.name}: {notion_page_date_iso}")
            else:
                try:
                    metadata = input_manager.get_file_metadata(audio_file_path)
                    # Use modification_date_iso, can be changed to creation_date_iso if preferred
                    notion_page_date_iso = metadata["modification_date_iso"].split("T")[0] # Get YYYY-MM-DD part
                    print(f"Using file metadata date for {audio_file_path.name}: {notion_page_date_iso} (from modification date)")
                except FileNotFoundError:
                    print(f"Could not get metadata for {audio_file_path.name}. Skipping this file.")
                    results.append({"file": str(audio_file_path), "status": "error", "message": "File metadata not found.", "url": ""})
                    continue
                except Exception as e:
                    print(f"Error getting metadata date for {audio_file_path.name}: {e}. Skipping this file.")
                    results.append({"file": str(audio_file_path), "status": "error", "message": f"Error getting metadata date: {e}", "url": ""})
                    continue

            if not notion_page_date_iso: # Should not happen if logic above is correct
                print(f"Error: Could not determine date for {audio_file_path.name}. Skipping.")
                results.append({"file": str(audio_file_path), "status": "error", "message": "Could not determine date for Notion page.", "url": ""})
                continue

            file_result = self.process_single_audio_file(audio_file_path, notion_page_date_iso)
            results.append(file_result)

        print(f"\n--- Finished processing folder: {folder_path_str} ---")
        return results

def main():
    parser = argparse.ArgumentParser(description="Voice2Notion: Process audio files and upload notes to Notion.")
    parser.add_argument("folder_path", type=str, nargs="?", default=None, help="Path to the folder containing audio files.")
    parser.add_argument("--notion-api-key", type=str, help="Notion API Key. Overrides settings file.")
    parser.add_argument("--notion-db-id", type=str, help="Notion Database ID. Overrides settings file.")
    parser.add_argument("--gemini-api-key", type=str, help="Gemini API Key. Overrides settings file.")
    parser.add_argument("--whisper-model", type=str, help="Whisper model size (e.g., tiny, base, small). Overrides settings file.")
    # Add more CLI args for other settings as needed (e.g. transcription service choice)

    args = parser.parse_args()

    print("--- Voice2Notion Initializing ---")

    # Load settings from file
    settings = config_manager.load_settings()

    # Override settings with CLI arguments if provided
    if args.notion_api_key:
        settings["notion_api_key"] = args.notion_api_key
        print("Using Notion API Key from CLI argument.")
    if args.notion_db_id:
        settings["notion_database_id"] = args.notion_db_id
        print("Using Notion Database ID from CLI argument.")
    if args.gemini_api_key:
        settings["gemini_api_key"] = args.gemini_api_key
        print("Using Gemini API Key from CLI argument.")
    if args.whisper_model:
        settings["whisper_model_size"] = args.whisper_model
        print(f"Using Whisper model size '{args.whisper_model}' from CLI argument.")

    # Determine folder_path (CLI arg > settings > current dir as last resort)
    folder_to_process = args.folder_path
    if not folder_to_process:
        folder_to_process = settings.get("audio_input_folder")
        if not folder_to_process: # If still not set, use current directory
            folder_to_process = "."
            print("No folder path provided via CLI or settings, defaulting to current directory.")
        else:
            print(f"Using audio input folder from settings: {folder_to_process}")
    else:
        print(f"Using audio input folder from CLI argument: {folder_to_process}")


    # Before saving, ensure sensitive keys are present, even if empty, if they came from CLI
    # This is more for if we decide to save settings later. For now, settings are just in memory for this run.
    # config_manager.save_settings(settings) # Optional: save updated settings

    orchestrator = Orchestrator(settings)

    if not Path(folder_to_process).exists():
        print(f"Error: The specified folder path does not exist: {folder_to_process}")
        print("Please provide a valid folder path.")
        return

    results = orchestrator.process_folder(folder_to_process)

    print("\n--- Overall Results ---")
    successful_uploads = 0
    failed_processing = 0
    for res in results:
        print(f"File: {res['file']}")
        print(f"  Status: {res['status']}")
        print(f"  Message: {res['message']}")
        if res['status'] == 'success':
            print(f"  URL: {res['url']}")
            successful_uploads +=1
        else:
            failed_processing +=1

    print(f"\nProcessing complete. {successful_uploads} file(s) uploaded successfully to Notion.")
    if failed_processing > 0:
        print(f"{failed_processing} file(s) encountered errors during processing.")

    print("--- Voice2Notion Finished ---")


if __name__ == "__main__":
    # Example of how to run from CLI:
    # python orchestrator.py /path/to/your/audio/files --notion-api-key "your_key" --notion-db-id "your_db_id" --gemini-api-key "your_gemini_key"
    #
    # To test without CLI args (relying on settings.json or env vars for services):
    # Create a settings.json in ~/.voice2notion/ or ensure Notion/Gemini keys are set in Orchestrator for services to init.
    # python orchestrator.py /path/to/your/audio/files
    #
    # For Whisper, ensure ffmpeg is installed. For Whisper & Gemini, ensure Python packages are installed.
    main()
