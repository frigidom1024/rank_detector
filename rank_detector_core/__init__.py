from .legend_recognizer import (
    AIAwareLegendRecognizer,
    RecognitionResult,
)

# 保存标志常量也可以直接导入
SAVE_NONE = AIAwareLegendRecognizer.SAVE_NONE
SAVE_UNKNOWN = AIAwareLegendRecognizer.SAVE_UNKNOWN
SAVE_LEGENDARY = AIAwareLegendRecognizer.SAVE_LEGENDARY
SAVE_ALL = AIAwareLegendRecognizer.SAVE_ALL

__all__ = [
    "AIAwareLegendRecognizer",
    "RecognitionResult",
    "SAVE_NONE",
    "SAVE_UNKNOWN",
    "SAVE_LEGENDARY",
    "SAVE_ALL",
]
