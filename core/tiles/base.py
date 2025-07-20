import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import arrow
import httpx
import trio
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ..config import header
from ..utils.xyz import GoogleXYZTile, Tile

max_concurrency = 10

__all__ = ["TileDownloader", "TileFile", "WindyTileDownloader"]


@dataclass
class TileFile:
    url: str
    tile: Tile
    file: Path = None


class TileDownloader(object):
    output_format = "tile_{x}_{y}.{format}"
    url_template = None

    def __init__(self, lat_bounds: list[float], lon_bounds: list[float], zoom: int):
        top_left = (lat_bounds[1], lon_bounds[0])
        right_bottom = (lat_bounds[0], lon_bounds[1])
        if self.url_template is None:
            raise NotImplementedError("url_template is not set")
        suffix = Path(self.url_template).suffix
        try:
            self.format = re.match(".(png|webp|jpg)?", suffix).group(1)
        except AttributeError:
            self.format = "png"
        self.zoom = zoom
        self.tile_xy = GoogleXYZTile(zoom=zoom)
        self.start_x, self.start_y, self.end_x, self.end_y = self.tile_xy.get_xy_range(
            top_left[0], top_left[1], right_bottom[0], right_bottom[1]
        )
        self.tiles = list(self.get_urls(top_left, right_bottom))
        self.len_y = self.end_y - self.start_y + 1
        self.len_x = len(self.tiles) // self.len_y

    def download(self, folder, **kwargs):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        for t in self.tiles:
            t.file = Path(folder) / self.output_format.format(
                x=t.tile.x, y=t.tile.y, format=self.format
            )

        results = trio.run(self._download_tiles_httpx, self.tiles)
        return results

    async def _download_tiles_httpx(self, tiles: list[TileFile]):
        limiter = trio.CapacityLimiter(max_concurrency)
        async with httpx.AsyncClient() as client:
            async with trio.open_nursery() as nursery:
                for t in tiles:
                    nursery.start_soon(self._request_httpx, limiter, client, t)
        return tiles

    def get_urls(
        self, top_left: tuple[float, float], right_bottom: tuple[float, float]
    ):
        for tile in self.tile_xy.iter_tile_xy(
            top_left[0], top_left[1], right_bottom[0], right_bottom[1]
        ):
            yield TileFile(url=self._get_url(tile.x, tile.y), tile=tile)

    async def _request_httpx(
        self, limiter: trio.CapacityLimiter, client: httpx.AsyncClient, t: TileFile
    ) -> TileFile:
        async with limiter:
            try:
                response = await client.get(t.url, headers=header, timeout=10)
                response.raise_for_status()
                with t.file.open("wb") as f:
                    f.write(response.content)
            except httpx.HTTPStatusError:
                t.file = None
        return t

    def _get_url(self, x, y, **kwargs):
        return self.url_template.format(z=self.zoom, x=x, y=y, **kwargs)

    def merge(self, filename) -> str:
        merged_pic, metaInfo = self._merge_tiles()
        merged_pic = merged_pic.convert("RGBA")
        merged_pic.save(filename, pnginfo=metaInfo)
        return filename

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        return Image.open(tile.file)

    def _merge_tiles(self):
        merged_pic = Image.new("RGBA", (self.len_x * 256, self.len_y * 256))

        for i, tile in enumerate(self.tiles):
            if tile.file is None or not tile.file.exists():
                continue
            tile_img = self._process_single_tile(tile)
            y, x = tile.tile.y - self.start_y, tile.tile.x - self.start_x
            merged_pic.paste(tile_img, (x * 256, y * 256))

        top_left = self.tile_xy.get_tile_lat_lng(self.start_x, self.start_y)
        bottom_right = self.tile_xy.get_tile_lat_lng(self.end_x + 1, self.end_y + 1)
        metaInfo = {
            "lat_bounds": [top_left[0], bottom_right[0]],
            "lng_bounds": [top_left[1], bottom_right[1]],
            "zoom": self.zoom,
            "projection": "EPSG:3857",
        }
        pnginfo = PngInfo()
        for k, v in metaInfo.items():
            pnginfo.add_text(k, json.dumps(v))
        return merged_pic, pnginfo

    def to_png(self, output: str, tmp_dir: str = None) -> str | None:
        if tmp_dir is None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                self.download(tmp_dir)
                return self.merge(output)
        else:
            self.download(tmp_dir)
            return self.merge(output)


class WindyTileDownloader(TileDownloader):
    url_template = None

    def __init__(self, date: arrow.Arrow, *args, **kwargs):
        self.date = date
        self.url_template = self.url_template.format(
            date=date, x="{x}", y="{y}", z="{z}"
        )
        print(self.url_template)
        super().__init__(*args, **kwargs)
