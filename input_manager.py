import os
from pathlib import Path
from datetime import datetime, timezone

def get_audio_files(folder_path_str: str, supported_formats: tuple = (".m4a", ".wav", ".mp3", ".aac", ".flac", ".ogg", ".opus")) -> list[Path]:
    """
    Scans the given folder_path (non-recursively) for files matching supported_formats.

    Args:
        folder_path_str: The string path to the folder to scan.
        supported_formats: A tuple of supported audio file extensions (e.g., (".mp3", ".wav")).

    Returns:
        A list of Path objects for a_files found.
        Returns an empty list if the folder_path is invalid or no files are found.
    """
    folder_path = Path(folder_path_str)
    audio_files = []

    if not folder_path.is_dir():
        print(f"Error: Folder not found or is not a directory: {folder_path_str}")
        return audio_files

    print(f"Scanning folder: {folder_path_str} for audio files with formats: {supported_formats}")
    for item in folder_path.iterdir():
        if item.is_file() and item.suffix.lower() in supported_formats:
            audio_files.append(item)
            print(f"Found audio file: {item.name}")

    if not audio_files:
        print(f"No audio files found in {folder_path_str} with the specified formats.")

    return audio_files

def get_file_metadata(file_path: Path) -> dict:
    """
    Returns metadata for the given file.

    Args:
        file_path: The Path object of the file.

    Returns:
        A dictionary containing:
            - filename: str
            - creation_date_iso: str (ISO 8601 format)
            - modification_date_iso: str (ISO 8601 format)
            - size_bytes: int

    Raises:
        FileNotFoundError: If the file_path does not exist or is not a file.
    """
    if not file_path.is_file(): # .is_file() also checks for existence
        raise FileNotFoundError(f"File not found or is not a regular file: {file_path}")

    stat_info = file_path.stat()

    # Creation time (platform dependent)
    try:
        # POSIX systems store birth time (creation)
        creation_timestamp = stat_info.st_birthtime
    except AttributeError:
        # Windows and other systems might store it in st_ctime
        # On Unix, st_ctime is the time of last metadata change.
        # For broader compatibility, we can use st_mtime as a fallback if st_birthtime is not available,
        # or acknowledge that true creation time might not always be available.
        # Here, we prioritize birthtime if available, else mtime.
        creation_timestamp = stat_info.st_mtime
        print(f"Warning: 'st_birthtime' not available for {file_path}. Using 'st_mtime' as creation date fallback.")


    creation_date = datetime.fromtimestamp(creation_timestamp, timezone.utc)
    modification_date = datetime.fromtimestamp(stat_info.st_mtime, timezone.utc)

    metadata = {
        "filename": file_path.name,
        "creation_date_iso": creation_date.isoformat(),
        "modification_date_iso": modification_date.isoformat(),
        "size_bytes": stat_info.st_size,
    }
    return metadata

if __name__ == "__main__":
    print("--- Testing input_manager.py ---")

    # Create a dummy folder and files for testing
    test_dir = Path("temp_input_manager_test_audio")
    test_dir.mkdir(exist_ok=True)

    dummy_files_info = {
        "audio1.mp3": "dummy content mp3",
        "audio2.wav": "dummy content wav",
        "document.txt": "not an audio file",
        "audio3.m4a": "dummy content m4a",
        "AUDIO4.WAV": "dummy content wav uppercase"
    }

    for fname, content in dummy_files_info.items():
        with open(test_dir / fname, "w") as f:
            f.write(content)

    print(f"\n1. Testing get_audio_files with folder: {test_dir}")
    audio_list = get_audio_files(str(test_dir))
    assert len(audio_list) == 4, f"Expected 4 audio files, got {len(audio_list)}"
    print(f"Found audio files: {[f.name for f in audio_list]}")

    print(f"\n2. Testing get_audio_files with non-existent folder:")
    non_existent_audio_list = get_audio_files("non_existent_folder_12345")
    assert len(non_existent_audio_list) == 0

    print(f"\n3. Testing get_file_metadata for {test_dir / 'audio1.mp3'}:")
    try:
        metadata = get_file_metadata(test_dir / "audio1.mp3")
        print(f"Metadata: {metadata}")
        assert metadata["filename"] == "audio1.mp3"
        assert "T" in metadata["creation_date_iso"] # Basic ISO check
        assert metadata["size_bytes"] > 0
    except FileNotFoundError as e:
        print(f"Error getting metadata: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in metadata test: {e}")


    print(f"\n4. Testing get_file_metadata for non-existent file:")
    try:
        get_file_metadata(Path("non_existent_file_12345.mp3"))
    except FileNotFoundError:
        print("Caught expected FileNotFoundError.")
    except Exception as e:
        print(f"Caught unexpected error for non-existent file metadata test: {e}")

    # Cleanup
    print("\nCleaning up test directory and files...")
    for fname in dummy_files_info.keys():
        (test_dir / fname).unlink(missing_ok=True)
    test_dir.rmdir()
    print("--- input_manager.py tests finished ---")
