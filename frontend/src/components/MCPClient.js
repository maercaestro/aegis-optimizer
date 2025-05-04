// Note: Using .js extension instead of .jsx since this is a utility class, not a React component

/**
 * Client implementation for the Model Context Protocol (MCP)
 */
class MCPClient {
  /**
   * Create a new MCP client
   * @param {Object} options - Configuration options
   * @param {string} options.apiEndpoint - The API endpoint URL
   * @param {Function} options.onMessage - Callback for client messages
   * @param {Function} options.onError - Callback for error handling
   */
  constructor(options) {
    this.apiEndpoint = options.apiEndpoint || 'http://localhost:5001';
    this.onMessage = options.onMessage || (msg => console.log('MCP Client:', msg));
    this.onError = options.onError || (err => console.error('MCP Client Error:', err));
    this.isConnected = false;
    this.pendingRequests = {};
    this.serverCapabilities = {};
    
    // Initialize connection
    this.initialize();
  }
  
  /**
   * Initialize the MCP client and fetch server capabilities
   */
  async initialize() {
    try {
      // Fetch server capabilities
      const response = await fetch(`${this.apiEndpoint}/mcp/capabilities`);
      if (!response.ok) {
        throw new Error(`Failed to fetch MCP capabilities: ${response.status}`);
      }
      
      const capabilities = await response.json();
      this.serverCapabilities = capabilities;
      this.isConnected = true;
      
      this.onMessage({
        type: 'system',
        content: 'MCP Client connected successfully'
      });
    } catch (error) {
      this.isConnected = false;
      this.onError(error);
    }
  }
  
  /**
   * Call a capability on an MCP server
   * @param {string} serverId - The server ID
   * @param {string} capabilityId - The capability ID
   * @param {Object} params - Parameters for the capability
   * @returns {Promise<Object>} - The result of the capability call
   */
  async callCapability(serverId, capabilityId, params = {}) {
    if (!this.isConnected) {
      await this.initialize();
      if (!this.isConnected) {
        throw new Error('MCP Client not connected');
      }
    }

    if (!this.serverCapabilities[serverId] || 
        !this.serverCapabilities[serverId].capabilities.includes(capabilityId)) {
      throw new Error(`Capability ${capabilityId} not found in server ${serverId}`);
    }

    const requestId = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    
    // Register the pending request
    this.pendingRequests[requestId] = { 
      serverId, 
      capabilityId, 
      params, 
      status: 'pending',
      timestamp: Date.now()
    };
    
    try {
      // Format the MCP request according to protocol specification
      const mcpRequest = {
        requestId,
        serverId,
        capabilityId,
        params,
        timestamp: Date.now()
      };
      
      // Send the MCP request to the server
      const response = await fetch(`${this.apiEndpoint}/mcp/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(mcpRequest)
      });
      
      if (!response.ok) {
        throw new Error(`MCP request failed with status ${response.status}`);
      }
      
      const result = await response.json();
      
      // Update the request status
      this.pendingRequests[requestId] = {
        ...this.pendingRequests[requestId],
        status: 'completed',
        result
      };
      
      return result;
    } catch (error) {
      // Update the request status on error
      this.pendingRequests[requestId] = {
        ...this.pendingRequests[requestId],
        status: 'failed',
        error: error.message
      };
      
      throw error;
    }
  }
  
  /**
   * Get all pending requests
   * @returns {Object} - Pending requests
   */
  getPendingRequests() {
    return this.pendingRequests;
  }
  
  /**
   * Get server capabilities
   * @returns {Object} - Server capabilities
   */
  getServerCapabilities() {
    return this.serverCapabilities;
  }
}

export default MCPClient;