import numpy as np
from PIL import Image
import httpx
import arrow
from matplotlib import cm

from core.tiles.base import TileFile

from .base import TileDownloader, WindyTileDownloader

__all__ = ["WindySatelliteInfraTileDownloader", "WindySatelliteVisTileDownloader", "RainviewSatelliteInfraTileDownloader"]


def undither_visir_mosaic(gray01: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    H, W = gray01.shape
    assert H % 2 == 0
    half = H // 2
    xNorm = (np.arange(W, dtype=np.float32) + 0.5) / W
    yTopNorm = (np.arange(half, dtype=np.float32) + 0.5) / half
    yBotNorm = (np.arange(half, dtype=np.float32) + 0.5 + half) / half
    xbin2d = np.broadcast_to(np.floor(xNorm * 16.0).astype(np.int32), (half, W))
    ybin_top2d = np.floor(yTopNorm[:, None] * 16.0).astype(np.int32)
    ybin_bot2d = np.floor(yBotNorm[:, None] * 16.0).astype(np.int32)
    parity_even_top = ((xbin2d + ybin_top2d) & 1) == 0
    parity_even_bot = ((xbin2d + ybin_bot2d) & 1) == 0
    vis_raw = gray01[:half, :]
    ir_raw  = gray01[half:, :]
    gate = (vis_raw > 0.0) | (ir_raw > 0.0)
    vis01 = np.where(gate & parity_even_top, 1.0 - vis_raw, vis_raw)
    ir01  = np.where(gate & (~parity_even_bot), 1.0 - ir_raw,  ir_raw)
    return vis01.astype(np.float32), ir01.astype(np.float32)


class WindySatelliteTileDownloader(WindyTileDownloader):
    url_template = "https://sat.windy.com/satellite{archive}/tile/deg140e/{date:YYYYMMDDHHmm}/{z}/{x}/{y}/visir.jpg?mosaic=true"

    def _parse_value(self, merged_pic: Image.Image) -> Image.Image:
        return merged_pic


class WindySatelliteInfraTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        data = np.array(img, dtype=np.float32) / 255.0
        _, ir01 = undither_visir_mosaic(data)
        return Image.fromarray((ir01 * 255).astype(np.uint8))


class WindySatelliteVisTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        data = np.array(img, dtype=np.float32) / 255.0
        vis01, _ = undither_visir_mosaic(data)
        return Image.fromarray((vis01 * 255).astype(np.uint8))


class RainviewSatelliteInfraTileDownloader(TileDownloader):
    api_url = "https://api.rainviewer.com/public/weather-maps.json"

    def __init__(self, date: arrow.Arrow, *args, **kwargs):
        self.timestamp = int(date.timestamp()/600) * 600
        self.date = arrow.get(self.timestamp)
        self._pre_init(date=self.date, **kwargs)
        print(self.url_template)
        super().__init__(*args, **kwargs)

    def _pre_init(self, date: arrow.Arrow, **kwargs):
        url_data = self._api()
        host = url_data["host"]
        satellites = url_data["satellite"]['infrared']
        ts = int(date.timestamp()/600) * 600
        for i in satellites:
            if i['time'] >= ts:
                self.url_template = f"{host}{i['path']}" + '/256/{z}/{x}/{y}/0/0_0.webp'
                break
        if not self.url_template:
            raise ValueError(f"No satellite found for date {date}")

    def _api(self):
        response = httpx.get(self.api_url)
        response.raise_for_status()
        return response.json()

    def _parse_value(self, merged_pic: Image.Image) -> Image.Image:
        return merged_pic
