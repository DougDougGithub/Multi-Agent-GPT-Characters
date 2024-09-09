from elevenlabs.client import ElevenLabs
from elevenlabs import play, stream, save, Voice, VoiceSettings
import time
import os

class ElevenLabsManager:

    def __init__(self):
        self.client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY')) # Defaults to ELEVEN_API_KEY)
        self.voices = self.client.voices.get_all().voices
        # Create a map of Names->IDs, so that we can easily grab a voice's ID later on 
        self.voice_to_id = {}
        for voice in self.voices:
           self.voice_to_id[voice.name] = voice.voice_id
        self.voice_to_settings = {}

    # Convert text to speech, then save it to file. Returns the file path.
    # Current model options (that I would use) are eleven_monolingual_v1 or eleven_turbo_v2
    # eleven_turbo_v2 takes about 60% of the time that eleven_monolingual_v1 takes
    # However eleven_monolingual_v1 seems to produce more variety and emphasis, whereas turbo feels more monotone. Turbo still sounds good, just a little less interesting
    def text_to_audio(self, input_text, voice="Doug VO Only", save_as_wave=True, subdirectory="", model_id="eleven_monolingual_v1"):
        # Currently seems to be a problem with the API where it uses default voice settings, rather than pulling the proper settings from the website
        # Workaround is to get the voice settings for each voice the first time it's used, then pass those settings in manually
        if voice not in self.voice_to_settings:
            self.voice_to_settings[voice] = self.client.voices.get_settings(self.voice_to_id[voice])
        voice_settings = self.voice_to_settings[voice]
        audio_saved = self.client.generate(text=input_text, voice=Voice(voice_id=self.voice_to_id[voice], settings=voice_settings), model=model_id,)
        if save_as_wave:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.wav"
        else:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.mp3"
        tts_file = os.path.join(os.path.abspath(os.curdir), subdirectory, file_name)
        save(audio_saved,tts_file)
        return tts_file