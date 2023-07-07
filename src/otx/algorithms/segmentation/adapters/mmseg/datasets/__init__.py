"""OTX Algorithms - Segmentation Dataset."""

# Copyright (C) 2023 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

from .dataset import MPASegDataset, get_annotation_mmseg_format
from .pipelines import (
    LoadAnnotationFromOTXDataset,
    LoadImageFromOTXDataset,
    MaskCompose,
    ProbCompose,
    TwoCropTransform,
)

__all__ = [
    "LoadAnnotationFromOTXDataset",
    "LoadImageFromOTXDataset",
    "MaskCompose",
    "ProbCompose",
    "TwoCropTransform",
    "get_annotation_mmseg_format",
    "MPASegDataset",
]