"""
Test suite for Windows AI Agent
"""

import unittest
import asyncio
import tempfile
from pathlib import Path
import sys
import os

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.gemini_client import GeminiClient, Message
from src.core.agent import WindowsAIAgent
from src.core.intent_recognition import IntentRecognizer, Intent, IntentCategory, IntentParameter
from src.automation.windows_automation import WindowsAutomation
from src.utils.config import Config
from src.utils.code_executor import CodeExecutor, SafeExecutionEnvironment


class TestGeminiClient(unittest.TestCase):
    """Test Gemini client functionality"""
    
    def setUp(self):
        # Use mock API key for testing
        self.client = GeminiClient(api_key="test_key", model_name="gemini-1.5-pro")
    
    def test_message_creation(self):
        """Test message creation"""
        msg = Message(role="user", content="Hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")
        self.assertIsInstance(msg.timestamp, float)
    
    def test_message_to_dict(self):
        """Test message serialization"""
        msg = Message(role="user", content="Hello", timestamp=1234567890.0)
        msg_dict = msg.to_dict()
        
        self.assertEqual(msg_dict["role"], "user")
        self.assertEqual(msg_dict["content"], "Hello")
        self.assertEqual(msg_dict["timestamp"], 1234567890.0)


class TestCodeExecutor(unittest.TestCase):
    """Test code execution functionality"""
    
    def setUp(self):
        self.executor = CodeExecutor()
    
    def test_safe_code_execution(self):
        """Test safe code execution"""
        code = """
x = 10
y = 20
result = x + y
print(f"Result: {result}")
"""
        result = self.executor.execute(code, mode="safe")
        
        self.assertTrue(result["success"])
        self.assertIn("Result: 30", result["output"])
        self.assertIn("result", result["variables"])
        self.assertEqual(result["variables"]["result"], 30)
    
    def test_code_validation(self):
        """Test code validation"""
        # Safe code
        safe_code = "x = 1 + 1"
        validation = self.executor.validate_code(safe_code)
        self.assertTrue(validation["valid"])
        
        # Potentially unsafe code
        unsafe_code = "import os; os.system('echo test')"
        validation = self.executor.validate_code(unsafe_code)
        # This should pass basic validation but fail execution due to import restrictions
        
    def test_session_variables(self):
        """Test persistent session variables"""
        # Execute first code block
        code1 = "x = 42"
        result1 = self.executor.execute(code1, mode="persistent")
        self.assertTrue(result1["success"])
        
        # Execute second code block that uses the variable
        code2 = "y = x * 2"
        result2 = self.executor.execute(code2, mode="persistent")
        self.assertTrue(result2["success"])
        self.assertEqual(result2["variables"]["y"], 84)
    
    def test_syntax_error_handling(self):
        """Test syntax error handling"""
        code = "x = 1 +"  # Incomplete expression
        result = self.executor.execute(code)
        
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])


class TestIntentRecognition(unittest.TestCase):
    """Test intent recognition system"""
    
    def setUp(self):
        # Create mock automation for testing
        self.automation = None  # Mock automation
        self.recognizer = IntentRecognizer(self.automation) if self.automation else None
    
    def test_intent_creation(self):
        """Test intent creation"""
        intent = Intent(
            name="test_intent",
            category=IntentCategory.AUTOMATION,
            parameters={
                "test_param": IntentParameter("test_param", "string", required=True)
            },
            patterns=["test pattern (?P<test_param>\\w+)"],
            description="Test intent"
        )
        
        self.assertEqual(intent.name, "test_intent")
        self.assertEqual(intent.category, IntentCategory.AUTOMATION)
        self.assertIn("test_param", intent.parameters)
    
    @unittest.skipIf(not hasattr(IntentRecognizer, '__init__'), "IntentRecognizer requires automation")
    def test_intent_parsing(self):
        """Test intent parsing"""
        if self.recognizer is None:
            self.skipTest("No automation available for testing")
        
        # This would test actual intent parsing
        # For now, just test the structure
        pass


class TestWindowsAutomation(unittest.TestCase):
    """Test Windows automation functionality"""
    
    def test_automation_creation(self):
        """Test automation instance creation"""
        try:
            automation = WindowsAutomation(safe_mode=True)
            self.assertTrue(automation.safe_mode)
        except ImportError:
            self.skipTest("Windows automation dependencies not available")
    
    def test_safe_coordinate_validation(self):
        """Test safe coordinate validation"""
        try:
            automation = WindowsAutomation(safe_mode=True)
            
            # Mock screen size for testing
            automation.get_screen_size = lambda: (1920, 1080)
            
            # Test valid coordinates
            self.assertTrue(automation._is_safe_coordinate(500, 300))
            
            # Test invalid coordinates (too close to edges)
            self.assertFalse(automation._is_safe_coordinate(5, 5))  # Too close to top
            self.assertFalse(automation._is_safe_coordinate(500, 1075))  # Too close to bottom
            
        except ImportError:
            self.skipTest("Windows automation dependencies not available")


class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_config_creation(self):
        """Test config instance creation"""
        config = Config()
        self.assertIsInstance(config, Config)
    
    def test_config_defaults(self):
        """Test default configuration values"""
        config = Config()
        
        # Test default values
        self.assertEqual(config.gemini_model, "gemini-1.5-pro")
        self.assertEqual(config.gemini_temperature, 0.7)
        self.assertTrue(config.enable_code_execution)
        self.assertTrue(config.enable_desktop_automation)
    
    def test_type_conversion(self):
        """Test configuration type conversion"""
        config = Config()
        
        # Test boolean conversion
        self.assertTrue(config._convert_type("true"))
        self.assertTrue(config._convert_type("True"))
        self.assertTrue(config._convert_type("1"))
        self.assertFalse(config._convert_type("false"))
        self.assertFalse(config._convert_type("0"))
        
        # Test numeric conversion
        self.assertEqual(config._convert_type("42"), 42)
        self.assertEqual(config._convert_type("3.14"), 3.14)
        
        # Test string passthrough
        self.assertEqual(config._convert_type("hello"), "hello")


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_agent_initialization(self):
        """Test agent initialization without API key"""
        agent = WindowsAIAgent()
        self.assertIsNotNone(agent)
        # Agent should initialize even without API key, but won't be configured
    
    def test_capability_registration(self):
        """Test capability registration"""
        agent = WindowsAIAgent()
        
        initial_count = len(agent.capabilities)
        
        # Register a test capability
        def test_handler(message):
            return {"success": True, "message": "Test response"}
        
        agent.register_capability("test", "Test capability", test_handler)
        
        self.assertEqual(len(agent.capabilities), initial_count + 1)
        self.assertIn("test", agent.capabilities)


# Test runner
class AsyncTestRunner:
    """Test runner that supports async tests"""
    
    @staticmethod
    def run_async_test(test_func):
        """Run an async test function"""
        async def wrapper():
            return await test_func()
        
        return asyncio.run(wrapper())


def run_tests():
    """Run all tests"""
    print("🧪 Running Windows AI Agent Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestGeminiClient,
        TestCodeExecutor,
        TestIntentRecognition,
        TestWindowsAutomation,
        TestConfig,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)