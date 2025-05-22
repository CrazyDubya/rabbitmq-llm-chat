# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    llms = db.relationship('LLM', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class LLM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    api_key = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# web_interface.py
from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail, Message
from flask_dance.contrib.google import make_google_blueprint, google
from models import db, User, LLM
from llm_registry import LLMRegistry
from chatroom_manager import ChatroomManager
from rabbitmq_module import RabbitMQ
import secrets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['MAIL_SERVER'] = 'your-mail-server'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'

db.init_app(app)
mail = Mail(app)

google_bp = make_google_blueprint(scope=['profile', 'email'])
app.register_blueprint(google_bp, url_prefix='/auth')

rabbitmq = RabbitMQ(host='localhost', port=5672, username='guest', password='guest')
llm_registry = LLMRegistry()
chatroom_manager = ChatroomManager()

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    if not google.authorized:
        return redirect(url_for('google.login'))
    user_info = google.get('/oauth2/v1/userinfo').json()
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    chatrooms = chatroom_manager.get_all_chatrooms()
    return render_template('index.html', chatrooms=chatrooms, user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        send_confirmation_email(user)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    user = User.verify_confirmation_token(token)
    if not user:
        return 'Invalid confirmation token'
    user.confirmed = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/register_llm', methods=['POST'])
def register_llm():
    name = request.form['name']
    description = request.form['description']
    user_id = request.form['user_id']
    api_key = secrets.token_hex(16)
    llm = LLM(name=name, description=description, api_key=api_key, user_id=user_id)
    db.session.add(llm)
    db.session.commit()
    llm_registry.register_llm(llm.id, api_key)
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    api_key = request.headers.get('Authorization')
    if not api_key:
        return 'Unauthorized', 401
    llm_id = llm_registry.get_llm_id(api_key)
    if not llm_id:
        return 'Invalid API key', 401
    chatroom_name = request.form['chatroom_name']
    message = request.form['message']
    rabbitmq.publish_message(chatroom_name, llm_id, message)
    return 'Message sent successfully'

def send_confirmation_email(user):
    token = user.generate_confirmation_token()
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = 'Please confirm your email'
    body = f'Please click the following link to confirm your email: {confirm_url}'
    send_email(user.email, subject, body)

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to])
    msg.body = body
    mail.send(msg)

if __name__ == '__main__':
    app.run()