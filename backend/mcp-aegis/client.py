"""
MCP Client implementation using OpenAI API
"""
import os
import json
import re
import sys
import asyncio
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import openai
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

class MCPClient:
    """
    Client for Model Context Protocol using OpenAI API for planning
    and the MCP server for tool execution.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the MCP client.
        
        Args:
            openai_api_key: OpenAI API key (will use environment variable if None)
            model: OpenAI model to use
        """
        self.openai_client = openai.OpenAI(api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.mcp_client = None
        self.tools_info = None
    
    async def connect(self):
        """Connect to the MCP server"""
        process_cmd = ["python", "server.py"]
        self.mcp_client = stdio_client(process_cmd)
        await self.mcp_client.initialize_session()
        
        # Get tools info for prompt construction
        self.tools_info = await self.mcp_client.get_tools()
        print(f"Connected to MCP server with {len(self.tools_info)} tools")
        return self
    
    def _generate_system_prompt(self) -> str:
        """Generate a system prompt based on available tools"""
        if not self.tools_info:
            return "You are a helpful assistant."
        
        tool_descriptions = []
        for tool in self.tools_info:
            params_desc = ", ".join([f"{p.name}" for p in tool.parameters]) if tool.parameters else "no parameters"
            tool_descriptions.append(f"- {tool.name}: {tool.description} | Parameters: {params_desc}")
        
        return f"""You are an assistant with access to a refinery schedule optimizer.
You can call the following tools to analyze the schedule:

{chr(10).join(tool_descriptions)}

When you need to use a tool:
1. Think about which tool is most appropriate for the question
2. Format your tool call exactly like this: TOOL[tool_name(param1="value1", param2="value2")]
3. Wait for the tool result before providing your final answer

Always base your answers on the data from the tools. If you can't answer with the available tools, say so."""
    
    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from the model's response"""
        # Match patterns like: TOOL[tool_name(param1="value1", param2="value2")]
        pattern = r'TOOL\[(\w+)\((.*?)\)\]'
        tool_calls = []
        
        matches = re.findall(pattern, text)
        for match in matches:
            tool_name = match[0]
            params_text = match[1]
            
            # Parse parameters
            params = {}
            if params_text.strip():
                # Match param="value" patterns
                param_pattern = r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|([^,\s]+))'
                param_matches = re.findall(param_pattern, params_text)
                for param_match in param_matches:
                    param_name = param_match[0]
                    # Find the first non-empty group which is the value
                    param_value = next((g for g in param_match[1:] if g), None)
                    params[param_name] = param_value
            
            tool_calls.append({
                "name": tool_name,
                "params": params
            })
            
        return tool_calls
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the MCP flow.
        
        Args:
            query: User query to process
            
        Returns:
            Dict with response and any debug information
        """
        if not self.mcp_client:
            await self.connect()
        
        # Step 1: Planning with OpenAI
        system_prompt = self._generate_system_prompt()
        
        planning_response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        planning_text = planning_response.choices[0].message.content
        print(f"Planning response: {planning_text[:200]}...")
        
        # Step 2: Extract and execute tool calls
        tool_calls = self._extract_tool_calls(planning_text)
        tool_results = []
        
        for call in tool_calls:
            print(f"Executing tool: {call['name']} with params: {call['params']}")
            try:
                result = await self.mcp_client.call_tool(call['name'], call['params'])
                tool_results.append({
                    "name": call['name'],
                    "params": call['params'],
                    "result": result,
                    "success": True
                })
            except Exception as e:
                print(f"Error calling tool {call['name']}: {str(e)}")
                tool_results.append({
                    "name": call['name'],
                    "params": call['params'],
                    "error": str(e),
                    "success": False
                })
        
        # Step 3: Generate final response
        if not tool_results:
            # If no tools were called, return the planning response directly
            return {
                "response": planning_text,
                "tool_calls": [],
                "debug": {
                    "planning_text": planning_text
                }
            }
        
        # Format tool results for the final prompt
        tool_results_text = []
        for tr in tool_results:
            if tr["success"]:
                result_str = json.dumps(tr["result"], indent=2)
                tool_results_text.append(f"TOOL RESULT for {tr['name']}:\n{result_str}")
            else:
                tool_results_text.append(f"TOOL ERROR for {tr['name']}:\n{tr['error']}")
        
        tool_results_combined = "\n\n".join(tool_results_text)
        
        final_response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains refinery scheduling data. Answer the user's question based on the tool results provided. Do not mention the tools or their names in your response."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": "I'll help answer that."},
                {"role": "user", "content": f"Here are the results from the tools:\n\n{tool_results_combined}\n\nPlease provide a clear, conversational answer based on this data."}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return {
            "response": final_response.choices[0].message.content,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "debug": {
                "planning_text": planning_text,
                "tool_results_text": tool_results_combined
            }
        }
    
    async def close(self):
        """Close the connection to the MCP server"""
        if self.mcp_client:
            await self.mcp_client.close()
            self.mcp_client = None


async def main():
    """Main function to demonstrate the client"""
    client = MCPClient()
    await client.connect()
    
    print("MCP Client connected and ready!")
    print("Enter your questions (or type 'exit' to quit):")
    
    while True:
        query = input("> ")
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        try:
            result = await client.process_query(query)
            print("\nRESPONSE:")
            print(result["response"])
            print("\n" + "-"*50)
        except Exception as e:
            print(f"Error: {str(e)}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())