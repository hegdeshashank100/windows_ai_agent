"""
Modern PyQt6 Chat Window for Windows AI Agent
"""

import sys
import asyncio
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea, QLabel,
    QFrame, QSplitter, QMenuBar, QMenu, QStatusBar, QProgressBar,
    QMessageBox, QFileDialog, QSystemTrayIcon, QCheckBox, QSpinBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, 
    QEasingCurve, QRect, QSize, pyqtSlot
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QAction,
    QTextCursor, QTextCharFormat, QPainter, QPen
)

from loguru import logger
from ..core.agent import WindowsAIAgent
from ..utils.config import config


class MessageWidget(QFrame):
    """Individual message widget with styling"""
    
    def __init__(self, message: str, sender: str, timestamp: float, parent=None):
        super().__init__(parent)
        self.message = message
        self.sender = sender
        self.timestamp = timestamp
        
        self.setup_ui()
        self.apply_styling()
    
    def setup_ui(self):
        """Setup the message UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Header with sender and timestamp
        header_layout = QHBoxLayout()
        
        self.sender_label = QLabel(self.sender)
        self.sender_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        
        time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        self.time_label = QLabel(time_str)
        self.time_label.setFont(QFont("Segoe UI", 8))
        
        header_layout.addWidget(self.sender_label)
        header_layout.addStretch()
        header_layout.addWidget(self.time_label)
        
        # Message content
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont("Segoe UI", 10))
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.message_label)
    
    def apply_styling(self):
        """Apply styling based on sender"""
        if self.sender == "You":
            # User message styling
            self.setStyleSheet("""
                MessageWidget {
                    background-color: #0078d4;
                    border-radius: 12px;
                    margin: 2px 50px 2px 2px;
                }
            """)
            self.sender_label.setStyleSheet("color: white;")
            self.time_label.setStyleSheet("color: #e0e0e0;")
            self.message_label.setStyleSheet("color: white;")
        else:
            # AI message styling
            self.setStyleSheet("""
                MessageWidget {
                    background-color: #f1f1f1;
                    border-radius: 12px;
                    margin: 2px 2px 2px 50px;
                }
            """)
            self.sender_label.setStyleSheet("color: #0078d4;")
            self.time_label.setStyleSheet("color: #666666;")
            self.message_label.setStyleSheet("color: #333333;")


class ChatThread(QThread):
    """Thread for handling AI chat responses"""
    
    message_received = pyqtSignal(str)
    message_chunk = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, agent: WindowsAIAgent):
        super().__init__()
        self.agent = agent
        self.message_queue = []
        self.is_processing = False
    
    def send_message(self, message: str, context: Optional[Dict] = None):
        """Queue a message for processing"""
        self.message_queue.append((message, context))
        if not self.is_processing:
            self.start()
    
    def run(self):
        """Process queued messages"""
        self.is_processing = True
        
        while self.message_queue:
            message, context = self.message_queue.pop(0)
            
            try:
                # Create event loop for async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Get response from agent
                response = loop.run_until_complete(
                    self.agent.process_message(message, context)
                )
                
                self.message_received.emit(response)
                
            except Exception as e:
                logger.error(f"Error in chat thread: {e}")
                self.error_occurred.emit(str(e))
            finally:
                loop.close()
        
        self.is_processing = False


class TypingIndicator(QLabel):
    """Animated typing indicator"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("AI is thinking")
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet("color: #666666; font-style: italic;")
        
        self.dots = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dots)
        
    def start_animation(self):
        """Start typing animation"""
        self.timer.start(500)
        self.show()
    
    def stop_animation(self):
        """Stop typing animation"""
        self.timer.stop()
        self.hide()
    
    def update_dots(self):
        """Update dot animation"""
        self.dots = (self.dots + 1) % 4
        dots_text = "." * self.dots
        self.setText(f"AI is thinking{dots_text}")


class ChatWindow(QMainWindow):
    """Main chat window for the Windows AI Agent"""
    
    def __init__(self, agent=None):
        super().__init__()
        
        # Initialize agent - use provided agent or create new one
        self.agent = agent if agent is not None else WindowsAIAgent()
        self.chat_thread = ChatThread(self.agent)
        
        # UI Components
        self.messages_layout = None
        self.scroll_area = None
        self.input_field = None
        self.send_button = None
        self.typing_indicator = None
        
        # State
        self.conversation_history = []
        
        # Setup
        self.setup_ui()
        self.setup_connections()
        self.apply_theme()
        
        # Check agent status
        self.check_agent_status()
        
        logger.info("Chat window initialized")
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Windows AI Agent")
        self.setGeometry(100, 100, config.window_width, config.window_height)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Chat area
        self.create_chat_area(main_layout)
        
        # Input area
        self.create_input_area(main_layout)
        
        # Status bar
        self.create_status_bar()
        
        # System tray (if supported)
        self.create_system_tray()
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        save_action = QAction("Save Conversation", self)
        save_action.triggered.connect(self.save_conversation)
        file_menu.addAction(save_action)
        
        load_action = QAction("Load Conversation", self)
        load_action.triggered.connect(self.load_conversation)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        clear_action = QAction("Clear Chat", self)
        clear_action.triggered.connect(self.clear_chat)
        edit_menu.addAction(clear_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("Help", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
    
    def create_chat_area(self, parent_layout):
        """Create the chat messages area"""
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Messages container
        messages_container = QWidget()
        self.messages_layout = QVBoxLayout(messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        
        # Typing indicator
        self.typing_indicator = TypingIndicator()
        self.typing_indicator.hide()
        self.messages_layout.addWidget(self.typing_indicator)
        
        self.scroll_area.setWidget(messages_container)
        parent_layout.addWidget(self.scroll_area)
        
        # Add welcome message
        self.add_welcome_message()
    
    def create_input_area(self, parent_layout):
        """Create the input area"""
        input_frame = QFrame()
        input_frame.setFixedHeight(80)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.setMinimumHeight(40)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.send_button.setMinimumSize(80, 40)
        self.send_button.setDefault(True)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        parent_layout.addWidget(input_frame)
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = self.statusBar()
        
        # Agent status
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar for long operations
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_system_tray(self):
        """Create system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)
            
            tray_menu.addSeparator()
            
            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(QApplication.instance().quit)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_activated)
    
    def setup_connections(self):
        """Setup signal-slot connections"""
        # Input connections
        self.send_button.clicked.connect(self.send_message)
        self.input_field.returnPressed.connect(self.send_message)
        
        # Chat thread connections
        self.chat_thread.message_received.connect(self.on_message_received)
        self.chat_thread.error_occurred.connect(self.on_error_occurred)
    
    def apply_theme(self):
        """Apply application theme"""
        if config.theme == "dark":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 20px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QStatusBar {
                background-color: #1e1e1e;
                color: #cccccc;
            }
        """)
    
    def apply_light_theme(self):
        """Apply light theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
            QScrollArea {
                background-color: #f5f5f5;
                border: none;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #cccccc;
                border-radius: 20px;
                padding: 8px 16px;
                color: #000000;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
    
    def add_welcome_message(self):
        """Add welcome message to chat"""
        welcome_text = """👋 **Welcome to Windows AI Agent!**

I'm your intelligent desktop assistant. I can help you with:

• **Desktop Automation** - Click, type, take screenshots
• **File Operations** - Create, organize, and manage files  
• **System Information** - Check performance and status
• **Application Control** - Open and manage programs
• **Code Execution** - Run Python code safely
• **Natural Conversation** - Just ask me anything!

**Quick Examples:**
- "Take a screenshot"
- "Open calculator" 
- "Show system information"
- "Create a file called notes.txt"

Type your message below to get started! 🚀"""

        self.add_message(welcome_text, "AI Assistant", time.time())
    
    def add_message(self, message: str, sender: str, timestamp: float):
        """Add a message to the chat"""
        message_widget = MessageWidget(message, sender, timestamp)
        
        # Insert before typing indicator
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)
        
        # Scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)
        
        # Store in history
        self.conversation_history.append({
            "message": message,
            "sender": sender,
            "timestamp": timestamp
        })
    
    def scroll_to_bottom(self):
        """Scroll chat area to bottom"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def send_message(self):
        """Send user message"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        # Add user message
        self.add_message(text, "You", time.time())
        
        # Clear input
        self.input_field.clear()
        
        # Disable input while processing
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        
        # Show typing indicator
        self.typing_indicator.start_animation()
        
        # Update status
        self.status_label.setText("Processing...")
        
        # Send to agent
        self.chat_thread.send_message(text)
    
    @pyqtSlot(str)
    def on_message_received(self, response: str):
        """Handle received message from agent"""
        # Stop typing indicator
        self.typing_indicator.stop_animation()
        
        # Add AI response
        self.add_message(response, "AI Assistant", time.time())
        
        # Re-enable input
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        
        # Update status
        self.status_label.setText("Ready")
    
    @pyqtSlot(str)
    def on_error_occurred(self, error: str):
        """Handle errors from chat thread"""
        self.typing_indicator.stop_animation()
        
        error_msg = f"❌ **Error:** {error}"
        self.add_message(error_msg, "System", time.time())
        
        # Re-enable input
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        
        # Update status
        self.status_label.setText("Error occurred")
    
    def check_agent_status(self):
        """Check and display agent configuration status"""
        if not self.agent.is_configured:
            error_msg = """⚠️ **Configuration Required**

The AI agent is not properly configured. Please check:

1. **Google API Key** - Set GOOGLE_API_KEY in your .env file
2. **Internet Connection** - Ensure you can reach Google's servers
3. **Dependencies** - Make sure all required packages are installed

Please configure the agent and restart the application."""

            self.add_message(error_msg, "System", time.time())
            self.status_label.setText("Not configured")
        else:
            self.status_label.setText("Ready")
    
    def clear_chat(self):
        """Clear chat history"""
        reply = QMessageBox.question(
            self, 
            "Clear Chat", 
            "Are you sure you want to clear the chat history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear UI
            while self.messages_layout.count() > 1:  # Keep typing indicator
                child = self.messages_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Clear history
            self.conversation_history.clear()
            
            # Clear agent history
            if self.agent and self.agent.gemini_client:
                self.agent.gemini_client.clear_history()
            
            # Add welcome message
            self.add_welcome_message()
    
    def save_conversation(self):
        """Save conversation to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Conversation",
            f"conversation_{int(time.time())}.json",
            "JSON files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.conversation_history, f, indent=2)
                
                self.status_label.setText(f"Conversation saved to {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save conversation: {e}")
    
    def load_conversation(self):
        """Load conversation from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Conversation",
            "",
            "JSON files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                # Clear current chat
                self.clear_chat()
                
                # Load messages
                for msg in history:
                    self.add_message(
                        msg["message"],
                        msg["sender"],
                        msg["timestamp"]
                    )
                
                self.status_label.setText(f"Conversation loaded from {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load conversation: {e}")
    
    def show_settings(self):
        """Show settings dialog"""
        # TODO: Implement settings dialog
        QMessageBox.information(
            self,
            "Settings",
            "Settings dialog coming soon!\n\nFor now, edit the .env file to change configuration."
        )
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h2>Windows AI Agent</h2>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Description:</b> Advanced Windows desktop automation with AI</p>
        
        <p><b>Features:</b></p>
        <ul>
            <li>Google Gemini AI integration</li>
            <li>Desktop automation and control</li>
            <li>Natural language interaction</li>
            <li>Safe code execution sandbox</li>
            <li>Modern PyQt6 interface</li>
        </ul>
        
        <p><b>Built with:</b> Python, PyQt6, Google Gemini API</p>
        """
        
        QMessageBox.about(self, "About Windows AI Agent", about_text)
    
    def show_help(self):
        """Show help dialog"""
        if self.agent and hasattr(self.agent, 'capabilities'):
            capabilities = self.agent.get_capabilities()
            help_text = f"""
            <h3>Available Capabilities:</h3>
            <ul>
                {''.join(f'<li>{cap}</li>' for cap in capabilities)}
            </ul>
            
            <h3>Example Commands:</h3>
            <ul>
                <li>"Take a screenshot"</li>
                <li>"Open calculator"</li>
                <li>"Show system info"</li>
                <li>"Type 'Hello World'"</li>
                <li>"Click at 500,300"</li>
                <li>"Create file notes.txt"</li>
            </ul>
            """
        else:
            help_text = """
            <h3>Getting Started:</h3>
            <p>Just type naturally! The AI understands conversational requests.</p>
            
            <h3>Examples:</h3>
            <ul>
                <li>Ask questions about your computer</li>
                <li>Request automation tasks</li>
                <li>Have general conversations</li>
            </ul>
            """
        
        QMessageBox.information(self, "Help", help_text)
    
    def tray_activated(self, reason):
        """Handle system tray activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


def main(agent=None):
    """Main function to run the chat window"""
    app = QApplication(sys.argv)
    app.setApplicationName("Windows AI Agent")
    app.setApplicationVersion("1.0.0")
    
    # Set application icon (if available)
    try:
        app.setWindowIcon(QIcon("assets/icon.png"))
    except:
        pass
    
    window = ChatWindow(agent)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())