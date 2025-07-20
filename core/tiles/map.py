from .base import TileDownloader


__all__ = ["GoogleSatelliteMapTileDownloader"]

class GoogleSatelliteMapTileDownloader(TileDownloader):
    url_template = "https://mt0.google.com/vt/lyrs=s{style}&x={x}&y={y}&z={z}"

    def __init__(self, style: dict, *args, **kwargs):
        self.style = style
        style_str = "".join([f"&{k}={v}" for k, v in style.items()])
        self.url_template = self.url_template.format(style=style_str, x="{x}", y="{y}", z="{z}")
        super().__init__(*args, **kwargs)
