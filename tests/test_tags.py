import unittest

from bot.tags import extract_tags


class ExtractTagsTest(unittest.TestCase):
    def test_single_tag_removed_from_body(self):
        self.assertEqual(
            extract_tags("купить хлеб #продукты"),
            ("купить хлеб", ["продукты"]),
        )

    def test_multiple_tags(self):
        self.assertEqual(
            extract_tags("купить хлеб #продукты #сегодня"),
            ("купить хлеб", ["продукты", "сегодня"]),
        )

    def test_lowercases_tags(self):
        self.assertEqual(
            extract_tags("собрание #Важное"),
            ("собрание", ["важное"]),
        )

    def test_dedupes_tags_preserving_order(self):
        self.assertEqual(
            extract_tags("x #a #b #a"),
            ("x", ["a", "b"]),
        )

    def test_tag_adjacent_to_punctuation(self):
        self.assertEqual(
            extract_tags("купить #хлеб, и молоко"),
            ("купить , и молоко", ["хлеб"]),
        )

    def test_cyrillic_and_hyphen(self):
        self.assertEqual(
            extract_tags("#долго-срок задача"),
            ("задача", ["долго-срок"]),
        )

    def test_no_tags_leaves_text_unchanged(self):
        self.assertEqual(
            extract_tags("просто заметка без тегов"),
            ("просто заметка без тегов", []),
        )


if __name__ == "__main__":
    unittest.main()