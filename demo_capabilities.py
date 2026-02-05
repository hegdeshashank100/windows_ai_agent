"""
Simple test to demonstrate Windows AI Agent capabilities
"""
import subprocess
import time
import os
import psutil
import sys

def test_app_launching():
    """Test launching common Windows applications"""
    print("🚀 Application Launching Test")
    print("="*50)
    
    apps_to_test = [
        ("Calculator", "calc.exe"),
        ("Notepad", "notepad.exe"),
        ("File Explorer", "explorer.exe"),
        ("Paint", "mspaint.exe")
    ]
    
    launched_pids = []
    
    for app_name, app_command in apps_to_test:
        try:
            print(f"Launching {app_name}...")
            process = subprocess.Popen(app_command, shell=True)
            launched_pids.append(process.pid)
            print(f"  ✅ {app_name} launched successfully (PID: {process.pid})")
            time.sleep(1)  # Brief delay between launches
        except Exception as e:
            print(f"  ❌ Failed to launch {app_name}: {str(e)}")
    
    return launched_pids

def test_system_info():
    """Test system information gathering"""
    print(f"\n📊 System Information Test")
    print("="*50)
    
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"CPU Usage: {cpu_percent}%")
        
        # Memory information
        memory = psutil.virtual_memory()
        print(f"Memory Usage: {memory.percent}% ({memory.used // (1024*1024)} MB / {memory.total // (1024*1024)} MB)")
        
        # Disk information  
        disk = psutil.disk_usage('C:')
        print(f"Disk Usage: {disk.percent:.1f}% ({disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB)")
        
        # Running processes count
        process_count = len(list(psutil.process_iter()))
        print(f"Running Processes: {process_count}")
        
    except Exception as e:
        print(f"❌ System info failed: {str(e)}")

def test_automation_readiness():
    """Test if automation dependencies are available"""
    print(f"\n🛠️  Automation Dependencies Test")
    print("="*50)
    
    dependencies = {
        "PyAutoGUI": None,
        "Win32 API": None,
        "PSUtil": True,  # We know this works
        "PyQt6": None
    }
    
    # Test PyAutoGUI
    try:
        import pyautogui
        screen_size = pyautogui.size()
        mouse_pos = pyautogui.position()
        dependencies["PyAutoGUI"] = True
        print(f"✅ PyAutoGUI: Working (Screen: {screen_size}, Mouse: {mouse_pos})")
    except Exception as e:
        dependencies["PyAutoGUI"] = False
        print(f"❌ PyAutoGUI: Failed - {str(e)}")
    
    # Test Win32 API
    try:
        import win32gui
        import win32api
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        dependencies["Win32 API"] = True
        print(f"✅ Win32 API: Working (Active window: '{window_title[:30]}...')")
    except Exception as e:
        dependencies["Win32 API"] = False
        print(f"❌ Win32 API: Failed - {str(e)}")
    
    # Test PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
        dependencies["PyQt6"] = True
        print(f"✅ PyQt6: Available")
    except Exception as e:
        dependencies["PyQt6"] = False
        print(f"❌ PyQt6: Failed - {str(e)}")
    
    # Test Google AI
    try:
        import google.generativeai as genai
        print(f"✅ Google Generative AI: Available")
    except Exception as e:
        print(f"❌ Google Generative AI: Failed - {str(e)}")
    
    return dependencies

def demonstrate_capabilities():
    """Show what the agent can do"""
    print(f"\n🎯 Windows AI Agent Capabilities")
    print("="*50)
    
    capabilities = [
        "🖱️  Mouse Control (Click, Drag, Scroll)",
        "⌨️  Keyboard Input (Type text, Hotkeys)",
        "📸 Screenshots (Full screen, Regions)",
        "🪟 Window Management (Find, Activate, Resize)",
        "📱 Application Control (Launch, Close, Monitor)",
        "💾 File Operations (Create, Read, Write, Delete)",
        "📊 System Monitoring (CPU, Memory, Disk, Processes)",
        "🧠 AI Integration (Gemini 2.0 Flash)",
        "🔒 Safe Code Execution (Python Sandbox)",
        "🎨 Modern GUI Interface (PyQt6)"
    ]
    
    for capability in capabilities:
        print(f"  {capability}")
    
    print(f"\n💬 Example Voice Commands:")
    commands = [
        "'Open calculator'",
        "'Take a screenshot'",
        "'Click at 500, 300'",
        "'Type hello world'",
        "'Show me system information'",
        "'Open notepad and write a note'",
        "'Minimize all windows'",
        "'Find the Chrome window'"
    ]
    
    for cmd in commands:
        print(f"  📢 {cmd}")

if __name__ == "__main__":
    print("🤖 Windows AI Agent Capability Demonstration")
    print("="*60)
    
    # Test system readiness
    deps = test_automation_readiness()
    
    # Test system information
    test_system_info()
    
    # Test application launching
    print(f"\n⚠️  Warning: This will launch several applications!")
    response = input("Continue with app launch test? (y/N): ").strip().lower()
    
    if response == 'y':
        launched_pids = test_app_launching()
        
        print(f"\n⏳ Applications are now running...")
        print("   You can see Calculator, Notepad, File Explorer, and Paint opened")
        
        # Wait a moment then offer to close
        time.sleep(3)
        response = input(f"\nClose launched applications? (y/N): ").strip().lower()
        if response == 'y':
            for pid in launched_pids:
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    print(f"Closed process {pid}")
                except:
                    pass
    
    # Show capabilities
    demonstrate_capabilities()
    
    print(f"\n✨ The Windows AI Agent is ready!")
    print("   Run 'python main.py' to start the GUI interface")
    print("   The agent can understand natural language and perform automation tasks")