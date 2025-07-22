#!/usr/bin/env python3
"""
Main application entry point for RabbitMQ LLM Chat Platform.
Consolidates multiple entry points into a unified command-line interface.
"""

import argparse
import sys
import os
import signal
import threading
import time
from typing import Optional

from config import config
from logger import get_logger, Logger
from web_interface import WebInterface
from consume import LLMConsumerService
from rabbitmq_module import RabbitMQ, RabbitMQError
from models import init_db, create_admin_user
from llm_registry import LLMRegistry
from chatroom_manager import ChatroomManager

logger = get_logger(__name__)


class Application:
    """Main application controller."""
    
    def __init__(self):
        """Initialize application."""
        self.web_interface: Optional[WebInterface] = None
        self.consumer_service: Optional[LLMConsumerService] = None
        self.rabbitmq: Optional[RabbitMQ] = None
        self.llm_registry = LLMRegistry()
        self.chatroom_manager = ChatroomManager()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def validate_config(self) -> bool:
        """
        Validate configuration and report issues.
        
        Returns:
            True if configuration is valid for production, False otherwise
        """
        issues = config.validate()
        
        if issues:
            logger.warning("Configuration validation issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            return False
        
        logger.info("Configuration validation passed")
        return True
    
    def setup_rabbitmq(self) -> bool:
        """
        Setup RabbitMQ connection and basic infrastructure.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            self.rabbitmq = RabbitMQ()
            self.rabbitmq.connect()
            
            # Create basic exchanges and queues
            logger.info("Setting up RabbitMQ infrastructure...")
            
            # Create common queues
            common_queues = [
                "llm_communication",
                "chatroom_history",
                "system_events"
            ]
            
            for queue in common_queues:
                self.rabbitmq.create_queue(queue)
            
            logger.info("RabbitMQ setup completed")
            return True
            
        except RabbitMQError as e:
            logger.error(f"Failed to setup RabbitMQ: {e}")
            return False
    
    def register_demo_llms(self) -> None:
        """Register demo LLMs for testing."""
        demo_llms = [
            {
                'llm_id': 'demo_local1',
                'name': 'Demo Local Model 1',
                'endpoint': 'http://localhost:8001/v1',
                'api_key': 'demo_key_1',
                'chatrooms': ['general', 'sports']
            },
            {
                'llm_id': 'demo_local2', 
                'name': 'Demo Local Model 2',
                'endpoint': 'http://localhost:8002/v1',
                'api_key': 'demo_key_2',
                'chatrooms': ['general', 'tech']
            }
        ]
        
        for llm_config in demo_llms:
            success = self.llm_registry.register_llm(**llm_config)
            if success:
                logger.info(f"Registered demo LLM: {llm_config['name']}")
    
    def create_demo_chatrooms(self) -> None:
        """Create demo chatrooms for testing."""
        demo_rooms = [
            {
                'name': 'general',
                'creator_id': 'system',
                'topic': 'General Discussion',
                'description': 'Open discussion for all topics'
            },
            {
                'name': 'sports',
                'creator_id': 'system', 
                'topic': 'Sports Talk',
                'description': 'Discuss your favorite sports and teams'
            },
            {
                'name': 'tech',
                'creator_id': 'system',
                'topic': 'Technology',
                'description': 'Technology discussions and programming'
            }
        ]
        
        for room_config in demo_rooms:
            success = self.chatroom_manager.create_chatroom(**room_config)
            if success:
                logger.info(f"Created demo chatroom: {room_config['name']}")
                
                # Create RabbitMQ queue for chatroom
                if self.rabbitmq:
                    try:
                        queue_name = f"chatroom_{room_config['name']}"
                        self.rabbitmq.create_queue(queue_name)
                    except RabbitMQError as e:
                        logger.error(f"Failed to create queue for {room_config['name']}: {e}")
    
    def run_web_server(self, host: Optional[str] = None, port: Optional[int] = None,
                      debug: Optional[bool] = None) -> None:
        """
        Run web server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Debug mode
        """
        logger.info("Starting web server...")
        
        self.web_interface = WebInterface()
        
        # Setup demo data if requested
        if config.get('demo_mode', default=True):
            self.register_demo_llms()
            self.create_demo_chatrooms()
        
        try:
            self.running = True
            self.web_interface.run(host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            logger.info("Web server stopped by user")
        except Exception as e:
            logger.error(f"Web server error: {e}")
            raise
        finally:
            self.running = False
    
    def run_consumer_service(self) -> None:
        """Run LLM consumer service."""
        logger.info("Starting LLM consumer service...")
        
        try:
            self.consumer_service = LLMConsumerService()
            self.running = True
            
            while self.running:
                try:
                    self.consumer_service.start_consuming()
                except KeyboardInterrupt:
                    logger.info("Consumer service stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Consumer service error: {e}")
                    if self.running:
                        logger.info("Restarting consumer service in 5 seconds...")
                        time.sleep(5)
                    
        finally:
            if self.consumer_service:
                self.consumer_service.stop()
            self.running = False
    
    def run_full_platform(self, host: Optional[str] = None, port: Optional[int] = None,
                         debug: Optional[bool] = None) -> None:
        """
        Run full platform (web server + consumer service).
        
        Args:
            host: Host to bind to
            port: Port to bind to  
            debug: Debug mode
        """
        logger.info("Starting full RabbitMQ LLM Chat Platform...")
        
        # Setup demo data
        if config.get('demo_mode', default=True):
            self.register_demo_llms()
            self.create_demo_chatrooms()
        
        # Start consumer service in background thread
        consumer_thread = threading.Thread(
            target=self.run_consumer_service,
            daemon=True,
            name="ConsumerService"
        )
        consumer_thread.start()
        
        # Start web server in main thread
        try:
            self.run_web_server(host=host, port=port, debug=debug)
        finally:
            self.running = False
            logger.info("Platform shutdown completed")
    
    def setup_database(self, create_admin: bool = False) -> None:
        """
        Setup database tables and optionally create admin user.
        
        Args:
            create_admin: Whether to create an admin user
        """
        logger.info("Setting up database...")
        
        from flask import Flask
        app = Flask(__name__)
        
        web_config = config.get_web_config()
        db_config = config.get_database_config()
        
        app.config['SQLALCHEMY_DATABASE_URI'] = db_config['uri']
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = db_config['track_modifications']
        app.config['SECRET_KEY'] = web_config['secret_key']
        
        init_db(app)
        
        if create_admin:
            with app.app_context():
                admin_email = input("Enter admin email: ").strip()
                admin_password = input("Enter admin password: ").strip()
                
                if admin_email and admin_password:
                    user = create_admin_user(admin_email, admin_password)
                    if user:
                        logger.info(f"Admin user created: {admin_email}")
                    else:
                        logger.info("Admin user already exists")
                else:
                    logger.error("Email and password are required")
        
        logger.info("Database setup completed")
    
    def show_status(self) -> None:
        """Show application status and statistics."""
        print("\n=== RabbitMQ LLM Chat Platform Status ===\n")
        
        # Configuration status
        print("Configuration:")
        validation_issues = config.validate()
        if validation_issues:
            print("  ❌ Configuration has issues:")
            for issue in validation_issues:
                print(f"     - {issue}")
        else:
            print("  ✅ Configuration is valid")
        
        # RabbitMQ status
        print("\nRabbitMQ:")
        try:
            rabbitmq = RabbitMQ()
            rabbitmq.connect()
            print("  ✅ Connection successful")
            rabbitmq.disconnect()
        except RabbitMQError as e:
            print(f"  ❌ Connection failed: {e}")
        
        # LLM Registry stats
        print("\nLLM Registry:")
        stats = self.llm_registry.get_registry_stats()
        print(f"  Total LLMs: {stats['total_llms']}")
        print(f"  Active: {stats['active']}")
        print(f"  Error: {stats['error']}")
        print(f"  Chatrooms covered: {stats['chatrooms_covered']}")
        
        # Chatroom stats
        print("\nChatrooms:")
        stats = self.chatroom_manager.get_chatroom_stats()
        print(f"  Total: {stats['total_chatrooms']}")
        print(f"  Active: {stats['active_chatrooms']}")
        print(f"  Messages: {stats['total_messages']}")
        print(f"  Participants: {stats['total_participants']}")
        
        print()


def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(description='RabbitMQ LLM Chat Platform')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set logging level')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Web server command
    web_parser = subparsers.add_parser('web', help='Run web server')
    web_parser.add_argument('--host', default=None, help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=None, help='Port to bind to')
    web_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Consumer service command
    subparsers.add_parser('consumer', help='Run LLM consumer service')
    
    # Full platform command
    full_parser = subparsers.add_parser('run', help='Run full platform (web + consumer)')
    full_parser.add_argument('--host', default=None, help='Host to bind to')
    full_parser.add_argument('--port', type=int, default=None, help='Port to bind to')
    full_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Setup commands
    setup_parser = subparsers.add_parser('setup', help='Setup database and infrastructure')
    setup_parser.add_argument('--create-admin', action='store_true', help='Create admin user')
    
    # Status command
    subparsers.add_parser('status', help='Show application status')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate configuration')
    
    args = parser.parse_args()
    
    # Setup logging
    Logger.setup_logging(args.log_level)
    
    app = Application()
    
    # Setup RabbitMQ for most commands
    if args.command in ['web', 'consumer', 'run', 'status']:
        if not app.setup_rabbitmq():
            logger.error("Failed to setup RabbitMQ - some features may not work")
    
    try:
        if args.command == 'web':
            app.run_web_server(host=args.host, port=args.port, debug=args.debug)
        
        elif args.command == 'consumer':
            app.run_consumer_service()
        
        elif args.command == 'run':
            app.run_full_platform(host=args.host, port=args.port, debug=args.debug)
        
        elif args.command == 'setup':
            app.setup_database(create_admin=args.create_admin)
        
        elif args.command == 'status':
            app.show_status()
        
        elif args.command == 'validate':
            is_valid = app.validate_config()
            sys.exit(0 if is_valid else 1)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()