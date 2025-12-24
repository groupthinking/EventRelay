"""
xAI Grok Python Wrapper
Full-featured client with Code Execution, Remote MCP Tools, and Advanced Usage

Base URL: https://api.x.ai

Endpoints:
- /v1/chat/completions  - Chat + tool calling
- /v1/responses         - Stateful responses API
- /v1/embeddings        - Text embeddings  
- /v1/images/generations - Image generation
- /v1/models            - List models
- /v1/tokenize-text     - Token counting
- /v1/files             - File uploads
- /v1/documents/search  - Collection search

Models:
- grok-code-fast-1      - Fast agentic coding
- grok-4-fast-reasoning - Fast with reasoning (grok-4-fast)
- grok-4                - Deep reasoning (grok-4-0709)
- grok-3               - General purpose
- grok-3-mini          - Lightweight
- grok-2-image-1212    - Image generation

Server-Side Tools (auto-executed by xAI):
- web_search           - Search the web ($5/1000 calls)
- x_search             - Search X/Twitter ($5/1000 calls)
- code_execution       - Run Python code ($5/1000 calls)
- document_search      - Search uploaded files ($5/1000 calls)
- collection_search    - Knowledge base search ($2.50/1000 calls)

Client-Side Tools (you execute locally):
- Custom function tools you define
- Must handle tool_calls, execute, return results

Agentic Flow:
1. Send message with tools
2. Model decides which tools to call
3. Server-side tools execute automatically
4. Client-side tools return to you for execution
5. You execute and return results
6. Model continues reasoning
7. Repeat until complete

Knowledge cutoff: November 2024 (Grok 3/4)
Max image size: 20MiB
Supported image types: jpg/jpeg, png

References:
- https://docs.x.ai/llms.txt
- https://docs.x.ai/docs/guides/tools/overview
- https://docs.x.ai/docs/guides/tools/advanced-usage
"""

import os
import json
import httpx
from typing import Optional, List, Dict, Any, Generator, Callable
from dataclasses import dataclass, field
from enum import Enum


class GrokModel(str, Enum):
    """Available Grok models"""
    # Code models
    CODE_FAST_1 = "grok-code-fast-1"
    
    # Grok 4 models
    GROK_4 = "grok-4-0709"
    GROK_4_FAST = "grok-4-fast"  # Alias for fast reasoning
    GROK_4_FAST_REASONING = "grok-4-fast-reasoning"
    GROK_4_FAST_NON_REASONING = "grok-4-fast-non-reasoning"
    GROK_4_1_FAST_REASONING = "grok-4-1-fast-reasoning"
    GROK_4_1_FAST_NON_REASONING = "grok-4-1-fast-non-reasoning"
    
    # Grok 3 models
    GROK_3 = "grok-3"
    GROK_3_MINI = "grok-3-mini"
    
    # Grok 2 models
    GROK_2 = "grok-2-1212"
    GROK_2_VISION = "grok-2-vision-1212"
    GROK_2_IMAGE = "grok-2-image-1212"


# Server-side tool names (auto-executed by xAI)
SERVER_SIDE_TOOLS = {
    "web_search", "browse_page",           # Web search tools
    "x_search", "x_user_search", "x_keyword_search",  # X search tools
    "code_execution",                       # Code execution
    "document_search", "collection_search", # Document tools
}


@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class Tool:
    """Tool definition for function calling"""
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class MCPTool:
    """Remote MCP Tool configuration"""
    server_url: str
    server_label: Optional[str] = None
    server_description: Optional[str] = None
    allowed_tool_names: Optional[List[str]] = None
    authorization: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "remote_mcp",
            "remote_mcp": {
                "server_url": self.server_url
            }
        }
        if self.server_label:
            result["remote_mcp"]["server_label"] = self.server_label
        if self.server_description:
            result["remote_mcp"]["server_description"] = self.server_description
        if self.allowed_tool_names:
            result["remote_mcp"]["allowed_tool_names"] = self.allowed_tool_names
        if self.authorization:
            result["remote_mcp"]["authorization"] = self.authorization
        if self.extra_headers:
            result["remote_mcp"]["extra_headers"] = self.extra_headers
        return result


@dataclass
class CodeExecutionTool:
    """Code Execution Tool - server-side Python execution"""
    type: str = "code_execution"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type}


@dataclass
class WebSearchTool:
    """Web Search Tool - server-side web search"""
    type: str = "web_search"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type}


@dataclass
class XSearchTool:
    """X (Twitter) Search Tool - server-side X/Twitter search"""
    type: str = "x_search"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type}


@dataclass
class DocumentSearchTool:
    """Document Search Tool - search uploaded files"""
    type: str = "document_search"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type}


@dataclass
class CollectionSearchTool:
    """Collection Search Tool - search knowledge bases"""
    type: str = "collection_search"
    collection_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.collection_id:
            result["collection_search"] = {"collection_id": self.collection_id}
        return result


class ToolCallType(str, Enum):
    """Tool call execution type"""
    SERVER = "server"  # Executed automatically by xAI
    CLIENT = "client"  # Must be executed locally by developer


@dataclass
class Usage:
    """Token usage information"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class StreamChunk:
    """Streaming response chunk"""
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    finish_reason: Optional[str] = None


@dataclass
class ChatResponse:
    """Chat completion response"""
    id: str
    model: str
    content: str
    tool_calls: List[Dict]
    usage: Usage
    finish_reason: str
    raw: Dict[str, Any]
    server_tool_calls: List[Dict] = field(default_factory=list)  # Server-executed tools
    citations: List[Dict] = field(default_factory=list)  # Search result citations


@dataclass
class AgenticResponse:
    """
    Agentic tool calling response - understanding the full response structure.
    
    Server-side tools (auto-executed):
    - web_search, browse_page: Search the web
    - x_search, x_user_search, x_keyword_search: Search X/Twitter
    - code_execution: Run Python code
    - document_search: Search uploaded files
    - collection_search: Knowledge base search
    
    Client-side tools (you execute):
    - Custom functions you define
    - Must handle tool_calls, execute locally, return results
    """
    response: ChatResponse
    pending_tool_calls: List[Dict]  # Client-side calls awaiting execution
    completed_tool_calls: List[Dict]  # Server-side calls already executed
    requires_action: bool  # True if client-side tools need execution
    
    @classmethod
    def from_response(cls, response: ChatResponse) -> "AgenticResponse":
        """Parse a ChatResponse into an AgenticResponse"""
        pending = []
        completed = []
        
        for call in response.tool_calls:
            # Server-side tools are already executed
            func_name = call.get("function", {}).get("name", "")
            if func_name in SERVER_SIDE_TOOLS:
                completed.append(call)
            else:
                pending.append(call)
        
        return cls(
            response=response,
            pending_tool_calls=pending,
            completed_tool_calls=completed,
            requires_action=len(pending) > 0
        )


class GrokClient:
    """
    xAI Grok API Client
    
    Features:
    - Chat completions with streaming
    - Code execution tool (server-side Python)
    - Remote MCP tools integration
    - Native function/tool calling
    - Parallel tool calls support
    - Cache optimization
    """
    
    BASE_URL = "https://api.x.ai/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = GrokModel.CODE_FAST_1,
        timeout: float = 120.0
    ):
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required. Set env var or pass api_key.")
        
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self._client.close()
    
    # =========================================================================
    # CHAT COMPLETIONS
    # =========================================================================
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stream: bool = False,
        parallel_tool_calls: bool = True,
        **kwargs
    ) -> ChatResponse | Generator[StreamChunk, None, None]:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to client model)
            tools: List of tools (functions, MCP, code_execution)
            tool_choice: "auto", "none", or specific tool
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            stream: Enable streaming response
            parallel_tool_calls: Allow parallel tool execution
            
        Returns:
            ChatResponse or Generator[StreamChunk] if streaming
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Process tools
        if tools:
            payload["tools"] = self._process_tools(tools)
            payload["parallel_tool_calls"] = parallel_tool_calls
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        payload.update(kwargs)
        
        if stream:
            return self._stream_chat(payload)
        
        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return self._parse_response(response.json())
    
    def _stream_chat(self, payload: Dict) -> Generator[StreamChunk, None, None]:
        """Stream chat completions with reasoning traces"""
        with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        yield StreamChunk(
                            content=delta.get("content", ""),
                            reasoning_content=delta.get("reasoning_content", ""),
                            tool_calls=delta.get("tool_calls", []),
                            finish_reason=chunk.get("choices", [{}])[0].get("finish_reason")
                        )
                    except json.JSONDecodeError:
                        continue
    
    def _process_tools(self, tools: List[Any]) -> List[Dict]:
        """Convert tool objects to API format"""
        processed = []
        for tool in tools:
            if isinstance(tool, (CodeExecutionTool, WebSearchTool, XSearchTool, 
                                DocumentSearchTool, CollectionSearchTool)):
                processed.append(tool.to_dict())
            elif isinstance(tool, MCPTool):
                processed.append(tool.to_dict())
            elif isinstance(tool, Tool):
                processed.append({"type": tool.type, "function": tool.function})
            elif isinstance(tool, dict):
                processed.append(tool)
            elif callable(tool):
                processed.append(self._function_to_tool(tool))
        return processed
    
    def _function_to_tool(self, func: Callable) -> Dict:
        """Convert a Python function to tool schema"""
        import inspect
        sig = inspect.signature(func)
        params = {}
        required = []
        
        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
            
            params[name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(name)
        
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": required
                }
            }
        }
    
    def _parse_response(self, data: Dict) -> ChatResponse:
        """Parse API response into ChatResponse"""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage_data = data.get("usage", {})
        
        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", ""),
            content=message.get("content", ""),
            tool_calls=message.get("tool_calls", []),
            usage=Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                reasoning_tokens=usage_data.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                cached_tokens=usage_data.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            ),
            finish_reason=choice.get("finish_reason", ""),
            raw=data
        )
    
    # =========================================================================
    # TOOL CALL HANDLING
    # =========================================================================
    
    def get_tool_call_type(self, tool_call: Dict) -> ToolCallType:
        """
        Determine if a tool call is server-side or client-side.
        
        Server-side tools (executed automatically by xAI):
        - web_search, browse_page
        - x_search, x_user_search, x_keyword_search
        - code_execution
        - document_search, collection_search
        
        Client-side tools (you must execute):
        - Any custom function tools you define
        """
        func_name = tool_call.get("function", {}).get("name", "")
        if func_name in SERVER_SIDE_TOOLS:
            return ToolCallType.SERVER
        return ToolCallType.CLIENT
    
    def parse_agentic_response(self, response: ChatResponse) -> AgenticResponse:
        """
        Parse a response into an AgenticResponse for easier handling.
        
        Example:
            response = client.chat(messages, tools=[...])
            agentic = client.parse_agentic_response(response)
            
            if agentic.requires_action:
                # Handle client-side tool calls
                for call in agentic.pending_tool_calls:
                    result = my_function(call["function"]["arguments"])
                    # ... continue conversation with result
        """
        return AgenticResponse.from_response(response)
    
    def execute_tool_calls(
        self,
        tool_calls: List[Dict],
        functions: Dict[str, Callable]
    ) -> List[Dict[str, str]]:
        """
        Execute client-side tool calls and return results.
        
        Args:
            tool_calls: Tool calls from model response
            functions: Dict mapping function names to callables
            
        Returns:
            List of tool result messages to append to conversation
        """
        results = []
        for call in tool_calls:
            # Skip server-side tools (already executed)
            if self.get_tool_call_type(call) == ToolCallType.SERVER:
                continue
                
            func_name = call["function"]["name"]
            if func_name in functions:
                try:
                    args = json.loads(call["function"]["arguments"])
                    result = functions[func_name](**args)
                    results.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": str(result)
                    })
                except Exception as e:
                    results.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": f"Error: {str(e)}"
                    })
        return results
    
    def run_agentic_loop(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        functions: Dict[str, Callable],
        max_iterations: int = 10,
        **kwargs
    ) -> ChatResponse:
        """
        Run a complete agentic loop handling client-side tool calls automatically.
        
        This method:
        1. Sends the initial request with tools
        2. If client-side tools are called, executes them
        3. Continues the conversation with results
        4. Repeats until no more tool calls or max iterations
        
        Args:
            messages: Initial conversation messages
            tools: List of tools (server-side + client-side)
            functions: Dict mapping client-side function names to callables
            max_iterations: Max tool call rounds (default 10)
            
        Returns:
            Final ChatResponse after all tool calls resolved
            
        Example:
            def get_weather(city: str) -> str:
                return f"72°F in {city}"
            
            response = client.run_agentic_loop(
                messages=[{"role": "user", "content": "Weather in NYC?"}],
                tools=[web_search(), weather_tool],
                functions={"get_weather": get_weather}
            )
        """
        current_messages = messages.copy()
        
        for _ in range(max_iterations):
            response = self.chat(current_messages, tools=tools, **kwargs)
            
            # Check for client-side tool calls
            client_calls = [
                call for call in response.tool_calls
                if self.get_tool_call_type(call) == ToolCallType.CLIENT
            ]
            
            if not client_calls:
                # No more client-side calls, we're done
                return response
            
            # Execute client-side tools
            tool_results = self.execute_tool_calls(client_calls, functions)
            
            # Add assistant response and tool results to messages
            current_messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls
            })
            current_messages.extend(tool_results)
        
        return response
        return results
    
    # =========================================================================
    # UTILITY ENDPOINTS
    # =========================================================================
    
    def list_models(self) -> List[Dict]:
        """List available models"""
        response = self._client.get("/models")
        response.raise_for_status()
        return response.json().get("data", [])
    
    def tokenize(self, text: str, model: Optional[str] = None) -> Dict:
        """Tokenize text and get token count"""
        response = self._client.post("/tokenize-text", json={
            "model": model or self.model,
            "text": text
        })
        response.raise_for_status()
        return response.json()
    
    def embeddings(self, input: str | List[str], model: str = "v1") -> Dict:
        """Generate text embeddings"""
        response = self._client.post("/embeddings", json={
            "model": model,
            "input": input if isinstance(input, list) else [input]
        })
        response.raise_for_status()
        return response.json()
    
    def generate_image(
        self,
        prompt: str,
        model: str = GrokModel.GROK_2_IMAGE,
        n: int = 1,
        **kwargs
    ) -> Dict:
        """Generate images from text prompt"""
        response = self._client.post("/images/generations", json={
            "model": model,
            "prompt": prompt,
            "n": n,
            **kwargs
        })
        response.raise_for_status()
        return response.json()
    
    def search_documents(
        self,
        query: str,
        collection_id: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> Dict:
        """
        Search through uploaded documents/collections.
        
        Args:
            query: Search query
            collection_id: Optional collection to search within
            max_results: Maximum results to return
        """
        payload = {
            "query": query,
            "max_results": max_results,
            **kwargs
        }
        if collection_id:
            payload["collection_id"] = collection_id
            
        response = self._client.post("/documents/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_api_key_info(self) -> Dict:
        """Get information about the current API key"""
        response = self._client.get("/api-key")
        response.raise_for_status()
        return response.json()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def code_execution() -> CodeExecutionTool:
    """Create a code execution tool (server-side)"""
    return CodeExecutionTool()


def web_search() -> WebSearchTool:
    """Create a web search tool (server-side)"""
    return WebSearchTool()


def x_search() -> XSearchTool:
    """Create an X/Twitter search tool (server-side)"""
    return XSearchTool()


def document_search() -> DocumentSearchTool:
    """Create a document search tool (server-side)"""
    return DocumentSearchTool()


def collection_search(collection_id: Optional[str] = None) -> CollectionSearchTool:
    """Create a collection search tool (server-side)"""
    return CollectionSearchTool(collection_id=collection_id)


def mcp(
    server_url: str,
    server_label: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None,
    authorization: Optional[str] = None
) -> MCPTool:
    """Create a remote MCP tool"""
    return MCPTool(
        server_url=server_url,
        server_label=server_label,
        allowed_tool_names=allowed_tools,
        authorization=authorization
    )


def function_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any]
) -> Tool:
    """Create a function tool"""
    return Tool(
        type="function",
        function={
            "name": name,
            "description": description,
            "parameters": parameters
        }
    )


# =============================================================================
# ASYNC CLIENT
# =============================================================================

class AsyncGrokClient:
    """Async version of GrokClient"""
    
    BASE_URL = "https://api.x.ai/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = GrokModel.CODE_FAST_1,
        timeout: float = 120.0
    ):
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self._client.aclose()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        stream: bool = False,
        **kwargs
    ):
        """Async chat completion"""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if tools:
            payload["tools"] = [
                t.to_dict() if hasattr(t, 'to_dict') else t
                for t in tools
            ]
        
        if stream:
            return self._stream_chat(payload)
        
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def _stream_chat(self, payload: Dict):
        """Async streaming"""
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue


# =============================================================================
# MAIN - QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Quick test
    client = GrokClient()
    
    print("=== Available Models ===")
    models = client.list_models()
    for m in models:
        print(f"  - {m['id']}")
    
    print("\n=== Simple Chat ===")
    response = client.chat([
        {"role": "user", "content": "Say 'Hello from Grok!' in one line"}
    ])
    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage.total_tokens} (reasoning: {response.usage.reasoning_tokens})")
