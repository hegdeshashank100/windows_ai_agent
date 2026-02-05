"""
Quick test for Gemini client functionality
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_gemini_client_basic():
    """Test basic Gemini client functionality"""
    try:
        from src.core.gemini_client import GeminiClient, Message
        
        # Test message creation
        msg = Message(role="user", content="test message")
        assert msg.role == "user"
        assert msg.content == "test message"
        assert msg.timestamp is not None
        print("✅ Message class working correctly")
        
        # Test client creation (without API key)
        client = GeminiClient(api_key="", model_name="gemini-1.5-pro")
        assert client.model_name == "gemini-1.5-pro"
        assert not client.is_configured  # Should be false without API key
        print("✅ GeminiClient initialization working")
        
        # Test client with mock API key
        client_with_key = GeminiClient(api_key="test_key", model_name="gemini-1.5-pro")
        assert client_with_key.api_key == "test_key"
        print("✅ GeminiClient with API key working")
        
        print("🎉 All basic tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_client_basic()
    sys.exit(0 if success else 1)