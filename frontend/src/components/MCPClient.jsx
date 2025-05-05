import React from 'react';

/**
 * Client for Model Context Protocol (MCP)
 * Connects to the MCP API Gateway
 */
class MCPClient {
  /**
   * Initialize the MCP client
   * @param {Object} config Configuration object
   * @param {string} config.apiEndpoint API endpoint URL
   * @param {Function} config.onMessage Message callback
   * @param {Function} config.onError Error callback
   */
  constructor({ apiEndpoint, onMessage, onError }) {
    this.apiEndpoint = apiEndpoint || 'http://localhost:5005';
    this.onMessage = onMessage;
    this.onError = onError;
    this.isConnected = false;
    this.serverCapabilities = {};
    
    // Initialize connection
    this.initialize();
  }

  /**
   * Initialize the connection to the MCP server
   */
  async initialize() {
    try {
      // First check if the API is available
      const response = await fetch(`${this.apiEndpoint}/`);
      if (!response.ok) {
        throw new Error(`API server not available: ${response.status}`);
      }
      
      // Then get capabilities
      const capResponse = await fetch(`${this.apiEndpoint}/mcp/capabilities`);
      if (!capResponse.ok) {
        throw new Error(`Failed to fetch MCP capabilities: ${capResponse.status}`);
      }
      
      const capabilities = await capResponse.json();
      this.serverCapabilities = capabilities;
      this.isConnected = true;
      
      if (this.onMessage) {
        this.onMessage({
          type: 'system',
          content: 'MCP Client connected successfully'
        });
      }
    } catch (error) {
      console.error('Error initializing MCP client:', error);
      this.isConnected = false;
      if (this.onError) {
        this.onError(error);
      }
    }
  }

  /**
   * Chat function for natural language interaction
   * @param {string} query User query
   * @returns {Promise} Promise that resolves with the response
   */
  async chat(query) {
    try {
      console.log(`Sending chat query to ${this.apiEndpoint}/mcp/chat:`, query);
      const response = await fetch(`${this.apiEndpoint}/mcp/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Chat request failed: ${response.status} - ${errorText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error in MCP chat:', error);
      throw error;
    }
  }

  /**
   * Call a specific capability
   * @param {string} serverId Server ID
   * @param {string} capabilityId Capability ID
   * @param {Object} params Parameters
   * @returns {Promise} Promise that resolves with the result
   */
  async callCapability(serverId, capabilityId, params = {}) {
    const requestId = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    
    try {
      const response = await fetch(`${this.apiEndpoint}/mcp/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requestId,
          serverId,
          capabilityId,
          params
        })
      });
      
      if (!response.ok) {
        throw new Error(`MCP request failed with status ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error calling capability:', error);
      throw error;
    }
  }

  /**
   * Send schedule data to server
   * @param {Object} data Schedule data
   * @returns {Promise} Promise that resolves with the response
   */
  async setScheduleData(data) {
    try {
      const response = await fetch(`${this.apiEndpoint}/mcp/set-schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        throw new Error(`Failed to set schedule data: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error setting schedule data:', error);
      throw error;
    }
  }

  /**
   * Check the status of the data
   * @returns {Promise} Promise that resolves with the data status
   */
  async checkDataStatus() {
    try {
      const response = await fetch(`${this.apiEndpoint}/mcp/data-status`);
      
      if (!response.ok) {
        throw new Error(`Failed to check data status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error checking data status:', error);
      throw error;
    }
  }
}

export default MCPClient;