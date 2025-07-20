from PIL import Image
import arrow

from core.tiles.base import TileFile

from .base import WindyTileDownloader


__all__ = ["WindySatelliteInfraTileDownloader", "WindySatelliteVisTileDownloader"]


class WindySatelliteTileDownloader(WindyTileDownloader):
    url_template = "https://sat.windy.com/satellite/tile/deg140e/{date:YYYYMMDDHHmm}/{z}/{x}/{y}/visir.jpg?mosaic=true"


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