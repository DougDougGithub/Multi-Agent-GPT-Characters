# Multi Agent GPT Characters
Web app that allows 3 GPT characters and a human to talk to each other.  
Written by DougDoug. Feel free to use this for whatever you want! Credit is appreciated but not required.  

This is uploaded for educational purposes. Unfortunately I don't have time to offer individual support or review pull requests, but ChatGPT or Claude can be very helpful if you are running into issues.

## SETUP:
1) This was written in Python 3.9.2. Install page here: https://www.python.org/downloads/release/python-392/

2) Run `pip install -r requirements.txt` to install all modules.

3) This uses the OpenAi API and Elevenlabs services. You'll need to set up an account with these services and generate an API key from them. Then add these keys as windows environment variables named OPENAI_API_KEY and ELEVENLABS_API_KEY respectively.

4) This app uses the GPT-4o model from OpenAi. As of this writing (Sep 3rd 2024), you need to pay $5 to OpenAi in order to get access to the GPT-4o model API. So after setting up your account with OpenAi, you will need to pay for at least $5 in credits so that your account is given the permission to use the GPT-4o model when running my app. See here: https://help.openai.com/en/articles/7102672-how-can-i-access-gpt-4-gpt-4-turbo-gpt-4o-and-gpt-4o-mini

5) Elevenlabs is the service I use for Ai voices. Once you've made Ai voices on the Elevenlabs website, open up multi_agent_gpt.py and make sure it's passing the name of your voices into each agent's init function.

6) This app uses the open source Whisper model from OpenAi for transcribing audio into text. This means you'll be running an Ai model locally on your PC, so ideally you have an Nvidia GPU to run this. The Whisper model is used to transcribe the user's microphone recordings, and is used to generate subtitles from the Elevenlabs audio every time an agent "speaks". This model was downloaded from Huggingface and should install automatically when you run the whisper_openai.py file.  
Note that you'll want to make sure you've installed torch with CUDA support, rather than just default torch, otherwise it will run very slow: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118.  
If you have issues with the Whisper model there are other services that can offer an audio-to-text service (including a Whisper API), but this solution currently works well for me.

7) This code runs a Flask web app and will display the agents' dialogue using HTML and javascript. By default it will run the server on "127.0.0.1:5151", but you can change this in multi_agent_gpt.py.

8) Optionally, you can use OBS Websockets and an OBS plugin to make images move while talking.  
First open up OBS. Make sure you're running version 28.X or later. Click Tools, then WebSocket Server Settings. Make sure "Enable WebSocket server" is checked. Then set Server Port to '4455' and set the Server Password to 'TwitchChat9'. If you use a different Server Port or Server Password in your OBS, just make sure you update the websockets_auth.py file accordingly.  
Next install the Move OBS plugin: https://obsproject.com/forum/resources/move.913/ Now you can use this plugin to add a filter to an audio source that will change an image's transform based on the audio waveform. For example, I have a filter on a specific audio track that will move each agent's bell pepper icon source image whenever that pepper is talking.  
Note that OBS must be open when you're running this code, otherwise OBS WebSockets won't be able to connect. If you don't need the images to move while talking, you can just delete the OBS portions of the code.

## Using the App

To start out, edit the ai_prompts.py file to design each agent's personality and the purpose of their conversation.  
By default the characters are told to discuss the greatest videogames of all time, but you can change this to anything you want, OpenAi is pretty great at having agents talk about pretty much anything.

Next run multi_agent_gpt.py

Once it's running you now have a number of options:

__Press Numpad7 to "talk" to the agents.__  
Numpad7 will start recording your microphone audio. Hit Numpad8 to stop recording. It will then transcribe your audio into text and add your dialogue into all 3 agents' chat history. Then it will pick a random agent to "activate" and have them start talking next.

__Numpad1 will "activate" Agent #1.__  
This means that agent will continue the conversation and start talking. Unless it has been "paused", it will also pick a random other agent and "activate" them to talk next, so that the conversation continues indefinitely.

__Numpad2 will "activate" Agent #2, Numpad3 will "activate" Agent #3.__

__F4 will "pause" all agents__   
This stops the agents from activating each other. Basically, use this to stop the conversation from continuing any further, and then you can talk to the agents again.

## Miscellaneous notes:

All agents will automatically store their "chat history" into a backup txt file as the conversation continues. This is done so that when you restart the program, each agent will automatically load from their backup file and thus restore the entire conversation, letting you continue it from where you left off. If you ever want to fully reset the conversation then just delete the backup txt files in the project.

If you want to have the agent dialogue displayed in OBS, you should add a browser source and set the URL to "127.0.0.1:5151". 
