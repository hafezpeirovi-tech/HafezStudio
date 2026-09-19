# Approved local body segmentation model

Downloaded with explicit user permission on 2026-09-09; no implicit runtime downloads.
Filename: human_segmentation_pphumanseg_2023mar.onnx
Size: 6,163,938 bytes
SHA256: 552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24
Source: https://github.com/opencv/opencv_zoo/tree/main/models/human_segmentation_pphumanseg
Weights: https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx
License: Apache-2.0; see PPHumanSeg-LICENSE.txt (PaddlePaddle Authors).
Input: RGB 192x192, float32 normalized (pixel/255 - .5)/.5, NCHW.
Output: two-class person/background probability map.

This is person segmentation, not a dedicated hand/pose detector. Every-frame
inference and complete frame coverage do not guarantee perfect segmentation.
Small/occluded limbs still need visual review. Never claim anatomical accuracy
solely from successful inference or coverage counts.
