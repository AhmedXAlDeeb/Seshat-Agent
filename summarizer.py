import google.generativeai as genai
import json
from pathlib import Path
import os

class MeetingAnalyzer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash-002")

    def _run_prompt(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def analyze(self, transcript_path: Path) -> dict:
        transcript = transcript_path.read_text(encoding="utf-8")
        print("Starting analysis using Gemini...")

        prompts = {
            "summary": f"Summarize the following meeting transcript:\n\n{transcript}",
            "participants": f"List the people who actively participated in the following meeting transcript. Only include names that actually spoke or contributed:\n\n{transcript}",
            "tasks": f"Extract any tasks or action items from the meeting transcript below. Include assignee names if mentioned:\n\n{transcript}",
            "deadlines": f"Extract any deadlines, due dates, or reminders mentioned in the following meeting transcript:\n\n{transcript}",
            "decisions": f"List the decisions made by the team in the following meeting transcript:\n\n{transcript}",
            "insights": f"What key insights or noteworthy takeaways can be inferred from the following meeting transcript? These could help with teamwork or project alignment:\n\n{transcript}"
        }

        results = {}
        for key, prompt in prompts.items():
            print(f"✨ Extracting {key}...")
            try:
                response = self._run_prompt(prompt)
                results[key] = response
            except Exception as e:
                print(f"Failed to extract {key}: {e}")
                results[key] = "ERROR"

        return results

    def save_analysis(self, analysis: dict, output_path: Path):
        output_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        print(f"Analysis saved to {output_path}")

if __name__ == "__main__":
    # Example usage for testing
    api_key = os.getenv("GEMINI_API_KEY")
    analyzer = MeetingAnalyzer(api_key)

    transcript_file = Path("transcripts/sample_transcript.txt")
    output_file = Path("analysis/sample_analysis.json")

    result = analyzer.analyze(transcript_file)
    analyzer.save_analysis(result, output_file)
