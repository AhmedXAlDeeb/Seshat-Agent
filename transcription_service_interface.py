from abc import ABC, abstractmethod
from pathlib import Path

class TranscriptionService(ABC):
    """
    Abstract base class for transcription services.
    """

    @abstractmethod
    def __init__(self, config: dict):
        """
        Initializes the transcription service with the given configuration.

        Args:
            config: A dictionary containing configuration parameters for the service.
        """
        pass

    @abstractmethod
    def transcribe(self, audio_path: Path) -> str:
        """
        Transcribes the audio file at the given path.

        Args:
            audio_path: The path to the audio file.

        Returns:
            The transcribed text.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the transcription service.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_config_schema() -> dict:
        """
        Returns a schema describing the configurable options for this service.
        The schema should be a dictionary where keys are parameter names
        and values describe the parameter (e.g., type, allowed values, description).
        Example:
        {
            "model_size": {
                "type": "string",
                "default": "base",
                "options": ["tiny", "base", "small", "medium", "large"],
                "description": "The model size for Whisper."
            },
            "language": {
                "type": "string",
                "default": "en",
                "description": "Language code for transcription (e.g., 'en', 'es')."
            }
        }
        """
        pass
