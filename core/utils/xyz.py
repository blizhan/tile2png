# -*- coding: utf-8 -*
import math
from typing import Tuple, List, Iterator
from itertools import product
from dataclasses import dataclass

# --- Constants ---
EARTH_RADIUS = 6378137
EQUATOR_CIRCUMFERENCE = 2 * math.pi * EARTH_RADIUS

@dataclass
class Point:
    """Represents a point with latitude and longitude."""
    lat: float
    lng: float

@dataclass
class Tile:
    """Represents a map tile with its coordinates and zoom level."""
    x: int
    y: int
    zoom: int
    point: Point  # Top-left corner of the tile


class GoogleXYZTile:
    """
    A class to handle conversions between geographical coordinates (lat/lng)
    and Google Maps tile coordinates (x, y, zoom) and pixel coordinates.
    """
    def __init__(
        self, 
        zoom: int,
        earth_radius: float = EARTH_RADIUS,
    ):
        self.earth_radius = earth_radius
        self.initial_resolution = self.earth_radius / 256.0
        self.origin_shift = self.earth_radius / 2.0
        self.zoom = zoom

    @property
    def num_tiles(self) -> int:
        """Number of tiles at the current zoom level."""
        return 1 << self.zoom

    def get_tile_xy(self, lat, lng) -> Tuple[int, int]:
        """ 获取指定经纬度对应的瓦片坐标
        """
        point_x = (180 + lng) * self.num_tiles / 360
        point_y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) * self.num_tiles / 2

        return int(point_x), int(point_y)


    def get_mercator_xy(self, lat, lng) -> Tuple[float, float]:
        """ 获取指定经纬度对应的墨卡托坐标
        """
        mx = (lng * self.origin_shift) / 180.0
        my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        my = (my * self.origin_shift) / 180.0
        res = self.initial_resolution / (2 ** self.zoom)
        px = (mx + self.origin_shift) / res
        py = (my + self.origin_shift) / res
        return px, py

    def get_tile_lat_lng(self, x, y) -> Tuple[float, float]:
        """ 获取瓦片左上角的经纬度
        """
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / self.num_tiles)))
        lat_deg = (180.0 / math.pi * lat_rad)
        lon_deg = (x / self.num_tiles * 360.0) - 180.0
        return lat_deg, lon_deg
        
    def iter_tile_xy(self, top_lat, left_lng, bottom_lat, right_lng) -> Iterator[Tile]:
        """ 获取指定经纬度范围内的所有瓦片坐标
        """
        pos_1x, pos_1y, pos_2x, pos_2y = self.get_xy_range(top_lat, left_lng, bottom_lat, right_lng)
        for x, y in product(range(pos_1x, pos_2x+1), range(pos_1y, pos_2y + 1)):
            yield Tile(x, y, self.zoom, Point(*self.get_tile_lat_lng(x, y)))

    def get_xy_range(self, top_lat, left_lng, bottom_lat, right_lng) -> Tuple[int, int, int, int]:
        """ 获取指定经纬度范围内的所有瓦片坐标
        """
        pos_1x, pos_1y = self.get_tile_xy(top_lat, left_lng)
        pos_2x, pos_2y = self.get_tile_xy(bottom_lat, right_lng)
        return pos_1x, pos_1y, pos_2x, pos_2y


if __name__ == "__main__":
    zoom = 10
    tile = GoogleXYZTile(zoom=zoom)
    print(tile.get_tile_xy(55.394,-2.711))
    # for t in tile.iter_tile_xy(85.05, -180, -85.05, 180):
    #     print(t)
