# web_interface.py
from flask import Flask, render_template, request, jsonify
from rabbitmq_module import RabbitMQ
from llm_registry import LLMRegistry
from chatroom_manager import ChatroomManager

app = Flask(__name__)
rabbitmq = RabbitMQ(host='localhost', port=5672, username='guest', password='guest')
rabbitmq.connect()
llm_registry = LLMRegistry()
chatroom_manager = ChatroomManager()

@app.route('/')
def index():
    chatrooms = chatroom_manager.get_all_chatrooms()
    return render_template('index2.html', chatrooms=chatrooms)

@app.route('/register_llm', methods=['POST'])
def register_llm():
    llm_name = request.form['llm_name']
    endpoint = request.form['endpoint']
    api_token = request.form['api_token']
    chatrooms = request.form['chatrooms'].split(',')
    llm_registry.register_llm(llm_name, endpoint, api_token, chatrooms)
    return jsonify({'message': 'LLM registered successfully'})

@app.route('/send_message', methods=['POST'])
def send_message():
    chatroom_name = request.form['chatroom_name']
    message = request.form['message']
    rabbitmq.publish_message(chatroom_name, chatroom_name, message)
    chatroom_manager.add_message_to_chatroom(chatroom_name, message)
    return jsonify({'message': 'Message sent successfully'})

if __name__ == '__main__':
    app.run()