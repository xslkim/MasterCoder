"""
Session persistence and recovery module for REQ-20
"""
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any


class Session:
    """Represents a conversation session"""
    
    def __init__(
        self,
        session_id: str,
        created_at: str,
        updated_at: str,
        working_directory: str,
        model: str,
        messages: Optional[List[Dict[str, Any]]] = None
    ):
        self.session_id = session_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.working_directory = working_directory
        self.model = model
        self.messages = messages or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "working_directory": self.working_directory,
            "model": self.model,
            "messages": self.messages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary"""
        return cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            working_directory=data["working_directory"],
            model=data["model"],
            messages=data.get("messages", [])
        )


class SessionManager:
    """Manages session persistence and recovery"""
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize session manager.
        
        Args:
            sessions_dir: Directory to store session files. If None, uses default.
        """
        if sessions_dir is None:
            home_dir = Path.home()
            self.sessions_dir = home_dir / ".mastercoder" / "sessions"
        else:
            self.sessions_dir = sessions_dir
        
        # Auto-create sessions directory
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID.
        Format: <timestamp>_<4-digit random hex>
        Example: 20260326_143022_a1b2
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_hex = secrets.token_hex(2)  # 4 hex characters
        return f"{timestamp}_{random_hex}"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def create_session(
        self,
        working_directory: str,
        model: str
    ) -> Session:
        """
        Create a new session.
        
        Args:
            working_directory: Current working directory
            model: Model name being used
            
        Returns:
            Newly created Session object
        """
        now = self._get_timestamp()
        session_id = self._generate_session_id()
        
        return Session(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            working_directory=working_directory,
            model=model,
            messages=[]
        )
    
    def save_session(self, session: Session) -> bool:
        """
        Save session to file using atomic write (temp file + rename).
        
        Args:
            session: Session object to save
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            session.updated_at = self._get_timestamp()
            
            session_file = self.sessions_dir / f"{session.session_id}.json"
            temp_file = self.sessions_dir / f"{session.session_id}.json.tmp"
            
            # Write to temp file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.rename(session_file)
            
            return True
        except Exception:
            return False
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load session from file.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Session object if found and valid, None otherwise
        """
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError, IOError):
            return None
    
    def get_most_recent_session(self) -> Optional[Session]:
        """
        Get the most recently updated session.
        
        Returns:
            Most recent Session object, or None if no sessions exist
        """
        sessions = self.list_sessions(limit=1)
        return sessions[0] if sessions else None
    
    def list_sessions(self, limit: int = 20) -> List[Session]:
        """
        List sessions sorted by updated_at descending.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of Session objects, most recent first
        """
        sessions = []
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = Session.from_dict(data)
                    sessions.append(session)
                except (json.JSONDecodeError, KeyError, IOError):
                    # Skip corrupted files
                    continue
            
            # Sort by updated_at descending
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            
            # Apply limit
            return sessions[:limit]
        except Exception:
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except Exception:
            return False
