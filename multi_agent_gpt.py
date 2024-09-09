# This code runs a thread that manages the frontend code, a thread that listens for keyboard presses from the human, and then threads for the 3 agents
# Once running, the human can activate a single agent and then let the agents continue an ongoing conversation.
# Each thread has the following core logic:

# Main Thread
    # Runs the web app

# Agent X
    # Waits to be activated
    # Once it is activated (by Doug or by another agent):
        # Acquire conversation lock
            # Get response from OpenAI
            # Add this new response to all other agents' chat histories
        # Creates TTS with ElevenLabs
        # Acquire speaking lock (so only 1 speaks at a time)
            # Pick another thread randomly, activate them
                # Because this happens within the speaking lock, we are guaranteed that the other agents are inactive when this called.
                # But, we start this now so that the next speaker can have their answer and audio ready to go the instant this agent is done talking.
            # Update client and OBS to display stuff
            # Play the TTS audio
            # Release speaking lock (Other threads can now talk)
    
# Human Input Thread
    # Listens for keypresses:

    # If F7 is pressed:
        # Toggles "pause" flag - stops other agents from activating additional agents

        # Record mic audio (until you press F8)

        # Get convo lock (but not speaking lock)
            # In theory, wait until everyone is done speaking, and because the agents are "paused" then no new ones will add to the convo
            # But to be safe, grab the convo lock to ensure that all agents HAVE to wait until my response is added into the convo history
        
        # Transcribe mic audio into text with Whisper
        # Add Doug's response into all agents' chat history
        
        # Release the convo lock
        # (then optionally press a key to trigger a specific bot)

    # If F4 pressed:
        # Toggles "pause" flag - stops all other agents from activating additional agents
    
    # If 1 pressed:
        # Turns off "pause" flag
        # Activates Agent 1
    
    # If 2 pressed: 
        # Turns off "pause" flag
        # Activates Agent 2
    
    # If 3 pressed: 
        # Turns off "pause" flag
        # Activates Agent 3

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
import threading
import time
import keyboard
import random
import logging
from rich import print

from audio_player import AudioManager
from eleven_labs import ElevenLabsManager
from openai_chat import OpenAiManager
from whisper_openai import WhisperManager
from obs_websockets import OBSWebsocketsManager
from ai_prompts import *

socketio = SocketIO
app = Flask(__name__)
app.config['SERVER_NAME'] = "127.0.0.1:5151"
socketio = SocketIO(app, async_mode="threading")
log = logging.getLogger('werkzeug') # Sets flask app to only print error messages, rather than all info logs
log.setLevel(logging.ERROR)

@app.route("/")
def home():
    return render_template('index.html')

@socketio.event
def connect():
    print("[green]The server connected to client!")

obswebsockets_manager = OBSWebsocketsManager()
whisper_manager = WhisperManager()
elevenlabs_manager = ElevenLabsManager()
audio_manager = AudioManager()

speaking_lock = threading.Lock()
conversation_lock = threading.Lock()

agents_paused = False

# Class that represents a single ChatGPT Agent and its information
class Agent():
    
    def __init__(self, agent_name, agent_id, filter_name, all_agents, system_prompt, elevenlabs_voice):
        # Flag of whether this agent should begin speaking
        self.activated = False 
        # Used to identify each agent in the conversation history
        self.name = agent_name 
        # an int used to ID this agent to the frontend code
        self.agent_id = agent_id 
        # the name of the OBS filter to activate when this agent is speaking
        # You don't need to use OBS filters as part of this code, it's optional for adding extra visual flair
        self.filter_name = filter_name 
        # A list of the other agents, so that you can pick one to randomly "activate" when you finish talking
        self.all_agents = all_agents
        # The name of the Elevenlabs voice that you want this agent to speak with
        self.voice = elevenlabs_voice
        # The name of the txt backup file where this agent's conversation history will be stored
        backup_file_name = f"backup_history_{agent_name}.txt"
        # Initialize the OpenAi manager with a system prompt and a file that you would like to save your conversation too
        # If the backup file isn't empty, then it will restore that backed up conversation for this agent
        self.openai_manager = OpenAiManager(system_prompt, backup_file_name) 
        # Optional - tells the OpenAi manager not to print as much
        self.openai_manager.logging = False

    def run(self):
        while True:
            # Wait until we've been activated
            if not self.activated:
                time.sleep(0.1)
                continue
                
            self.activated = False
            print(f"[italic purple] {self.name} has STARTED speaking.")
            
            # This lock isn't necessary in theory, but for safety we will require this lock whenever updating any agent's convo history
            with conversation_lock:
                # Generate a response to the conversation
                openai_answer = self.openai_manager.chat_with_history("Okay what is your response? Try to be as chaotic and bizarre and adult-humor oriented as possible. Again, 3 sentences maximum.")
                openai_answer = openai_answer.replace("*", "")
                print(f'[magenta]Got the following response:\n{openai_answer}')

                # Add your new response into everyone else's chat history, then have them save their chat history
                # This agent's responses are marked as "assistant" role to itself, so everyone elses messages are "user" role.
                for agent in self.all_agents:
                    if agent is not self:
                        agent.openai_manager.chat_history.append({"role": "user", "content": f"[{self.name}] {openai_answer}"})
                        agent.openai_manager.save_chat_to_backup()

            # Create audio response
            tts_file = elevenlabs_manager.text_to_audio(openai_answer, self.voice, False)

            # Process the audio to get subtitles
            audio_and_timestamps = whisper_manager.audio_to_text(tts_file, "sentence")

            # Wait here until the current speaker is finished
            with speaking_lock:

                # If we're "paused", then simply finish speaking without activating another agent
                # Otherwise, pick another agent randomly, then activate it
                if not agents_paused:
                    other_agents = [agent for agent in self.all_agents if agent is not self]
                    random_agent = random.choice(other_agents)
                    random_agent.activated = True

                # Activate move filter on the image
                obswebsockets_manager.set_filter_visibility("Line In", self.filter_name, True)
            
                # Play the TTS audio (without pausing)
                audio_manager.play_audio(tts_file, False, False, True)

                # While the audio is playing, display each sentence on the front-end
                # Each dictionary will look like: {'text': 'here is my speech', 'start_time': 11.58, 'end_time': 14.74}
                socketio.emit('start_agent', {'agent_id': self.agent_id})
                try:
                    for i in range(len(audio_and_timestamps)):
                        current_sentence = audio_and_timestamps[i]
                        duration = current_sentence['end_time'] - current_sentence['start_time']
                        socketio.emit('agent_message', {'agent_id': self.agent_id, 'text': f"{current_sentence['text']}"})
                        time.sleep(duration)
                        # If this is not the final sentence, sleep for the gap of time inbetween this sentence and the next one starting
                        if i < (len(audio_and_timestamps) - 1):
                            time_between_sentences = audio_and_timestamps[i+1]['start_time'] - current_sentence['end_time']
                            time.sleep(time_between_sentences)
                except Exception:
                    print(f"[magenta] Whoopsie! There was a problem and I don't know why. This was the current_sentence it broke on: {current_sentence}")
                socketio.emit('clear_agent', {'agent_id': self.agent_id})
            
                time.sleep(1) # Wait one second before the next person talks, otherwise their audio gets cut off

                # Turn off the filter in OBS
                obswebsockets_manager.set_filter_visibility("Line In", self.filter_name, False)

            print(f"[italic purple] {self.name} has FINISHED speaking.")        


# Class that handles human input, this thread is how you can manually activate or pause the other agents
class Human():
    
    def __init__(self, name, all_agents):
        self.name = name # This will be added to the beginning of the response
        self.all_agents = all_agents

    def run(self):
        global agents_paused
        while True:

            # Speak into mic and add the dialogue to the chat history
            if keyboard.is_pressed('num 7'):

                # Toggles "pause" flag - stops other agents from activating additional agents
                agents_paused = True
                print(f"[italic red] Agents have been paused")

                # Record mic audio from Doug (until he presses '=')
                print(f"[italic green] DougDoug has STARTED speaking.")
                mic_audio = audio_manager.record_audio(end_recording_key='num 8')

                with conversation_lock:
                    # Transcribe mic audio into text with Whisper
                    transcribed_audio = whisper_manager.audio_to_text(mic_audio)
                    print(f"[teal]Got the following audio from Doug:\n{transcribed_audio}")

                    # Add Doug's response into all agents chat history
                    for agent in self.all_agents:
                        agent.openai_manager.chat_history.append({"role": "user", "content": f"[{self.name}] {transcribed_audio}"})
                        agent.openai_manager.save_chat_to_backup() # Tell the other agents to save their chat history to their backup file
                
                print(f"[italic magenta] DougDoug has FINISHED speaking.")

                # Activate another agent randomly
                agents_paused = False
                random_agent = random.randint(0, len(self.all_agents)-1)
                print(f"[cyan]Activating Agent {random_agent+1}")
                self.all_agents[random_agent].activated = True

            
            # "Pause" the other agents.
            # Whoever is currently speaking will finish, but no future agents will be activated
            if keyboard.is_pressed('f4'):
                print("[italic red] Agents have been paused")
                agents_paused = True
                time.sleep(1) # Wait for a bit to ensure you don't press this twice in a row
            
            # Activate Agent 1
            if keyboard.is_pressed('num 1'):
                print("[cyan]Activating Agent 1")
                agents_paused = False
                self.all_agents[0].activated = True
                time.sleep(1) # Wait for a bit to ensure you don't press this twice in a row
            
            # Activate Agent 2
            if keyboard.is_pressed('num 2'):
                print("[cyan]Activating Agent 2")
                agents_paused = False
                self.all_agents[1].activated = True
                time.sleep(1) # Wait for a bit to ensure you don't press this twice in a row
            
            # Activate Agent 3
            if keyboard.is_pressed('num 3'):
                print("[cyan]Activating Agent 3")
                agents_paused = False
                self.all_agents[2].activated = True
                time.sleep(1) # Wait for a bit to ensure you don't press this twice in a row
            
            time.sleep(0.05)
                


def start_bot(bot):
    bot.run()

if __name__ == '__main__':

    all_agents = []

    # Agent 1
    agent1 = Agent("OSWALD", 1, "Audio Move - Wario Pepper", all_agents, VIDEOGAME_AGENT_1, "Dougsworth")
    agent1_thread = threading.Thread(target=start_bot, args=(agent1,))
    agent1_thread.start()

    # Agent 2
    agent2 = Agent("TONY KING OF NEW YORK", 2, "Audio Move - Waluigi Pepper", all_agents, VIDEOGAME_AGENT_2, "Tony Emperor of New York")
    agent2_thread = threading.Thread(target=start_bot, args=(agent2,))
    agent2_thread.start()

    # Agent 3
    agent3 = Agent("VICTORIA", 3, "Audio Move - Gamer Pepper", all_agents, VIDEOGAME_AGENT_3, "Victoria")
    agent3_thread = threading.Thread(target=start_bot, args=(agent3,))
    agent3_thread.start()

    all_agents.append(agent1)
    all_agents.append(agent2)
    all_agents.append(agent3)

    # Human thread
    human = Human("DOUGDOUG", all_agents)
    human_thread = threading.Thread(target=start_bot, args=(human,))
    human_thread.start()

    print("[italic green]!!AGENTS ARE READY TO GO!!\nPress Num 1, Num 2, or Num3 to activate an agent.\nPress F7 to speak to the agents.")

    socketio.run(app)

    agent1_thread.join()
    agent2_thread.join()
    agent3_thread.join()
    human_thread.join()