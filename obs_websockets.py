import time
from obswebsocket import obsws, requests  # noqa: E402
from websockets_auth import WEBSOCKET_HOST, WEBSOCKET_PORT, WEBSOCKET_PASSWORD

##########################################################
##########################################################

class OBSWebsocketsManager:
    ws = None
    
    def __init__(self):
        # Connect to websockets
        self.ws = obsws(WEBSOCKET_HOST, WEBSOCKET_PORT, WEBSOCKET_PASSWORD)
        self.ws.connect()
        print("Connected to OBS Websockets!\n")

    def disconnect(self):
        self.ws.disconnect()

    # Set the current scene
    def set_scene(self, new_scene):
        self.ws.call(requests.SetCurrentProgramScene(sceneName=new_scene))

    # Set the visibility of any source's filters
    def set_filter_visibility(self, source_name, filter_name, filter_enabled=True):
        self.ws.call(requests.SetSourceFilterEnabled(sourceName=source_name, filterName=filter_name, filterEnabled=filter_enabled))

    # Set the visibility of any source
    def set_source_visibility(self, scene_name, source_name, source_visible=True):
        response = self.ws.call(requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
        myItemID = response.datain['sceneItemId']
        self.ws.call(requests.SetSceneItemEnabled(sceneName=scene_name, sceneItemId=myItemID, sceneItemEnabled=source_visible))

    # Returns the current text of a text source
    def get_text(self, source_name):
        response = self.ws.call(requests.GetInputSettings(inputName=source_name))
        return response.datain["inputSettings"]["text"]

    # Returns the text of a text source
    def set_text(self, source_name, new_text):
        self.ws.call(requests.SetInputSettings(inputName=source_name, inputSettings = {'text': new_text}))

    def get_source_transform(self, scene_name, source_name):
        response = self.ws.call(requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
        myItemID = response.datain['sceneItemId']
        response = self.ws.call(requests.GetSceneItemTransform(sceneName=scene_name, sceneItemId=myItemID))
        transform = {}
        transform["positionX"] = response.datain["sceneItemTransform"]["positionX"]
        transform["positionY"] = response.datain["sceneItemTransform"]["positionY"]
        transform["scaleX"] = response.datain["sceneItemTransform"]["scaleX"]
        transform["scaleY"] = response.datain["sceneItemTransform"]["scaleY"]
        transform["rotation"] = response.datain["sceneItemTransform"]["rotation"]
        transform["sourceWidth"] = response.datain["sceneItemTransform"]["sourceWidth"] # original width of the source
        transform["sourceHeight"] = response.datain["sceneItemTransform"]["sourceHeight"] # original width of the source
        transform["width"] = response.datain["sceneItemTransform"]["width"] # current width of the source after scaling, not including cropping. If the source has been flipped horizontally, this number will be negative.
        transform["height"] = response.datain["sceneItemTransform"]["height"] # current height of the source after scaling, not including cropping. If the source has been flipped vertically, this number will be negative.
        transform["cropLeft"] = response.datain["sceneItemTransform"]["cropLeft"] # the amount cropped off the *original source width*. This is NOT scaled, must multiply by scaleX to get current # of cropped pixels
        transform["cropRight"] = response.datain["sceneItemTransform"]["cropRight"] # the amount cropped off the *original source width*. This is NOT scaled, must multiply by scaleX to get current # of cropped pixels
        transform["cropTop"] = response.datain["sceneItemTransform"]["cropTop"] # the amount cropped off the *original source height*. This is NOT scaled, must multiply by scaleY to get current # of cropped pixels
        transform["cropBottom"] = response.datain["sceneItemTransform"]["cropBottom"] # the amount cropped off the *original source height*. This is NOT scaled, must multiply by scaleY to get current # of cropped pixels
        return transform

    # The transform should be a dictionary containing any of the following keys with corresponding values
    # positionX, positionY, scaleX, scaleY, rotation, width, height, sourceWidth, sourceHeight, cropTop, cropBottom, cropLeft, cropRight
    # e.g. {"scaleX": 2, "scaleY": 2.5}
    # Note: there are other transform settings, like alignment, etc, but these feel like the main useful ones.
    # Use get_source_transform to see the full list
    def set_source_transform(self, scene_name, source_name, new_transform):
        response = self.ws.call(requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
        myItemID = response.datain['sceneItemId']
        self.ws.call(requests.SetSceneItemTransform(sceneName=scene_name, sceneItemId=myItemID, sceneItemTransform=new_transform))

    # Note: an input, like a text box, is a type of source. This will get *input-specific settings*, not the broader source settings like transform and scale
    # For a text source, this will return settings like its font, color, etc
    def get_input_settings(self, input_name):
        return self.ws.call(requests.GetInputSettings(inputName=input_name))

    # Get list of all the input types
    def get_input_kind_list(self):
        return self.ws.call(requests.GetInputKindList())

    # Get list of all items in a certain scene
    def get_scene_items(self, scene_name):
        return self.ws.call(requests.GetSceneItemList(sceneName=scene_name))
    
    # Immediately ends the stream. Use with caution.
    def stop_stream(self):
        return self.ws.call(requests.StopStream())

