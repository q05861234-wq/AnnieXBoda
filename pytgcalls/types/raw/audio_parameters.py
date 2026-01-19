from ...statictypes import statictypes
from ..py_object import PyObject
from ..stream.audio_quality import AudioQuality


class AudioParameters(PyObject):
    @statictypes
    def __init__(
        self,
        bitrate: int = 48000,
        channels: int = 2, # Default requested: Stereo
    ):
        # 1. بنجيب سقف الجودة المسموح به في المكتبة عشان منخرجش عنه
        # Safety First: Get the maximum allowed values
        max_bit, max_chan = max(AudioQuality, key=lambda x: x.value[0]).value
        
        # 2. العقل الذكي (Smart Logic):
        # اطلب 48000، بس لو السقف أقل، انزل للسقف عشان البوت ميفصلش
        self.bitrate: int = min(48000, max_bit)
        
        # اطلب Stereo (2)، بس لو السقف (1)، اشتغل Mono عادي ومتهنجش
        self.channels: int = min(2, max_chan)
