import unittest
from musicsort.utils.filename_cleaner import clean_filename, split_artist_title

class TestFilenameCleaner(unittest.TestCase):
    def test_leading_track_numbers(self):
        self.assertEqual(clean_filename("01 - Brown Munde.mp3"), "Brown Munde")
        self.assertEqual(clean_filename("001 Song Name.flac"), "Song Name")
        self.assertEqual(clean_filename("12. Track Name.wav"), "Track Name")

    def test_middle_track_segments(self):
        # Middle track number parsing: Atif_Aslam_Greatest_Hits_09_Bheegi_Yaadein
        self.assertEqual(
            clean_filename("Atif_Aslam_Greatest_Hits_09_Bheegi_Yaadein.flac"),
            "Bheegi Yaadein"
        )
        self.assertEqual(
            clean_filename("Linkin_Park_Meteora_03_Somewhere_I_Belong.mp3"),
            "Somewhere I Belong"
        )

    def test_version_bracket_preservation(self):
        # Versions in parentheses/brackets should be cleaned and appended back
        self.assertEqual(
            clean_filename("01 - Song Name (Remastered 2020).mp3"),
            "Song Name (Remastered 2020)"
        )
        self.assertEqual(
            clean_filename("Kesariya [Acoustic Live].wav"),
            "Kesariya [Acoustic Live]"
        )

    def test_collaborations_standardization(self):
        # ft., featuring, ft, w/ should map to feat.
        self.assertEqual(
            clean_filename("Eminem ft. Rihanna - Love The Way You Lie.mp3"),
            "Eminem feat. Rihanna - Love the Way You Lie"
        )
        self.assertEqual(
            clean_filename("Song Name featuring Kanye West.flac"),
            "Song Name feat. Kanye West"
        )

    def test_acronym_casing_preservation(self):
        # Acronyms (fully capitalized, length >= 2) must remain uppercase
        self.assertEqual(
            clean_filename("STFU - DESIRES (prod. by Drake).mp3"),
            "STFU - DESIRES (prod. by Drake)"
        )
        self.assertEqual(
            clean_filename("USA Anthem.mp3"),
            "USA Anthem"
        )

    def test_split_artist_title(self):
        self.assertEqual(
            split_artist_title("Linkin Park - In The End"),
            ("Linkin Park", "In The End")
        )
        self.assertEqual(
            split_artist_title("Brown Munde"),
            ("", "Brown Munde")
        )

if __name__ == "__main__":
    unittest.main()
