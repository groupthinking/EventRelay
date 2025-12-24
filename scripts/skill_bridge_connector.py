#!/usr/bin/env python3
"""
Skill Bridge Connector - Multi-Agent Collective Learning
Connects skill_builder.py with mcp-bridge for network-wide skill sharing
Anti-bloat: <100 lines, extends existing systems
"""
import json
import sys
import asyncio
from pathlib import Path
import threading
import time
from datetime import datetime

# Add mcp-bridge to path
sys.path.append('/Users/garvey/mcp-bridge')

from skill_builder import SkillBuilder

class CollectiveSkillBuilder(SkillBuilder):
    """Extended SkillBuilder with multi-agent network sharing"""

    def __init__(self):
        super().__init__()
        self.connection_id = f"eventrelay_{int(time.time())}"
        self.bridge_available = self._check_bridge()

        if self.bridge_available:
            self._start_listener()
            print(f"🌐 Collective learning active: {self.connection_id}")
        else:
            print("⚠️  Running in isolated mode (bridge unavailable)")

    def _check_bridge(self):
        """Verify bridge database exists"""
        bridge_db = Path.home() / ".claude" / "claude_bridge_enhanced.db"
        return bridge_db.exists()

    def capture_error_resolution(self, error_type, error_msg, resolution, context=""):
        """Capture skill locally and broadcast to network"""
        # Local capture
        skill = super().capture_error_resolution(error_type, error_msg, resolution, context)

        # Network broadcast
        if self.bridge_available:
            self._broadcast_skill(skill)

        return skill

    def _broadcast_skill(self, skill):
        """Broadcast skill to all agents via bridge"""
        try:
            import sqlite3
            bridge_db = Path.home() / ".claude" / "claude_bridge_enhanced.db"

            with sqlite3.connect(bridge_db) as conn:
                message_id = f"skill_{skill['id']}_{int(time.time())}"
                conn.execute("""
                    INSERT INTO enhanced_messages
                    (message_id, from_connection, to_connection, from_app, to_app,
                     priority, content, status, created_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_id,
                    self.connection_id,
                    "all",
                    "eventrelay",
                    "all",
                    "high",
                    json.dumps(skill),
                    "pending",
                    datetime.now().isoformat()
                ))
                conn.commit()

            print(f"🌐 Skill #{skill['id']} broadcasted to network")
        except Exception as e:
            print(f"⚠️  Broadcast failed: {e}")

    def _start_listener(self):
        """Start background thread to receive skills from network"""
        listener_thread = threading.Thread(target=self._listen_for_skills, daemon=True)
        listener_thread.start()

    def _listen_for_skills(self):
        """Background process to receive skills from other agents"""
        import sqlite3
        bridge_db = Path.home() / ".claude" / "claude_bridge_enhanced.db"

        while True:
            try:
                with sqlite3.connect(bridge_db) as conn:
                    # Get pending messages for this app
                    cursor = conn.execute("""
                        SELECT message_id, from_connection, content
                        FROM enhanced_messages
                        WHERE (to_app = 'eventrelay' OR to_app = 'all')
                        AND status = 'pending'
                        AND from_connection != ?
                        ORDER BY created_time ASC
                        LIMIT 10
                    """, (self.connection_id,))

                    messages = cursor.fetchall()

                    for msg_id, from_conn, content in messages:
                        self._receive_skill(json.loads(content), from_conn)

                        # Mark as delivered
                        conn.execute("""
                            UPDATE enhanced_messages
                            SET status = 'delivered', delivered_time = ?
                            WHERE message_id = ?
                        """, (datetime.now().isoformat(), msg_id))

                    conn.commit()

                time.sleep(2)  # Poll every 2 seconds
            except Exception as e:
                print(f"⚠️  Listener error: {e}")
                time.sleep(5)

    def _receive_skill(self, skill, from_connection):
        """Apply skill learned by another agent"""
        # Check if we already have this skill
        existing = self.find_matching_skill(skill["error_type"], skill["pattern"])

        if not existing:
            # Add to our local database
            self.skills["skills"].append(skill)
            self._save_skills()
            print(f"📚 Learned from network: {skill['error_type']} (from {from_connection})")
        else:
            print(f"✓ Already know: {skill['error_type']}")

# Global instance for easy access
collective_builder = CollectiveSkillBuilder()

def collective_auto_resolve(error_type, error_msg, context=""):
    """Auto-resolve using collective knowledge"""
    skill = collective_builder.find_matching_skill(error_type, error_msg)

    if skill:
        print(f"🔧 Collective resolution: {skill['resolution']}")
        collective_builder.apply_skill(skill['id'], success=True)
        return skill['resolution']
    else:
        print(f"⚠️  New error - capturing for collective learning")
        return None

if __name__ == "__main__":
    print("🌐 Collective Skill Builder - Multi-Agent Learning System")
    print("=" * 60)

    # Demo: Test skill broadcasting
    builder = CollectiveSkillBuilder()

    # Capture a skill that will be broadcast
    builder.capture_error_resolution(
        error_type="ImportError",
        error_msg="No module named 'youtube_transcript_api'",
        resolution="pip install youtube-transcript-api",
        context="YouTube processing dependency"
    )

    print(f"\n📊 Stats: {builder.get_stats()}")
    print("🔄 Listening for network skills...")

    # Keep alive to demonstrate listener
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 Shutting down collective learning")
