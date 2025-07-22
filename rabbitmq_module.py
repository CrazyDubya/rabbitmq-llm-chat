"""
Improved RabbitMQ module with proper error handling, connection management, and security.
Consolidates RabbitMQ functionality from multiple files into a single, robust implementation.
"""

import json
import time
from typing import Callable, Dict, Any, Optional, Union
import pika
import pika.exceptions
from contextlib import contextmanager

from config import config
from logger import get_logger

logger = get_logger(__name__)


class RabbitMQError(Exception):
    """Custom exception for RabbitMQ-related errors."""
    pass


class RabbitMQ:
    """
    Improved RabbitMQ client with proper connection management, error handling, and security.
    """
    
    def __init__(self, rabbitmq_config: Optional[Dict[str, Any]] = None):
        """
        Initialize RabbitMQ client with configuration.
        
        Args:
            rabbitmq_config: Optional configuration dict, uses global config if not provided
        """
        self.config = rabbitmq_config or config.get_rabbitmq_config()
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._is_connected = False
        
        logger.info(f"Initialized RabbitMQ client for {self.config['host']}:{self.config['port']}")
    
    def connect(self) -> None:
        """
        Establish connection to RabbitMQ server with retry logic.
        
        Raises:
            RabbitMQError: If connection fails after retries
        """
        if self._is_connected:
            logger.debug("Already connected to RabbitMQ")
            return
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                credentials = pika.PlainCredentials(
                    self.config['username'], 
                    self.config['password']
                )
                
                parameters = pika.ConnectionParameters(
                    host=self.config['host'],
                    port=self.config['port'],
                    virtual_host=self.config['virtual_host'],
                    credentials=credentials,
                    connection_attempts=3,
                    retry_delay=retry_delay,
                    socket_timeout=self.config.get('connection_timeout', 30),
                    heartbeat=self.config.get('heartbeat', 600)
                )
                
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare main exchange
                self.channel.exchange_declare(
                    exchange=self.config['exchange'],
                    exchange_type='topic',
                    durable=True
                )
                
                self._is_connected = True
                logger.info("Successfully connected to RabbitMQ")
                return
                
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise RabbitMQError(f"Failed to connect to RabbitMQ after {max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
                raise RabbitMQError(f"Unexpected connection error: {e}")
    
    def disconnect(self) -> None:
        """Safely close connection to RabbitMQ."""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            self._is_connected = False
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def ensure_connected(self) -> None:
        """Ensure connection is established, reconnect if necessary."""
        if not self._is_connected or (self.connection and self.connection.is_closed):
            logger.info("Reconnecting to RabbitMQ...")
            self.connect()
    
    @contextmanager
    def connection_context(self):
        """Context manager for automatic connection management."""
        try:
            self.ensure_connected()
            yield self
        finally:
            pass  # Keep connection alive for reuse
    
    def create_queue(self, queue_name: str, durable: bool = True, 
                    exclusive: bool = False, auto_delete: bool = False,
                    bind_to_exchange: bool = True, routing_key: Optional[str] = None) -> None:
        """
        Create a queue with proper configuration.
        
        Args:
            queue_name: Name of the queue
            durable: Whether queue survives server restart
            exclusive: Whether queue is exclusive to this connection
            auto_delete: Whether queue is deleted when not in use
            bind_to_exchange: Whether to bind queue to main exchange
            routing_key: Routing key for binding (defaults to queue_name)
        """
        self.ensure_connected()
        
        try:
            self.channel.queue_declare(
                queue=queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete
            )
            
            if bind_to_exchange:
                routing_key = routing_key or queue_name
                self.channel.queue_bind(
                    exchange=self.config['exchange'],
                    queue=queue_name,
                    routing_key=routing_key
                )
            
            logger.info(f"Created queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Error creating queue {queue_name}: {e}")
            raise RabbitMQError(f"Failed to create queue {queue_name}: {e}")
    
    def publish_message(self, routing_key: str, message: Union[str, dict], 
                       exchange: Optional[str] = None, persistent: bool = True) -> None:
        """
        Publish message to exchange with proper error handling.
        
        Args:
            routing_key: Routing key for message
            message: Message content (string or dict)
            exchange: Exchange name (uses default if not provided)
            persistent: Whether message should be persistent
        """
        self.ensure_connected()
        
        try:
            exchange = exchange or self.config['exchange']
            
            # Convert dict to JSON string
            if isinstance(message, dict):
                message_body = json.dumps(message)
            else:
                message_body = str(message)
            
            properties = pika.BasicProperties(
                delivery_mode=2 if persistent else 1,  # 2 = persistent
                timestamp=int(time.time()),
                content_type='application/json' if isinstance(message, dict) else 'text/plain'
            )
            
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=properties
            )
            
            logger.debug(f"Published message to {routing_key}")
            
        except Exception as e:
            logger.error(f"Error publishing message to {routing_key}: {e}")
            raise RabbitMQError(f"Failed to publish message: {e}")
    
    def consume_messages(self, queue_name: str, callback: Callable, 
                        auto_ack: bool = False, prefetch_count: int = 1) -> None:
        """
        Start consuming messages from queue with proper error handling.
        
        Args:
            queue_name: Name of queue to consume from
            callback: Callback function for message processing
            auto_ack: Whether to auto-acknowledge messages
            prefetch_count: Number of messages to prefetch
        """
        self.ensure_connected()
        
        try:
            self.channel.basic_qos(prefetch_count=prefetch_count)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            
            logger.info(f"Started consuming from queue: {queue_name}")
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping message consumption...")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error consuming from {queue_name}: {e}")
            raise RabbitMQError(f"Failed to consume messages: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience function for getting RabbitMQ instance
def get_rabbitmq_client(config_override: Optional[Dict[str, Any]] = None) -> RabbitMQ:
    """
    Get configured RabbitMQ client instance.
    
    Args:
        config_override: Optional configuration override
        
    Returns:
        Configured RabbitMQ client
    """
    return RabbitMQ(config_override)