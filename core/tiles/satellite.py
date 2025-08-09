import numpy as np
from PIL import Image

from core.tiles.base import TileFile

from .base import WindyTileDownloader

__all__ = ["WindySatelliteInfraTileDownloader", "WindySatelliteVisTileDownloader"]


class WindySatelliteTileDownloader(WindyTileDownloader):
    url_template = "https://sat.windy.com/satellite{archive}/tile/deg9e/{date:YYYYMMDDHHmm}/{z}/{x}/{y}/visir.jpg?mosaic=true"

    def _parse_value(self, merged_pic: Image.Image) -> Image.Image:
        data = np.array(merged_pic, dtype=np.uint8)[..., 0]
        data = np.where((data >= 128), 255 - data, data)
        return Image.fromarray(data)


class WindySatelliteInfraTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        return img.crop((0, 256, 256, 512))


class WindySatelliteVisTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        return img.crop((0, 0, 256, 256))
