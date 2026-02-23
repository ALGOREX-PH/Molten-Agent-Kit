#!/usr/bin/env python3
"""
Molten Agents Kit - Agent Runner
Quick script to run your Moltbook AI agent
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("molten_agent.cli")

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

            logger.info("Registering %s...", name)
            result = register_agent(name, desc)

            if result.get("success"):
                # Print credentials directly — users must see these regardless of log level
                print("\n" + "="*50)
                print("SAVE THESE CREDENTIALS!")
                print("="*50)
                print(f"API Key: {result['agent']['api_key']}")
                print(f"Claim URL: {result['agent']['claim_url']}")
                print(f"Verification: {result['agent']['verification_code']}")
                print("\n1. Add API key to .env as MOLTBOOK_API_KEY")
                print("2. Send claim_url to your human to verify via Twitter")
            else:
                logger.error("Registration failed: %s", json.dumps(result, indent=2))

        elif cmd == "once":
            # Run single heartbeat
            logger.info("Running single heartbeat...")
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
            logger.info("Status: %s", json.dumps(status, indent=2))
            logger.info("Profile: %s", json.dumps(profile, indent=2))

        else:
            logger.error("Unknown command: %s", cmd)
            print("Usage: python run.py [register|once|status]")
            print("       python run.py  (runs continuously)")

    else:
        # Run continuously (reads interval from config.json post_interval_minutes)
        run_continuous()


if __name__ == "__main__":
    main()
