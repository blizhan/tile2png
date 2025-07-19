import tempfile
from typing import Optional

import arrow
import click

from core.tiles import RainViewerRadarV2TileDownloader, WindyRadarV2TileDownloader


@click.group()
def cli():
    pass

@cli.group()
def radar():
    pass

@radar.command()
@click.option("--lat_bounds", type=click.Tuple([float, float]), required=True)
@click.option("--lon_bounds", type=click.Tuple([float, float]), required=True)
@click.option("--zoom", type=int, default=7)
@click.option("--output", type=str, default=None)
def windy(
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    print(lat_bounds, lon_bounds, zoom, output)
    now = arrow.utcnow()
    floored_minute = (now.minute // 5) * 5
    top_left = (lat_bounds[1], lon_bounds[0])
    bottom_right = (lat_bounds[0], lon_bounds[1])
    now = now.floor("minute").replace(minute=floored_minute)
    tile = WindyRadarV2TileDownloader(
        now,
        1555,
        top_left,
        bottom_right,
        zoom=zoom,
    )
    if output is None:
        output = f"windy_{now.format('YYYYMMDDHHmmss')}.png"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tile.download(tmp_dir)
        tile.merge(output)

@radar.command()
@click.option("--lat_bounds", type=click.Tuple([float, float]), required=True)
@click.option("--lon_bounds", type=click.Tuple([float, float]), required=True)
@click.option("--zoom", type=int, default=7)
@click.option("--output", type=str, default=None)
def rainviewer(
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    now = arrow.utcnow()
    floored_minute = (now.minute // 10) * 10
    now = now.floor("minute").replace(minute=floored_minute)
    top_left = (lat_bounds[1], lon_bounds[0])
    bottom_right = (lat_bounds[0], lon_bounds[1])
    tile = RainViewerRadarV2TileDownloader(
        int(now.timestamp()),
        top_left,
        bottom_right,
        zoom=zoom,
    )
    if output is None:
        output = f"rainviewer_{now.format('YYYYMMDDHHmmss')}.png"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tile.download(tmp_dir)
        tile.merge(output)

if __name__ == "__main__":
    cli()