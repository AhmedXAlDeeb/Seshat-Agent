import os
import subprocess
import shutil
from pathlib import Path
import whisper

# Configuration
BASE_DIR = Path(__file__).parent.resolve()
RECORDINGS_DIR = BASE_DIR / "recordings"
PROCESSED_DIR = BASE_DIR / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
WHISPER_MODEL_SIZE = "base"
SUPPORTED_VIDEO_FORMATS = (".mp4", ".mkv", ".mov")

# Ensure folders exist
for folder in [RECORDINGS_DIR, PROCESSED_DIR, TRANSCRIPTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

class Transcriber:
    def __init__(self, model_size=WHISPER_MODEL_SIZE):
        print(f"üî† Loading Whisper model '{model_size}'...")
        self.model = whisper.load_model(model_size)

    def convert_to_wav(self, video_path: Path, wav_path: Path):
        """Convert video to mono 16kHz WAV using ffmpeg."""
        print(f"üéß Converting {video_path.name} to WAV...")
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def transcribe_audio(self, wav_path: Path) -> str:
        """Transcribe the WAV file and return the text."""
        print(f"üìù Transcribing {wav_path.name}...")
        result = self.model.transcribe(str(wav_path))
        return result["text"]

    def process_recording(self, video_path: Path):
        """Process a single video: convert, transcribe, save, and move."""
        base_name = video_path.stem
        wav_path = RECORDINGS_DIR / f"{base_name}.wav"
        transcript_path = TRANSCRIPTS_DIR / f"{base_name}_notes.txt"

        if transcript_path.exists():
            print(f"‚è© Already transcribed: {video_path.name}")
            return

        try:
            self.convert_to_wav(video_path, wav_path)
            transcript = self.transcribe_audio(wav_path)
            transcript_path.write_text(transcript, encoding="utf-8")
            print(f"‚úÖ Saved transcript to {transcript_path.name}")

            # Move original video and WAV
            shutil.move(str(video_path), PROCESSED_DIR / video_path.name)
            shutil.move(str(wav_path), PROCESSED_DIR / wav_path.name)
            print(f"üìÅ Moved files to processed/: {video_path.name}")

        except subprocess.CalledProcessError:
            print(f"‚ùå ffmpeg failed on: {video_path.name}")
        except Exception as e:
            print(f"‚ùå Error processing {video_path.name}: {e}")

    def process_all(self):
        """Process all video files in the recordings folder."""
        print(f"üìÇ Looking for recordings in {RECORDINGS_DIR}")
        for video_file in RECORDINGS_DIR.iterdir():
            if video_file.suffix.lower() in SUPPORTED_VIDEO_FORMATS:
                self.process_recording(video_file)

# --- Test the module when run directly ---
if __name__ == "__main__":
    print("üîÅ Starting transcription pipeline...")
    transcriber = Transcriber()
    transcriber.process_all()
    print("üéâ All done!")
