import hashlib
import io
import unittest

from backend.file_hashing import FileTooLargeError, hash_bytes, hash_stream
from backend.security_utils import human_size, identify_hash


class FileHashingTests(unittest.TestCase):
    def test_known_vectors(self):
        r = hash_bytes(b"abc")
        self.assertEqual(r.sha256, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(r.sha1, "a9993e364706816aba3e25717850c26c9cd0d89d")
        self.assertEqual(r.md5, "900150983cd24fb0d6963f7d28e17f72")
        self.assertEqual(r.size, 3)

    def test_empty(self):
        self.assertEqual(hash_bytes(b"").sha256, hashlib.sha256(b"").hexdigest())

    def test_multi_chunk_matches_hashlib(self):
        data = b"x" * (3 * 1024 * 1024 + 17)
        self.assertEqual(hash_stream(io.BytesIO(data)).sha256, hashlib.sha256(data).hexdigest())

    def test_size_limit(self):
        with self.assertRaises(FileTooLargeError):
            hash_bytes(b"x" * 100, max_bytes=50)

    def test_identify_hash(self):
        self.assertEqual(identify_hash("a" * 32), "MD5")
        self.assertEqual(identify_hash("A" * 40), "SHA-1")
        self.assertEqual(identify_hash("0" * 64), "SHA-256")
        self.assertIsNone(identify_hash("g" * 64))
        self.assertIsNone(identify_hash("abc"))
        self.assertIsNone(identify_hash(""))

    def test_human_size(self):
        self.assertEqual(human_size(512), "512 B")
        self.assertEqual(human_size(2048), "2.0 KB")


if __name__ == "__main__":
    unittest.main()
