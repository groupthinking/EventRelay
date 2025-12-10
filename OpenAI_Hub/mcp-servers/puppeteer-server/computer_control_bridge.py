#!/usr/bin/env python3
"""
Computer Control Bridge - Provides computer_20250124 equivalent functionality
Creates the environment for direct computer interaction from oversight system
"""

import subprocess
import time
import os
import json
from datetime import datetime
from pathlib import Path

class ComputerControlBridge:
    def __init__(self):
        self.log_file = Path("/Users/garvey/computer_control_logs.txt")
        self.setup_logging()
        
    def setup_logging(self):
        with open(self.log_file, 'a') as f:
            f.write(f"\n[{datetime.now()}] 🖥️ Computer Control Bridge initialized\n")
    
    def log_action(self, action, params, result):
        """Log all computer actions for oversight"""
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now()}] ACTION: {action} | PARAMS: {params} | RESULT: {result}\n")
    
    def screenshot(self):
        """Capture screenshot using macOS screencapture"""
        try:
            # Allow custom screenshot path or use default
            screenshot_path = getattr(self, 'screenshot_path', "/Users/garvey/oversight_screenshot.png")
            result = subprocess.run([
                'screencapture', '-x', screenshot_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_action("screenshot", {}, "success")
                return {"status": "success", "path": screenshot_path}
            else:
                self.log_action("screenshot", {}, f"error: {result.stderr}")
                return {"status": "error", "message": result.stderr}
                
        except Exception as e:
            self.log_action("screenshot", {}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def left_click(self, x, y):
        """Click at coordinates using cliclick"""
        try:
            result = subprocess.run([
                'cliclick', 'c:' + str(x) + ',' + str(y)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_action("left_click", {"x": x, "y": y}, "success")
                return {"status": "success"}
            else:
                self.log_action("left_click", {"x": x, "y": y}, f"error: {result.stderr}")
                return {"status": "error", "message": result.stderr}
                
        except Exception as e:
            self.log_action("left_click", {"x": x, "y": y}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def type_text(self, text):
        """Type text using cliclick"""
        try:
            result = subprocess.run([
                'cliclick', 't:' + text
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_action("type", {"text": text}, "success")
                return {"status": "success"}
            else:
                self.log_action("type", {"text": text}, f"error: {result.stderr}")
                return {"status": "error", "message": result.stderr}
                
        except Exception as e:
            self.log_action("type", {"text": text}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def key_press(self, key):
        """Press key using AppleScript for reliable input"""
        try:
            # Use AppleScript key codes for reliable input
            key_codes = {
                "enter": 36,
                "return": 36,
                "escape": 53,
                "tab": 48,
                "space": 49,
                "delete": 51,
                "backspace": 51
            }
            
            if key.lower() in key_codes:
                key_code = key_codes[key.lower()]
                applescript = f'tell application "System Events" to key code {key_code}'
                result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
            else:
                # For regular characters, use keystroke
                applescript = f'tell application "System Events" to keystroke "{key}"'
                result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_action("key_press", {"key": key}, "success")
                return {"status": "success"}
            else:
                self.log_action("key_press", {"key": key}, f"error: {result.stderr}")
                return {"status": "error", "message": result.stderr}
                
        except Exception as e:
            self.log_action("key_press", {"key": key}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def activate_application(self, app_name):
        """Activate application using AppleScript"""
        try:
            applescript = f'''
            tell application "{app_name}"
                activate
            end tell
            '''
            
            result = subprocess.run([
                'osascript', '-e', applescript
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_action("activate_app", {"app": app_name}, "success")
                return {"status": "success"}
            else:
                self.log_action("activate_app", {"app": app_name}, f"error: {result.stderr}")
                return {"status": "error", "message": result.stderr}
                
        except Exception as e:
            self.log_action("activate_app", {"app": app_name}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def respond_to_cursor_subagent(self, message="yes"):
        """Specialized function to respond to subagent Claude in Cursor"""
        try:
            # Step 1: Activate Cursor
            self.activate_application("Cursor")
            time.sleep(1)
            
            # Step 2: Type the message
            self.type_text(message)
            time.sleep(0.5)
            
            # Step 3: Press Enter
            self.key_press("enter")
            
            self.log_action("cursor_response", {"message": message}, "success")
            return {"status": "success", "message": f"Sent '{message}' to Cursor subagent"}
            
        except Exception as e:
            self.log_action("cursor_response", {"message": message}, f"exception: {e}")
            return {"status": "error", "message": str(e)}
    
    def computer_use_action(self, action_type, params):
        """Main interface that mimics computer_20250124 tool"""
        
        if action_type == "screenshot":
            return self.screenshot()
            
        elif action_type == "left_click":
            x = params.get("coordinate", [0, 0])[0]
            y = params.get("coordinate", [0, 0])[1]
            return self.left_click(x, y)
            
        elif action_type == "type":
            text = params.get("text", "")
            return self.type_text(text)
            
        elif action_type == "key":
            key = params.get("key", "")
            return self.key_press(key)
            
        elif action_type == "activate_cursor":
            return self.respond_to_cursor_subagent(params.get("message", "yes"))
            
        else:
            return {"status": "error", "message": f"Unknown action: {action_type}"}

# Global instance for easy access
computer = ComputerControlBridge()

if __name__ == "__main__":
    print("🖥️ Computer Control Bridge Ready")
    print("Available actions: screenshot, left_click, type, key, activate_cursor")
    print("Testing immediate response to Cursor subagent...")
    
    # Immediate test - respond to subagent
    result = computer.respond_to_cursor_subagent("yes")
    print(f"Result: {result}")