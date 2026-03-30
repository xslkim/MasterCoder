"""
Tests for REQ-20: Session Persistence and Recovery
"""
import json
import os
import tempfile
import shutil
from pathlib import Path

from mastercoder.session import SessionManager
from mastercoder.message_manager import MessageManager


class TestSessionSave:
    """Test session save functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_session_save_creates_file(self):
        """Test that saving a session creates a file"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        
        # Add some messages
        msg_manager = MessageManager()
        msg_manager.add_message("system", "You are MasterCoder")
        msg_manager.add_message("user", "Hello")
        msg_manager.add_message("assistant", "Hi there!")
        
        session.messages = msg_manager.get_messages()
        manager.save_session(session)
        
        # Check file exists
        session_file = self.sessions_dir / f"{session.session_id}.json"
        assert session_file.exists()
    
    def test_session_save_content_correct(self):
        """Test that saved session content is correct"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        
        # Add messages
        msg_manager = MessageManager()
        msg_manager.add_message("system", "You are MasterCoder")
        msg_manager.add_message("user", "Hello")
        msg_manager.add_message("assistant", "Hi there!")
        
        session.messages = msg_manager.get_messages()
        manager.save_session(session)
        
        # Read and verify content
        session_file = self.sessions_dir / f"{session.session_id}.json"
        with open(session_file, 'r') as f:
            data = json.load(f)
        
        assert data["session_id"] == session.session_id
        assert data["working_directory"] == "/home/user/project"
        assert data["model"] == "gpt-4o"
        assert len(data["messages"]) == 3
        assert data["messages"][0]["role"] == "system"
        assert data["messages"][1]["role"] == "user"
        assert data["messages"][2]["role"] == "assistant"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_session_save_is_atomic(self):
        """Test that session save uses atomic write (temp file + rename)"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        
        msg_manager = MessageManager()
        msg_manager.add_message("system", "You are MasterCoder")
        session.messages = msg_manager.get_messages()
        
        manager.save_session(session)
        
        # Check no temp files left
        temp_files = list(self.sessions_dir.glob("*.tmp"))
        assert len(temp_files) == 0
        
        # Check session file exists
        session_file = self.sessions_dir / f"{session.session_id}.json"
        assert session_file.exists()


class TestSessionRestore:
    """Test session restore functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_restore_session_messages_correct(self):
        """Test that restoring a session loads messages correctly"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create and save a session
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        
        msg_manager = MessageManager()
        msg_manager.add_message("system", "You are MasterCoder")
        msg_manager.add_message("user", "What is Python?")
        msg_manager.add_message("assistant", "Python is a programming language.")
        
        session.messages = msg_manager.get_messages()
        manager.save_session(session)
        
        # Restore the session
        restored = manager.load_session(session.session_id)
        
        assert restored is not None
        assert restored.session_id == session.session_id
        assert len(restored.messages) == 3
        assert restored.messages[1]["content"] == "What is Python?"
        assert restored.messages[2]["content"] == "Python is a programming language."
    
    def test_restore_nonexistent_session_returns_none(self):
        """Test that loading nonexistent session returns None"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        result = manager.load_session("nonexistent_session_id")
        assert result is None
    
    def test_restore_corrupted_json_returns_none(self):
        """Test that loading corrupted JSON returns None with clear error"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create a corrupted session file
        corrupted_file = self.sessions_dir / "20260326_143022_a1b2.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json }")
        
        result = manager.load_session("20260326_143022_a1b2")
        assert result is None


class TestResumeRecentSession:
    """Test --resume functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_resume_without_session_id_returns_most_recent(self):
        """Test that --resume without session_id returns most recent session"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create multiple sessions
        session1 = manager.create_session(
            working_directory="/home/user/project1",
            model="gpt-4o"
        )
        session1.messages = [{"role": "system", "content": "test1"}]
        manager.save_session(session1)
        
        # Wait a bit to ensure different timestamp
        import time
        time.sleep(0.01)
        
        session2 = manager.create_session(
            working_directory="/home/user/project2",
            model="deepseek"
        )
        session2.messages = [{"role": "system", "content": "test2"}]
        manager.save_session(session2)
        
        # Get most recent
        recent = manager.get_most_recent_session()
        
        assert recent is not None
        assert recent.session_id == session2.session_id
        assert recent.model == "deepseek"
    
    def test_resume_with_specific_session_id(self):
        """Test that --resume with session_id loads specific session"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        session.messages = [
            {"role": "system", "content": "You are MasterCoder"},
            {"role": "user", "content": "Hello"}
        ]
        manager.save_session(session)
        
        # Load by session_id
        loaded = manager.load_session(session.session_id)
        
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert len(loaded.messages) == 2


class TestSessionsList:
    """Test /sessions command functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sessions_list_sorted_by_updated_at_desc(self):
        """Test that session list is sorted by updated_at descending"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create sessions with different timestamps
        session1 = manager.create_session(
            working_directory="/home/user/project1",
            model="gpt-4o"
        )
        session1.messages = [{"role": "system", "content": "test"}]
        manager.save_session(session1)
        
        import time
        time.sleep(0.01)
        
        session2 = manager.create_session(
            working_directory="/home/user/project2",
            model="deepseek"
        )
        session2.messages = [{"role": "system", "content": "test"}]
        manager.save_session(session2)
        
        time.sleep(0.01)
        
        session3 = manager.create_session(
            working_directory="/home/user/project3",
            model="gpt-4o"
        )
        session3.messages = [{"role": "system", "content": "test"}]
        manager.save_session(session3)
        
        # Get sorted list
        sessions = manager.list_sessions(limit=20)
        
        assert len(sessions) == 3
        # Most recent first
        assert sessions[0].session_id == session3.session_id
        assert sessions[1].session_id == session2.session_id
        assert sessions[2].session_id == session1.session_id
    
    def test_sessions_list_limit_20(self):
        """Test that session list returns at most 20 sessions"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create 25 sessions
        for i in range(25):
            session = manager.create_session(
                working_directory=f"/home/user/project{i}",
                model="gpt-4o"
            )
            session.messages = [{"role": "system", "content": f"test{i}"}]
            manager.save_session(session)
            
            import time
            time.sleep(0.001)  # Small delay for different timestamps
        
        sessions = manager.list_sessions(limit=20)
        assert len(sessions) == 20


class TestClearGeneratesNewSession:
    """Test that /clear generates new session_id"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_clear_generates_new_session_id(self):
        """Test that clear creates a new session with different session_id"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        # Create initial session
        session1 = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        session1.messages = [
            {"role": "system", "content": "You are MasterCoder"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        manager.save_session(session1)
        
        # Clear and create new session
        session2 = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        session2.messages = [{"role": "system", "content": "You are MasterCoder"}]
        manager.save_session(session2)
        
        # Session IDs should be different
        assert session1.session_id != session2.session_id
        
        # Both files should exist
        file1 = self.sessions_dir / f"{session1.session_id}.json"
        file2 = self.sessions_dir / f"{session2.session_id}.json"
        assert file1.exists()
        assert file2.exists()


class TestSessionFileNoSensitiveInfo:
    """Test that session files don't contain sensitive information"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / ".mastercoder" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_session_file_no_api_key(self):
        """Test that session file doesn't contain API key"""
        manager = SessionManager(sessions_dir=self.sessions_dir)
        
        session = manager.create_session(
            working_directory="/home/user/project",
            model="gpt-4o"
        )
        session.messages = [{"role": "system", "content": "You are MasterCoder"}]
        manager.save_session(session)
        
        # Read file content
        session_file = self.sessions_dir / f"{session.session_id}.json"
        with open(session_file, 'r') as f:
            content = f.read()
        
        # Should not contain api_key field
        assert "api_key" not in content
        assert "MASTERCODER_API_KEY" not in content
        assert "sk-" not in content


class TestSessionsDirectoryAutoCreation:
    """Test that sessions directory is auto-created"""
    
    def test_sessions_directory_auto_created(self):
        """Test that sessions directory is created if it doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        sessions_dir = Path(temp_dir) / ".mastercoder" / "sessions"
        
        # Directory doesn't exist yet
        assert not sessions_dir.exists()
        
        # Create manager - should create directory
        SessionManager(sessions_dir=sessions_dir)
        
        # Directory should now exist
        assert sessions_dir.exists()
        
        # Cleanup
        shutil.rmtree(temp_dir)
