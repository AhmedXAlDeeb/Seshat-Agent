import os

# Attempt to import Google Generative AI, provide guidance if not installed
try:
    import google.generativeai as genai
except ImportError:
    print("Error: The 'google-generativeai' library is not installed. Please install it by running: pip install google-generativeai")
    genai = None # Set to None so parts of the module can be loaded for inspection if needed

class SummarizerService:
    """
    A service to generate summaries and action items from text transcripts
    using Google's Gemini API.
    """
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Using the recommended model name

    def __init__(self, api_key: str, model_name: str = None):
        """
        Initializes the SummarizerService.

        Args:
            api_key: The Google API key for Gemini.
            model_name: The specific Gemini model to use (e.g., "gemini-1.5-flash-latest").
                        Defaults to DEFAULT_MODEL_NAME.

        Raises:
            ValueError: If the API key is not provided.
            RuntimeError: If the Google Generative AI SDK is not installed or fails to configure.
        """
        if not genai:
            raise RuntimeError(
                "Google Generative AI SDK (google-generativeai) is not installed. "
                "Please install it: pip install google-generativeai"
            )

        if not api_key:
            raise ValueError("API key for Gemini (SummarizerService) not provided.")

        try:
            genai.configure(api_key=api_key)
            print("Google Generative AI configured successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to configure Google Generative AI: {e}") from e

        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        try:
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini model '{self.model_name}' initialized.")
        except Exception as e:
            # This could be due to invalid model name, permissions, or other issues
            raise RuntimeError(f"Failed to initialize Gemini model '{self.model_name}': {e}") from e


    def _generate_content_with_gemini(self, prompt: str) -> str:
        """Helper function to generate content using the Gemini model with error handling."""
        try:
            response = self.model.generate_content(prompt)
            # Ensure 'text' attribute exists and handle potential issues with the response structure.
            if hasattr(response, 'text') and response.text:
                return response.text
            elif response.candidates and response.candidates[0].content.parts:
                 # More robust way to access text if direct .text is not available or empty
                return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
            else:
                # Log the full response if the expected text is not found for debugging
                print(f"Warning: Gemini response did not contain expected text structure. Full response: {response}")
                return "" # Return empty string or raise an error
        except AttributeError as ae: # If response.text doesn't exist
            print(f"Warning: Gemini response attribute error: {ae}. Full response: {response}")
            return ""
        except Exception as e:
            # This catches API errors, network issues, etc.
            print(f"Error during Gemini API call: {e}")
            # Depending on the error, you might want to raise it or return a specific error indicator
            # For now, printing error and returning empty string to allow main flow to continue with partial data
            # In a production system, more sophisticated retry logic or error reporting would be needed.
            raise RuntimeError(f"Gemini API call failed: {e}") from e


    def analyze_transcript(self, transcript: str, original_filename: str) -> dict:
        """
        Analyzes a transcript to generate a summary and extract action items.

        Args:
            transcript: The text transcript of a meeting or audio file.
            original_filename: The name of the original audio file, for context.

        Returns:
            A dictionary containing:
            {
                "summary": "A concise summary of the transcript.",
                "action_items": ["Action item 1", "Action item 2", ...],
                "original_filename": "original_audio.mp3"
            }
            Returns empty strings/lists for summary/action items if generation fails.
        """
        if not transcript or not transcript.strip():
            print("Warning: Transcript is empty. Skipping analysis.")
            return {
                "summary": "",
                "action_items": [],
                "original_filename": original_filename
            }

        print(f"Analyzing transcript for '{original_filename}' (length: {len(transcript)} chars)...")

        # Prompt for Summary
        summary_prompt = f"""
        Original Filename: {original_filename}
        Transcript:
        ---
        {transcript}
        ---
        Based on the transcript above, provide a concise summary of the main topics and discussion points.
        The summary should be a single, coherent paragraph. Do not include any preamble like "Here is the summary:".
        Focus on the key information conveyed.
        Summary:
        """

        # Prompt for Action Items
        action_items_prompt = f"""
        Original Filename: {original_filename}
        Transcript:
        ---
        {transcript}
        ---
        Based on the transcript above, identify any specific action items, tasks, or follow-ups mentioned.
        List them as a bulleted list. Each action item should be a clear, concise statement.
        If no action items are found, output "No action items identified."
        Do not include any preamble like "Here are the action items:".
        Action Items:
        -
        """

        summary_text = ""
        action_items_list = []

        try:
            print("Generating summary...")
            summary_text = self._generate_content_with_gemini(summary_prompt).strip()
            print(f"Raw summary received: '{summary_text[:100]}...'") # Log snippet
        except RuntimeError as e:
            print(f"Failed to generate summary: {e}")
            # Keep summary_text as empty string

        try:
            print("Extracting action items...")
            raw_action_items_text = self._generate_content_with_gemini(action_items_prompt).strip()
            print(f"Raw action items received: '{raw_action_items_text[:100]}...'") # Log snippet

            if raw_action_items_text and raw_action_items_text.lower() not in ["no action items identified.", "no action items found."]:
                action_items_list = [item.strip() for item in raw_action_items_text.split('\n') if item.strip().startswith('-')]
                action_items_list = [item.lstrip('- ').strip() for item in action_items_list if item.lstrip('- ').strip()] # Clean up prefixes and empty items
            elif "no action items identified" in raw_action_items_text.lower() or "no action items found" in raw_action_items_text.lower() :
                 action_items_list = [] # Explicitly set to empty
            else: # If the output is unexpected (not "no action items" and not a list)
                print(f"Warning: Action items output was not in expected format and not 'no action items'. Output: '{raw_action_items_text}'")
                action_items_list = [] # Default to empty if parsing fails or format is odd

        except RuntimeError as e:
            print(f"Failed to extract action items: {e}")
            # Keep action_items_list as empty

        print(f"Analysis complete for '{original_filename}'. Summary length: {len(summary_text)}, Action Items found: {len(action_items_list)}")

        return {
            "summary": summary_text,
            "action_items": action_items_list,
            "original_filename": original_filename
        }

if __name__ == "__main__":
    print("--- Testing SummarizerService ---")

    # This test requires a valid GEMINI_API_KEY environment variable.
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        print("Skipping SummarizerService tests: GEMINI_API_KEY environment variable not set.")
        print("Please set this variable to run these tests: export GEMINI_API_KEY='your_api_key_here'")
    else:
        print(f"Using Gemini API Key from environment variable (last 5 chars): ...{gemini_api_key[-5:]}")

        # Test 1: Initialization
        print("\n1. Test Initialization")
        try:
            summarizer = SummarizerService(api_key=gemini_api_key)
            print("SummarizerService initialized successfully.")
        except Exception as e:
            print(f"Initialization failed: {e}")
            summarizer = None # Ensure summarizer is None if init fails

        if summarizer:
            # Test 2: Analyze a sample transcript
            print("\n2. Test Analyze Transcript")
            sample_transcript = """
            Hello team, welcome to the meeting. Today we discussed the Q3 project goals.
            Alice needs to finalize the report by Friday. Bob, please schedule a follow-up with the client.
            We also agreed that the new marketing campaign looks promising.
            Remember, the deadline for budget submission is next Wednesday.
            This was a productive session.
            """
            filename = "sample_meeting.wav"

            try:
                analysis_result = summarizer.analyze_transcript(sample_transcript, filename)
                print("\nAnalysis Result:")
                print(f"  Original Filename: {analysis_result['original_filename']}")
                print(f"  Summary: {analysis_result['summary']}")
                print(f"  Action Items: {analysis_result['action_items']}")

                assert analysis_result["original_filename"] == filename
                assert len(analysis_result["summary"]) > 0, "Summary should not be empty"
                # It's hard to assert specific action items as LLM output can vary.
                # Check if it's a list, and potentially if it contains expected keywords if stable enough.
                assert isinstance(analysis_result["action_items"], list), "Action items should be a list."
                if len(analysis_result["action_items"]) > 0:
                    print("Found some action items, which is good.")
                else:
                    print("No action items identified by the model for this sample, or extraction failed.")

            except RuntimeError as e:
                print(f"Transcript analysis failed: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during transcript analysis test: {e}")

            # Test 3: Empty transcript
            print("\n3. Test Empty Transcript")
            try:
                empty_transcript_result = summarizer.analyze_transcript("", "empty.wav")
                print(f"Empty transcript result: {empty_transcript_result}")
                assert empty_transcript_result["summary"] == ""
                assert empty_transcript_result["action_items"] == []
            except Exception as e:
                print(f"Test with empty transcript failed: {e}")
        else:
            print("Summarizer not initialized, skipping further tests.")

    # Test 4: Initialization without API Key
    print("\n4. Test Initialization without API Key")
    try:
        SummarizerService(api_key="")
        print("Error: SummarizerService initialized with empty API key (unexpected).")
    except ValueError as e:
        print(f"Caught expected ValueError for empty API key: {e}")
    except Exception as e:
        print(f"Caught unexpected error for empty API key test: {e}")

    print("\n--- SummarizerService tests finished ---")
