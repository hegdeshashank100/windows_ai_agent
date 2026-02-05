"""
Entry point script with command line interface
"""

import argparse
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import main as app_main, setup_logging
from tests.test_agent import run_tests
from src.utils.config import config


def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Windows AI Agent - Advanced Desktop Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    # Start the GUI application
  python run.py --test            # Run test suite
  python run.py --config          # Show current configuration
  python run.py --help            # Show this help message

For more information, see README.md or docs/examples.md
        """
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Run the test suite'
    )
    
    parser.add_argument(
        '--config',
        action='store_true', 
        help='Show current configuration'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run without GUI (CLI mode - not implemented yet)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Windows AI Agent 1.0.0'
    )
    
    return parser


def show_config():
    """Display current configuration"""
    print("🔧 Windows AI Agent Configuration")
    print("=" * 40)
    print(f"Google API Key: {'✅ Set' if config.google_api_key else '❌ Not set'}")
    print(f"Gemini Model: {config.gemini_model}")
    print(f"Debug Mode: {config.debug_mode}")
    print(f"Log Level: {config.log_level}")
    print(f"Code Execution: {'✅ Enabled' if config.enable_code_execution else '❌ Disabled'}")
    print(f"Desktop Automation: {'✅ Enabled' if config.enable_desktop_automation else '❌ Disabled'}")
    print(f"Window Size: {config.window_width}x{config.window_height}")
    print(f"Theme: {config.theme}")
    print()
    
    if not config.google_api_key:
        print("⚠️  Warning: Google API key not set!")
        print("Please set GOOGLE_API_KEY in your .env file")
        print("Get a free API key from: https://makersuite.google.com/app/apikey")


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup basic logging
    setup_logging()
    
    try:
        if args.test:
            print("🧪 Running test suite...")
            success = run_tests()
            return 0 if success else 1
        
        elif args.config:
            show_config()
            return 0
        
        elif args.no_gui:
            print("❌ CLI mode not implemented yet.")
            print("Please use the GUI mode by running without --no-gui")
            return 1
        
        else:
            # Set debug mode if requested
            if args.debug:
                config.debug_mode = True
            
            # Start the main application
            return app_main()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())