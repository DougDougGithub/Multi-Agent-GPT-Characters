import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from rich import print
import time

class WhisperManager():

    # Uses Whisper on HuggingFace: https://huggingface.co/openai/whisper-large-v3
    # Need to make sure you've installed torch with CUDA support, rather than just default torch: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    # I tried a lot but could not get Flash Attention 2 to install. It would speed up performance but isn't necessary.

    def __init__(self):
        print(torch.cuda.is_available())  # Should return True if CUDA is available
        print(torch.cuda.get_device_name(0))  # Should return the name of your GPU, e.g., "NVIDIA GeForce RTX 4070 Ti"
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = "openai/whisper-large-v3"

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        )
        model.to(device)
        model.generation_config.is_multilingual = False
        model.generation_config.language = "en"

        processor = AutoProcessor.from_pretrained(model_id)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=256,
            chunk_length_s=30,
            batch_size=16,
            return_timestamps=True,
            torch_dtype=torch_dtype,
            device=device,
        )
    
    # Converts an audio file into transcribed text. Can provide also provide timestamps
    # wav and mp3 files appear to take the same amount of time to process
    # With test files, word timestamps took 3.5-4 seconds, sentence timestamps took 2.2 seconds, no timestamps took 1.9-2 seconds
    def audio_to_text(self, audio_file, timestamps=None):
        if timestamps == None:
            result = self.pipe(audio_file, return_timestamps=False)
        elif timestamps == "sentence":
            result = self.pipe(audio_file, return_timestamps=True)
        elif timestamps == "word":
            result = self.pipe(audio_file, return_timestamps="word")
        else:
            result = {"text": " "}
        if timestamps == None:
            # If they didn't want the timestamps, then just return the text
            return result["text"]
        else:
            # Return an array of dictionaries that contain every sentence/word with its corresponding start and end time
            # I reformat the data a bit so that it's more intuitive to work with.
            # Each dictionary will look like: {'text': 'here is my speech', 'start_time': 11.58, 'end_time': 14.74}
            timestamped_chunks = []
            for chunk in result['chunks']:
                new_chunk = {
                    'text': chunk['text'],
                    'start_time': chunk['timestamp'][0],
                    'end_time': chunk['timestamp'][1]
                }
                timestamped_chunks.append(new_chunk)
            return timestamped_chunks

