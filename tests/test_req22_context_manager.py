"""REQ-22：上下文管理手动添加文件验收测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mastercoder.config import Config
from mastercoder.conversation import ConversationLoop


def test_handle_user_input_injects_file_content_before_api_call(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
	readme = tmp_path / "README.md"
	readme.write_text("# Project Title", encoding="utf-8")
	monkeypatch.setenv("MASTERCODER_API_KEY", "sk-test")

	conversation = ConversationLoop(Config(working_dir=tmp_path))
	captured: dict[str, list[dict[str, str]]] = {}

	def fake_stream_chat(messages: list[dict[str, str]]):
		captured["messages"] = messages
		yield "summary"

	monkeypatch.setattr(conversation._api_client, "stream_chat", fake_stream_chat)

	conversation._handle_user_input("@README.md 概括一下这个文件")

	user_message = captured["messages"][-1]["content"]
	assert "概括一下这个文件" in user_message
	assert "File: README.md" in user_message
	assert "# Project Title" in user_message
	assert "@README.md" not in user_message
	assert "summary" in capsys.readouterr().out


def test_handle_user_input_injects_multiple_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
	(tmp_path / "a.py").write_text("def a():\n    return 'a'\n", encoding="utf-8")
	(tmp_path / "b.py").write_text("def b():\n    return 'b'\n", encoding="utf-8")
	monkeypatch.setenv("MASTERCODER_API_KEY", "sk-test")

	conversation = ConversationLoop(Config(working_dir=tmp_path))
	captured: dict[str, list[dict[str, str]]] = {}

	def fake_stream_chat(messages: list[dict[str, str]]):
		captured["messages"] = messages
		if False:
			yield ""

	monkeypatch.setattr(conversation._api_client, "stream_chat", fake_stream_chat)

	conversation._handle_user_input("@a.py @b.py 对比差异")

	user_message = captured["messages"][-1]["content"]
	assert "对比差异" in user_message
	assert "File: a.py" in user_message
	assert "File: b.py" in user_message


def test_handle_user_input_directory_reference_reports_error(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	(tmp_path / "docs").mkdir()
	monkeypatch.setenv("MASTERCODER_API_KEY", "sk-test")

	conversation = ConversationLoop(Config(working_dir=tmp_path))
	captured: dict[str, list[dict[str, str]]] = {}

	def fake_stream_chat(messages: list[dict[str, str]]):
		captured["messages"] = messages
		if False:
			yield ""

	monkeypatch.setattr(conversation._api_client, "stream_chat", fake_stream_chat)

	conversation._handle_user_input("@docs 这个目录里有什么")

	user_message = captured["messages"][-1]["content"]
	assert "Directory references are not supported" in user_message


def test_handle_user_input_without_references_is_unchanged(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	monkeypatch.setenv("MASTERCODER_API_KEY", "sk-test")

	conversation = ConversationLoop(Config(working_dir=tmp_path))
	captured: dict[str, list[dict[str, str]]] = {}

	def fake_stream_chat(messages: list[dict[str, str]]):
		captured["messages"] = messages
		if False:
			yield ""

	monkeypatch.setattr(conversation._api_client, "stream_chat", fake_stream_chat)

	conversation._handle_user_input("普通消息")

	assert captured["messages"][-1]["content"] == "普通消息"
