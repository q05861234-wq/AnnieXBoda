from ...statictypes import statictypes
from ..py_object import PyObject
from ..stream.video_quality import VideoQuality


class VideoParameters(PyObject):
    @statictypes
    def __init__(
        self,
        width: int = 1280,      # 🔥 Smart Upgrade: Default to HD Width
        height: int = 720,      # 🔥 Smart Upgrade: Default to HD Height
        frame_rate: int = 30,   # 🔥 Smart Upgrade: Smooth 30 FPS
        adjust_by_height: bool = True,
    ):
        # 1. بنجيب أقصى قدرات بتدعمها المكتبة حالياً
        max_w, max_h, max_fps = max(
            VideoQuality, key=lambda x: x.value[0],
        ).value

        # 2. العقل (Safety Logic):
        # حاول تشغل الـ HD (1280x720) اللي طلبناه فوق
        # لكن لو السيرفر آخره أقل، ارضى بالمتاح عشان البوت ميكرشش
        self.width: int = min(width, max_w)
        self.height: int = min(height, max_h)
        self.frame_rate: int = min(frame_rate, max_fps)
        
        self.adjust_by_height: bool = adjust_by_height
