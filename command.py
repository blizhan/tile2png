import functools
import tempfile
from re import L
from typing import Optional

import arrow
import click

from core.tiles import *

common_options = [
    click.option(
        "--lat_bounds",
        type=click.Tuple([float, float]),
        required=True,
        help="Latitude bounds (min, max)",
    ),
    click.option(
        "--lon_bounds",
        type=click.Tuple([float, float]),
        required=True,
        help="Longitude bounds (min, max)",
    ),
    click.option("--zoom", type=int, default=7, help="Map zoom level"),
    click.option("--output", type=str, default=None, help="Output file name"),
]


def add_options(options):
    """A decorator factory that adds a list of click options to a command."""

    def decorator(func):
        for option in reversed(options):
            func = option(func)
        return func

    return decorator


@click.group()
def cli():
    pass


@cli.group()
def radar():
    pass


@cli.group()
def sate():
    pass


@cli.group()
def map():
    pass


@sate.command()
@add_options(common_options)
@click.option("--type", type=click.Choice(["infra", "vis"]), required=True)
def windy(
    type: str,
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    now = arrow.utcnow().shift(minutes=-15)
    floored_minute = (now.minute // 10) * 10
    now = now.floor("minute").replace(minute=floored_minute)
    if type == "infra":
        tile = WindySatelliteInfraTileDownloader(
            now,
            lat_bounds,
            lon_bounds,
            zoom=zoom,
        )
    elif type == "vis":
        tile = WindySatelliteVisTileDownloader(
            now,
            lat_bounds,
            lon_bounds,
            zoom=zoom,
        )
    if output is None:
        output = f"windy_sate-{type}_{now.format('YYYYMMDDHHmmss')}.png"
    tile.to_png(output)


@radar.command()
@add_options(common_options)
def windy(
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    now = arrow.utcnow().shift(minutes=-5)
    floored_minute = (now.minute // 5) * 5
    now = now.floor("minute").replace(minute=floored_minute)
    tile = WindyRadarV2TileDownloader(
        now,
        lat_bounds,
        lon_bounds,
        zoom=zoom,
    )
    if output is None:
        output = f"windy_radar_{now.format('YYYYMMDDHHmmss')}.png"
    tile.to_png(output)


@radar.command()
@add_options(common_options)
def rainviewer(
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    now = arrow.utcnow()
    floored_minute = (now.minute // 10) * 10
    now = now.floor("minute").replace(minute=floored_minute)
    tile = RainViewerRadarV2TileDownloader(
        int(now.timestamp()),
        lat_bounds,
        lon_bounds,
        zoom=zoom,
    )
    if output is None:
        output = f"rainviewer_radar_{now.format('YYYYMMDDHHmmss')}.png"
    tile.to_png(output)


@map.command()
@add_options(common_options)
def google(
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    tile = GoogleSatelliteMapTileDownloader(
        {},
        lat_bounds,
        lon_bounds,
        zoom=zoom,
    )
    if output is None:
        output = f"google_satellite_map.png"
    tile.to_png(output)


if __name__ == "__main__":
    cli()
