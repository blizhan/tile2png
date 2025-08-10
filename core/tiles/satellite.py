import numpy as np
from PIL import Image
import httpx
import arrow
from matplotlib import cm

from core.tiles.base import TileFile

from .base import TileDownloader, WindyTileDownloader

__all__ = ["WindySatelliteInfraTileDownloader", "WindySatelliteVisTileDownloader", "RainviewSatelliteInfraTileDownloader"]


def undither_visir_mosaic(gray01: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    官方 MOSAIC 去棋盘（与 radar-plus.js 中 PREPROCESS+MOSAIC 一致）:
    - 输入: 灰度 mosaic（上半可见光 VIS，下半红外 IR），0..1
    - 输出: (vis01, ir01) 各为 [H/2, W]，已按“坐标奇偶棋盘”取反校正
    """
    H, W = gray01.shape
    assert H % 2 == 0, "mosaic tile height must be even"
    half = H // 2
    vis_raw = gray01[:half, :]       # 上半可见光
    ir_raw  = gray01[half:, :]       # 下半红外
    # 计算 16×16 归一化网格上的“棋盘奇偶”
    # 与着色器等价：parity = (floor(u*16) + floor(v*16)) % 2
    # 注意：v 的量纲是整张 mosaic 的 H，而不是半幅的 H/2
    x = np.arange(W, dtype=np.float32)
    y_top = np.arange(half, dtype=np.float32)                  # 0..H/2-1
    y_bot = y_top + half                                       # H/2..H-1
    # 像素中心 -> 归一化坐标再乘 16，做 floor
    xbin = np.floor((x + 0.5) * 16.0 / W).astype(np.int32)     # [W]
    ybin_top = np.floor((y_top + 0.5) * 16.0 / H).astype(np.int32)   # [H/2]
    ybin_bot = np.floor((y_bot + 0.5) * 16.0 / H).astype(np.int32)   # [H/2]
    # 扩展为 [H/2, W]
    xbin2d = np.broadcast_to(xbin, (half, W))
    parity_even_top = ((xbin2d + ybin_top[:, None]) & 1) == 0
    parity_even_bot = ((xbin2d + ybin_bot[:, None]) & 1) == 0
    # 官方门限：仅在 (ir>0 || vis>0) 时才做取反
    gate = (vis_raw > 0.0) | (ir_raw > 0.0)
    # MOSAIC 规则（与 GLSL 对应）：
    # - VIS: parity_even ==> 取反
    # - IR : parity_odd  ==> 取反  <=> 非 parity_even
    vis01 = np.where(gate & parity_even_top, 1.0 - vis_raw, vis_raw)
    ir01  = np.where(gate & (~parity_even_bot), 1.0 - ir_raw,  ir_raw)
    # 裁剪数值范围
    vis01 = np.clip(vis01, 0.0, 1.0).astype(np.float32)
    ir01  = np.clip(ir01,  0.0, 1.0).astype(np.float32)
    return vis01, ir01


class WindySatelliteTileDownloader(WindyTileDownloader):
    url_template = "https://sat.windy.com/satellite{archive}/tile/deg140e/{date:YYYYMMDDHHmm}/{z}/{x}/{y}/visir.jpg?mosaic=true"

    def _parse_value(self, merged_pic: Image.Image) -> Image.Image:
        return merged_pic
        # data = np.array(merged_pic, dtype=np.uint8)[..., 0]
        # data = np.where((data >= 128), 255 - data, data)
        # return Image.fromarray(data)
        data = np.array(merged_pic, dtype=np.float32)[..., 0] / 255.0
        t_max = 321.25
        t_min = 182.75
        cmap_name = 'turbo'
        gamma = 1.1
        temp_k = t_min + data * (t_max - t_min)
        v_norm = (temp_k - t_min) / (t_max - t_min)  # 与 p 等价，但写出公式更直观
        colored = lut_colorize(v_norm, cmap_name=cmap_name)
        # colored = apply_gamma(ir_colored, gamma=gamma)
        print(colored.min(), colored.max())
        return Image.fromarray((colored * 255).astype(np.uint8))


class WindySatelliteInfraTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        data = np.array(img, dtype=np.float32) / 255.0
        vis01, ir01 = undither_visir_mosaic(data)
        print(vis01.min(), vis01.max())
        print(ir01.min(), ir01.max())
        return Image.fromarray((ir01 * 255).astype(np.uint8))
        return img.crop((0, 256, 256, 512))


class WindySatelliteVisTileDownloader(WindySatelliteTileDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        img = Image.open(tile.file)
        data = np.array(img, dtype=np.float32) / 255.0
        vis01, ir01 = undither_visir_mosaic(data)
        print(vis01.min(), vis01.max())
        print(ir01.min(), ir01.max())
        return Image.fromarray((vis01 * 255).astype(np.uint8))
        return img.crop((0, 0, 256, 256))


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
