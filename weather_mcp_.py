# =====================================================
# weather_mcp_.py
# Generative Weather UI MCP Server (powered by xAI/Grok)
#
# How to use it
#
# Install Requirements:
#
#   Bash
#   pip install mcp requests openai
#
# Set your API Key:
#
#   Bash
#   export xai="your-api-key-here"
#
# Run the server:
#
#   python weather_mcp_.py
#
# This MCP server exposes a tool that:
#   1. Fetches live weather from wttr.in (no key required)
#   2. Uses Grok (via the xAI API) to write a clever joke + generate
#      a fully self-contained, custom HTML/CSS/Vanilla JS UI
#   3. Returns the complete HTML page as a string
#
# The UI is 100% generative — no external frameworks or CDNs.
#
# Quick Preview (view the UI directly, no MCP client needed):
#
#   Bash
#   export xai="your-api-key-here"
#   python weather_mcp_.py --demo --location "San Francisco"
#
#   Or for instant preview without any API key:
#   python weather_mcp_.py --mock --location "San Francisco"
#
# This will generate the full custom HTML and save it as
# weather_ui.html. Just open the file in your browser to see the current version.
#
# Connect to your MCP Client:
#
# Configure your MCP-compatible client (like claude or grok ) to run the Python script. When you ask the agent, "What's the weather in San Francisco? Show me a custom UI," the host client will call the tool, the LLM will generate the raw, imaginative HTML, and the client will render the sandboxed UI directly in your chat interface.
#
# Example for Claude Desktop (macOS):
#   Config file: ~/Library/Application Support/Claude/claude_desktop_config.json
#
#   Add this under "mcpServers":
#
#     "generative-weather": {
#       "command": "python",
#       "args": ["/absolute/path/to/weather_mcp_.py"],
#       "env": {
#         "xai": "your-api-key-here"
#       }
#     }
#
#   Then restart Claude Desktop.
#
#   Try the prompt:
#     "What's the weather in San Francisco? Show me a custom UI"
#
# The agent will automatically discover the tool, call it, receive the
# self-contained HTML, and render the generative UI in the chat.
# =====================================================

import os
import sys
import argparse


def _get_xai_client():
    """Resolve xAI API key from 'xai' or standard 'XAI_API_KEY' env var."""
    from openai import OpenAI  # lazy import

    api_key = os.environ.get("xai") or os.environ.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing xAI API key. Please run:\n"
            "  export xai=\"your-api-key-here\"\n"
            "or\n"
            "  export XAI_API_KEY=\"your-api-key-here\""
        )
    return OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",  # xAI is OpenAI-compatible
    )


def generate_weather_ui(location: str) -> str:
    """
    Fetches live weather for a location, generates a joke, and dynamically
    creates a fully custom HTML/CSS/JS UI to render the result.
    Powered by Grok via the xAI API.

    This is the core "current version" of the generative UI logic from the
    Ruben Casas talk. Call it directly (via --demo) to preview the HTML.
    """
    import requests  # lazy import

    # 1. Fetch live data from a Weather API (wttr.in requires no auth key)
    try:
        response = requests.get(f"https://wttr.in/{location}?format=j1")
        response.raise_for_status()
        data = response.json()
        current = data["current_condition"][0]
        weather_data = {
            "location": location,
            "temperature_f": current["temp_F"],
            "condition": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
        }
    except Exception as e:
        weather_data = {"location": location, "error": str(e)}

    # 2. Use Grok (xAI) to generate the joke + fully custom HTML/CSS/JS UI
    client = _get_xai_client()

    prompt = f"""
You are a Generative UI Agent.

Here is the live weather data for {location}:
{weather_data}

Your task:
1. Write a clever, context-aware joke about this specific weather condition and location.
2. Generate a highly imaginative, dynamic, and custom UI to display this weather data and the joke.
3. The output must be a SINGLE, fully self-contained HTML file. Include ALL CSS inside <style> tags and ALL JavaScript inside <script> tags.
4. Do not rely on any external component libraries, frameworks, or CDNs (no React, Tailwind, Bootstrap, external fonts, etc.). Use pure HTML5 + CSS3 + Vanilla JS only.
5. Make the design visually delightful and appropriate to the current weather (colors, mood, animations, particles, etc.).
6. Output ONLY the raw HTML code. Do not wrap it in markdown code blocks (e.g. no ```html or ```).
"""

    completion = client.chat.completions.create(
        model="grok-2-1212",  # Grok model via xAI
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
    )

    html_output = completion.choices[0].message.content.strip()

    # Strip accidental markdown formatting
    if html_output.startswith("```html"):
        html_output = html_output[7:]
    if html_output.startswith("```"):
        html_output = html_output[3:]
    if html_output.endswith("```"):
        html_output = html_output[:-3]

    return html_output.strip()


def _generate_mock_ui(location: str) -> str:
    """Generate a beautiful self-contained preview UI without any API calls.
    This lets you instantly view what the current version style looks like.
    """
    import datetime
    now = datetime.datetime.now().strftime("%I:%M %p")

    # Fun mock data
    mock = {
        "location": location,
        "temperature_f": "62",
        "condition": "Partly Cloudy",
        "humidity": "68",
        "joke": "Why did the cloud break up with the sun? It needed some space... and a little shade!",
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather • {mock['location']}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&amp;family=Space+Grotesk:wght@500;600&amp;display=swap');
        
        :root {{
            --bg: #0a0a0a;
            --card: #121212;
            --accent: #3b82f6;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            background: linear-gradient(145deg, #0a0a0a, #111111);
            color: #f1f1f1;
            font-family: 'Inter', system_ui, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 720px;
            width: 92%;
            background: var(--card);
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.4);
            overflow: hidden;
            border: 1px solid #222;
        }}
        
        .header {{
            background: linear-gradient(to right, #1a1a1a, #111);
            padding: 24px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #222;
        }}
        
        .location {{
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }}
        
        .time {{
            font-size: 13px;
            opacity: 0.6;
            font-family: monospace;
        }}
        
        .main {{
            padding: 48px 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            position: relative;
        }}
        
        .temp {{
            font-size: 96px;
            font-weight: 700;
            line-height: 1;
            margin: 8px 0;
            background: linear-gradient(90deg, #fff, #ddd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-family: 'Space Grotesk', system_ui, sans-serif;
        }}
        
        .condition {{
            font-size: 22px;
            font-weight: 500;
            color: #aaa;
            margin-bottom: 12px;
        }}
        
        .details {{
            display: flex;
            gap: 32px;
            margin: 24px 0 40px;
            font-size: 15px;
            color: #888;
        }}
        
        .detail {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .joke {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 16px;
            padding: 24px 28px;
            font-size: 15.5px;
            line-height: 1.5;
            max-width: 460px;
            position: relative;
        }}
        
        .joke::before {{
            content: "💬";
            position: absolute;
            top: -10px;
            left: 28px;
            background: #1a1a1a;
            padding: 0 8px;
            font-size: 18px;
        }}
        
        .clouds {{
            position: absolute;
            top: 30px;
            right: 40px;
            width: 140px;
            height: 60px;
            opacity: 0.15;
        }}
        
        .cloud {{
            position: absolute;
            background: #fff;
            border-radius: 50%;
            box-shadow: 0 4px 10px rgb(0 0 0 / 0.1);
        }}
        
        .cloud1 {{ width: 80px; height: 42px; top: 10px; left: 10px; }}
        .cloud2 {{ width: 60px; height: 32px; top: 20px; left: 55px; }}
        
        .footer {{
            padding: 16px 32px;
            background: #0a0a0a;
            font-size: 12px;
            color: #555;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .badge {{
            background: #222;
            color: #777;
            padding: 2px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-family: monospace;
        }}
        
        .generative-note {{
            font-size: 11px;
            opacity: 0.4;
            margin-top: 8px;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-12px); }}
        }}
        
        .weather-icon {{
            font-size: 64px;
            margin-bottom: 8px;
            animation: float 3s ease-in-out infinite;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <div class="location">{mock['location']}</div>
                <div class="time">{now}</div>
            </div>
            <div class="badge">LIVE</div>
        </div>
        
        <!-- Main content -->
        <div class="main">
            <!-- Animated decorative clouds -->
            <div class="clouds">
                <div class="cloud cloud1"></div>
                <div class="cloud cloud2"></div>
            </div>
            
            <div class="weather-icon">⛅</div>
            
            <div class="temp">{mock['temperature_f']}°</div>
            <div class="condition">{mock['condition']}</div>
            
            <div class="details">
                <div class="detail">
                    <span>💧</span>
                    <span>{mock['humidity']}% humidity</span>
                </div>
            </div>
            
            <!-- The joke -->
            <div class="joke">
                {mock['joke']}
            </div>
            
            <div class="generative-note">
                Generated live by Grok • No components used
            </div>
        </div>
        
        <div class="footer">
            <div>wttr.in + xAI</div>
            <div>Generative UI Demo</div>
        </div>
    </div>
    
    <script>
        // Tiny bit of interactivity for the demo
        console.log('%c[Generative UI] Self-contained preview loaded', 'color:#555');
        
        const container = document.querySelector('.container');
        
        container.addEventListener('mousemove', (e) => {{
            const rect = container.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) - 0.5;
            const y = ((e.clientY - rect.top) / rect.height) - 0.5;
            
            container.style.transform = `perspective(1000px) rotateX(${{-y * 6}}deg) rotateY(${{x * 8}}deg)`;
        }});
        
        container.addEventListener('mouseleave', () => {{
            container.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
        }});
        
        // Easter egg: click the temp to change mood
        const temp = document.querySelector('.temp');
        let clicks = 0;
        temp.addEventListener('click', () => {{
            clicks++;
            const moods = ['☀️', '🌧️', '❄️', '⛈️', '🌫️'];
            document.querySelector('.weather-icon').textContent = moods[clicks % moods.length];
            
            if (clicks % 3 === 0) {{
                container.style.transition = 'transform 0.4s cubic-bezier(0.23, 1, 0.32, 1)';
                container.style.transform = 'scale(0.96)';
                setTimeout(() => {{
                    container.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
                }}, 180);
            }}
        }});
        
        // Keyboard hint
        document.addEventListener('keydown', (e) => {{
            if (e.key === '?') {{
                temp.click();
            }}
        }});
    </script>
</body>
</html>"""
    return html


def _start_mcp_server():
    """Load MCP bits only when actually running in server mode."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("GenerativeWeatherUI")

    # Register the pure generative function as an MCP tool
    mcp.tool()(generate_weather_ui)

    print("Starting GenerativeWeatherUI MCP server (stdio transport)...")
    mcp.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generative Weather UI MCP Server (powered by xAI/Grok) — Ruben Casas style demo"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Direct preview mode using real Grok (requires xai key): generate weather + joke + full custom HTML UI and save it."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Instant preview with no API key or internet after install: shows a beautiful representative generative UI immediately."
    )
    parser.add_argument(
        "--location",
        default="San Francisco",
        help="Location for the weather data and generated UI (default: San Francisco)"
    )
    parser.add_argument(
        "--output",
        default="weather_ui.html",
        help="Filename to write the generated HTML to (default: weather_ui.html)"
    )

    args = parser.parse_args()

    if args.demo or args.mock:
        mode = "REAL (Grok)" if args.demo else "MOCK (instant preview)"
        print(f"🌤️  [{mode}] Generating UI for: {args.location}")

        try:
            if args.mock:
                html = _generate_mock_ui(args.location)
                note = " (mock mode — beautiful example of the style)"
            else:
                html = generate_weather_ui(args.location)
                note = ""

            with open(args.output, "w", encoding="utf-8") as f:
                f.write(html)

            abs_path = os.path.abspath(args.output)
            print(f"\n✅ Success! Saved current version{note}")
            print(f"   File: {args.output}")
            print(f"   Open in browser →  file://{abs_path}")
            print("   (Fully self-contained single HTML file)")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if not args.mock:
                print("   For real Grok generation you need:")
                print("     pip install mcp requests openai")
                print('     export xai="your-xai-api-key-here"')
            sys.exit(1)
    else:
        _start_mcp_server()
