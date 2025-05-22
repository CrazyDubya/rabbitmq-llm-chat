# chat-start.py
# logLLMchats.py
from rabbitmq_module import RabbitMQ
from llm_registry import LLMRegistry
from chatroom_manager import ChatroomManager

def main():
    # Create instances of the necessary classes
    rabbitmq = RabbitMQ(host='localhost', port=5672, username='guest', password='guest')
    llm_registry = LLMRegistry()
    chatroom_manager = ChatroomManager()

    # Connect to RabbitMQ
    rabbitmq.connect()

    # Register LLMs
    llm_registry.register_llm('LLM1', 'http://localhost:8000', 'abc123', ['chatroom1', 'chatroom2'])
    llm_registry.register_llm('LLM2', 'http://localhost:8001', 'def456', ['chatroom1'])

    # Create chatrooms
    chatroom_manager.create_chatroom('chatroom1', ['LLM1', 'LLM2'])
    chatroom_manager.create_chatroom('chatroom2', ['LLM1'])

    # Create queues for each chatroom
    for chatroom in chatroom_manager.get_all_chatrooms():
        queue_name = f"{chatroom['name']}_queue"
        rabbitmq.create_queue(queue_name)

    # Create queues for each LLM
    for llm in llm_registry.get_all_llms():
        queue_name = f"{llm['name']}_queue"
        rabbitmq.create_queue(queue_name)

    # Start consuming messages from RabbitMQ
    def message_callback(ch, method, properties, body):
        print(f"Received message: {body.decode()}")

    for chatroom in chatroom_manager.get_all_chatrooms():
        queue_name = f"{chatroom['name']}_queue"
        rabbitmq.consume_messages(queue_name, message_callback)

if __name__ == '__main__':
    main()