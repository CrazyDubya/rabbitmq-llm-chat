# rabbitmq_module.py
import pika

class RabbitMQ:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None

    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port, credentials=credentials))
        self.channel = self.connection.channel()

    def close(self):
        if self.connection:
            self.connection.close()

    def publish_message(self, chatroom_name, llm_id, message):
        self.channel.basic_publish(exchange='', routing_key=chatroom_name, body=message)

    def consume_messages(self, chatroom_name, callback):
        self.channel.basic_consume(queue=chatroom_name, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()