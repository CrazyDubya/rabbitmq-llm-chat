"""
Improved LLM Consumer Service with proper error handling, configuration, and architecture.
Processes messages from RabbitMQ and generates LLM responses.
"""

import json
import os
import time
from typing import Dict, Any, Optional, List
import pika

from config import config
from logger import get_logger
from rabbitmq_module import RabbitMQ, RabbitMQError

logger = get_logger(__name__)


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize LLM provider.
        
        Args:
            provider_config: Provider configuration dictionary
        """
        self.config = provider_config
        self.api_key = provider_config.get('api_key')
        self.models = provider_config.get('models', [])
    
    def process_message(self, model_name: str, messages: List[Dict[str, str]], 
                       temperature: float, max_tokens: int) -> str:
        """
        Process message and generate response.
        
        Args:
            model_name: Name of the model to use
            messages: List of message dictionaries
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement process_message")


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """Initialize OpenAI provider."""
        super().__init__(provider_config)
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.error("OpenAI package not installed")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def process_message(self, model_name: str, messages: List[Dict[str, str]], 
                       temperature: float, max_tokens: int) -> str:
        """Process message using OpenAI API."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")
        
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """Initialize Anthropic provider."""
        super().__init__(provider_config)
        
        if not self.api_key:
            logger.warning("Anthropic API key not configured")
            return
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized")
        except ImportError:
            logger.error("Anthropic package not installed")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            self.client = None
    
    def process_message(self, model_name: str, messages: List[Dict[str, str]], 
                       temperature: float, max_tokens: int) -> str:
        """Process message using Anthropic API."""
        if not self.client:
            raise RuntimeError("Anthropic client not available")
        
        try:
            # Convert messages format for Anthropic
            system_prompt = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append(msg)
            
            # Use the last user message as the main input
            user_content = user_messages[-1]["content"] if user_messages else ""
            
            response = self.client.messages.create(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LocalModelProvider(LLMProvider):
    """Local model provider using OpenAI-compatible API."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """Initialize local model provider."""
        super().__init__(provider_config)
        
        # Load local model configuration
        try:
            with open("apis/config.json") as f:
                self.local_config = json.load(f).get("LOCAL_MODELS", {})
        except FileNotFoundError:
            logger.warning("Local model config file not found: apis/config.json")
            self.local_config = {}
        except json.JSONDecodeError:
            logger.error("Invalid JSON in local model config file")
            self.local_config = {}
        
        try:
            from openai import OpenAI
            self.openai_class = OpenAI
            logger.info("Local model provider initialized")
        except ImportError:
            logger.error("OpenAI package not installed for local models")
            self.openai_class = None
    
    def process_message(self, model_name: str, messages: List[Dict[str, str]], 
                       temperature: float, max_tokens: int) -> str:
        """Process message using local model."""
        if not self.openai_class:
            raise RuntimeError("OpenAI package not available for local models")
        
        if model_name not in self.local_config:
            raise ValueError(f"Local model {model_name} not configured")
        
        model_config = self.local_config[model_name]
        base_url = f"http://localhost:{model_config['port']}/v1"
        
        try:
            client = self.openai_class(api_key="NONE", base_url=base_url)
            
            response = client.chat.completions.create(
                model=model_config["name"],
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Local model API error for {model_name}: {e}")
            raise


class LLMConsumerService:
    """Improved LLM Consumer Service with multiple provider support."""
    
    def __init__(self):
        """Initialize consumer service."""
        self.rabbitmq: Optional[RabbitMQ] = None
        self.providers: Dict[str, LLMProvider] = {}
        self.llm_config = config.get_llm_config()
        self.running = False
        
        self._setup_providers()
        self._setup_rabbitmq()
    
    def _setup_providers(self) -> None:
        """Setup LLM providers based on configuration."""
        provider_configs = self.llm_config.get('providers', {})
        
        # Setup OpenAI provider
        if 'openai' in provider_configs:
            openai_config = provider_configs['openai']
            if openai_config.get('api_key'):
                self.providers['openai'] = OpenAIProvider(openai_config)
                logger.info("Registered OpenAI provider")
        
        # Setup Anthropic provider
        if 'anthropic' in provider_configs:
            anthropic_config = provider_configs['anthropic']
            if anthropic_config.get('api_key'):
                self.providers['anthropic'] = AnthropicProvider(anthropic_config)
                logger.info("Registered Anthropic provider")
        
        # Setup local model provider
        self.providers['local'] = LocalModelProvider({})
        logger.info("Registered local model provider")
        
        if not self.providers:
            logger.warning("No LLM providers configured")
    
    def _setup_rabbitmq(self) -> None:
        """Setup RabbitMQ connection."""
        try:
            self.rabbitmq = RabbitMQ()
            self.rabbitmq.connect()
            
            # Declare queues for known models
            model_queues = [
                "sports.football.local1",
                "sports.football.local2", 
                "sports.football.haiku",
                "general.openai.gpt4",
                "general.anthropic.claude"
            ]
            
            for queue in model_queues:
                self.rabbitmq.create_queue(queue)
            
            logger.info("RabbitMQ setup completed for consumer service")
            
        except RabbitMQError as e:
            logger.error(f"Failed to setup RabbitMQ: {e}")
            self.rabbitmq = None
    
    def process_message(self, ch, method, properties, body) -> None:
        """
        Process incoming message from RabbitMQ.
        
        Args:
            ch: Channel
            method: Method
            properties: Message properties
            body: Message body
        """
        try:
            message_data = json.loads(body)
            logger.debug(f"Processing message: {message_data}")
            
            # Extract message information
            model_name = message_data.get("model_name")
            provider = message_data.get("provider", "local")
            chatroom = message_data.get("chatroom", "general")
            topic = message_data.get("topic", "general discussion")
            
            if not model_name:
                logger.error("Message missing model_name")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Get provider
            if provider not in self.providers:
                logger.error(f"Unknown provider: {provider}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            llm_provider = self.providers[provider]
            
            # Create system prompt based on chatroom and topic
            system_prompt = f"""
            You are participating in a chatroom named '{chatroom}' with other AI models and users.
            The current topic is: {topic}
            
            Please engage naturally in the conversation. Be helpful, informative, and friendly.
            Keep responses concise but meaningful. Do not identify yourself as an AI model unless relevant.
            You can assume a persona or name if it helps the conversation flow.
            """
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {topic}. Please contribute to the discussion."}
            ]
            
            # Generate response
            try:
                response = llm_provider.process_message(
                    model_name=model_name,
                    messages=messages,
                    temperature=self.llm_config.get('temperature', 0.7),
                    max_tokens=self.llm_config.get('max_tokens', 1000)
                )
                
                logger.info(f"{provider.title()} {model_name} response: {response[:100]}...")
                
                # Publish response back to chatroom
                response_data = {
                    "chatroom_name": chatroom,
                    "sender_id": f"{provider}_{model_name}",
                    "sender_type": "llm",
                    "content": response,
                    "timestamp": time.time(),
                    "metadata": {
                        "provider": provider,
                        "model": model_name,
                        "topic": topic
                    }
                }
                
                if self.rabbitmq:
                    routing_key = f"chatroom_{chatroom}"
                    self.rabbitmq.publish_message(routing_key, response_data)
                
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(f"Error generating response from {provider} {model_name}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start_consuming(self) -> None:
        """Start consuming messages from RabbitMQ."""
        if not self.rabbitmq:
            logger.error("RabbitMQ not available")
            return
        
        logger.info("Starting LLM consumer service...")
        self.running = True
        
        try:
            # Setup QoS
            self.rabbitmq.channel.basic_qos(prefetch_count=1)
            
            # Start consuming from known queues
            consume_queues = [
                "sports.football.local1",
                "sports.football.local2",
                "sports.football.haiku"
            ]
            
            for queue in consume_queues:
                self.rabbitmq.channel.basic_consume(
                    queue=queue,
                    on_message_callback=self.process_message,
                    auto_ack=False
                )
            
            logger.info(f"Consuming from queues: {consume_queues}")
            self.rabbitmq.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Consumer service interrupted")
            self.stop()
        except Exception as e:
            logger.error(f"Consumer service error: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the consumer service."""
        self.running = False
        
        if self.rabbitmq and self.rabbitmq.channel:
            try:
                self.rabbitmq.channel.stop_consuming()
                logger.info("Stopped consuming messages")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
        
        if self.rabbitmq:
            self.rabbitmq.disconnect()


def main():
    """Main function for standalone execution."""
    logger.info("Starting LLM Consumer Service...")
    
    consumer = LLMConsumerService()
    
    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        consumer.stop()
        logger.info("Consumer service shutdown completed")


if __name__ == "__main__":
    main()