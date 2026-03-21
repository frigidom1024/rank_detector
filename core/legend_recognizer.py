from dataclasses import dataclass
from pathlib import Path


@dataclass
class RecognitionResult:
    rank: str           # "Legendary" 或 "Unknown"
    level: int          # 传奇排名，或 0
    confidence: float   # 置信度 0-1


class AIAwareLegendRecognizer:
    def __init__(
        self,
        api_key: str,
        api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        api_model: str = "doubao-seed-2-0-pro-260215",
        legend_dir: str = "data/legend",
        unknown_dir: str = "data/unknown",
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.api_model = api_model
        self.legend_dir = Path(legend_dir)
        self.unknown_dir = Path(unknown_dir)
        self._id_counter = 0

        self.legend_dir.mkdir(parents=True, exist_ok=True)
        self.unknown_dir.mkdir(parents=True, exist_ok=True)

    def _get_next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter