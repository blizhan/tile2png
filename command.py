from typing import Optional

import arrow
import click

from core.tiles import *

common_options = [
    click.option(
        "--lat_bounds",
        type=click.Tuple([float, float]),
        default=[0, 0],
        help="Latitude bounds (min, max)",
    ),
    click.option(
        "--lon_bounds",
        type=click.Tuple([float, float]),
        default=[0, 0],
        help="Longitude bounds (min, max)",
    ),
    click.option(
        "--center_latlng",
        type=click.Tuple([float, float]),
        default=None,
        help="Center latitude and longitude",
    ),
    click.option("--date", type=str, default=None, help="Date"),
    click.option("--archive", type=bool, default=True, help="Use archive"),
    click.option("--radius", type=int, default=1000 * 50, help="Radius in meters"),
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


@cli.group()
def tile():
    pass


@sate.command()
@add_options(common_options)
@click.option("--type", type=click.Choice(["infra", "vis"]), required=True)
def windy(
    type: str,
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    date: Optional[str] = None,
    archive: bool = True,
    center_latlng: Optional[tuple[float, float]] = None,
    radius: Optional[int] = 0,
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    if date is None:
        now = arrow.utcnow().shift(minutes=-15)
    else:
        now = arrow.get(date)
    floored_minute = (now.minute // 10) * 10
    now = now.floor("minute").replace(minute=floored_minute)
    if type == "infra":
        tile = WindySatelliteInfraTileDownloader(
            now,
            archive=archive,
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            center_latlng=center_latlng,
            radius=radius,
            zoom=zoom,
        )
    elif type == "vis":
        tile = WindySatelliteVisTileDownloader(
            now,
            archive=archive,
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            center_latlng=center_latlng,
            radius=radius,
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
    date: Optional[str] = None,
    archive: bool = True,
    center_latlng: Optional[tuple[float, float]] = None,
    radius: Optional[int] = 0,
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    if date is None:
        now = arrow.utcnow().shift(minutes=-5)
    else:
        now = arrow.get(date)
    floored_minute = (now.minute // 5) * 5
    now = now.floor("minute").replace(minute=floored_minute)
    tile = WindyRadarV2TileDownloader(
        now,
        archive=archive,
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        center_latlng=center_latlng,
        radius=radius,
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
    center_latlng: Optional[tuple[float, float]] = None,
    radius: Optional[int] = 0,
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    now = arrow.utcnow().shift(minutes=-5)
    floored_minute = (now.minute // 10) * 10
    now = now.floor("minute").replace(minute=floored_minute)
    tile = RainViewerRadarV2TileDownloader(
        int(now.timestamp()),
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        center_latlng=center_latlng,
        radius=radius,
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
    center_latlng: Optional[tuple[float, float]] = None,
    radius: Optional[int] = 0,
    zoom: Optional[int] = 7,
    output: Optional[str] = None,
):
    tile = GoogleSatelliteMapTileDownloader(
        {},
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        center_latlng=center_latlng,
        radius=radius,
        zoom=zoom,
    )
    if output is None:
        output = "google_satellite_map.png"
    tile.to_png(output)


@tile.command()
@add_options(common_options)
@click.option("--url_template", type=str, required=True)
def tile(
    url_template: str,
    lat_bounds: tuple[float, float],
    lon_bounds: tuple[float, float],
    center_latlng: Optional[tuple[float, float]] = None,
    radius: Optional[int] = 0,
    zoom: Optional[int] = 10,
    output: Optional[str] = None,
):
    class UDFTTileDownloader(TileDownloader):
        url_template = url_template

    tile = UDFTTileDownloader(
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        center_latlng=center_latlng,
        radius=radius,
        zoom=zoom,
    )
    tile.download()
    if output is None:
        output = f"download_map-zoom{zoom}.webp"
    tile.merge(output)


if __name__ == "__main__":
    cli()
