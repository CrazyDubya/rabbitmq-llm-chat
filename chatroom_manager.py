# chatroom_manager.py
from models import db, User, LLM

class ChatroomManager:
    def __init__(self):
        self.chatrooms = {}

    def create_chatroom(self, chatroom_name, user_id):
        if chatroom_name not in self.chatrooms:
            self.chatrooms[chatroom_name] = {
                'name': chatroom_name,
                'user_id': user_id,
                'messages': []
            }
            return True
        return False

    def get_chatroom(self, chatroom_name):
        return self.chatrooms.get(chatroom_name)

    def get_all_chatrooms(self):
        return list(self.chatrooms.values())

    def add_message_to_chatroom(self, chatroom_name, llm_id, message):
        chatroom = self.get_chatroom(chatroom_name)
        if chatroom:
            chatroom['messages'].append({
                'llm_id': llm_id,
                'message': message
            })
            return True
        return False
