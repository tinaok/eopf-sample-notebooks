import numpy as np
import xarray as xr
from typing import Dict
import scipy.ndimage
from xarray import DataArray
from skimage import segmentation, graph
from skimage.filters import sobel
from skimage.util import view_as_windows
import functools
import gc
import sys
import random
import logging

# Add the onnx dependencies to the path
sys.path.insert(1, "../onnx_models/dependencies")

import onnxruntime as ort


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ONNXSegmentationInference:
    def __init__(self, model_path: str, tile_size: int = 128, overlap: int = 32):
        self.model_path = model_path
        self.tile_size = tile_size
        self.overlap = overlap
        self.ort_session = ort.InferenceSession(model_path)
        logger.info(
            f"Loaded ONNX model from {model_path} with tile size {tile_size} and overlap {overlap}"
        )

    def tile(self, data: xr.DataArray):
        step = self.tile_size - self.overlap
        padded = data.pad(x=self.overlap, y=self.overlap, mode="reflect")
        x_tiles = view_as_windows(
            padded.x.values, step=step, window_shape=(self.tile_size,)
        )
        y_tiles = view_as_windows(
            padded.y.values, step=step, window_shape=(self.tile_size,)
        )
        logger.info(
            f"Tiling data into {x_tiles.shape[0]} x {y_tiles.shape[0]} tiles of size {self.tile_size} with overlap {self.overlap}"
        )
        tiles = []
        for i in range(y_tiles.shape[0]):
            for j in range(x_tiles.shape[0]):
                x_idx = i * step
                y_idx = j * step
                tile = padded.isel(
                    x=slice(x_idx, x_idx + self.tile_size),
                    y=slice(y_idx, y_idx + self.tile_size),
                )
                tiles.append(((i, j), tile))
        return tiles, padded

    def infer_tile(self, tile: xr.DataArray):
        arr = tile.values
        if arr.ndim == 2:
            raise ValueError("Tile must have 3 bands/time steps for model input.")
        if arr.shape[0] != 3:
            raise ValueError(f"Tile must have 3 bands/time steps, got {arr.shape[0]}")
        arr = np.transpose(arr, (1, 2, 0))  # (128, 128, 3)
        arr = arr.reshape(1, 128 * 128, 3)  # (1, 16384, 3)
        arr = arr.astype(np.float32)
        input_name = self.ort_session.get_inputs()[0].name
        pred = self.ort_session.run(None, {input_name: arr})[0]
        pred = np.squeeze(pred)
        # --- Fix: reshape if needed ---
        if pred.shape == (128 * 128,):
            pred = pred.reshape((128, 128))
        elif pred.shape == (1, 128, 128):
            pred = pred[0]
        elif pred.shape == (128, 128):
            pass
        else:
            raise ValueError(f"Unexpected prediction shape: {pred.shape}")
        return pred

    def stitch(self, tiles, padded_shape, original_shape):
        # Simple average in overlap regions
        logger.info(
            f"Stitching {len(tiles)} tiles into shape {padded_shape} with original shape {original_shape}"
        )
        result = np.zeros(padded_shape, dtype=np.float32)
        count = np.zeros(padded_shape, dtype=np.float32)
        step = self.tile_size - self.overlap
        idx = 0
        for i in range(0, padded_shape[0] - self.tile_size + 1, step):
            for j in range(0, padded_shape[1] - self.tile_size + 1, step):
                result[i : i + self.tile_size, j : j + self.tile_size] += tiles[idx]
                count[i : i + self.tile_size, j : j + self.tile_size] += 1
                idx += 1
        # Avoid division by zero
        result = result / np.maximum(count, 1)
        # Crop to original shape
        x0 = self.overlap
        y0 = self.overlap
        x1 = x0 + original_shape[0]
        y1 = y0 + original_shape[1]
        return result[x0:x1, y0:y1]

    def run(self, data: xr.DataArray):
        tiles, padded = self.tile(data)
        logger.info(f"Running inference on {len(tiles)} tiles")
        # select only 5% of the tiles for inference to save time
        if len(tiles) > 100:
            tiles = random.sample(tiles, max(1, len(tiles) // 20))
        logger.info(f"Selected {len(tiles)} tiles for inference")
        preds = [self.infer_tile(tile) for _, tile in tiles]
        logger.info(f"Stitching {len(preds)} predictions")
        stitched = self.stitch(
            preds,
            padded.shape[-2:],  # (x, y)
            data.shape[-2:],
        )
        logger.info(f"Stitched prediction shape: {stitched.shape}")
        # Return as DataArray with original coords
        return xr.DataArray(
            stitched, dims=("x", "y"), coords={"x": data.x, "y": data.y}
        )


def tile_cube(cube: xr.DataArray, tile_size=128, overlap=32):
    step = tile_size - overlap
    padded = cube.pad(x=overlap, y=overlap, mode="reflect")
    print(np.unique(padded["x"]).size == padded["x"].size)
    x_tiles = view_as_windows(padded.x.values, step=step, window_shape=(tile_size,))
    y_tiles = view_as_windows(padded.y.values, step=step, window_shape=(tile_size,))

    tiles = []
    for i in range(y_tiles.shape[0]):
        for j in range(x_tiles.shape[0]):
            x_start = padded.x[i * step].item()
            y_start = padded.y[j * step].item()
            tile = padded.sel(
                x=slice(x_start, x_start + tile_size),
                y=slice(y_start, y_start + tile_size),
            )
            tiles.append(((i, j), tile))
    return tiles, x_tiles.shape


def apply_kernel(
    data: xr.DataArray, kernel: np.ndarray, mode="constant", cval=0
) -> xr.DataArray:
    def convolve(data_chunk):
        return scipy.ndimage.binary_dilation(data_chunk, structure=kernel).astype(
            np.uint8
        )

    return xr.apply_ufunc(
        convolve,
        data,
        input_core_dims=[["x", "y"]],
        output_core_dims=[["x", "y"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[np.uint8],
        dask_gufunc_kwargs={
            "allow_rechunk": True,
        },
    )


def scl_to_cloud_mask(scl: xr.DataArray) -> xr.DataArray:
    mask1_values = [2, 4, 5, 6, 7]
    mask2_values = [3, 8, 9, 10, 11]

    mask1 = xr.zeros_like(scl)
    mask2 = xr.zeros_like(scl)
    for val in mask1_values:
        mask1 = mask1 | (scl == val)
    for val in mask2_values:
        mask2 = mask2 | (scl == val)

    mask1 = mask1.astype(bool)
    mask2 = mask2.astype(bool)

    kernel1 = np.ones((17, 17), dtype=bool)
    kernel2 = np.ones((77, 77), dtype=bool)
    erosion_kernel = np.ones((3, 3), dtype=bool)

    mask1_dilated = apply_kernel(mask1, kernel1)
    mask2_dilated = apply_kernel(mask2, kernel2)

    combined_mask = (mask1_dilated | mask2_dilated).astype(np.uint8)

    def erode(data_chunk):
        return scipy.ndimage.binary_erosion(
            data_chunk, structure=erosion_kernel
        ).astype(np.uint8)

    cloud_mask = xr.apply_ufunc(
        erode,
        combined_mask,
        input_core_dims=[["x", "y"]],
        output_core_dims=[["x", "y"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[np.uint8],
    )

    return cloud_mask


def apply_datacube(cube: DataArray, context: Dict) -> DataArray:
    # get the underlying array without the bands and t dimension
    _data = cube.squeeze("t", drop=True).squeeze("bands", drop=True).values
    # compute edges
    edges = sobel(_data)
    # Perform felzenszwalb segmentation
    segment = segmentation.felzenszwalb(
        _data, scale=120, sigma=0.0, min_size=30, channel_axis=None
    )
    # Perform the rag boundary analysis and merge the segments
    bgraph = graph.rag_boundary(segment, edges)
    # merging segments
    mergedsegment = graph.cut_threshold(segment, bgraph, 0.15, in_place=False)
    # create a data cube and perform masking operations
    output_arr = DataArray(
        mergedsegment.reshape(cube.shape), dims=cube.dims, coords=cube.coords
    )
    output_arr = output_arr.where(
        cube >= 0.3
    )  # Mask the output pixels based on the cube values <0.3
    output_arr = output_arr.where(
        output_arr >= 0
    )  # Mask all values less than or equal to zero
    return output_arr


model_names = frozenset(
    [
        "BelgiumCropMap_unet_3BandsGenerator_Network1.onnx",
        "BelgiumCropMap_unet_3BandsGenerator_Network2.onnx",
        "BelgiumCropMap_unet_3BandsGenerator_Network3.onnx",
    ]
)


@functools.lru_cache(maxsize=1)
def load_ort_sessions(names):
    """
    Load the models and make the prediction functions.
    The lru_cache avoids loading the model multiple times on the same worker.

    @param modeldir: Model directory
    @return: Loaded model sessions
    """
    # inspect(message="Loading convolutional neural networks as ONNX runtime sessions ...")
    return [ort.InferenceSession(f"onnx_models/{model_name}") for model_name in names]


def process_window_onnx(ndvi_stack: xr.DataArray, patch_size=128) -> xr.DataArray:
    """Compute prediction.

    Compute predictions using ML models. ML models takes three inputs images and predicts
    one image. Four predictions are made per model using three random images. Three images
    are considered to save computational time. Final result is median of these predictions.

    Parameters
    ----------
    ndvi_stack : DataArray
        ndvi data
    patch_size : Int
        Size of the sample

    Returns
    -------
    xr.DataArray
        Machine learning prediction.
    """
    # we'll do 12 predictions: use 3 networks, and for each random take 3 NDVI images and repeat 4 times
    ort_sessions = load_ort_sessions(model_names)  # get models

    predictions_per_model = 4
    no_rand_images = 3  # Number of random images that are needed for input
    no_images = ndvi_stack.t.shape[0]

    # Range of index of images
    _range = range(no_images)
    # List of all predictions
    prediction = []
    for ort_session in ort_sessions:
        # make 4 predictions per model
        for i in range(predictions_per_model):
            # initialize a predicter array
            random.seed(
                i
            )  # without seed we will have random number leading to non-reproducible results.
            _idx = random.choices(
                _range, k=no_rand_images
            )  # Random selection of 3 images for input
            # re-shape the input data for ML input
            input_data = ndvi_stack.isel(t=_idx).data.reshape(
                1, patch_size * patch_size, no_rand_images
            )
            ort_inputs = {ort_session.get_inputs()[0].name: input_data}

            # Run ML to predict
            ort_outputs = ort_session.run(None, ort_inputs)
            # reshape ort_outputs and append it to prediction list
            prediction.append(ort_outputs[0].reshape((patch_size, patch_size)))

    # free up some memory to avoid memory errors
    gc.collect()

    # Create a DataArray of all predictions
    all_predictions = xr.DataArray(
        prediction,
        dims=["predict", "x", "y"],
        coords={
            "predict": range(len(prediction)),
            "x": ndvi_stack.coords["x"],
            "y": ndvi_stack.coords["y"],
        },
    )
    # final prediction is the median of all predictions per pixel
    return all_predictions.median(dim="predict")


def preprocess_datacube(
    cubearray: xr.DataArray, min_images: int
) -> tuple[bool, xr.DataArray]:
    """Preprocess data for machine learning.

    Preprocess data by clamping NVDI values and first check if the
    data is valid for machine learning and then check if there is good
    data to perform machine learning.

    Parameters
    ----------
    cubearray : xr.DataArray
        Input datacube
    min_images : int
        Minimum number of samples to consider for machine learning.

    Returns
    -------
    bool
        True refers to data is invalid for machine learning.
    xr.DataArray
        If above bool is False, return data for machine learning else returns a
        sample containing nan (similar to machine learning output).
    """
    # Preprocessing data
    # check if bands is in the dims and select the first index
    if "bands" in cubearray.dims:
        nvdi_stack = cubearray.isel(bands=0)
    else:
        nvdi_stack = cubearray
    # Clamp out of range NDVI values
    nvdi_stack = nvdi_stack.where(lambda nvdi_stack: nvdi_stack < 0.92, 0.92)
    nvdi_stack = nvdi_stack.where(lambda nvdi_stack: nvdi_stack > -0.08)
    nvdi_stack += 0.08
    # Count the amount of invalid pixels in each time sample.
    sum_invalid = nvdi_stack.isnull().sum(dim=["x", "y"])
    # Check % of invalid pixels in each time sample by using mean
    sum_invalid_mean = nvdi_stack.isnull().mean(dim=["x", "y"])
    # Fill the invalid pixels with value 0
    nvdi_stack_data = nvdi_stack.fillna(0)

    # Check if data is valid for machine learning. If invalid, return True and
    # an DataArray of nan values (similar to the machine learning output)
    if (
        sum_invalid_mean.data < 1
    ).sum() <= min_images:  # number of invalid time sample less then min images
        # create a nan dataset and return
        nan_data = xr.zeros_like(nvdi_stack.sel(t=sum_invalid_mean.t[0], drop=True))
        nan_data = nan_data.where(lambda nan_data: nan_data > 1)
        return True, nan_data

    # Data selection: valid data for machine learning
    # select time samples where there are no invalid pixels
    if (sum_invalid.data == 0).sum() >= min_images:
        good_data = nvdi_stack_data.sel(t=sum_invalid[sum_invalid.data == 0].t)
    else:  # select the 4 best time samples with least amount of invalid pixels.
        good_data = nvdi_stack_data.sel(
            t=sum_invalid.sortby(sum_invalid).t[:min_images]
        )
    return False, good_data.transpose("x", "y", "t")


def apply_datacube_segmentation(cube: xr.DataArray, context: Dict) -> xr.DataArray:
    # select atleast best 4 temporal images of ndvi for ML
    min_images = 4

    # preprocess the datacube
    invalid_data, ndvi_stack = preprocess_datacube(cube, min_images)

    # If data is invalid, there is no need to run prediction algorithm so
    # return prediction as nan DataArray and reintroduce time and bands dimensions
    if invalid_data:
        return ndvi_stack.expand_dims(
            dim={"t": [(cube.t.dt.year.values[0])], "bands": ["prediction"]}
        )

    # Machine learning prediction: process the window
    result = process_window_onnx(ndvi_stack)
    # Reintroduce time and bands dimensions
    result_xarray = result.expand_dims(
        dim={"t": [(cube.t.dt.year.values[0])], "bands": ["prediction"]}
    )
    # Return the resulting xarray
    return result_xarray
