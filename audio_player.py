import pygame
import time
import os
import asyncio
import subprocess
import threading
import keyboard
import wave
import pyaudio
import soundfile as sf
from mutagen.mp3 import MP3
from pydub import AudioSegment
from rich import print

class AudioManager:

    # Variables for recording audio from mic
    is_recording = False
    audio_frames = []
    audio_format = pyaudio.paInt16
    channels = 2
    rate = 44100
    chunk = 1024

    def __init__(self):
        # Use higher frequency to prevent audio glitching noises
        # Use higher buffer because why not (default is 512)
        pygame.mixer.init(frequency=48000, buffer=1024) 

    def play_audio(self, file_path, sleep_during_playback=True, delete_file=False, play_using_music=True):
        """
        Parameters:
        file_path (str): path to the audio file
        sleep_during_playback (bool): means program will wait for length of audio file before returning
        delete_file (bool): means file is deleted after playback (note that this shouldn't be used for multithreaded function calls)
        play_using_music (bool): means it will use Pygame Music, if false then uses pygame Sound instead
        """
        if not pygame.mixer.get_init(): # Reinitialize mixer if needed
            pygame.mixer.init(frequency=48000, buffer=1024) 
        if play_using_music:
            # Pygame Music can only play one file at a time
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                converted = False
            except:
                # Wav files from Elevenlabs don't work with Pygame's Music for some fucking reason (works fine with Sound)
                # If there's an error here that's likely why, so convert it to a format that Pygame can handle
                # You can't convert the file in place so just convert it into a temp file that you delete later
                converted_wav = "temp_convert.wav"
                subprocess.run(["ffmpeg", "-y", "-i", file_path, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", converted_wav])
                converted = True
                pygame.mixer.music.load(converted_wav)
                pygame.mixer.music.play()
        else:
            # Pygame Sound lets you play multiple sounds simultaneously
            pygame_sound = pygame.mixer.Sound(file_path) 
            pygame_sound.play()

        if sleep_during_playback:
            # Sleep until file is done playing
            file_length = self.get_audio_length(file_path)
            time.sleep(file_length)
            # Delete the file
            if delete_file:
                # Stop Pygame so file can be deleted
                # Note: this will stop the audio on other threads as well, so it's not good if you're playing multiple sounds at once
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                try:  
                    os.remove(file_path)
                    if converted:
                        os.remove(converted_wav) # Remove the converted wav if it was created
                except PermissionError:
                    print(f"Couldn't remove {file_path} because it is being used by another process.")

    async def play_audio_async(self, file_path):
        """
        Parameters:
        file_path (str): path to the audio file
        """
        if not pygame.mixer.get_init(): # Reinitialize mixer if needed
            pygame.mixer.init(frequency=48000, buffer=1024) 
        pygame_sound = pygame.mixer.Sound(file_path) 
        pygame_sound.play()

        # Sleep for the duration of the audio.
        # Must use asyncio.sleep() because time.sleep() will block the thread, even if it's in an async function
        file_length = self.get_audio_length(file_path)
        await asyncio.sleep(file_length)
    
    def get_audio_length(self, file_path):
        # Calculate length of the file based on the file format
        _, ext = os.path.splitext(file_path) # Get the extension of this file
        if ext.lower() == '.wav':
            wav_file = sf.SoundFile(file_path)
            file_length = wav_file.frames / wav_file.samplerate
            wav_file.close()
        elif ext.lower() == '.mp3':
            mp3_file = MP3(file_path)
            file_length = mp3_file.info.length
        else:
            print("Unknown audio file type. Returning 0 as file length")
            file_length = 0
        return file_length
    
    def combine_audio_files(self, input_files):
        # input_files is an array of file paths
        output_file = os.path.join(os.path.abspath(os.curdir), f"___Msg{str(hash(' '.join(input_files)))}.wav")
        combined = None
        for file in input_files:
            audio = AudioSegment.from_file(file)
            if combined is None:
                combined = audio
            else:
                combined += audio
        if combined:
            combined.export(output_file, format=os.path.splitext(output_file)[1][1:])
            print(f"Combined file saved as: {output_file}")
        else:
            print("No files to combine.")
        return output_file
    
    def start_recording(self, stream):
        self.audio_frames = []
        while self.is_recording:
            data = stream.read(self.chunk)
            self.audio_frames.append(data)
        print("[red]DONE RECORDING!")

    def record_audio(self, end_recording_key='=', audio_device=None):
        # Records audio from an audio input device.
        # Example device names are "Line In (Realtek(R) Audio)", "Sample (TC-Helicon GoXLR)", or just leave empty to use default mic
        # For some reason this doesn't work on the Broadcast GoXLR Mix, the other 3 GoXLR audio inputs all work fine.
        # Both Azure Speech-to-Text AND this script have issues listening to Broadcast Stream Mix, so just ignore it.
        audio = pyaudio.PyAudio()
        
        if audio_device is None:
            # If no audio_device is provided, use the default mic
            audio_stream = audio.open(format=self.audio_format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk)
        else:
            # If an audio device was provided, find its index
            device_index = None
            for i in range(audio.get_device_count()):
                dev_info = audio.get_device_info_by_index(i)
                # print(dev_info['name'])
                if audio_device in dev_info['name']:
                    device_index = i
                    # Some audio devices only support specific sample rates, so make sure to find a sample rate that's compatible with the device
                    # This was necessary on certain GoXLR input but only sometimes. But this fixes the issues so w/e.
                    supported_rates = [96000, 48000, 44100, 32000, 22050, 16000, 11025, 8000]
                    for rate in supported_rates:
                        try:
                            if audio.is_format_supported(rate, input_device=device_index, input_channels=self.channels, input_format=self.audio_format):
                                self.rate = rate
                                break
                        except ValueError:
                            continue
            if device_index is None:
                raise ValueError(f"Device '{audio_device}' not found")
            if self.rate is None:
                raise ValueError(f"No supported sample rate found for device '{audio_device}'")
            audio_stream = audio.open(format=self.audio_format, channels=self.channels, rate=self.rate, input=True, input_device_index=device_index, frames_per_buffer=self.chunk)
                    
        # Start recording an a second thread
        self.is_recording = True
        threading.Thread(target=self.start_recording, args=(audio_stream,)).start()

        # Wait until end key is pressed
        while True:
            if keyboard.is_pressed(end_recording_key):
                break
            time.sleep(0.05) # Add this to reduce CPU usage
        
        self.is_recording = False
        time.sleep(0.1) # Just for safety, no clue if this is needed

        filename = f"mic_recording_{int(time.time())}.wav"
        wave_file = wave.open(filename, 'wb')
        wave_file.setnchannels(self.channels)
        wave_file.setsampwidth(audio.get_sample_size(self.audio_format))
        wave_file.setframerate(self.rate)
        wave_file.writeframes(b''.join(self.audio_frames))
        wave_file.close()

        # Close the stream and PyAudio
        audio_stream.stop_stream()
        audio_stream.close()
        audio.terminate()

        return filename
        
