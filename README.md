# RabbitMQ LLM Chat Platform

A distributed multi-agent communication platform using RabbitMQ message queues for orchestrating conversations between multiple Language Model agents in real-time.

## 🎯 Features

- **Multi-Agent Architecture**: Support for multiple LLM agents communicating through message queues
- **RabbitMQ Integration**: Robust message routing and delivery with RabbitMQ
- **LLM Registry**: Dynamic registration and management of different AI models
- **Real-time Communication**: Asynchronous message processing and routing
- **Web Interface**: Browser-based chat interface for human-AI interaction
- **Scalable Design**: Distributed architecture supporting horizontal scaling
- **Message Persistence**: Durable message storage and replay capabilities

## 🏗️ Architecture

### Core Components

- **Chat Manager**: Central orchestration of chat rooms and participant management
- **LLM Registry**: Dynamic registration and routing of different AI models
- **Message Router**: RabbitMQ-based message routing and delivery system
- **Web Interface**: Real-time web-based chat interface
- **Consumer Services**: Background workers processing LLM responses

### Message Flow

```
Human Input → Web Interface → RabbitMQ → LLM Agents → Response Queue → Web Interface
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install RabbitMQ
brew install rabbitmq  # macOS
# or
sudo apt-get install rabbitmq-server  # Ubuntu

# Python dependencies
pip install -r requirements.txt
```

### Installation

1. **Start RabbitMQ**:
   ```bash
   rabbitmq-server
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

3. **Start the platform**:
   ```bash
   python chat-start.py
   ```

4. **Access web interface**:
   Open `http://localhost:5000`

## 🔧 Core Components

### **chatroom_manager.py**
Central chat room orchestration:
- Multi-room management
- User session handling
- Message routing coordination
- Real-time updates via WebSocket

### **llm_registry.py**
Dynamic AI model registration:
- Model capability registration
- Load balancing across models
- Health monitoring and failover
- Performance metrics tracking

### **rabbitmq_module.py**
Message queue integration:
- Queue setup and configuration
- Message publishing and consumption
- Dead letter queue handling
- Connection management and retry logic

### **consume.py**
Background message processing:
- Asynchronous message consumption
- LLM response generation
- Error handling and retry logic
- Performance monitoring

### **web_interface.py**
Flask-based web server:
- HTTP request handling
- WebSocket communication
- Session management
- API endpoints

## 🌐 Web Interface

### **index.html**
Main chat interface:
- Real-time messaging display
- User input handling
- Room navigation
- Agent status indicators

### **index2.html**
Alternative interface:
- Enhanced feature set
- Advanced configuration options
- Improved user experience
- Additional visualization tools

## 📊 Message Processing

### **Chat Flow**
1. User sends message through web interface
2. Message published to RabbitMQ exchange
3. Appropriate LLM agents consume message
4. Agents generate responses
5. Responses routed back through message queue
6. Web interface displays results in real-time

### **Queue Management**
- Dedicated queues for each chat room
- Message persistence and durability
- Dead letter queues for failed messages
- Queue monitoring and management

## 🔧 Configuration

### **RabbitMQ Setup**
```python
RABBITMQ_CONFIG = {
    "host": "localhost",
    "port": 5672,
    "virtual_host": "/",
    "exchange": "llm_chat",
    "queue_prefix": "chat_room_"
}
```

### **LLM Integration**
```python
LLM_PROVIDERS = {
    "openai": ["gpt-4", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-sonnet", "claude-3-haiku"]
}
```

## 🔄 Advanced Features

### **Load Balancing**
- Automatic distribution of requests across available agents
- Health monitoring and failover capabilities
- Performance-based routing decisions

### **Message Persistence**
- Durable message storage in RabbitMQ
- Conversation history replay
- Message archival and cleanup

### **Scalability**
- Horizontal scaling of consumer services
- Multiple RabbitMQ instances support
- Distributed agent deployment

## 📈 Monitoring

### **Performance Metrics**
- Message throughput and latency
- Agent response times and quality
- Queue depth and processing rates

### **Logging**
- Comprehensive chat logging via `logLLMchats.py`
- Error tracking and debugging
- Performance analytics

## 🛠️ Development

### **Adding New LLM Providers**
1. Register in `llm_registry.py`
2. Implement response generation logic
3. Configure queue routing
4. Update web interface

### **Custom Message Types**
1. Define message schema in `models.py`
2. Implement processing logic
3. Update consumer services
4. Test integration

## 🔒 Security

- User authentication and session management
- API key protection for LLM services
- Message encryption for sensitive conversations
- Rate limiting and abuse prevention

## 📁 Project Structure

```
rabbitmq-llm-chat/
├── chat-start.py          # Application entry point
├── chatroom_manager.py    # Chat room orchestration
├── llm_registry.py        # AI model management
├── rabbitmq_module.py     # Message queue integration
├── consume.py            # Background processing
├── web_interface.py      # Flask web server
├── models.py            # Data models
├── rabbit.py            # RabbitMQ utilities
├── logLLMchats.py       # Logging system
├── index.html           # Main web interface
├── index2.html          # Alternative interface
├── requirements.txt     # Dependencies
└── README.md           # Documentation
```

## 🧪 Testing

### **Running Tests**
```bash
python -m pytest tests/ -v
```

### **Manual Testing**
1. Start RabbitMQ server
2. Run `python chat-start.py`
3. Open web interface
4. Test message routing and responses

## 🚀 Deployment

### **Production Setup**
```bash
# Install and configure RabbitMQ
sudo systemctl start rabbitmq-server

# Deploy application
python chat-start.py --production
```

### **Docker Deployment**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "chat-start.py"]
```

## 🤝 Contributing

Contributions welcome for:
- New LLM provider integrations
- Enhanced web interface features
- Performance optimizations
- Additional message queue backends

## 📄 License

This project demonstrates distributed AI systems and message queue architectures for educational and research purposes.

---

**Note**: This platform showcases advanced concepts in distributed systems, message queues, and multi-agent AI architectures.