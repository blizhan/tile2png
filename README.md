# tile2png


## usage

### Radar
Rainviewer
```python
uv run command.py radar rainviewer --lat_bounds 37.742 41.875 --lon_bounds 113.782 119.161 --output radar_rainviewer.png
```
![](sample/rainviewer_radar_20250720025000.png)
Windy
```python
uv run command.py radar windy --lat_bounds 37.742 41.875 --lon_bounds 113.782 119.161 --output radar_windy.png
```
![](sample/windy_radar_20250720025000.png)

### Satellite

```python
# vis
uv run command.py sate windy --type vis --lat_bounds 37.742 41.875 --lon_bounds 113.782 119.161--output windy_sate-vis.png

uv run command.py sate windy --type infra --lat_bounds 37.742 41.875 --lon_bounds 113.782 119.161 --output windy_sate-infra.png
```
![](sample/windy_sate-vis_20250720023000.png)

### Map

Google Satellite Map
```python
uv run command.py map google --lat_bounds 39.6 39.65 --lon_bounds 113.6 113.7 --zoom 15 --output map.webp
```
![](sample/google_sate_map.webp)


## Todo

- [ ] function
    - [ ] output projection
- [ ] other map tiles support
    - [ ] windy