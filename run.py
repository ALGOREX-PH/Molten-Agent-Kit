#!/usr/bin/env python3
"""
Molten Agents Kit - Agent Runner
Quick script to run your Moltbook AI agent
"""

import sys
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent / "agent"))

from my_agent import run_continuous, run_heartbeat, load_config
from moltbook_client import register_agent
import json


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "register":
            # Register a new Moltbook account
            config = load_config()
            name = config.get("agent_name") or input("Agent name: ")
            desc = config.get("agent_description") or input("Description: ")

            print(f"\nRegistering {name}...")
            result = register_agent(name, desc)
            print(json.dumps(result, indent=2))

            if result.get("success"):
                print("\n" + "="*50)
                print("WARNING: SAVE THESE CREDENTIALS!")
                print("="*50)
                print(f"API Key: {result['agent']['api_key']}")
                print(f"Claim URL: {result['agent']['claim_url']}")
                print(f"Verification: {result['agent']['verification_code']}")
                print("\n1. Add API key to .env as MOLTBOOK_API_KEY")
                print("2. Send claim_url to your human to verify via Twitter")

        elif cmd == "once":
            # Run single heartbeat
            print("Running single heartbeat...")
            run_heartbeat()

        elif cmd == "status":
            # Check status
            from moltbook_client import MoltbookClient
            config = load_config()
            client = MoltbookClient(
                api_key=config.get("moltbook_api_key", ""),
                openai_api_key=config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
            )
            status = client.get_status()
            profile = client.get_me()
            print("Status:", json.dumps(status, indent=2))
            print("Profile:", json.dumps(profile, indent=2))

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python run.py [register|once|status]")
            print("       python run.py  (runs continuously)")

    else:
        # Run continuously (reads interval from config.json post_interval_minutes)
        run_continuous()


if __name__ == "__main__":
    main()
