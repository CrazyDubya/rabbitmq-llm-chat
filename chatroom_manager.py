# chatroom_manager.py
from models import db, User, LLM


class ChatroomManager:
    """Manages chatrooms and their messages.

    This class is responsible for creating, retrieving, and managing
    multiple chatrooms, including adding messages to them.
    """

    def __init__(self):
        """Initializes the ChatroomManager with an empty dictionary to store chatrooms."""
        self.chatrooms = {}

    def create_chatroom(self, chatroom_name: str, user_id: int) -> bool:
        """Creates a new chatroom.

        Args:
            chatroom_name (str): The desired name for the new chatroom.
            user_id (int): The ID of the user creating the chatroom.

        Returns:
            bool: True if the chatroom was created successfully, False if a
                  chatroom with the same name already exists.
        """
        if chatroom_name not in self.chatrooms:
            self.chatrooms[chatroom_name] = {
                "name": chatroom_name,
                "user_id": user_id,
                "messages": [],
            }
            return True
        return False

    def get_chatroom(self, chatroom_name: str) -> dict | None:
        """Retrieves a specific chatroom by its name.

        Args:
            chatroom_name (str): The name of the chatroom to retrieve.

        Returns:
            dict | None: The chatroom object (a dictionary) if found,
                         otherwise None.
        """
        return self.chatrooms.get(chatroom_name)

    def get_all_chatrooms(self) -> list[dict]:
        """Retrieves a list of all chatrooms.

        Returns:
            list[dict]: A list of all chatroom objects. Each chatroom
                        is represented as a dictionary.
        """
        return list(self.chatrooms.values())

    def add_message_to_chatroom(
        self, chatroom_name: str, llm_id: int, message: str
    ) -> bool:
        """Adds a message to a specified chatroom.

        Args:
            chatroom_name (str): The name of the chatroom to add the message to.
            llm_id (int): The ID of the LLM sending the message.
            message (str): The content of the message.

        Returns:
            bool: True if the message was added successfully, False if the
                  chatroom does not exist.
        """
        chatroom = self.get_chatroom(chatroom_name)
        if chatroom:
            chatroom["messages"].append({"llm_id": llm_id, "message": message})
            return True
        return False
