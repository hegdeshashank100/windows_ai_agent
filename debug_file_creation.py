import asyncio
from src.core.intent_recognition import IntentRecognizer
from src.automation.windows_automation import WindowsAutomation

async def test_file_creation():
    automation = WindowsAutomation()
    engine = IntentRecognizer(automation)
    
    # Test the original failing command
    commands = [
        'create text file named hegde in desktop',
        'create text file named index.html'
    ]
    
    for cmd in commands:
        print(f"\n=== Testing: {cmd} ===")
        parsed = await engine.parse_intent(cmd)
        print(f"Parsed intent: {parsed.extracted_params if parsed else 'None'}")
        
        if parsed:
            result = await engine.execute_intent(parsed)
            print(f"Result: {result}")
        else:
            print("No intent parsed")

if __name__ == "__main__":
    asyncio.run(test_file_creation())