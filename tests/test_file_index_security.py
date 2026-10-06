from files.file_index import FileIndex


class DisabledEmbeddingProvider:
    is_available = False
    model = None

    def embed(self, texts):
        raise AssertionError("Sensitive-file test must not call embeddings")


def test_sensitive_files_are_never_indexed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "notes.txt").write_text(
        "ordinary project notes",
        encoding="utf-8",
    )
    (workspace / "credentials.json").write_text(
        '{"token":"TOP_SECRET_MARKER"}',
        encoding="utf-8",
    )
    (workspace / "local.properties").write_text(
        "API_KEY=TOP_SECRET_MARKER",
        encoding="utf-8",
    )
    (workspace / "client_secret.json").write_text(
        '{"client_secret":"TOP_SECRET_MARKER"}',
        encoding="utf-8",
    )
    (workspace / "private.pem").write_text(
        "TOP_SECRET_MARKER",
        encoding="utf-8",
    )

    index = FileIndex(
        db_path=tmp_path / "index.sqlite3",
        roots=[workspace],
        embedding_provider=DisabledEmbeddingProvider(),
    )

    result = index.scan()

    assert result["indexed"] == 1
    assert index.stats()["files"] == 1
    assert index.search("ordinary project notes")
    assert index.search("TOP_SECRET_MARKER") == []
    assert index.search("credentials.json") == []


def test_sensitive_path_filter_is_case_insensitive():
    assert FileIndex._is_sensitive_file.__func__(
        FileIndex,
        __import__("pathlib").Path("CREDENTIALS.JSON"),
    )
