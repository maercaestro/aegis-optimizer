"""
Web UI for the MCP Client
"""
import os
import asyncio
from flask import Flask, request, jsonify, render_template
from client import MCPClient

app = Flask(__name__, 
            static_folder="static", 
            template_folder="templates")

# Global client instance
mcp_client = None

@app.route('/')
def index():
    """Render the main UI"""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
async def api_query():
    """API endpoint to process a query"""
    global mcp_client
    
    if not mcp_client:
        mcp_client = MCPClient()
        await mcp_client.connect()
    
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        result = await mcp_client.process_query(query)
        return jsonify({
            "response": result["response"],
            "debug": {
                "tool_calls": [f"{tc['name']}({tc['params']})" for tc in result["tool_calls"]]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create necessary directories
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)

# Create a simple HTML template
with open(os.path.join(os.path.dirname(__file__), 'templates', 'index.html'), 'w') as f:
    f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Aegis MCP Client</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }
        .chat-container { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .message { margin: 5px 0; padding: 5px 10px; border-radius: 5px; }
        .user { background-color: #e3f2fd; text-align: right; }
        .assistant { background-color: #f5f5f5; }
        .input-container { display: flex; }
        #user-input { flex: 1; padding: 8px; }
        button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .debug-info { font-size: 0.8em; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Aegis MCP Client</h1>
    <div class="chat-container" id="chat-container"></div>
    <div class="input-container">
        <input type="text" id="user-input" placeholder="Ask about the refinery schedule..." />
        <button onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        const chatContainer = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        
        async function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;
            
            // Add user message to chat
            addMessage(query, 'user');
            userInput.value = '';
            
            // Add loading indicator
            const loadingId = showLoading();
            
            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to get response');
                }
                
                const data = await response.json();
                
                // Hide loading indicator
                hideLoading(loadingId);
                
                // Add assistant response
                addMessage(data.response, 'assistant', data.debug);
            } catch (error) {
                // Hide loading indicator
                hideLoading(loadingId);
                
                // Add error message
                addMessage(`Error: ${error.message}`, 'assistant error');
            }
        }
        
        function addMessage(text, role, debug = null) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', role);
            messageDiv.textContent = text;
            
            if (debug && debug.tool_calls && debug.tool_calls.length > 0) {
                const debugDiv = document.createElement('div');
                debugDiv.classList.add('debug-info');
                debugDiv.textContent = `Tools used: ${debug.tool_calls.join(', ')}`;
                messageDiv.appendChild(debugDiv);
            }
            
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function showLoading() {
            const loadingDiv = document.createElement('div');
            loadingDiv.classList.add('message', 'assistant');
            loadingDiv.textContent = 'Thinking...';
            chatContainer.appendChild(loadingDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return loadingDiv;
        }
        
        function hideLoading(loadingElement) {
            if (loadingElement && loadingElement.parentNode) {
                loadingElement.parentNode.removeChild(loadingElement);
            }
        }
        
        // Allow Enter key to send message
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>""")

def run_app():
    """Run the Flask app with asyncio support"""
    port = int(os.environ.get("MCP_WEB_PORT", 5006))
    
    # Start the Flask app with asyncio support
    import nest_asyncio
    nest_asyncio.apply()
    
    from asgiref.wsgi import WsgiToAsgi
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    
    asgi_app = WsgiToAsgi(app)
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    
    print(f"Starting MCP Web Client on http://127.0.0.1:{port}")
    asyncio.run(serve(asgi_app, config))

if __name__ == '__main__':
    run_app()