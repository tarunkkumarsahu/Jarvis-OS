import tempfile
import unittest
from pathlib import Path

from files.file_index import FileIndex


class DisabledEmbeddingProvider:
    is_available = False
    model = None

    def embed(self, texts):
        raise AssertionError("Sensitive-file test must not call embeddings")


class FileIndexSecurityTests(unittest.TestCase):
    def test_sensitive_files_are_never_indexed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "workspace"
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
                db_path=root / "index.sqlite3",
                roots=[workspace],
                embedding_provider=DisabledEmbeddingProvider(),
            )

            result = index.scan()

            self.assertEqual(result["indexed"], 1)
            self.assertEqual(index.stats()["files"], 1)
            self.assertTrue(index.search("ordinary project notes"))
            self.assertEqual(index.search("TOP_SECRET_MARKER"), [])
            self.assertEqual(index.search("credentials.json"), [])

    def test_sensitive_path_filter_is_case_insensitive(self):
        self.assertTrue(
            FileIndex._is_sensitive_file(Path("CREDENTIALS.JSON"))
        )
        self.assertTrue(
            FileIndex._is_sensitive_file(Path("LOCAL.PROPERTIES"))
        )
        self.assertTrue(
            FileIndex._is_sensitive_file(Path("private.PEM"))
        )


if __name__ == "__main__":
    unittest.main()
