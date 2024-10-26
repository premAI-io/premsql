import base64
import io
from abc import ABC, abstractmethod

import pandas as pd
from PIL import Image


class BasePlotTool(ABC):
    @abstractmethod
    def run(self, data: pd.DataFrame, plot_config: dict):
        raise NotImplementedError()

    @abstractmethod
    def convert_plot_to_image(self, fig):
        raise NotImplementedError

    def convert_image_to_base64(self, image: Image.Image) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def save_image(self, image: Image.Image, file_path: str, format: str = "PNG"):
        image.save(file_path, format=format)

    def plot_from_base64(self, output_base64: str):
        image_data = base64.b64decode(output_base64)
        return Image.open(io.BytesIO(image_data))
