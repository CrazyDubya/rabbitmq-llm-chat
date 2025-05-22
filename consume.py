import json
import pika
from openai import OpenAI
import anthropic
import os

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
    message = json.loads(body)
    model_name = message["model_name"]
    system_prompt = """
    You are participating in a chatroom with other AI models. The chatroom topic is sports, and the subtopic is football.
    Please engage in the conversation based on the provided topic and subtopic. You can reply a maximum of 3 times. Speak less stilted, more human, and do not identify as a model. Assume a name if you wish.
    """

    if model_name == "local1":
        local1_response = local_model.process_local_model(
            "local1",
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": "Topic: sports, Subtopic: football"}],
            temperature=0.7,
            max_tokens=1000
        )
        print(f"Local Model 1 response: {local1_response}")
    elif model_name == "local2":
        local2_response = local_model.process_local_model(
            "local2",
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": "Topic: sports, Subtopic: football"}],
            temperature=0.7,
            max_tokens=1000
        )
        print(f"Local Model 2 response: {local2_response}")
    elif model_name == "haiku":
        claude_response = claude_model.process_claude_model(
            "haiku",
            temperature=0.7,
            system_prompt=system_prompt,
            refined_input="Topic: sports, Subtopic: football",
            max_tokens=1000
        )
        print(f"Claude-haiku response: {claude_response}")

if __name__ == "__main__":
    local_model = LocalModel()
    claude_model = Claude3()

    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    channel.basic_consume(queue="sports.football.local1", on_message_callback=process_message, auto_ack=True)
    channel.basic_consume(queue="sports.football.local2", on_message_callback=process_message, auto_ack=True)
    channel.basic_consume(queue="sports.football.haiku", on_message_callback=process_message, auto_ack=True)

    print("Waiting for messages...")
    channel.start_consuming()