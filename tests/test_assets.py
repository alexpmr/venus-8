import unittest
from pathlib import Path
from PIL import Image

from scripts.create_icon import draw_icon
from venus8.mockup_ui import ARTWORK_W, ART_H, reference_image_path


class TestOfficialArtwork(unittest.TestCase):
    def test_original_artwork_is_packaged_not_thumbnail(self):
        artwork=Path("docs/venus-8-mockup.png")
        self.assertTrue(artwork.is_file(),"Original artwork missing")
        with Image.open(artwork) as image:
            self.assertEqual(image.size,(ARTWORK_W,ART_H))
        self.assertEqual(reference_image_path().name, "venus-8-mockup.png")

    def test_custom_synthesizer_taskbar_icon(self):
        size=256
        icon=draw_icon(size)
        self.assertEqual(icon.size,(size,size))
        # Ivory keyboard area, given in 512px drawing units and scaled down.
        self.assertGreater(icon.getpixel((size*256//512,size*400//512))[3],0)

if __name__ == "__main__":
    unittest.main()
