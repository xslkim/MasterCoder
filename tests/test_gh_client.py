from mastercoder_automation.gh_client import GhClient


def test_merge_pr_falls_back_without_auto(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, gh_token=None):
        calls.append(cmd)
        if cmd[-1] == "--auto":
            raise RuntimeError(
                "命令失败：gh pr merge 24 --repo xslkim/MasterCoder --squash --delete-branch --auto\n"
                "Message: Pull request Protected branch rules not configured for this branch"
            )
        return "merged"

    monkeypatch.setattr("mastercoder_automation.gh_client._run", fake_run)

    client = GhClient(repo="xslkim/MasterCoder")
    client.merge_pr(24, gh_token="token")

    assert calls == [
        [
            "gh",
            "pr",
            "merge",
            "24",
            "--repo",
            "xslkim/MasterCoder",
            "--squash",
            "--delete-branch",
            "--auto",
        ],
        [
            "gh",
            "pr",
            "merge",
            "24",
            "--repo",
            "xslkim/MasterCoder",
            "--squash",
            "--delete-branch",
        ],
    ]


def test_merge_pr_reraises_other_errors(monkeypatch) -> None:
    def fake_run(cmd, gh_token=None):
        raise RuntimeError("命令失败：gh pr merge\npermission denied")

    monkeypatch.setattr("mastercoder_automation.gh_client._run", fake_run)

    client = GhClient(repo="xslkim/MasterCoder")
    try:
        client.merge_pr(24, gh_token="token")
    except RuntimeError as exc:
        assert "permission denied" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")