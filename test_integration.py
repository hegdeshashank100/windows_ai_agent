"""
Test the integrated agent's automation capabilities
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import the main integrated agent class
sys.path.insert(0, str(project_root))
from main import IntegratedWindowsAgent

async def test_automation_commands():
    """Test automation commands through the integrated agent"""
    print("🧪 Testing Integrated Agent Automation")
    print("="*50)
    
    # Initialize the integrated agent
    agent = IntegratedWindowsAgent()
    
    print(f"✅ Agent initialized: {agent.is_configured}")
    print(f"✅ Automation available: {agent.automation is not None}")
    print(f"✅ Intent recognizer available: {agent.intent_recognizer is not None}")
    
    # Test automation commands
    test_commands = [
        "open calculator",
        "take a screenshot", 
        "get system information"
    ]
    
    print(f"\n🤖 Testing Automation Commands:")
    
    for cmd in test_commands:
        print(f"\n🔹 Testing: '{cmd}'")
        try:
            response = await agent.process_message(cmd)
            print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_automation_commands())