/**
 * MCP Service Interface Module
 * Provides programmatic access to MCP services
 */

import http from 'http';

class MCPServiceInterface {
  constructor(options = {}) {
    this.serviceName = options.serviceName || 'unknown';
    this.coreUrl = options.coreUrl || 'http://localhost:51234';
    this.options = options;
    this.initialized = false;
    this.capabilities = {};
    
    console.log(`[${this.serviceName}] Initializing service interface`);
  }
  
  async initialize() {
    try {
      const response = await this.request(`/service/${this.serviceName}/status`);
      this.capabilities = response.capabilities || {};
      this.environment = response.environment || {};
      this.initialized = true;
      console.log(`[${this.serviceName}] Successfully initialized`);
      return true;
    } catch (error) {
      console.error(`[${this.serviceName}] Initialization failed:`, error.message);
      return false;
    }
  }
  
  async execute(action, params = {}) {
    if (!this.initialized) {
      await this.initialize();
    }
    
    try {
      const response = await this.request(
        `/service/${this.serviceName}/execute`, 
        'POST',
        { action, params }
      );
      return response;
    } catch (error) {
      console.error(`[${this.serviceName}] Execution failed:`, error.message);
      throw error;
    }
  }
  
  async getCapabilities() {
    if (!this.initialized) {
      await this.initialize();
    }
    return this.capabilities;
  }
  
  request(path, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
      const url = new URL(path, this.coreUrl);
      
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      };
      
      const req = http.request(url, options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            const jsonData = JSON.parse(responseData);
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(jsonData);
            } else {
              reject(new Error(jsonData.message || 'Request failed'));
            }
          } catch (error) {
            reject(new Error(`Failed to parse response: ${error.message}`));
          }
        });
      });
      
      req.on('error', (error) => {
        reject(error);
      });
      
      if (data) {
        req.write(JSON.stringify(data));
      }
      
      req.end();
    });
  }
}

// Export service interface with pre-configured settings
export default function createInterface(options = {}) {
  const serviceName = 'communication-hub';
  return new MCPServiceInterface({
    serviceName,
    ...options
  });
}
