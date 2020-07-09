class RegKeyCannotBeReadError(Exception):

    """
    Custom exception definition, that will be raised in case of an error in reading process of a registry key
    :param msg: The custom message to be shown.
    """
    def __init__(self, msg, key_name):
        super().__init__("Registry Key Cannot be Read! Msg: " + str(msg))
        self.key_name = key_name
