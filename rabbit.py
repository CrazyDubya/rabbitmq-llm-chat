import os
import json
import time
import random
import anthropic
import pika
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    def publish_message(self, exchange, routing_key, message):
        self.channel.basic_publish(exchange=exchange, routing_key=routing_key, body=message)

    def consume_messages(self, queue, callback):
        self.channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()
class LocalModel:
    def __init__(self):
        with open("apis/config.json") as f:
            self.config = json.load(f)["LOCAL_MODELS"]

    def process_local_model(self, model_name, messages, temperature, max_tokens):
        base_url = f"http://localhost:{self.config[model_name]['port']}/v1"
        client = OpenAI(api_key="NONE", base_url=base_url)

        response = client.chat.completions.create(
            model=self.config[model_name]["name"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
class Claude3:
    def __init__(self):
        self.api_key = os.environ.get("CLAUDE_API_KEY")
        with open("apis/config.json") as f:
            self.config = json.load(f)["CLAUDE_MODELS"]

    def process_claude_model(self, model_name, temperature, system_prompt, refined_input, max_tokens):
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.config[model_name]["name"],
            temperature=temperature,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": refined_input}]
        )
        return response.content[0].text

def process_message(ch, method, properties, body):
    try:
        message = json.loads(body)
        model_name = message["model_name"]

        if model_name == "local1":
            logger.info(f"Processing message for Local Model 1")
            local1_response = local_model.process_local_model(
                "local1",
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": "Topic: sports, Subtopic: football"}],
                temperature,
                max_tokens
            )
            logger.info(f"Local Model 1 response: {local1_response}")
            rabbitmq.publish_message("chatroom_history", "sports.football.local1", local1_response)
        elif model_name == "local2":
            logger.info(f"Processing message for Local Model 2")
            local2_response = local_model.process_local_model(
                "local2",
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": "Topic: sports, Subtopic: football"}],
                temperature,
                max_tokens
            )
            logger.info(f"Local Model 2 response: {local2_response}")
            rabbitmq.publish_message("chatroom_history", "sports.football.local2", local2_response)
        elif model_name == "haiku":
            logger.info(f"Processing message for Claude-haiku")
            claude_response = claude_model.process_claude_model(
                "haiku",
                temperature,
                system_prompt,
                "Topic: sports, Subtopic: football",
                max_tokens
            )
            logger.info(f"Claude-haiku response: {claude_response}")
            rabbitmq.publish_message("chatroom_history", "sports.football.haiku", claude_response)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def main():
    global local_model, claude_model, rabbitmq, max_tokens, temperature, delay, system_prompt

    local_model = LocalModel()
    claude_model = Claude3()
    rabbitmq = RabbitMQ(host="localhost", port=5672, username="guest", password="guest")
    rabbitmq.connect()


    rabbitmq.channel.queue_declare(queue="sports.football.haiku")
    rabbitmq.channel.queue_declare(queue="sports.football.local1")
    rabbitmq.channel.queue_declare(queue="sports.football.local2")

    rabbitmq.channel.queue_bind(exchange="llm_communication", queue="sports.football.haiku", routing_key="sports.football.haiku")
    rabbitmq.channel.queue_bind(exchange="llm_communication", queue="sports.football.local1", routing_key="sports.football.local1")
    rabbitmq.channel.queue_bind(exchange="llm_communication", queue="sports.football.local2", routing_key="sports.football.local2")

    max_tokens = 1000
    temperature = 0.7
    delay = 5

    system_prompt = """
    You are participating in a chatroom with other AI models. The chatroom topic is sports, and the subtopic is football.
    Please engage in the conversation based on the provided topic and subtopic. You can reply a maximum of 3 times. Speak less stilted, more human, and do not identify as a model. Assume a name if you wish.
    """

    for model_name in ["local1", "local2", "haiku"]:
        message = json.dumps({"model_name": model_name})
        rabbitmq.publish_message("llm_communication", f"sports.football.{model_name}", message)
        time.sleep(delay)

    try:
        rabbitmq.consume_messages("llm_communication", process_message)
    except KeyboardInterrupt:
        logger.info("Stopping the application...")
    finally:
        rabbitmq.close()
        logger.info("Application stopped.")

if __name__ == '__main__':
    app.run()