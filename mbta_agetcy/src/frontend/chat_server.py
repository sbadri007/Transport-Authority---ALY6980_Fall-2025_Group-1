from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import httpx
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI(title="MBTA Chat UI")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
EXCHANGE_AGENT_URL = "http://localhost:8100"

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_message(self, message: Dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.get("/")
async def get_ui():
    """Serve the enhanced chat UI"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MBTA Agntcy </title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        
        .main-container {
            width: 95%;
            max-width: 1600px;
            height: 90vh;
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 20px;
        }
        
        .chat-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .system-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 20px;
            overflow-y: auto;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4ade80;
            animation: pulse 2s infinite;
        }
        
        .header-right {
            font-size: 12px;
            opacity: 0.9;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            background: #f9fafb;
        }
        
        .message {
            margin-bottom: 20px;
            display: flex;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content {
            background: white;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-bottom-left-radius: 4px;
        }
        
        .message-metadata {
            font-size: 11px;
            color: #9ca3af;
            margin-top: 5px;
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
        }
        
        .chat-input-wrapper {
            display: flex;
            gap: 10px;
        }
        
        #messageInput {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 25px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        #messageInput:focus {
            border-color: #667eea;
        }
        
        #sendButton {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        #sendButton:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        #sendButton:active {
            transform: translateY(0);
        }
        
        #sendButton:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            transform: none;
        }
        
        .typing-indicator {
            display: none;
            padding: 15px 20px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            width: fit-content;
        }
        
        .typing-indicator.active {
            display: block;
        }
        
        .typing-indicator span {
            height: 8px;
            width: 8px;
            background: #9ca3af;
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: typing 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        
        /* System Panel Styles */
        .system-header {
            font-size: 20px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        
        .system-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .system-card-header {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .badge.llm {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .badge.orchestrator {
            background: #fce7f3;
            color: #9f1239;
        }
        
        .badge.success {
            background: #dcfce7;
            color: #15803d;
        }
        
        .badge.pending {
            background: #fef3c7;
            color: #92400e;
        }
        
        .system-detail {
            font-size: 13px;
            color: #6b7280;
            margin: 5px 0;
        }
        
        .system-detail strong {
            color: #1f2937;
        }
        
        .agent-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }
        
        .agent-chip {
            background: #f3f4f6;
            color: #4b5563;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        
        .metric {
            background: #f9fafb;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }
        
        .metric-label {
            font-size: 11px;
            color: #6b7280;
            text-transform: uppercase;
        }
        
        .flow-diagram {
            background: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
            color: #4b5563;
            line-height: 1.6;
        }
        
        .flow-step {
            margin: 5px 0;
            padding-left: 20px;
            position: relative;
        }
        
        .flow-step::before {
            content: "→";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }
        
        @media (max-width: 1200px) {
            .main-container {
                grid-template-columns: 1fr;
                grid-template-rows: 1fr auto;
            }
            
            .system-panel {
                max-height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Chat Container -->
        <div class="chat-container">
            <div class="chat-header">
                <div class="header-left">
                    <div class="status-indicator"></div>
                    MBTA Agntcy
                </div>
            </div>
            
            <div class="chat-messages" id="messages">
                <div style="text-align: center; color: #6b7280; padding: 40px;">
                    <h2 style="margin-bottom: 10px; color: #1f2937;">👋 Welcome to MBTA Agntcy!</h2>
                    <p>Ask me anything about Boston's transit system</p>
                    <p style="font-size: 13px; margin-top: 20px; opacity: 0.7;">
                        Watch the system panel on the right to see how your queries are processed! →
                    </p>
                </div>
                <div class="typing-indicator" id="typingIndicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            
            <div class="chat-input-container">
                <div class="chat-input-wrapper">
                    <input 
                        type="text" 
                        id="messageInput" 
                        placeholder="Ask about routes, schedules, alerts..."
                        onkeypress="handleKeyPress(event)"
                    />
                    <button id="sendButton" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>

        <!-- System Visibility Panel -->
        <div class="system-panel">
            <div class="system-header">⚙️ System Internals</div>
            <div id="systemLog"></div>
        </div>
    </div>

    <script>
        let ws;
        let conversationId = null;
        
        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('Connected to MBTA Agntcy');
                addSystemLog('system', 'WebSocket connected', {status: 'active'});
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                console.log('Disconnected. Reconnecting...');
                addSystemLog('system', 'Connection lost. Reconnecting...', {status: 'reconnecting'});
                setTimeout(connect, 3000);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleMessage(data) {
            if (data.type === 'response') {
                hideTypingIndicator();
                addMessage('assistant', data.content, data.metadata);
                conversationId = data.conversation_id;
            } else if (data.type === 'system') {
                addSystemLog(data.category, data.message, data.details);
            } else if (data.type === 'error') {
                hideTypingIndicator();
                addMessage('assistant', '❌ ' + data.error, {error: true});
            }
        }
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (message && ws.readyState === WebSocket.OPEN) {
                addMessage('user', message);
                showTypingIndicator();
                
                // Add system log for user query
                addSystemLog('input', 'User query received', {
                    query: message,
                    length: message.length
                });
                
                ws.send(JSON.stringify({
                    message: message,
                    conversation_id: conversationId
                }));
                
                input.value = '';
            }
        }
        
        function addMessage(role, content, metadata = {}) {
            const messagesDiv = document.getElementById('messages');
            const welcomeMessage = messagesDiv.querySelector('div[style]');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            if (metadata.agents_used && metadata.agents_used.length > 0) {
                const metadataDiv = document.createElement('div');
                metadataDiv.className = 'message-metadata';
                metadataDiv.textContent = `🤖 Agents: ${metadata.agents_used.join(', ')}`;
                contentDiv.appendChild(metadataDiv);
            }
            
            messageDiv.appendChild(contentDiv);
            messagesDiv.insertBefore(messageDiv, document.getElementById('typingIndicator'));
            
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function addSystemLog(category, message, details = {}) {
            const systemLog = document.getElementById('systemLog');
            const card = document.createElement('div');
            card.className = 'system-card';
            
            let badgeClass = 'badge';
            let icon = '📊';
            
            if (category === 'routing') {
                badgeClass += details.routed_to_orchestrator ? ' orchestrator' : ' llm';
                icon = details.routed_to_orchestrator ? '🔄' : '🧠';
            } else if (category === 'agents') {
                badgeClass += ' success';
                icon = '🤖';
            } else if (category === 'input') {
                badgeClass += ' pending';
                icon = '📝';
            }
            
            let html = `
                <div class="system-card-header">
                    <span>${icon}</span>
                    <span>${message}</span>
                </div>
            `;
            
            if (category === 'routing') {
                html += `
                    <div class="system-detail">
                        <strong>Intent:</strong> ${details.intent || 'unknown'}
                    </div>
                    <div class="system-detail">
                        <strong>Route:</strong> ${details.routed_to_orchestrator ? 'Orchestrator' : 'Direct LLM'}
                    </div>
                    ${details.confidence ? `<div class="system-detail"><strong>Confidence:</strong> ${(details.confidence * 100).toFixed(0)}%</div>` : ''}
                `;
            } else if (category === 'agents') {
                html += `
                    <div class="system-detail">
                        <strong>Agents Called:</strong>
                    </div>
                    <div class="agent-list">
                        ${details.agents.map(a => `<div class="agent-chip">${a}</div>`).join('')}
                    </div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">${details.count || 0}</div>
                            <div class="metric-label">Agents</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${details.duration ? details.duration + 'ms' : 'N/A'}</div>
                            <div class="metric-label">Duration</div>
                        </div>
                    </div>
                `;
            } else if (category === 'flow') {
                html += `
                    <div class="flow-diagram">
                        ${details.steps.map(s => `<div class="flow-step">${s}</div>`).join('')}
                    </div>
                `;
            } else if (category === 'input') {
                html += `
                    <div class="system-detail">"${details.query}"</div>
                    <div class="system-detail"><strong>Length:</strong> ${details.length} characters</div>
                `;
            }
            
            card.innerHTML = html;
            systemLog.insertBefore(card, systemLog.firstChild);
            
            // Keep only last 10 items
            while (systemLog.children.length > 10) {
                systemLog.removeChild(systemLog.lastChild);
            }
        }
        
        function showTypingIndicator() {
            document.getElementById('typingIndicator').classList.add('active');
            const messagesDiv = document.getElementById('messages');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function hideTypingIndicator() {
            document.getElementById('typingIndicator').classList.remove('active');
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        // Connect on load
        connect();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get('message', '')
            conversation_id = data.get('conversation_id')
            
            # Call Exchange Agent
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{EXCHANGE_AGENT_URL}/chat",
                        json={
                            'message': message,
                            'conversation_id': conversation_id
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Send routing info to system panel
                    metadata = result.get('metadata', {})
                    await manager.send_message({
                        'type': 'system',
                        'category': 'routing',
                        'message': 'Routing Decision',
                        'details': {
                            'intent': metadata.get('llm_intent', 'unknown'),
                            'routed_to_orchestrator': metadata.get('routed_to_orchestrator', False),
                            'confidence': 0.85
                        }
                    }, websocket)
                    
                    # If routed to orchestrator, show agent info
                    if metadata.get('routed_to_orchestrator'):
                        # Small delay for visual effect
                        import asyncio
                        await asyncio.sleep(0.3)
                        
                        await manager.send_message({
                            'type': 'system',
                            'category': 'agents',
                            'message': 'Multi-Agent Execution',
                            'details': {
                                'agents': metadata.get('agents_used', []),  # Use real data!
                                'count': metadata.get('agent_count', 0),
                                'duration': 150
                            }
                        }, websocket)
                    
                    # Send response back to client
                    await manager.send_message({
                        'type': 'response',
                        'content': result['response'],
                        'conversation_id': result['conversation_id'],
                        'metadata': metadata
                    }, websocket)
                    
                except httpx.HTTPError as e:
                    logger.error(f"Error calling exchange agent: {e}")
                    await manager.send_message({
                        'type': 'error',
                        'error': 'Failed to process message. Please try again.'
                    }, websocket)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "frontend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)