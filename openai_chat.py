from openai import OpenAI
import tiktoken
import os
from rich import print
import base64
import time
import json

class OpenAiManager:
    
    def __init__(self, system_prompt=None, chat_history_backup=None):
        """
        Optionally provide a chat_history_backup txt file and a system_prompt string.
        If the backup file is provided, we load the chat history from it.
        If the backup file already exists, then we don't add the system prompt into the convo history, because we assume that it already has a system prompt in it.
        Alternatively you manually add new system prompts into the chat history at any point. 
        """

        self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        self.logging = True # Determines whether the module should print out its results
        self.tiktoken_encoder = None # Used to calculate the token count in messages
        self.chat_history = []

        # If a backup file is provided, we will save our chat history to that file after every call
        self.chat_history_backup = chat_history_backup
        
        # If the backup file already exists, we load its contents into the chat_history
        if chat_history_backup and os.path.exists(chat_history_backup):
            with open(chat_history_backup, 'r') as file:
                self.chat_history = json.load(file)
        elif system_prompt:
            # If the chat history file doesn't exist, then our chat history is currently empty.
            # If we were provided a system_prompt, add it into the chat history as the first message.
            self.chat_history.append(system_prompt)

    # Write our current chat history to the txt file
    def save_chat_to_backup(self):
        if self.chat_history_backup:
            with open(self.chat_history_backup, 'w') as file:
                json.dump(self.chat_history, file)

    def num_tokens_from_messages(self, messages, model='gpt-4o'):
        """Returns the number of tokens used by a list of messages.
        The code below is an adaptation of this text-only version: https://platform.openai.com/docs/guides/chat/managing-tokens 

        Note that image tokens are calculated differently from text.
        The guide for image token calculation is here: https://platform.openai.com/docs/guides/vision
        Short version is that a 1920x1080 image is going to be 1105 tokens, so just using that for all images for now.
        In the future I could swap to 'detail: low' and cap it at 85 tokens. Might be necessary for certain use cases.

        There are three message formats we have to check:
        Version 1: the 'content' is just a text string
            'content' = 'What are considered some of the most popular characters in videogames?'
        Version 2: the content is an array with a single dictionary, with two key/value pairs
            'content' = [{'type': 'text', 'text': 'What are considered some of the most popular characters in videogames?'}]
        Version 3: the content is an array with two dictionaries, one for the text portion and one for the image portion
            'content' = [{'type': 'text', 'text': 'Okay now please compare the previous image I sent you with this new image!'}, {'type': 'image_url', 'image_url': {'url': 'https://i.gyazo.com/8ec349446dbb538727e515f2b964224c.png', 'detail': 'high'}}]
        """
        try:
            if self.tiktoken_encoder == None:
                self.tiktoken_encoder = tiktoken.encoding_for_model(model) # We store this value so we don't have to check again every time
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    if key == 'role':
                        num_tokens += len(self.tiktoken_encoder.encode(value))
                    elif key == 'content':
                        # In the case that value is just a string, simply get its token value and move on
                        if isinstance(value, str):
                            num_tokens += len(self.tiktoken_encoder.encode(value))
                            continue

                        # In this case the 'content' variables value is an array of dictionaries
                        for message_data in value:
                            for content_key, content_value in message_data.items():
                                if content_key == 'type':
                                    num_tokens += len(self.tiktoken_encoder.encode(content_value))
                                elif content_key == 'text': 
                                    num_tokens += len(self.tiktoken_encoder.encode(content_value))
                                elif content_key == "image_url":
                                    num_tokens += 1105 # Assumes the image is 1920x1080 and that detail is set to high               
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        except Exception:
            # Either this model is not implemented in tiktoken, or there was some error processing the messages
            raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.""")

    # Asks a question with no chat history
    def chat(self, prompt=""):
        if not prompt:
            print("Didn't receive input!")
            return

        # Check that the prompt is under the token context limit
        chat_question = [{"role": "user", "content": prompt}]
        if self.num_tokens_from_messages(chat_question) > 128000:
            print("The length of this chat question is too large for the GPT model")
            return

        print("[yellow]\nAsking ChatGPT a question...")
        completion = self.client.chat.completions.create(
          model="gpt-4o",
          messages=chat_question
        )

        # Process the answer
        openai_answer = completion.choices[0].message.content
        if self.logging:
            print(f"[green]\n{openai_answer}\n")
        return openai_answer
    
    # Analyze an image without history
    # Works with jpg, jpeg, or png. Alternatively can provide an image URL by setting local_image to False
    # More info here: https://platform.openai.com/docs/guides/vision
    def analyze_image(self, prompt, image_path, local_image=True):
        # Use default prompt if one isn't provided
        if prompt is None:
            prompt = "Please give me a detailed description of this image."
        # If this is a local image, encode it into base64. Otherwise just use the provided URL.
        if local_image:
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                    url = f"data:image/jpeg;base64,{base64_image}"
            except:
                print("[red]ERROR: COULD NOT BASE64 ENCODE THE IMAGE. PANIC!!")
                return None
        else:
            url = image_path # The provided image path is a URL
        if self.logging:
            print("[yellow]\nAsking ChatGPT to analyze image...")
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                            "detail": "high"
                        }
                    },
                ],
                },
            ],
            max_tokens=4096, # max of 4096 tokens as of Dec 25th 2023
        )
        openai_answer = completion.choices[0].message.content
        if self.logging:
            print(f"[green]\n{openai_answer}\n")
        return openai_answer
    

    # Asks a question that includes the full conversation history
    # Can include a mix of text and images
    def chat_with_history(self, prompt="", image_path="", local_image=True):
        
        # If we received a prompt, add it into our chat history.
        # Prompts are technically optional because the Ai can just continue the conversation from where it left off.
        if prompt is not None and prompt != "":
            # Create a new chat message with the text prompt
            new_chat_message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
            # If an image is provided, add the image url info into our new message.
            if image_path != "":
                # If this is a local image, we encode it into base64. Otherwise just use the provided URL.
                if local_image:
                    try:
                        with open(image_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                            url = f"data:image/jpeg;base64,{base64_image}"
                    except:
                        print("[red]ERROR: COULD NOT BASE64 ENCODE THE IMAGE. PANIC!!")
                        return None
                else:
                    url = image_path # The provided image path is a URL
                new_image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": url,
                        "detail": "high"
                    }
                }
                new_chat_message["content"].append(new_image_content)

            # Add the new message into our chat history
            self.chat_history.append(new_chat_message)

        # Check total token limit. Remove old messages as needed
        if self.logging:
            print(f"[coral]Chat History has a current token length of {self.num_tokens_from_messages(self.chat_history)}")
        while self.num_tokens_from_messages(self.chat_history) > 128000:
            self.chat_history.pop(1) # We skip the 1st message since it's the system message
            if self.logging:
                print(f"Popped a message! New token length is: {self.num_tokens_from_messages(self.chat_history)}")

        if self.logging:
            print("[yellow]\nAsking ChatGPT a question...")
        completion = self.client.chat.completions.create(
          model="gpt-4o",
          messages=self.chat_history
        )

        # Add this answer to our chat history
        self.chat_history.append({"role": completion.choices[0].message.role, "content": completion.choices[0].message.content})

        # If a backup file was provided, write out convo history to the txt file
        self.save_chat_to_backup()

        # Return answer
        openai_answer = completion.choices[0].message.content
        if self.logging:
            print(f"[green]\n{openai_answer}\n")
        return openai_answer
    
