import os
import subprocess
import shutil
from pathlib import Path
import tempfile
import wave # For creating dummy audio

# Attempt to import whisper, provide a clear error message if it fails.
try:
    import whisper
except ImportError:
    print("Error: The 'whisper' library is not installed. Please install it by running: pip install openai-whisper")
    # Depending on the desired behavior, you might re-raise the error or exit.
    # For now, we'll let it proceed so other parts of the module (like schema) can be inspected.
    whisper = None

from transcription_service_interface import TranscriptionService

TEMP_AUDIO_PARENT_DIR = Path(tempfile.gettempdir()) / "seshat_agent_temp_audio"

class WhisperTranscriber(TranscriptionService):
    """
    Transcription service using OpenAI's Whisper model.
    """
    MODEL_LEVELS = ["tiny", "base", "small", "medium", "large"]
    DEFAULT_MODEL = "base"

    def __init__(self, config: dict):
        if not whisper:
            raise RuntimeError("Whisper library is not available. Please install openai-whisper.")

        self.model_size = config.get("model_size", self.DEFAULT_MODEL)
        if self.model_size not in self.MODEL_LEVELS:
            print(f"Warning: Invalid model size '{self.model_size}'. Falling back to '{self.DEFAULT_MODEL}'.")
            self.model_size = self.DEFAULT_MODEL

        self.temp_audio_dir = TEMP_AUDIO_PARENT_DIR / f"whisper_{os.getpid()}"
        try:
            self.temp_audio_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Could not create temporary audio directory: {self.temp_audio_dir}. Error: {e}") from e

        print(f"Initializing Whisper model '{self.model_size}'...")
        try:
            self.model = whisper.load_model(self.model_size)
            print(f"Whisper model '{self.model_size}' loaded successfully.")
        except Exception as e:
            print(f"Error loading Whisper model '{self.model_size}': {e}")
            if self.model_size != self.DEFAULT_MODEL:
                print(f"Attempting to load fallback model '{self.DEFAULT_MODEL}'...")
                try:
                    self.model = whisper.load_model(self.DEFAULT_MODEL)
                    self.model_size = self.DEFAULT_MODEL
                    print(f"Fallback Whisper model '{self.model_size}' loaded successfully.")
                except Exception as fallback_e:
                    raise RuntimeError(f"Failed to load Whisper model '{self.model_size}' and fallback '{self.DEFAULT_MODEL}': {fallback_e}") from fallback_e
            else:
                raise RuntimeError(f"Failed to load Whisper model '{self.model_size}': {e}") from e


    def _is_ffmpeg_available(self) -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _convert_to_wav(self, audio_path: Path) -> Path:
        """
        Converts an audio file to WAV format (mono, 16kHz, pcm_s16le) using ffmpeg.
        If the input is already a WAV file with correct specs, it's copied.
        Stores the converted file in the self.temp_audio_dir.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {audio_path}")

        wav_filename = f"{audio_path.stem}_converted.wav"
        wav_path = self.temp_audio_dir / wav_filename

        # Ensure the parent directory for wav_path exists
        wav_path.parent.mkdir(parents=True, exist_ok=True)

        if audio_path.suffix.lower() == ".wav":
            try:
                with wave.open(str(audio_path), 'rb') as wf:
                    if wf.getnchannels() == 1 and wf.getframerate() == 16000 and wf.getsampwidth() == 2:
                        print(f"Input file {audio_path} is already in desired WAV format. Copying.")
                        shutil.copy(audio_path, wav_path)
                        return wav_path
            except wave.Error as e:
                print(f"Could not read input WAV file {audio_path} metadata: {e}. Proceeding with conversion.")
            except Exception as e: # Catch other potential errors like shutil.SameFileError if paths are identical
                print(f"An unexpected error occurred while checking WAV format: {e}. Proceeding with conversion.")


        if not self._is_ffmpeg_available():
            raise FileNotFoundError("ffmpeg is not installed or not found in PATH. It is required for audio conversion.")

        # Command to convert to WAV, 16kHz, mono, 16-bit PCM
        command = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ac", "1",             # Mono
            "-ar", "16000",         # 16kHz
            "-acodec", "pcm_s16le", # 16-bit PCM
            "-y",                   # Overwrite output file if it exists
            str(wav_path)
        ]
        print(f"Converting {audio_path} to WAV format at {wav_path}...")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(f"Conversion successful: {result.stdout}")
            return wav_path
        except subprocess.CalledProcessError as e:
            error_message = f"ffmpeg conversion failed for {audio_path}.\n"
            error_message += f"Command: {' '.join(command)}\n"
            error_message += f"Return code: {e.returncode}\n"
            error_message += f"ffmpeg stdout: {e.stdout}\n"
            error_message += f"ffmpeg stderr: {e.stderr}\n"
            # Clean up partially converted file if it exists
            if wav_path.exists():
                wav_path.unlink()
            raise RuntimeError(error_message) from e
        except FileNotFoundError:
            # This should ideally be caught by _is_ffmpeg_available, but as a safeguard:
            raise FileNotFoundError("ffmpeg not found during conversion. Please ensure it is installed and in your PATH.")


    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        converted_wav_path = None
        try:
            converted_wav_path = self._convert_to_wav(audio_path)
            print(f"Transcribing {converted_wav_path} using Whisper model '{self.model_size}'...")
            result = self.model.transcribe(str(converted_wav_path))
            transcription = result["text"]
            print("Transcription successful.")
            return transcription
        except FileNotFoundError as e: # Specifically for audio_path or ffmpeg
            raise e
        except RuntimeError as e: # For ffmpeg conversion errors
            raise e
        except Exception as e:
            raise RuntimeError(f"Whisper transcription failed for {audio_path}: {e}") from e
        finally:
            if converted_wav_path and converted_wav_path.exists():
                try:
                    converted_wav_path.unlink()
                    print(f"Cleaned up temporary WAV file: {converted_wav_path}")
                except OSError as e:
                    print(f"Warning: Could not delete temporary file {converted_wav_path}. Error: {e}")
            # Consider cleaning up self.temp_audio_dir if it's empty or in a destructor/cleanup method
            # For now, individual files are cleaned. The directory itself might persist.

    @property
    def name(self) -> str:
        return "OpenAI Whisper"

    @staticmethod
    def get_config_schema() -> dict:
        return {
            "model_size": {
                "type": "string",
                "default": WhisperTranscriber.DEFAULT_MODEL,
                "options": WhisperTranscriber.MODEL_LEVELS,
                "description": "The model size for Whisper (e.g., 'tiny', 'base', 'small'). "
                               "Larger models are more accurate but slower and require more memory."
            }
            # Future options like 'language' could be added here.
        }

    def __del__(self):
        """Attempt to clean up the temporary directory when the object is garbage collected."""
        if hasattr(self, 'temp_audio_dir') and self.temp_audio_dir.exists():
            try:
                shutil.rmtree(self.temp_audio_dir)
                print(f"Cleaned up temporary directory: {self.temp_audio_dir}")
            except OSError as e:
                # This might fail if files are still locked or due to permissions
                print(f"Warning: Could not delete temporary directory {self.temp_audio_dir} on cleanup. Error: {e}")


def _create_dummy_audio_file(file_path: Path, duration_ms: int = 1000, sample_rate: int = 44100, channels: int = 1, sampwidth: int = 2) -> bool:
    """Creates a dummy WAV file for testing."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with wave.open(str(file_path), 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sampwidth) # Bytes per sample
            wf.setframerate(sample_rate)
            num_frames = int(sample_rate * (duration_ms / 1000.0))
            # Simple silent audio data (zeros)
            audio_data = b'\x00\x00' * num_frames * channels
            wf.writeframes(audio_data)
        print(f"Created dummy audio file: {file_path}")
        return True
    except Exception as e:
        print(f"Error creating dummy audio file {file_path}: {e}")
        return False

if __name__ == "__main__":
    print("Running WhisperTranscriber direct test...")

    # Setup a temporary directory for this test run
    test_run_temp_dir = Path(tempfile.gettempdir()) / "whisper_transcriber_test"
    test_run_temp_dir.mkdir(parents=True, exist_ok=True)

    # Dummy audio file paths
    dummy_wav_path = test_run_temp_dir / "dummy_audio.wav"
    dummy_mp3_path = test_run_temp_dir / "dummy_audio.mp3" # We'll just name it .mp3, content is WAV

    # Create dummy audio (WAV, as it's simple to generate)
    if not _create_dummy_audio_file(dummy_wav_path, duration_ms=500, sample_rate=16000): # Correct rate for direct use
        print("Failed to create dummy WAV for testing. Aborting.")
        shutil.rmtree(test_run_temp_dir)
        exit(1)

    # Create another "mp3" file (actually WAV content for simplicity in this test,
    # as creating a real mp3 requires an encoder like lame/ffmpeg anyway)
    # This is to test the conversion path.
    if not _create_dummy_audio_file(dummy_mp3_path, duration_ms=500, sample_rate=44100): # Different sample rate
        print("Failed to create dummy MP3 (as WAV) for testing. Aborting.")
        shutil.rmtree(test_run_temp_dir)
        exit(1)

    transcriber = None
    try:
        # Test with default config
        config = {"model_size": "tiny"} # Use tiny for faster testing
        transcriber = WhisperTranscriber(config=config)

        print(f"\n--- Testing with schema: {WhisperTranscriber.get_config_schema()} ---")
        print(f"--- Transcriber Name: {transcriber.name} ---")

        # Test 1: Transcribe the WAV file (should be copied or directly used if format matches)
        print(f"\n--- Test 1: Transcribing WAV file: {dummy_wav_path} ---")
        try:
            transcript_wav = transcriber.transcribe(dummy_wav_path)
            print(f"Transcript (WAV): '{transcript_wav}'")
        except Exception as e:
            print(f"Error during WAV transcription test: {e}")
            if "ffmpeg" in str(e).lower():
                print("This might be due to ffmpeg not being installed. Please ensure ffmpeg is in your PATH.")

        # Test 2: Transcribe the MP3 file (should be converted)
        # Ensure ffmpeg is available before running this test
        if transcriber._is_ffmpeg_available():
            print(f"\n--- Test 2: Transcribing MP3 (dummy) file: {dummy_mp3_path} ---")
            try:
                transcript_mp3 = transcriber.transcribe(dummy_mp3_path)
                print(f"Transcript (MP3): '{transcript_mp3}'")
            except Exception as e:
                print(f"Error during MP3 transcription test: {e}")
        else:
            print(f"\n--- Test 2: SKIPPED - ffmpeg not found. Cannot test MP3 conversion. ---")
            print("Please install ffmpeg to enable conversion of various audio formats.")

        # Test 3: FileNotFoundError for transcribe
        print("\n--- Test 3: Transcribing non-existent file ---")
        try:
            transcriber.transcribe(Path("non_existent_audio.mp3"))
        except FileNotFoundError as e:
            print(f"Caught expected error: {e}")
        except Exception as e:
            print(f"Caught unexpected error: {e}")

    except RuntimeError as e:
        print(f"RuntimeError during WhisperTranscriber initialization or testing: {e}")
        if "whisper" in str(e).lower() and "not available" in str(e).lower():
             print("Please ensure 'openai-whisper' is installed: pip install openai-whisper")
        elif "model" in str(e).lower():
            print("This could be an issue with downloading or loading the Whisper model. Check network or model files.")
    except Exception as e:
        print(f"An unexpected error occurred during the test: {e}")
    finally:
        print("\n--- Test Cleanup ---")
        # Clean up the per-object temporary directory created by the transcriber instance
        if transcriber and hasattr(transcriber, 'temp_audio_dir') and transcriber.temp_audio_dir.exists():
            try:
                shutil.rmtree(transcriber.temp_audio_dir)
                print(f"Cleaned up WhisperTranscriber instance temp directory: {transcriber.temp_audio_dir}")
            except Exception as e:
                print(f"Error cleaning up instance temp directory {transcriber.temp_audio_dir}: {e}")

        # Clean up the test run's temporary directory
        if test_run_temp_dir.exists():
            try:
                shutil.rmtree(test_run_temp_dir)
                print(f"Cleaned up test run temp directory: {test_run_temp_dir}")
            except Exception as e:
                print(f"Error cleaning up test run temp directory {test_run_temp_dir}: {e}")

        print("WhisperTranscriber test finished.")
