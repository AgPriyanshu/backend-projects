import numpy as np


def encode_terrain_rgb(elevation: np.ndarray) -> np.ndarray:
    # Handle nodata/NaNs (set to a base level, e.g., 0 for visual purposes or keep as NaNs)
    elevation = np.nan_to_num(elevation, nan=0.0)

    # Mapbox Terrain-RGB formula
    val = (elevation + 10000.0) * 10.0
    val = np.clip(val, 0, 16777215).astype(np.uint32)

    r = (val >> 16) & 255
    g = (val >> 8) & 255
    b = val & 255

    # Stack into RGB
    return np.stack([r, g, b]).astype(np.uint8)

test_data = np.array([[[1.0, 100.0], [-50.0, 8848.0]]], dtype=np.float32)
print(test_data.shape)
encoded = encode_terrain_rgb(test_data)
print(encoded.shape)
print(encoded[:, 0, 1]) # for 100.0 -> height = 100. (100+10000)*10 = 101000. 101000 >> 16 = 1. (101000 >> 8) % 256 = 138. 101000 % 256 = 136.
