import time
from datetime import datetime, timedelta
from calendar_agent import get_todays_meetings
from obs_control import start_obs_recording, stop_obs_recording
from transcriber import Transcriber
from summarizer import MeetingAnalyzer
from notion_writer import create_meeting_page
from pathlib import Path
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

def main_loop():
    transcriber = Transcriber()
    analyzer = MeetingAnalyzer(GEMINI_API_KEY)

    while True:
        meetings = get_todays_meetings()
        if not meetings:
            print("No meetings found for today.")
            time.sleep(300)
            continue

        for meeting in meetings:
            props = meeting["properties"]
            title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "No title"
            date_start = props["Date"]["date"]["start"]
            start_dt = datetime.fromisoformat(date_start)
            now = datetime.now()
            diff = (start_dt - now).total_seconds()

            if diff > 0:
                print(f"Next meeting '{title}' at {date_start}. Waiting {int(diff)} seconds.")
                time.sleep(diff)

            print(f"Meeting '{title}' starting. Starting OBS recording...")
            start_obs_recording()

            # Wait for meeting duration or a fixed time (e.g., 1 hour)
            meeting_duration = 3600  # seconds
            print(f"Recording for {meeting_duration//60} minutes...")
            time.sleep(meeting_duration)

            print("Stopping OBS recording...")
            stop_obs_recording()

            # Find the latest recording in recordings/
            recordings_dir = Path(__file__).parent / "recordings"
            video_files = sorted(recordings_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not video_files:
                print("No recording found to transcribe.")
                continue
            video_path = video_files[0]

            print(f"Transcribing {video_path.name}...")
            transcriber.process_recording(video_path)

            # Find the transcript
            transcripts_dir = Path(__file__).parent / "transcripts"
            transcript_path = transcripts_dir / f"{video_path.stem}_notes.txt"
            if not transcript_path.exists():
                print("Transcript not found.")
                continue

            print("Analyzing transcript...")
            analysis = analyzer.analyze(transcript_path)

            print("Saving analysis...")
            analysis_path = Path(__file__).parent / "analysis" / f"{video_path.stem}_analysis.json"
            analyzer.save_analysis(analysis, analysis_path)

            print("Writing meeting summary to Notion...")
            meeting_data = {
                "title": title,
                "date": date_start
            }
            create_meeting_page(meeting_data, analysis)

        print("All meetings processed. Sleeping for 5 minutes.")
        time.sleep(300)

if __name__ == "__main__":
    main_loop()