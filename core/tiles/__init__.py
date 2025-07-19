class GoogleMapsWebDownloader(object):

    def __init__(self):
        self.tiles = None
        self.len_x = None
        self.len_y = None

    def download(self, top_left, right_bottom, folder, **kwargs):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        urls_points, xy = self._get_urls(top_left, right_bottom, kwargs.get('zoom'), kwargs.get('style'))

        results = self._download(urls_points, folder, *xy, kwargs.get('format'))
        self.tiles = [img for row in results for img in row]

    def _download(self, urls_points, folder, len_x, len_y, fformat):
        path = Path(folder)
        path.mkdir(exist_ok=True, parents=True)

        per_process = len(urls_points) // mp.cpu_count()

        urls_and_names = [
            (url, os.path.join(folder, fr'tile_{p[0]:.4f}_{p[1]:.4f}.{fformat}'))
            for i, (url,p) in enumerate(urls_points)
        ]
        split_urls = [
            urls_and_names[i:i + per_process]
            for i in range(0, len(urls_and_names), per_process)
        ]
        with ProcessPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self._download_tiles, split_urls))
        return results

    def _download_tiles(self, urls_and_names):
        with ThreadPoolExecutor(max_workers=max_threads) as pool:
            byte_images = list(pool.map(
                lambda v: self._request(v[0], v[1]), urls_and_names)
            )

        return byte_images

    def _get_urls(self, top_left, right_bottom, zoom, style):
        pos1x, pos1y, pos2x, pos2y = utils.latlon2px(*top_left, *right_bottom, zoom)
        len_x, len_y = utils.get_region_size(pos1x, pos1y, pos2x, pos2y)
        self.len_x = len_x
        self.len_y = len_y

        return [(self.get_url(i, j, zoom, style), utils.get_lat_lon(i, j, zoom))
                for j in range(pos1y, pos1y + len_y)
                for i in range(pos1x, pos1x + len_x)], (len_x, len_y)

    def _request(self, url, name):
        if os.path.exists(name):
            return name
        try:
            _HEADERS = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.68'
            }
            _header = ' '.join([f'-H "{k}: {v}"' for k,v in _HEADERS.items()])
            check_call(f'curl -x {proxy.get("proxy_type")}://{proxy.get("host")}:{proxy.get("port")} {_header} "{url}" -o {name}', shell=True)
            time.sleep(3)
            return name
        except Exception as e:
            return None

    @staticmethod
    def get_url(x, y, z, style):
        return f"http://mts0.googleapis.com/vt?lyrs={style}&x={x}&y={y}&z={z}"

    @staticmethod
    def _save_bytes(response, output):
        with open(output, 'wb') as f:
            f.write(response)

    def merge(self, filename):
        self._merge_and_save(filename)

    def _merge_and_save(self, filename):
        len_xy = int(np.rint(np.sqrt(len(self.tiles))))
        if os.path.exists(filename):
            return
        merged_pic = self._merge_tiles(self.tiles, self.len_x, self.len_y)
        merged_pic = merged_pic.convert('RGB')
        merged_pic.save(filename)

    @staticmethod
    def _merge_tiles(tiles, len_x, len_y):
        merged_pic = Image.new('RGBA', (len_x * 256, len_y * 256))

        for i, tile in enumerate(tiles):
            if tile is None or not os.path.exists(tile):
                continue
            with Image.open(tile) as tile_img:
                y, x = i // len_x, i % len_x
                merged_pic.paste(tile_img, (x * 256, y * 256))

        return merged_pic

