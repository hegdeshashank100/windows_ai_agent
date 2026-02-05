"""
Memory Management System for Windows AI Agent
Provides context memory, conversation history, and file tracking
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    """Single memory entry"""
    timestamp: float
    entry_type: str  # 'conversation', 'action', 'file_created', 'file_opened', 'context'
    data: Dict[str, Any]
    importance: int = 1  # 1-5 scale, 5 being most important
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

@dataclass
class FileMemory:
    """Track created/opened files"""
    path: str
    filename: str
    file_type: str
    created_at: float
    last_accessed: float
    content_summary: str = ""
    user_intent: str = ""

@dataclass
class ConversationContext:
    """Current conversation context"""
    current_task: Optional[str] = None
    last_created_files: List[str] = None
    last_opened_files: List[str] = None
    pending_actions: List[str] = None
    user_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.last_created_files is None:
            self.last_created_files = []
        if self.last_opened_files is None:
            self.last_opened_files = []
        if self.pending_actions is None:
            self.pending_actions = []
        if self.user_preferences is None:
            self.user_preferences = {}

class MemoryManager:
    """Manages conversation memory, context, and file tracking"""
    
    def __init__(self, memory_file: str = "agent_memory.json", max_entries: int = 1000):
        self.memory_file = Path(memory_file)
        self.max_entries = max_entries
        self.memories: List[MemoryEntry] = []
        self.files: Dict[str, FileMemory] = {}
        self.context = ConversationContext()
        
        self._load_memory()
    
    def _load_memory(self):
        """Load memory from file"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load memories
                for entry_data in data.get('memories', []):
                    self.memories.append(MemoryEntry.from_dict(entry_data))
                
                # Load files
                for file_path, file_data in data.get('files', {}).items():
                    self.files[file_path] = FileMemory(**file_data)
                
                # Load context
                if 'context' in data:
                    self.context = ConversationContext(**data['context'])
                
                logger.info(f"Loaded {len(self.memories)} memories and {len(self.files)} file records")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
    
    def _save_memory(self):
        """Save memory to file"""
        try:
            # Trim old memories if too many
            if len(self.memories) > self.max_entries:
                # Keep the most important and recent memories
                sorted_memories = sorted(self.memories, key=lambda x: (x.importance, x.timestamp), reverse=True)
                self.memories = sorted_memories[:self.max_entries]
            
            data = {
                'memories': [memory.to_dict() for memory in self.memories],
                'files': {path: asdict(file_mem) for path, file_mem in self.files.items()},
                'context': asdict(self.context)
            }
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def add_conversation(self, user_message: str, ai_response: str, intent: Optional[str] = None):
        """Add conversation to memory"""
        self.memories.append(MemoryEntry(
            timestamp=time.time(),
            entry_type='conversation',
            data={
                'user_message': user_message,
                'ai_response': ai_response,
                'intent': intent
            },
            importance=2
        ))
        self._save_memory()
    
    def add_action(self, action_type: str, details: Dict[str, Any], importance: int = 3):
        """Add action to memory"""
        self.memories.append(MemoryEntry(
            timestamp=time.time(),
            entry_type='action',
            data={
                'action_type': action_type,
                **details
            },
            importance=importance
        ))
        
        # Update context based on action
        if action_type == 'file_created':
            file_path = details.get('path', '')
            if file_path:
                self.context.last_created_files.append(file_path)
                # Keep only last 5 files
                self.context.last_created_files = self.context.last_created_files[-5:]
        
        self._save_memory()
    
    def add_file_memory(self, file_path: str, file_type: str, user_intent: str = "", content_summary: str = ""):
        """Track a created or accessed file"""
        file_memory = FileMemory(
            path=file_path,
            filename=Path(file_path).name,
            file_type=file_type,
            created_at=time.time(),
            last_accessed=time.time(),
            content_summary=content_summary,
            user_intent=user_intent
        )
        
        self.files[file_path] = file_memory
        
        # Add to action memory too
        self.add_action('file_created', {
            'path': file_path,
            'filename': file_memory.filename,
            'type': file_type,
            'intent': user_intent
        }, importance=4)
    
    def get_recent_files(self, limit: int = 5) -> List[FileMemory]:
        """Get recently created/accessed files"""
        sorted_files = sorted(self.files.values(), key=lambda x: x.last_accessed, reverse=True)
        return sorted_files[:limit]
    
    def get_context_for_message(self, message: str) -> Dict[str, Any]:
        """Get intelligent, relevant context for processing a message"""
        context = {
            'recent_files': [],
            'recent_actions': [],
            'current_task': self.context.current_task,
            'suggestions': [],
            'conversation_history': [],
            'user_patterns': {},
            'smart_suggestions': []
        }
        
        # Get recent files with intelligent prioritization
        recent_files = self.get_recent_files(5)
        context['recent_files'] = [
            {
                'path': f.path,
                'filename': f.filename,
                'type': f.file_type,
                'intent': f.user_intent,
                'created_ago': self._format_time_ago(f.created_at),
                'relevance_score': self._calculate_file_relevance(f, message)
            } for f in recent_files
        ]
        
        # Sort by relevance
        context['recent_files'].sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Get recent actions with context
        recent_actions = [m for m in self.memories[-15:] if m.entry_type == 'action']
        context['recent_actions'] = [
            {
                'action': m.data.get('action_type'),
                'details': m.data,
                'time': m.timestamp,
                'time_ago': self._format_time_ago(m.timestamp)
            } for m in recent_actions
        ]
        
        # Get recent conversation for context
        recent_conversations = [m for m in self.memories[-10:] if m.entry_type == 'conversation']
        context['conversation_history'] = [
            {
                'user_message': m.data.get('user_message', '')[:100],
                'ai_response': m.data.get('ai_response', '')[:100],
                'intent': m.data.get('intent'),
                'time_ago': self._format_time_ago(m.timestamp)
            } for m in recent_conversations
        ]
        
        # Analyze user patterns
        context['user_patterns'] = self._analyze_user_patterns()
        
        # Generate intelligent suggestions
        context['suggestions'] = self._generate_suggestions(message)
        context['smart_suggestions'] = self._generate_smart_suggestions(message, context)
        
        return context
    
    def _calculate_file_relevance(self, file_memory: FileMemory, message: str) -> float:
        """Calculate how relevant a file is to the current message"""
        relevance = 0.0
        message_lower = message.lower()
        
        # File name mentions
        if file_memory.filename.lower() in message_lower:
            relevance += 0.8
        
        # File type mentions
        if file_memory.file_type in message_lower:
            relevance += 0.6
        
        # Recent file bonus
        import time
        age_hours = (time.time() - file_memory.created_at) / 3600
        if age_hours < 1:
            relevance += 0.5
        elif age_hours < 24:
            relevance += 0.3
        
        # Intent matching
        if any(word in message_lower for word in file_memory.user_intent.lower().split()):
            relevance += 0.4
        
        return relevance
    
    def _format_time_ago(self, timestamp: float) -> str:
        """Format timestamp as human readable 'time ago' string"""
        import time
        
        seconds_ago = time.time() - timestamp
        
        if seconds_ago < 60:
            return "just now"
        elif seconds_ago < 3600:
            minutes = int(seconds_ago / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds_ago < 86400:
            hours = int(seconds_ago / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds_ago / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def _analyze_user_patterns(self) -> Dict[str, Any]:
        """Analyze user behavior patterns from memory"""
        patterns = {
            'preferred_locations': {},
            'file_types': {},
            'common_commands': {},
            'work_hours': [],
            'productivity_score': 0.0
        }
        
        try:
            # Analyze file creation patterns
            for file_mem in self.files.values():
                # Location preferences
                location = str(Path(file_mem.path).parent)
                patterns['preferred_locations'][location] = patterns['preferred_locations'].get(location, 0) + 1
                
                # File type preferences
                patterns['file_types'][file_mem.file_type] = patterns['file_types'].get(file_mem.file_type, 0) + 1
            
            # Analyze command patterns
            for memory in self.memories[-50:]:
                if memory.entry_type == 'conversation':
                    user_msg = memory.data.get('user_message', '').lower()
                    # Extract command patterns
                    for word in ['create', 'open', 'show', 'take', 'launch']:
                        if word in user_msg:
                            patterns['common_commands'][word] = patterns['common_commands'].get(word, 0) + 1
            
            # Calculate productivity score based on recent activity
            recent_actions = len([m for m in self.memories[-20:] if m.entry_type == 'action'])
            patterns['productivity_score'] = min(1.0, recent_actions / 10.0)
            
        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")
        
        return patterns
    
    def _generate_smart_suggestions(self, message: str, context: dict) -> List[str]:
        """Generate intelligent suggestions based on full context"""
        suggestions = []
        message_lower = message.lower()
        
        # Smart file operation suggestions
        if any(word in message_lower for word in ['create', 'make', 'new']):
            patterns = context.get('user_patterns', {})
            preferred_types = patterns.get('file_types', {})
            if preferred_types:
                top_type = max(preferred_types.keys(), key=lambda k: preferred_types[k])
                suggestions.append(f"Based on your history, you often create {top_type} files")
        
        # Smart location suggestions  
        if 'file' in message_lower:
            patterns = context.get('user_patterns', {})
            preferred_locations = patterns.get('preferred_locations', {})
            if preferred_locations:
                top_location = max(preferred_locations.keys(), key=lambda k: preferred_locations[k])
                location_name = Path(top_location).name or "your usual folder"
                suggestions.append(f"You typically save files in {location_name}")
        
        # Context-aware suggestions
        if any(word in message_lower for word in ['open', 'show', 'view']) and context.get('recent_files'):
            latest_file = context['recent_files'][0]
            suggestions.append(f"You recently created {latest_file['filename']} {latest_file['created_ago']}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _generate_suggestions(self, message: str) -> List[str]:
        """Generate smart suggestions based on context and message"""
        suggestions = []
        message_lower = message.lower()
        
        # If asking to open something and we recently created files
        if any(word in message_lower for word in ['open', 'show', 'view', 'launch']) and self.context.last_created_files:
            latest_file = self.context.last_created_files[-1]
            filename = Path(latest_file).name
            suggestions.append(f"Open the recently created file: {filename}")
        
        # If asking about files
        if 'file' in message_lower and self.context.last_created_files:
            suggestions.append("Referring to recently created files")
        
        return suggestions
    
    def update_context(self, **kwargs):
        """Update conversation context"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        self._save_memory()
    
    def get_file_by_name(self, filename: str) -> Optional[FileMemory]:
        """Find file by filename (case insensitive)"""
        for file_mem in self.files.values():
            if file_mem.filename.lower() == filename.lower():
                return file_mem
        return None
    
    def clear_old_memories(self, days: int = 30):
        """Clear memories older than specified days"""
        cutoff_time = time.time() - (days * 24 * 3600)
        self.memories = [m for m in self.memories if m.timestamp > cutoff_time or m.importance >= 4]
        self._save_memory()
    
    def get_conversation_summary(self, limit: int = 5) -> str:
        """Get a summary of recent conversation"""
        recent_conversations = [
            m for m in self.memories[-limit*2:] 
            if m.entry_type == 'conversation'
        ][-limit:]
        
        summary_parts = []
        for conv in recent_conversations:
            user_msg = conv.data.get('user_message', '')[:100]
            summary_parts.append(f"User: {user_msg}")
        
        return " | ".join(summary_parts)