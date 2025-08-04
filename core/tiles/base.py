import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import asyncio
import arrow
import httpx
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ..config import header
from ..utils.xyz import GoogleXYZTile, Tile
from ..utils.proj import get_mymx, get_latlng, crop_image

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
    tilesize = 256

    def __init__(
        self,
        zoom: int,
        lat_bounds: list[float] = [],
        lon_bounds: list[float] = [],
        center_latlng: tuple[float, float] = None,
        radius: int = 0,
        parse: bool = True,
        crop: bool = True,
    ):
        if center_latlng:
            center_lat, center_lon = center_latlng
            center_my, center_mx = get_mymx(center_lat, center_lon)
            top_left_latlng = get_latlng(center_my + radius, center_mx - radius)
            bottom_right_latlng = get_latlng(center_my - radius, center_mx + radius)
            lat_bounds = [bottom_right_latlng[0], top_left_latlng[0]]
            lon_bounds = [top_left_latlng[1], bottom_right_latlng[1]]
            print(lat_bounds, lon_bounds)

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
        self.crop = crop

        top_left_latlng = self.tile_xy.get_tile_lat_lng(self.start_x, self.start_y)
        bottom_right_latlng = self.tile_xy.get_tile_lat_lng(
            self.end_x + 1, self.end_y + 1
        )

        top_left_mymx = get_mymx(*top_left_latlng)
        bottom_right_mymx = get_mymx(*bottom_right_latlng)

        self.tile_lat_bounds = [bottom_right_latlng[0], top_left_latlng[0]]
        self.tile_lng_bounds = [top_left_latlng[1], bottom_right_latlng[1]]
        self.tile_my_bounds = [bottom_right_mymx[0], top_left_mymx[0]]
        self.tile_mx_bounds = [top_left_mymx[1], bottom_right_mymx[1]]
        if self.crop:
            top_left_latlng = (lat_bounds[1], lon_bounds[0])
            bottom_right_latlng = (lat_bounds[0], lon_bounds[1])
            top_left_mymx = get_mymx(*top_left_latlng)
            bottom_right_mymx = get_mymx(*bottom_right_latlng)
        self.real_lat_bounds = [bottom_right_latlng[0], top_left_latlng[0]]
        self.real_lng_bounds = [top_left_latlng[1], bottom_right_latlng[1]]
        self.real_my_bounds = [bottom_right_mymx[0], top_left_mymx[0]]
        self.real_mx_bounds = [top_left_mymx[1], bottom_right_mymx[1]]
        print(self.real_my_bounds, self.real_mx_bounds)
        self.success_count = 0
        self.parse = parse
        self.meta_info = {}
        self.max_retries = 3
        self.retry_delay = 1
        self.image = None
        self.timeout = 20



    def download(self, folder, **kwargs):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        for t in self.tiles:
            t.file = Path(folder) / self.output_format.format(
                x=t.tile.x, y=t.tile.y, format=self.format
            )

        results = asyncio.run(self._download_tiles_httpx(self.tiles))
        for t in results:
            if t.file is not None:
                self.success_count += 1
        print(f"success_count: {self.success_count} total: {len(self.tiles)}")
        return results

    async def _download_tiles_httpx(self, tiles: list[TileFile]):
        semaphore = asyncio.Semaphore(max_concurrency)
        async with httpx.AsyncClient() as client:
            tasks = [self._request_httpx(semaphore, client, t) for t in tiles]
            await asyncio.gather(*tasks, return_exceptions=True)
        return tiles

    def get_urls(
        self, top_left: tuple[float, float], right_bottom: tuple[float, float]
    ):
        for tile in self.tile_xy.iter_tile_xy(
            top_left[0], top_left[1], right_bottom[0], right_bottom[1]
        ):
            yield TileFile(url=self._get_url(tile.x, tile.y), tile=tile)

    async def _request_httpx(
        self, semaphore: asyncio.Semaphore, client: httpx.AsyncClient, t: TileFile
    ) -> TileFile:
        attempt = 0
        while attempt < self.max_retries:
            async with semaphore:
                try:
                    response = await client.get(t.url, headers=header, timeout=self.timeout)
                    response.raise_for_status()
                    with t.file.open("wb") as f:
                        f.write(response.content)
                    return t
                except (
                    httpx.HTTPStatusError,
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.ReadError,
                ):
                    attempt += 1
                    await asyncio.sleep(self.retry_delay)
        t.file = None
        return t

    def _get_url(self, x, y, **kwargs):
        return self.url_template.format(z=self.zoom, x=x, y=y, **kwargs)

    def merge(self, filename) -> str:
        merged_pic, metaInfo = self._merge_tiles()
        merged_pic.save(filename, pnginfo=metaInfo)
        print(filename)
        return filename

    def _process_single_tile(self, tile: TileFile) -> Image.Image:
        return Image.open(tile.file)
    
    def _parse_value(self, merged_pic: Image.Image) -> Image.Image:
        raise NotImplementedError("Not implemented")

    def _merge_tiles(self):
        merged_pic = Image.new("RGBA", (self.len_x * self.tilesize, self.len_y * self.tilesize))

        for i, tile in enumerate(self.tiles):
            if tile.file is None or not tile.file.exists():
                continue
            tile_img = self._process_single_tile(tile)
            y, x = tile.tile.y - self.start_y, tile.tile.x - self.start_x
            merged_pic.paste(tile_img, (x * self.tilesize, y * self.tilesize))

        if self.parse:
            merged_pic = self._parse_value(merged_pic)
        
        if self.crop:
            merged_pic = self._crop(merged_pic, self.real_my_bounds, self.real_mx_bounds)

        self.image = merged_pic

        self.meta_info.update({
            "lat_bounds": self.real_lat_bounds,
            "lng_bounds": self.real_lng_bounds,
            "zoom": self.zoom,
            "projection": "EPSG:3857",
            "my_bounds": self.real_my_bounds,
            "mx_bounds": self.real_mx_bounds,
        })
        pnginfo = PngInfo()
        for k, v in self.meta_info.items():
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

    def _crop(
        self, image: Image.Image, my_bounds: list[float], mx_bounds: list[float]
    ) -> Image.Image | None:
        img = crop_image(
            image,
            self.tile_my_bounds,
            self.tile_mx_bounds,
            my_bounds,
            mx_bounds,
        )
        return img.resize((670, 670))


class WindyTileDownloader(TileDownloader):
    url_template = None

    def __init__(self, date: arrow.Arrow, *args, **kwargs):
        self.date = date
        self.url_template = self.url_template.format(
            date=date, x="{x}", y="{y}", z="{z}"
        )
        print(self.url_template)
        super().__init__(*args, **kwargs)
