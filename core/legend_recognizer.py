from dataclasses import dataclass

@dataclass
class RecognitionResult:
    rank: str           # "Legendary" 或 "Unknown"
    level: int          # 传奇排名，或 0
    confidence: float   # 置信度 0-1