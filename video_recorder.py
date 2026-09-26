"""
High-Performance PyAV H.264 Video Recorder
Produces HTML5/Web-compatible MP4 (H.264 + AAC/yuv420p) clips
Playable directly in Google Chrome, Edge, Safari, iOS, and Streamlit.
"""
import os
import av
import numpy as np
import logging

logger = logging.getLogger("video_recorder")

class H264VideoWriter:
    def __init__(self, output_path: str, width: int, height: int, fps: int = 15):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.container = None
        self.stream = None
        self.frame_count = 0
        self._init_writer()

    def _init_writer(self):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            self.container = av.open(self.output_path, mode='w', options={'movflags': '+faststart'})
            self.stream = self.container.add_stream('h264', rate=self.fps)
            self.stream.width = self.width
            self.stream.height = self.height
            self.stream.pix_fmt = 'yuv420p'
            # Fast encoding preset for real-time CCTV capture
            self.stream.options = {'preset': 'veryfast', 'crf': '23'}
        except Exception as e:
            logger.error(f"Failed to initialize PyAV H264 writer: {e}")
            self.container = None

    def write_frame(self, bgr_frame: np.ndarray):
        if self.container is None or self.stream is None:
            return
        try:
            h, w = bgr_frame.shape[:2]
            if w != self.width or h != self.height:
                import cv2
                bgr_frame = cv2.resize(bgr_frame, (self.width, self.height))

            video_frame = av.VideoFrame.from_ndarray(bgr_frame, format='bgr24')
            for packet in self.stream.encode(video_frame):
                self.container.mux(packet)
            self.frame_count += 1
        except Exception as e:
            logger.error(f"Error encoding video frame: {e}")

    def close(self):
        if self.container is None:
            return
        try:
            # Flush encoder
            for packet in self.stream.encode():
                self.container.mux(packet)
            self.container.close()
            logger.info(f"Closed video writer: {self.output_path} ({self.frame_count} frames)")
        except Exception as e:
            logger.error(f"Error closing video container: {e}")
        finally:
            self.container = None
            self.stream = None
