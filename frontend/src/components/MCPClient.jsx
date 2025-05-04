import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const MCPClient = ({ apiEndpoint, onMessage, onError }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [pendingRequests, setPendingRequests] = useState({});
  const [serverCapabilities, setServerCapabilities] = useState({});

  // Initialize MCP client
  useEffect(() => {
    const initClient = async () => {
      try {
        // Fetch server capabilities
        const response = await fetch(`${apiEndpoint}/mcp/capabilities`);
        if (!response.ok) {
          throw new Error('Failed to fetch MCP capabilities');
        }
        
        const capabilities = await response.json();
        setServerCapabilities(capabilities);
        setIsConnected(true);
        
        if (onMessage) {
          onMessage({
            type: 'system',
            content: 'MCP Client connected successfully'
          });
        }
      } catch (error) {
        console.error('Error initializing MCP client:', error);
        setIsConnected(false);
        if (onError) {
          onError(error);
        }
      }
    };
    
    initClient();
  }, [apiEndpoint, onMessage, onError]);

  // Function to call a capability
  const callCapability = async (serverId, capabilityId, params = {}) => {
    if (!isConnected) {
      throw new Error('MCP Client not connected');
    }

    if (!serverCapabilities[serverId] || 
        !serverCapabilities[serverId].capabilities.includes(capabilityId)) {
      throw new Error(`Capability ${capabilityId} not found in server ${serverId}`);
    }

    const requestId = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    
    // Register the pending request
    setPendingRequests(prev => ({
      ...prev,
      [requestId]: { 
        serverId, 
        capabilityId, 
        params, 
        status: 'pending',
        timestamp: Date.now()
      }
    }));
    
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
      const response = await fetch(`${apiEndpoint}/mcp/execute`, {
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
      setPendingRequests(prev => ({
        ...prev,
        [requestId]: {
          ...prev[requestId],
          status: 'completed',
          result
        }
      }));
      
      return result;
    } catch (error) {
      // Update the request status on error
      setPendingRequests(prev => ({
        ...prev,
        [requestId]: {
          ...prev[requestId],
          status: 'failed',
          error: error.message
        }
      }));
      
      throw error;
    }
  };

  // MCP client interface
  return {
    isConnected,
    serverCapabilities,
    pendingRequests,
    callCapability
  };
};

MCPClient.propTypes = {
  apiEndpoint: PropTypes.string.isRequired,
  onMessage: PropTypes.func,
  onError: PropTypes.func
};

export default MCPClient;