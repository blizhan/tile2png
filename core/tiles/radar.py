import tempfile

import arrow

from .base import TileDownloader, WindyTileDownloader

__all__ = ["RainViewerRadarV2TileDownloader", "WindyRadarV2TileDownloader"]


class RainViewerRadarV2TileDownloader(TileDownloader):
    url_template = "https://cdn.rainviewer.com/v2/radar/{timestamp}/256/{z}/{x}/{y}/255/1_1_1_0.webp"

    def __init__(self, timestamp: int, *args, **kwargs):
        self.timestamp = timestamp
        self.url_template = self.url_template.format(
            timestamp=timestamp, x="{x}", y="{y}", z="{z}"
        )
        print(self.url_template)
        super().__init__(*args, **kwargs)


class WindyRadarV2TileDownloader(WindyTileDownloader):
    url_template = "https://rdr.windy.com/radar2/composite/{date:YYYY/MM/DD/HHmm}/{z}/{x}/{y}/reflectivity.png?multichannel=true&maxt={date:YYYYMMDDHHmmss}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


if __name__ == "__main__":
    now = arrow.utcnow()
    print(now)
    timestamp = int(now.timestamp()) // 600 * 600
    top_left = (41.87501349541372, 113.78232363984644)
    bottom_right = (37.74276146796519, 119.16156979277075)
    lat_bounds = [top_left[0], bottom_right[0]]
    lon_bounds = [top_left[1], bottom_right[1]]
    tile = RainViewerRadarV2TileDownloader(
        timestamp,
        lat_bounds,
        lon_bounds,
        zoom=7,
    )
    with tempfile.TemporaryDirectory(dir="./test/") as tmp_dir:
        tile.download(tmp_dir)
        print(tmp_dir)
        tile.merge("test/merged_rainviewer.png")

    floored_minute = (now.minute // 5) * 5
    now = now.floor("minute").replace(minute=floored_minute)
    tile = WindyRadarV2TileDownloader(
        now,
        lat_bounds,
        lon_bounds,
        zoom=7,
    )
    with tempfile.TemporaryDirectory(dir="./test/") as tmp_dir:
        tile.download(tmp_dir)
        print(tmp_dir)
        tile.merge("test/merged_windy.png")
