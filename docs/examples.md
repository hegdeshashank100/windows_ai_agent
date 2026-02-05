# Windows AI Agent Usage Examples

This document provides comprehensive examples of how to use the Windows AI Agent.

## 🚀 Getting Started

### 1. Basic Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your Google API key

# Run the application
python main.py
```

### 2. First Conversation

When you start the agent, you'll see a modern chat interface. Here are some examples to get you started:

## 💬 Natural Language Examples

### General Conversation

```
You: Hello! What can you do?
AI: Hi there! I'm your Windows AI Assistant. I can help with desktop automation,
    file operations, system monitoring, code execution, and general conversation.
    Try asking me to take a screenshot or open an application!
```

### System Information

```
You: Show me system information
AI: 💻 **System Information:**

**CPU Usage:** 15.2%
**Memory:** 8.3 GB available / 16.0 GB total (48.1% used)
**Disk:** 245.7 GB free / 512.0 GB total (52.0% used)
**Screen Resolution:** 1920x1080
```

## 🖱️ Desktop Automation Examples

### Screenshots

```
You: Take a screenshot
AI: 📸 **Screenshot captured!**

📁 Saved to: `C:\Users\YourName\Desktop\ai_screenshot_1699123456.png`
📏 Size: 1920×1080 pixels
```

### Mouse Operations

```
You: Click at 500,300
AI: ✅ **click_coordinates**: Clicked at (500, 300) with left button

You: Right click 100,200
AI: ✅ **click_coordinates**: Clicked at (100, 200) with right button
```

### Keyboard Input

```
You: Type "Hello World"
AI: ✅ **type_text**: Typed text: Hello World

You: Press ctrl+c
AI: ✅ **send_hotkey**: Pressed hotkey: ctrl+c
```

## 📱 Application Management

### Opening Applications

```
You: Open calculator
AI: ✅ **open_application**: Opened calculator

You: Launch notepad
AI: ✅ **open_application**: Opened notepad

You: Start file explorer
AI: ✅ **open_application**: Opened explorer
```

### Window Management

```
You: Minimize all windows
AI: ✅ **minimize_window**: Minimized all windows

You: Minimize notepad
AI: ✅ **minimize_window**: Minimized window: Notepad

You: Close calculator
AI: ⚠️ This will close the Calculator application. Are you sure? (y/n)
```

## 📁 File Operations

### Creating Files

```
You: Create a file called todo.txt
AI: ✅ **create_file**: Created file: C:\Users\YourName\todo.txt

You: Create a new file called "notes.txt" with content "My important notes"
AI: ✅ **create_file**: Created file: C:\Users\YourName\notes.txt
```

### Creating Folders

```
You: Create folder Documents/Projects
AI: ✅ **create_folder**: Created folder: C:\Users\YourName\Documents\Projects

You: New directory C:/temp/ai_workspace
AI: ✅ **create_folder**: Created folder: C:\temp\ai_workspace
```

## 💻 Code Execution Examples

### Simple Calculations

````
You: Run this code:
```python
x = 25
y = 47
result = x * y
print(f"{x} × {y} = {result}")
````

AI: ✅ **Code executed successfully!**

**Output:**

```
25 × 47 = 1175
```

**Variables created:**
• `x` = 25
• `y` = 47  
• `result` = 1175

⏱️ _Execution time: 0.002s_

```

### Data Processing
```

You: Execute:

```python
import math
import datetime

numbers = [1, 4, 9, 16, 25, 36]
sqrt_numbers = [math.sqrt(n) for n in numbers]

print("Original numbers:", numbers)
print("Square roots:", sqrt_numbers)
print("Current time:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
```

AI: ✅ **Code executed successfully!**

**Output:**

```
Original numbers: [1, 4, 9, 16, 25, 36]
Square roots: [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
Current time: 2024-11-07 14:30:25
```

```

### File Operations in Code
```

You: Run this Python code:

```python
import json
from datetime import datetime

# Create some sample data
data = {
    "timestamp": datetime.now().isoformat(),
    "user": "AI Agent User",
    "tasks": [
        {"id": 1, "task": "Learn Python", "completed": True},
        {"id": 2, "task": "Automate workflows", "completed": False}
    ]
}

# Save to JSON file
with open("tasks.json", "w") as f:
    json.dump(data, f, indent=2)

print("Tasks saved to tasks.json")
print(f"Total tasks: {len(data['tasks'])}")
```

AI: ✅ **Code executed successfully!**

**Output:**

```
Tasks saved to tasks.json
Total tasks: 2
```

```

## 🔧 Advanced Features

### Chain Multiple Operations
```

You: Take a screenshot, then open calculator, then type 25\*47
AI: I'll help you with that! Let me do each step:

📸 **Screenshot captured!**
📁 Saved to: `C:\Users\YourName\Desktop\ai_screenshot_1699123456.png`

✅ **Opened calculator**

✅ **Typed text: 25\*47**

All tasks completed successfully!

```

### System Monitoring
```

You: Show me detailed system status
AI: 💻 **System Monitor Report**

**📊 Performance:**
• CPU Usage: 18.7%
• Memory: 7.2 GB free / 16.0 GB total (55.0% used)
• Disk: 234.1 GB free / 512.0 GB total (54.3% used)

**🖥️ Display:**
• Resolution: 1920×1080
• Mouse Position: 856, 432

**🔝 Top Processes (by memory):**
• chrome.exe: 342.1 MB (5.2% CPU)
• python.exe: 128.7 MB (12.1% CPU)
• explorer.exe: 89.3 MB (0.8% CPU)
• winlogon.exe: 45.2 MB (0.1% CPU)
• svchost.exe: 38.9 MB (0.3% CPU)

```

## ❗ Error Handling Examples

### Unsafe Code
```

You: Run this code: import os; os.system("del C:\\\*")
AI: ❌ **Code execution failed:**

```
Prohibited operations: Prohibited import: os
```

```

### Invalid Coordinates
```

You: Click at -100,5000
AI: ❌ **click_coordinates failed**: Coordinate outside safe area

```

### Application Not Found
```

You: Open invalidapp
AI: ❌ **open_application**: Unknown application: invalidapp

```

## 🎯 Tips for Best Results

### 1. Be Specific
```

Good: "Take a screenshot and save it to C:/screenshots/desktop.png"
Better than: "screenshot"

```

### 2. Use Natural Language
```

Good: "Open calculator and compute 15% of 250"
Good: "Create a file called shopping_list.txt with my grocery items"

```

### 3. Chain Related Tasks
```

Good: "Take a screenshot, open paint, and paste the image"
Good: "Create a folder called 'AI Projects' and then create a file inside it"

````

### 4. Code Execution Best Practices
```python
# Good: Clear, safe code with output
import datetime
import math

# Calculate compound interest
principal = 1000
rate = 0.05
time = 10

amount = principal * (1 + rate) ** time
print(f"Investment grows from ${principal} to ${amount:.2f} in {time} years")
````

### 5. Ask for Help

```
You: What can you help me with?
You: Show me examples of what you can do
You: Help me automate my daily tasks
```

## 🔒 Security Features

The agent includes several safety features:

- **Safe Mode**: Prevents dangerous operations
- **Code Sandbox**: Restricts code execution to safe operations
- **Confirmation**: Asks before potentially destructive actions
- **Input Validation**: Validates all inputs and coordinates
- **Module Restrictions**: Only allows whitelisted Python modules

## 📞 Getting Help

If you encounter issues:

1. **Check Configuration**: Ensure your .env file has the correct API key
2. **Review Logs**: Check the logs/ directory for detailed error information
3. **Test Components**: Run `python tests/test_agent.py` to verify setup
4. **Ask the Agent**: Try "help" or "what can you do?" in the chat

## 🎮 Fun Examples

### Creative Automation

```
You: Create a file with today's date and write a haiku about computers
AI: ✅ Created file: 2024-11-07.txt

Content written:
"Silicon minds think
Electrons dance through circuits
Code becomes magic"
```

### Mathematical Exploration

```
You: Generate fibonacci numbers and create a visualization
AI: [Executes code that generates fibonacci sequence and creates a simple text chart]
```

### System Interaction

```
You: What's the current time and how long has the system been running?
AI: [Provides current time, system uptime, and performance metrics]
```

Remember: The AI Agent learns from your interactions and gets better at understanding your specific needs and preferences over time!
