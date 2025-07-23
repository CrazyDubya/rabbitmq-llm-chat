"""
Improved Flask web interface with proper configuration, security, and error handling.
Separated from database models and using modern Flask patterns.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound
import secrets
from typing import Optional, Dict, Any

from config import config
from logger import get_logger
from models import db, User, LLM, init_db
from rabbitmq_module import RabbitMQ, RabbitMQError
from llm_registry import LLMRegistry
from chatroom_manager import ChatroomManager

logger = get_logger(__name__)


class WebInterface:
    """Flask web interface with improved security and error handling."""
    
    def __init__(self):
        """Initialize Flask application with configuration."""
        self.app = Flask(__name__)
        self.rabbitmq: Optional[RabbitMQ] = None
        self.llm_registry = LLMRegistry()
        self.chatroom_manager = ChatroomManager()
        
        self._setup_app()
        self._setup_routes()
        self._setup_error_handlers()
    
    def _setup_app(self) -> None:
        """Setup Flask application configuration."""
        web_config = config.get_web_config()
        db_config = config.get_database_config()
        
        # Flask configuration
        self.app.config['SQLALCHEMY_DATABASE_URI'] = db_config['uri']
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = db_config['track_modifications']
        self.app.config['SECRET_KEY'] = web_config['secret_key']
        
        # Validate secret key
        if web_config['secret_key'] == 'dev-key-change-in-production':
            logger.warning("Using default secret key - change for production!")
        
        # Initialize extensions
        init_db(self.app)
        
        # CORS configuration
        if config.get('security', 'cors', 'enabled'):
            CORS(self.app, origins=config.get('security', 'cors', 'origins', default=['*']))
        
        # Rate limiting
        if config.get('security', 'rate_limit', 'enabled'):
            self.limiter = Limiter(
                app=self.app,
                key_func=get_remote_address,
                default_limits=[f"{config.get('security', 'rate_limit', 'requests_per_minute', default=60)}/minute"]
            )
        
        # Initialize RabbitMQ connection
        try:
            self.rabbitmq = RabbitMQ()
            self.rabbitmq.connect()
            logger.info("RabbitMQ connection established")
        except RabbitMQError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.rabbitmq = None
    
    def _setup_routes(self) -> None:
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main page route."""
            try:
                chatrooms = [room.to_dict() for room in self.chatroom_manager.get_all_chatrooms()]
                return render_template('index2.html', chatrooms=chatrooms)
            except Exception as e:
                logger.error(f"Error loading index page: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/health')
        def health_check():
            """Health check endpoint."""
            health_status = {
                'status': 'healthy',
                'timestamp': config.get('timestamp', default='unknown'),
                'services': {
                    'database': 'up',
                    'rabbitmq': 'up' if self.rabbitmq and self.rabbitmq._is_connected else 'down'
                },
                'stats': {
                    'chatrooms': self.chatroom_manager.get_chatroom_stats(),
                    'llms': self.llm_registry.get_registry_stats()
                }
            }
            
            status_code = 200 if health_status['services']['rabbitmq'] == 'up' else 503
            return jsonify(health_status), status_code
        
        @self.app.route('/api/chatrooms', methods=['GET'])
        def get_chatrooms():
            """Get all chatrooms API endpoint."""
            try:
                chatrooms = [room.to_dict() for room in self.chatroom_manager.get_all_chatrooms()]
                return jsonify({'chatrooms': chatrooms})
            except Exception as e:
                logger.error(f"Error getting chatrooms: {e}")
                return jsonify({'error': 'Failed to get chatrooms'}), 500
        
        @self.app.route('/api/chatrooms', methods=['POST'])
        def create_chatroom():
            """Create new chatroom API endpoint."""
            try:
                data = request.get_json()
                if not data:
                    raise BadRequest("JSON data required")
                
                name = data.get('name', '').strip()
                creator_id = data.get('creator_id', 'anonymous')
                topic = data.get('topic', '')
                description = data.get('description', '')
                
                if not name:
                    return jsonify({'error': 'Chatroom name is required'}), 400
                
                success = self.chatroom_manager.create_chatroom(
                    name=name,
                    creator_id=creator_id,
                    topic=topic,
                    description=description
                )
                
                if success:
                    # Create RabbitMQ queue for chatroom
                    if self.rabbitmq:
                        try:
                            queue_name = f"chatroom_{name}"
                            self.rabbitmq.create_queue(queue_name)
                            logger.info(f"Created queue for chatroom: {name}")
                        except RabbitMQError as e:
                            logger.error(f"Failed to create queue for chatroom {name}: {e}")
                    
                    return jsonify({'message': 'Chatroom created successfully', 'name': name}), 201
                else:
                    return jsonify({'error': 'Chatroom already exists'}), 409
                    
            except BadRequest as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Error creating chatroom: {e}")
                return jsonify({'error': 'Failed to create chatroom'}), 500
        
        @self.app.route('/api/llms/register', methods=['POST'])
        def register_llm():
            """Register LLM API endpoint."""
            try:
                data = request.get_json()
                if not data:
                    raise BadRequest("JSON data required")
                
                required_fields = ['name', 'endpoint', 'chatrooms']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400
                
                llm_id = data.get('llm_id') or f"llm_{secrets.token_hex(8)}"
                name = data['name']
                endpoint = data['endpoint']
                api_token = data.get('api_token') or secrets.token_hex(32)
                chatrooms = data['chatrooms'] if isinstance(data['chatrooms'], list) else [data['chatrooms']]
                
                success = self.llm_registry.register_llm(
                    llm_id=llm_id,
                    name=name,
                    endpoint=endpoint,
                    api_key=api_token,
                    chatrooms=chatrooms
                )
                
                if success:
                    return jsonify({
                        'message': 'LLM registered successfully',
                        'llm_id': llm_id,
                        'api_token': api_token
                    }), 201
                else:
                    return jsonify({'error': 'LLM already registered or API key in use'}), 409
                    
            except BadRequest as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Error registering LLM: {e}")
                return jsonify({'error': 'Failed to register LLM'}), 500
        
        @self.app.route('/api/messages/send', methods=['POST'])
        def send_message():
            """Send message API endpoint."""
            try:
                # Check authentication
                api_key = request.headers.get('Authorization')
                if not api_key:
                    api_key = request.headers.get('X-API-Key')
                
                if not api_key:
                    raise Unauthorized("API key required")
                
                # Remove 'Bearer ' prefix if present
                if api_key.startswith('Bearer '):
                    api_key = api_key[7:]
                
                # Validate API key
                llm_info = self.llm_registry.get_llm_by_api_key(api_key)
                if not llm_info:
                    raise Unauthorized("Invalid API key")
                
                data = request.get_json()
                if not data:
                    raise BadRequest("JSON data required")
                
                chatroom_name = data.get('chatroom_name')
                message = data.get('message')
                
                if not chatroom_name or not message:
                    return jsonify({'error': 'chatroom_name and message are required'}), 400
                
                # Check if LLM can access this chatroom
                if chatroom_name not in llm_info.chatrooms:
                    return jsonify({'error': 'LLM not authorized for this chatroom'}), 403
                
                # Add message to chatroom
                message_id = self.chatroom_manager.add_message_to_chatroom(
                    chatroom_name=chatroom_name,
                    sender_id=llm_info.llm_id,
                    content=message,
                    sender_type='llm'
                )
                
                # Publish to RabbitMQ
                if self.rabbitmq:
                    try:
                        routing_key = f"chatroom_{chatroom_name}"
                        message_data = {
                            'message_id': message_id,
                            'chatroom_name': chatroom_name,
                            'sender_id': llm_info.llm_id,
                            'sender_type': 'llm',
                            'content': message,
                            'timestamp': config.get('timestamp', default='unknown')
                        }
                        self.rabbitmq.publish_message(routing_key, message_data)
                        logger.info(f"Message published to RabbitMQ: {routing_key}")
                    except RabbitMQError as e:
                        logger.error(f"Failed to publish message to RabbitMQ: {e}")
                        # Don't fail the request, message is still stored
                
                return jsonify({
                    'message': 'Message sent successfully',
                    'message_id': message_id
                }), 200
                
            except (Unauthorized, BadRequest) as e:
                return jsonify({'error': str(e)}), e.code
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return jsonify({'error': 'Failed to send message'}), 500
        
        @self.app.route('/api/chatrooms/<chatroom_name>/messages', methods=['GET'])
        def get_chatroom_messages(chatroom_name: str):
            """Get messages from chatroom API endpoint."""
            try:
                limit = min(int(request.args.get('limit', 50)), 100)  # Cap at 100
                offset = int(request.args.get('offset', 0))
                
                messages = self.chatroom_manager.get_chatroom_messages(
                    chatroom_name=chatroom_name,
                    limit=limit,
                    offset=offset
                )
                
                return jsonify({
                    'messages': [msg.to_dict() for msg in messages],
                    'count': len(messages)
                })
                
            except ValueError as e:
                return jsonify({'error': 'Invalid limit or offset parameter'}), 400
            except Exception as e:
                logger.error(f"Error getting messages for chatroom {chatroom_name}: {e}")
                return jsonify({'error': 'Failed to get messages'}), 500
        
        @self.app.route('/api/llms', methods=['GET'])
        def get_llms():
            """Get LLM registry API endpoint."""
            try:
                llms = [llm.to_dict() for llm in self.llm_registry.get_all_llms()]
                stats = self.llm_registry.get_registry_stats()
                
                return jsonify({
                    'llms': llms,
                    'stats': stats
                })
            except Exception as e:
                logger.error(f"Error getting LLMs: {e}")
                return jsonify({'error': 'Failed to get LLMs'}), 500
    
    def _setup_error_handlers(self) -> None:
        """Setup error handlers."""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Internal server error: {error}")
            return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.errorhandler(RabbitMQError)
        def rabbitmq_error(error):
            logger.error(f"RabbitMQ error: {error}")
            return jsonify({'error': 'Message queue service unavailable'}), 503
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None, 
            debug: Optional[bool] = None) -> None:
        """
        Run the Flask application.
        
        Args:
            host: Host to bind to (uses config default if not provided)
            port: Port to bind to (uses config default if not provided)
            debug: Debug mode (uses config default if not provided)
        """
        web_config = config.get_web_config()
        
        run_host = host or web_config['host']
        run_port = port or web_config['port']
        run_debug = debug if debug is not None else web_config['debug']
        
        logger.info(f"Starting web interface on {run_host}:{run_port} (debug={run_debug})")
        self.app.run(host=run_host, port=run_port, debug=run_debug)


def create_app() -> Flask:
    """
    Factory function to create Flask app.
    
    Returns:
        Configured Flask application
    """
    web_interface = WebInterface()
    return web_interface.app


# Standalone execution
if __name__ == '__main__':
    web_interface = WebInterface()
    web_interface.run()