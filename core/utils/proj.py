from PIL import Image
from pyproj import Transformer

w2m = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
m2w = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def get_mymx(lat, lon):
    x, y = w2m.transform(lon, lat)
    return y, x


def get_latlng(my, mx):
    lon, lat = m2w.transform(mx, my)
    return lat, lon


def crop_image(
    img: Image.Image,
    img_my_bounds: list[float],
    img_mx_bounds: list[float],
    crop_my_bounds: list[float],
    crop_mx_bounds: list[float],
) -> Image.Image | None:
    w, h = img.size
    img_mx_resolution = w / (img_mx_bounds[1] - img_mx_bounds[0])
    img_my_resolution = h / (img_my_bounds[1] - img_my_bounds[0])

    if (
        crop_mx_bounds[0] > img_mx_bounds[1]
        or crop_mx_bounds[1] < img_mx_bounds[0]
        or crop_my_bounds[0] > img_my_bounds[1]
        or crop_my_bounds[1] < img_my_bounds[0]
    ):
        return None

    # img_mx_bounds[0], img_my_bounds[1] is pixel 0,0
    # upper left
    crop_px_ul = int((crop_mx_bounds[0] - img_mx_bounds[0]) * img_mx_resolution)
    crop_py_ul = int((img_my_bounds[1] - crop_my_bounds[1]) * img_my_resolution)

    # lower right
    crop_px_lr = int((crop_mx_bounds[1] - img_mx_bounds[0]) * img_mx_resolution)
    crop_py_lr = int((img_my_bounds[1] - crop_my_bounds[0]) * img_my_resolution)

    # Pillow crop (左,上,右,下)
    crop = img.crop((crop_px_ul, crop_py_ul, crop_px_lr, crop_py_lr))

    return crop
