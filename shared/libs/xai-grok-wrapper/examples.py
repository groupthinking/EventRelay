"""
Example usage of the Grok Client wrapper
Demonstrates: Code Execution, MCP Tools, Function Calling, Streaming, Agentic Loop
"""

from grok_client import (
    GrokClient, 
    GrokModel,
    ToolCallType,
    code_execution,
    web_search,
    x_search,
    mcp, 
    function_tool
)


def example_basic_chat():
    """Basic chat completion"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Chat")
    print("="*60)
    
    with GrokClient() as client:
        response = client.chat([
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Explain Python decorators in 2 sentences."}
        ])
        
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.usage.total_tokens}")


def example_streaming():
    """Streaming with reasoning traces"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Streaming with Reasoning")
    print("="*60)
    
    with GrokClient(model=GrokModel.CODE_FAST_1) as client:
        print("Response: ", end="", flush=True)
        
        for chunk in client.chat(
            messages=[{"role": "user", "content": "Write a Python quicksort in 5 lines"}],
            stream=True
        ):
            if chunk.reasoning_content:
                print(f"\n[Thinking: {chunk.reasoning_content[:50]}...]", end="")
            if chunk.content:
                print(chunk.content, end="", flush=True)
        
        print()


def example_code_execution():
    """Server-side code execution tool"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Code Execution Tool")
    print("="*60)
    
    with GrokClient(model=GrokModel.GROK_4_FAST_REASONING) as client:
        response = client.chat(
            messages=[{
                "role": "user", 
                "content": "Calculate the first 10 Fibonacci numbers using Python code execution"
            }],
            tools=[code_execution()]
        )
        
        print(f"Response: {response.content}")
        if response.tool_calls:
            print(f"Tool calls made: {len(response.tool_calls)}")


def example_mcp_tools():
    """Remote MCP tools integration"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Remote MCP Tools")
    print("="*60)
    
    with GrokClient(model=GrokModel.GROK_4_1_FAST_REASONING) as client:
        response = client.chat(
            messages=[{
                "role": "user",
                "content": "What can you tell me about https://github.com/xai-org/xai-sdk-python?"
            }],
            tools=[
                mcp(
                    server_url="https://mcp.deepwiki.com/mcp",
                    server_label="deepwiki"
                )
            ]
        )
        
        print(f"Response: {response.content[:500]}...")


def example_function_calling():
    """Native function/tool calling with client-side execution"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Function Calling")
    print("="*60)
    
    # Define client-side functions
    def get_weather(city: str) -> str:
        """Get current weather for a city"""
        # Mock implementation
        return f"Weather in {city}: 72°F, Sunny"
    
    def calculate_tip(amount: float, percentage: float) -> str:
        """Calculate tip amount"""
        tip = amount * (percentage / 100)
        return f"Tip: ${tip:.2f}, Total: ${amount + tip:.2f}"
    
    # Create tool definitions
    weather_tool = function_tool(
        name="get_weather",
        description="Get current weather for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    )
    
    tip_tool = function_tool(
        name="calculate_tip",
        description="Calculate tip for a bill",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Bill amount"},
                "percentage": {"type": "number", "description": "Tip percentage"}
            },
            "required": ["amount", "percentage"]
        }
    )
    
    with GrokClient() as client:
        # Initial request
        response = client.chat(
            messages=[{
                "role": "user",
                "content": "What's the weather in San Francisco and calculate 20% tip on $85"
            }],
            tools=[weather_tool, tip_tool],
            parallel_tool_calls=True  # Enable parallel execution
        )
        
        if response.tool_calls:
            print(f"Tool calls requested: {len(response.tool_calls)}")
            
            # Execute tools locally
            functions = {
                "get_weather": get_weather,
                "calculate_tip": calculate_tip
            }
            
            tool_results = client.execute_tool_calls(response.tool_calls, functions)
            
            for result in tool_results:
                print(f"  Tool result: {result['content']}")
            
            # Continue conversation with results
            messages = [
                {"role": "user", "content": "What's the weather in San Francisco and calculate 20% tip on $85"},
                {"role": "assistant", "content": response.content, "tool_calls": response.tool_calls},
                *tool_results
            ]
            
            final_response = client.chat(messages=messages)
            print(f"\nFinal Response: {final_response.content}")


def example_agentic_workflow():
    """Multi-step agentic workflow with tools"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Agentic Workflow")
    print("="*60)
    
    system_prompt = """You are a senior engineer acting inside an IDE.
    - Implement changes safely with minimal diffs
    - Use tools when needed for calculations or verification
    - Output clear, actionable responses
    - Think step by step for complex tasks"""
    
    with GrokClient(model=GrokModel.CODE_FAST_1) as client:
        response = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": """
## Context
```python
# Current implementation in utils.py
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
```

## Task
Refactor this function to:
1. Use list comprehension
2. Add type hints
3. Handle edge cases (None, empty list)
4. Add docstring
                """}
            ],
            tools=[code_execution()],
            max_tokens=1000
        )
        
        print(f"Response:\n{response.content}")


def example_hybrid_tools():
    """Mix server-side and client-side tools"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Hybrid Tools (Server + Client)")
    print("="*60)
    
    # Client-side function
    def fetch_user_data(user_id: str) -> str:
        """Fetch user data from local database"""
        # Mock data
        users = {
            "123": {"name": "Alice", "plan": "premium"},
            "456": {"name": "Bob", "plan": "free"}
        }
        return str(users.get(user_id, {"error": "User not found"}))
    
    user_tool = function_tool(
        name="fetch_user_data",
        description="Fetch user data from local database",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID"}
            },
            "required": ["user_id"]
        }
    )
    
    with GrokClient(model=GrokModel.GROK_4_FAST_REASONING) as client:
        response = client.chat(
            messages=[{
                "role": "user",
                "content": "Look up user 123 and calculate their discount (premium=20%, free=5%) on $100"
            }],
            tools=[
                user_tool,        # Client-side
                code_execution()  # Server-side
            ]
        )
        
        print(f"Initial response: {response.content}")
        
        if response.tool_calls:
            # Handle client-side tools
            tool_results = client.execute_tool_calls(
                response.tool_calls,
                {"fetch_user_data": fetch_user_data}
            )
            
            if tool_results:
                messages = [
                    {"role": "user", "content": "Look up user 123 and calculate their discount"},
                    {"role": "assistant", "content": response.content, "tool_calls": response.tool_calls},
                    *tool_results
                ]
                final = client.chat(messages=messages, tools=[code_execution()])
                print(f"Final: {final.content}")


def example_agentic_loop():
    """Automatic agentic loop with client-side tools"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Agentic Loop (Automatic)")
    print("="*60)
    
    # Define client-side functions
    def get_stock_price(symbol: str) -> str:
        """Get current stock price"""
        prices = {"AAPL": 185.50, "GOOGL": 142.30, "MSFT": 378.90}
        price = prices.get(symbol, 0)
        print(f"  [TOOL CALLED]: get_stock_price({symbol}) -> ${price}")
        return f"${price}"
    
    def calculate_gain(current_price: float, percentage: float) -> str:
        """Calculate price after percentage gain"""
        new_price = current_price * (1 + percentage / 100)
        print(f"  [TOOL CALLED]: calculate_gain({current_price}, {percentage}%) -> ${new_price:.2f}")
        return f"${new_price:.2f}"
    
    stock_tool = function_tool(
        name="get_stock_price",
        description="Get current stock price for a symbol",
        parameters={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Stock symbol like AAPL"}},
            "required": ["symbol"]
        }
    )
    
    calc_tool = function_tool(
        name="calculate_gain",
        description="Calculate price after percentage gain",
        parameters={
            "type": "object",
            "properties": {
                "current_price": {"type": "number", "description": "Current price"},
                "percentage": {"type": "number", "description": "Gain percentage"}
            },
            "required": ["current_price", "percentage"]
        }
    )
    
    with GrokClient(model=GrokModel.CODE_FAST_1) as client:
        # The agentic loop handles everything automatically
        response = client.run_agentic_loop(
            messages=[{
                "role": "user",
                "content": "Get AAPL stock price and calculate 10% gain on it"
            }],
            tools=[stock_tool, calc_tool],
            functions={
                "get_stock_price": get_stock_price,
                "calculate_gain": calculate_gain
            },
            max_iterations=5
        )
        
        print(f"\nFinal Response: {response.content}")


def example_web_search():
    """Server-side web search tool"""
    print("\n" + "="*60)
    print("EXAMPLE 9: Web Search (Server-Side)")
    print("="*60)
    
    with GrokClient(model=GrokModel.GROK_4_FAST_REASONING) as client:
        response = client.chat(
            messages=[{
                "role": "user",
                "content": "What are the latest developments in AI coding assistants in 2024?"
            }],
            tools=[web_search()]
        )
        
        print(f"Response: {response.content[:800]}...")
        
        # Check for citations
        if response.citations:
            print("\nCitations:")
            for cite in response.citations[:3]:
                print(f"  - {cite}")


def example_tool_type_detection():
    """Demonstrate server vs client tool detection"""
    print("\n" + "="*60)
    print("EXAMPLE 10: Tool Type Detection")
    print("="*60)
    
    custom_tool = function_tool(
        name="my_custom_function",
        description="A custom function",
        parameters={"type": "object", "properties": {}}
    )
    
    with GrokClient() as client:
        response = client.chat(
            messages=[{
                "role": "user",
                "content": "Search the web for Python tips and call my_custom_function"
            }],
            tools=[web_search(), custom_tool]
        )
        
        # Parse into agentic response
        agentic = client.parse_agentic_response(response)
        
        print(f"Requires action: {agentic.requires_action}")
        print(f"Server-side calls: {len(agentic.completed_tool_calls)}")
        print(f"Client-side calls: {len(agentic.pending_tool_calls)}")
        
        for call in response.tool_calls:
            call_type = client.get_tool_call_type(call)
            name = call["function"]["name"]
            print(f"  - {name}: {call_type.value}")


if __name__ == "__main__":
    import sys
    
    examples = {
        "1": ("Basic Chat", example_basic_chat),
        "2": ("Streaming", example_streaming),
        "3": ("Code Execution", example_code_execution),
        "4": ("MCP Tools", example_mcp_tools),
        "5": ("Function Calling", example_function_calling),
        "6": ("Agentic Workflow", example_agentic_workflow),
        "7": ("Hybrid Tools", example_hybrid_tools),
        "8": ("Agentic Loop", example_agentic_loop),
        "9": ("Web Search", example_web_search),
        "10": ("Tool Type Detection", example_tool_type_detection),
    }
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice in examples:
            examples[choice][1]()
        elif choice == "all":
            for _, (name, func) in examples.items():
                try:
                    func()
                except Exception as e:
                    print(f"Error in {name}: {e}")
        else:
            print(f"Unknown example: {choice}")
    else:
        print("xAI Grok Client Examples")
        print("=" * 40)
        print("\nUsage: python examples.py [1-10|all]\n")
        for k, (name, _) in examples.items():
            print(f"  {k}: {name}")
        print("\n  all: Run all examples")
        print("\nQuick start: python examples.py 1")
