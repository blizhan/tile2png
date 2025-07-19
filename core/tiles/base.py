import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import trio
from PIL import Image

from core.config import header
from core.utils.xyz import GoogleXYZTile, Tile

max_concurrency = 10


@dataclass
class TileFile:
    url: str
    tile: Tile
    file: Path = None


class TileDownloader(object):
    output_format = "tile_{x}_{y}.{format}"
    url_template = "https://cdn.rainviewer.com/v2/radar/1752904200/256/{z}/{x}/{y}/255/1_1_1_0.webp"
    url_template = "https://rdr.windy.com/radar2/composite/2025/07/19/1325/{z}/{x}/{y}/reflectivity.png?multichannel=true&maxt=20250719132143"

    def __init__(self, top_left, right_bottom, zoom: int):
        suffix = Path(self.url_template).suffix
        self.format = re.match(".(png|webp|jpg)?", suffix).group(1)
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

    def merge(self, filename):
        merged_pic = self._merge_tiles()
        merged_pic = merged_pic.convert("RGBA")
        merged_pic.save(filename)

    def _merge_tiles(self):
        print(self.len_x, self.len_y)
        merged_pic = Image.new("RGBA", (self.len_x * 256, self.len_y * 256))

        for i, tile in enumerate(self.tiles):
            if tile.file is None or not tile.file.exists():
                continue
            with Image.open(tile.file) as tile_img:
                y, x = tile.tile.y - self.start_y, tile.tile.x - self.start_x
                merged_pic.paste(tile_img, (x * 256, y * 256))

        top_left = self.tile_xy.get_tile_lat_lng(self.start_x, self.start_y)
        bottom_right = self.tile_xy.get_tile_lat_lng(self.end_x + 1, self.end_y + 1)
        print(top_left, bottom_right)
        print(self.start_x, self.start_y, self.end_x, self.end_y)
        return merged_pic


if __name__ == "__main__":
    tile = TileDownloader(
        (41.87501349541372, 113.78232363984644),
        (37.74276146796519, 119.16156979277075),
        zoom=7,
    )
    with tempfile.TemporaryDirectory(dir="./test/") as tmp_dir:
        tile.download(tmp_dir)
        print(tmp_dir)
        tile.merge("test/merged.png")
