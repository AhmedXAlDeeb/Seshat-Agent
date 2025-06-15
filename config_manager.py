import json
from pathlib import Path
import os

SETTINGS_DIR = Path.home() / ".voice2notion"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

def get_default_settings() -> dict:
    """
    Returns a dictionary with default keys and empty/default values for the application settings.
    """
    return {
        "notion_api_key": "",
        "notion_database_id": "",
        "transcription_service": "OpenAI Whisper", # Default service
        "whisper_model_size": "base", # Default for Whisper
        "google_stt_api_key_path": "", # For Google STT
        "gemini_api_key": "",
        "audio_input_folder": str(Path.home() / "Recordings"), # Example default input folder
        # Add other service-specific configs as needed, e.g.,
        # "azure_speech_key": "",
        # "azure_speech_region": "",
    }

def ensure_config_dir_exists():
    """
    Ensures that the settings directory (~/.voice2notion) exists.
    Creates it if it doesn't.
    """
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        # print(f"Configuration directory ensured: {SETTINGS_DIR}")
    except OSError as e:
        print(f"Error creating configuration directory {SETTINGS_DIR}: {e}")
        # Depending on severity, might want to raise this or handle more gracefully
        raise

def load_settings() -> dict:
    """
    Loads settings from SETTINGS_FILE.
    If the file is not found, corrupted, or an error occurs, it returns default settings.
    """
    ensure_config_dir_exists() # Ensure directory is there before trying to load

    if not SETTINGS_FILE.exists():
        print(f"Settings file not found at {SETTINGS_FILE}. Returning default settings.")
        # Optionally, save default settings here immediately:
        # default_settings = get_default_settings()
        # save_settings(default_settings)
        # return default_settings
        return get_default_settings()

    try:
        with open(SETTINGS_FILE, 'r') as f:
            loaded_settings_from_file = json.load(f)

        # Merge with defaults to ensure all keys are present
        default_settings = get_default_settings()
        # Prioritize loaded settings, but ensure all default keys exist
        # This way, if new settings are added to defaults, old config files still work
        final_settings = default_settings.copy()
        final_settings.update(loaded_settings_from_file)

        print(f"Settings loaded successfully from {SETTINGS_FILE}.")
        return final_settings
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {SETTINGS_FILE}: {e}. Returning default settings.")
        return get_default_settings()
    except Exception as e:
        print(f"An unexpected error occurred while loading settings from {SETTINGS_FILE}: {e}. Returning default settings.")
        return get_default_settings()

def save_settings(settings: dict):
    """
    Saves the given settings dictionary to SETTINGS_FILE in JSON format.
    """
    ensure_config_dir_exists()

    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        print(f"Settings saved successfully to {SETTINGS_FILE}.")
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")
        # Depending on severity, might want to raise this
        raise

if __name__ == "__main__":
    print("--- Testing config_manager.py ---")

    # Ensure a clean state for testing by trying to remove the existing file if it exists
    if SETTINGS_FILE.exists():
        try:
            SETTINGS_FILE.unlink()
            print(f"Removed existing settings file for fresh test: {SETTINGS_FILE}")
        except OSError as e:
            print(f"Could not remove existing settings file: {e}")
            # This is not critical for the test itself, but good to note.

    if SETTINGS_DIR.exists() and not os.listdir(SETTINGS_DIR): # if dir exists and is empty
        try:
            SETTINGS_DIR.rmdir()
            print(f"Removed existing empty settings directory for fresh test: {SETTINGS_DIR}")
        except OSError as e:
            print(f"Could not remove existing settings directory: {e}")


    print("\n1. Testing ensure_config_dir_exists:")
    try:
        ensure_config_dir_exists()
        assert SETTINGS_DIR.exists() and SETTINGS_DIR.is_dir(), "SETTINGS_DIR should exist and be a directory."
        print(f"Config directory {SETTINGS_DIR} exists or was created.")
    except Exception as e:
        print(f"ensure_config_dir_exists() test failed: {e}")


    print("\n2. Testing get_default_settings:")
    defaults = get_default_settings()
    print(f"Default settings: {defaults}")
    assert "notion_api_key" in defaults
    assert "transcription_service" in defaults


    print("\n3. Testing load_settings (file not found):")
    # Ensure file doesn't exist initially for this part of the test
    if SETTINGS_FILE.exists(): SETTINGS_FILE.unlink()
    settings_loaded = load_settings()
    print(f"Loaded settings (should be defaults): {settings_loaded}")
    assert settings_loaded["notion_api_key"] == "" # Check against a default value
    assert settings_loaded["audio_input_folder"] == str(Path.home() / "Recordings")


    print("\n4. Testing save_settings and then load_settings:")
    test_settings_to_save = {
        "notion_api_key": "test_key_123",
        "notion_database_id": "test_db_456",
        "transcription_service": "Test Service",
        "custom_param": "custom_value" # Test merging: custom_param should be in loaded if defaults don't overwrite
    }
    try:
        save_settings(test_settings_to_save)
        assert SETTINGS_FILE.exists(), "SETTINGS_FILE should have been created by save_settings."

        settings_reloaded = load_settings()
        print(f"Reloaded settings: {settings_reloaded}")
        assert settings_reloaded["notion_api_key"] == "test_key_123"
        assert settings_reloaded["notion_database_id"] == "test_db_456"
        assert settings_reloaded["transcription_service"] == "Test Service"
        # Check if new keys not in defaults are preserved
        assert settings_reloaded.get("custom_param") == "custom_value"
        # Check if default keys are still present if not in saved dict (e.g. gemini_api_key)
        assert "gemini_api_key" in settings_reloaded
        assert settings_reloaded["gemini_api_key"] == get_default_settings()["gemini_api_key"]

    except Exception as e:
        print(f"save_settings/load_settings test failed: {e}")


    print("\n5. Testing load_settings with corrupted JSON file:")
    try:
        with open(SETTINGS_FILE, 'w') as f:
            f.write("{corrupted_json_data: ") # Write invalid JSON

        corrupted_settings = load_settings()
        print(f"Settings after loading corrupted file (should be defaults): {corrupted_settings}")
        assert corrupted_settings["notion_api_key"] == "" # Back to default
    except Exception as e:
        print(f"Corrupted JSON test failed: {e}")


    # Clean up after tests
    print("\nCleaning up test settings file...")
    if SETTINGS_FILE.exists():
        try:
            SETTINGS_FILE.unlink()
            print(f"Deleted settings file: {SETTINGS_FILE}")
        except OSError as e:
            print(f"Error deleting settings file during cleanup: {e}")

    # Attempt to remove the directory if it's empty
    if SETTINGS_DIR.exists() and not os.listdir(SETTINGS_DIR):
        try:
            SETTINGS_DIR.rmdir()
            print(f"Deleted settings directory: {SETTINGS_DIR}")
        except OSError as e:
            print(f"Error deleting settings directory during cleanup: {e} (Might not be empty if other processes use it)")

    print("--- config_manager.py tests finished ---")
