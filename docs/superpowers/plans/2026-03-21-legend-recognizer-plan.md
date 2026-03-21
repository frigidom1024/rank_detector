# AIAware Legend Recognizer Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Create a Python module for recognizing Legendary rank icons from images using AI

**Architecture:** Standalone module `core/legend_recognizer.py` with `AIAwareLegendRecognizer` class, configurable API settings and output directories passed by caller.

**Tech Stack:** Python, requests, cv2, PIL

---

## File Structure

- **Create:** `core/legend_recognizer.py` - Main module with `AIAwareLegendRecognizer` class
- **Create:** `core/__init__.py` - Module exports

---

## Chunk 1: Core Module Structure

### Task 1: Create legend_recognizer.py with RecognitionResult dataclass

**Files:**
- Create: `core/legend_recognizer.py`

- [ ] **Step 1: Write the RecognitionResult dataclass**

```python
from dataclasses import dataclass

@dataclass
class RecognitionResult:
    rank: str           # "Legendary" 或 "Unknown"
    level: int          # 传奇排名，或 0
    confidence: float   # 置信度 0-1
```

- [ ] **Step 2: Run test to verify it works**

Run: `python -c "from core.legend_recognizer import RecognitionResult; r = RecognitionResult('Legendary', 5286, 0.99); print(r)"`
Expected: Output RecognitionResult

- [ ] **Step 3: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add RecognitionResult dataclass"
```

---

### Task 2: Implement AIAwareLegendRecognizer class with __init__

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write __init__ with API and directory config**

```python
class AIAwareLegendRecognizer:
    def __init__(
        self,
        api_key: str,
        api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        api_model: str = "doubao-seed-2-0-pro-260215",
        legend_dir: str = "data/legend",
        unknown_dir: str = "data/unknown"
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.api_model = api_model
        self.legend_dir = Path(legend_dir)
        self.unknown_dir = Path(unknown_dir)
        self.legend_dir.mkdir(parents=True, exist_ok=True)
        self.unknown_dir.mkdir(parents=True, exist_ok=True)
        self._legend_counter = self._get_next_id(self.legend_dir)
        self._unknown_counter = self._get_next_id(self.unknown_dir)

    def _get_next_id(self, directory: Path) -> int:
        """获取目录下最大序号+1"""
        max_id = 0
        for f in directory.glob("*.png"):
            try:
                name = f.stem
                parts = name.split("_")
                if len(parts) >= 3:
                    idx = int(parts[-1])
                    max_id = max(max_id, idx)
            except:
                pass
        return max_id + 1
```

- [ ] **Step 2: Test initialization**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; r = AIAwareLegendRecognizer(api_key='test', legend_dir='test_legend', unknown_dir='test_unknown'); print(r.legend_dir, r.unknown_dir)"`
Expected: directories created and paths printed

- [ ] **Step 3: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add AIAwareLegendRecognizer init with configurable API and dirs"
```

---

## Chunk 2: Image Loading & Cropping

### Task 3: Implement _load_image method

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write _load_image supporting path/URL/array**

```python
import requests
from PIL import Image
import numpy as np
import cv2
import io

def _load_image(self, source) -> Optional[np.ndarray]:
    """加载图片，支持文件路径、URL、numpy数组"""
    if isinstance(source, np.ndarray):
        return source

    if isinstance(source, str) and source.startswith(('http://', 'https://')):
        # 下载 URL
        response = requests.get(source, timeout=30)
        if response.status_code != 200:
            return None
        pil_img = Image.open(io.BytesIO(response.content))
        pil_img = pil_img.convert('RGB')
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 本地文件
    img = cv2.imread(source)
    if img is None:
        pil_img = Image.open(source).convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img
```

- [ ] **Step 2: Test with existing image**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; r = AIAwareLegendRecognizer(api_key='test'); img = r._load_image('data/Leg/Leg_58.png'); print(img.shape if img is not None else 'Failed')"`
Expected: Image shape printed

- [ ] **Step 3: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add _load_image for path/URL/array"
```

---

### Task 4: Implement _crop_image method

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write _crop_image using CROP_REGION**

```python
CROP_REGION = {"x1": 0.00, "y1": 0.00, "x2": 0.10, "y2": 0.25}

def _crop_image(self, img: np.ndarray) -> np.ndarray:
    """裁剪 ROI 区域"""
    h, w = img.shape[:2]
    x1 = int(w * CROP_REGION["x1"])
    y1 = int(h * CROP_REGION["y1"])
    x2 = int(w * CROP_REGION["x2"])
    y2 = int(h * CROP_REGION["y2"])
    return img[y1:y2, x1:x2]
```

- [ ] **Step 2: Test cropping**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; r = AIAwareLegendRecognizer(api_key='test'); img = r._load_image('data/Leg/Leg_58.png'); crop = r._crop_image(img); print(f'Original: {img.shape}, Crop: {crop.shape}')"`
Expected: Original and crop shapes printed

- [ ] **Step 3: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add _crop_image method"
```

---

## Chunk 3: AI Recognition

### Task 5: Implement _call_api and _recognize methods

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write Legendary-specific prompt and call logic**

```python
LEGENDARY_PROMPT = """你是一位游戏段位徽章识别专家，请识别这张图片是否是传奇(Legendary)段位。

【传奇(Legendary)特征】
- 红金火焰特效
- 顶部有红色/深红色水晶
- 金色边框装饰
- 底部有火焰/光芒纹理
- 下方有阿拉伯数字排名（如 58, 139, 5286, 9425, 13141 等）

如果不是传奇，返回 rank=Unknown, level=0
如果是传奇，返回 rank=Legendary, level=下方的排名数字

请以JSON格式返回：{"rank":"Legendary","level":58,"confidence":0.95}

只返回JSON，不要其他内容。"""

def _encode_image_from_array(self, img: np.ndarray) -> str:
    """将 numpy 数组编码为 base64"""
    _, buffer = cv2.imencode('.png', img)
    return base64.b64encode(buffer).decode("utf-8")

def _call_api(self, image_base64: str, prompt: str) -> Optional[Dict]:
    """调用豆包 API"""
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": self.api_model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": f"data:image/png;base64,{image_base64}"},
                {"type": "input_text", "text": prompt}
            ]
        }]
    }
    try:
        response = requests.post(
            f"{self.api_base_url}/responses",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def _parse_response(self, response: Dict) -> RecognitionResult:
    """解析 API 响应"""
    try:
        content = ""
        for item in response.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        content = c.get("text", "")
                        break

        if not content:
            return RecognitionResult("Unknown", 0, 0.0)

        # 去除 markdown 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return RecognitionResult(
            rank=data.get("rank", "Unknown"),
            level=int(data.get("level", 0)),
            confidence=float(data.get("confidence", 0.0))
        )
    except Exception as e:
        print(f"Parse error: {e}")
        return RecognitionResult("Unknown", 0, 0.0)

def _recognize(self, img: np.ndarray) -> RecognitionResult:
    """识别图片"""
    image_base64 = self._encode_image_from_array(img)
    response = self._call_api(image_base64, LEGENDARY_PROMPT)
    if response is None:
        return RecognitionResult("Unknown", 0, 0.0)
    return self._parse_response(response)
```

- [ ] **Step 2: Test recognition on Legendary image**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; import os; r = AIAwareLegendRecognizer(api_key=os.environ.get('VOLCENGINE_API_KEY')); img = r._load_image('data/Leg/Leg_58.png'); crop = r._crop_image(img); result = r._recognize(crop); print(result)"`
Expected: RecognitionResult with rank, level, confidence

- [ ] **Step 3: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add AI recognition with prompt and API call"
```

---

## Chunk 4: Save & Output

### Task 6: Implement _save_image method

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write _save_image with naming**

```python
def _save_image(self, img: np.ndarray, rank: str, level: int) -> str:
    """保存图片到对应目录"""
    if rank == "Legendary":
        filename = f"Legend_{level}_{self._legend_counter:03d}.png"
        filepath = self.legend_dir / filename
        self._legend_counter += 1
    else:
        filename = f"Unknown_{self._unknown_counter:03d}.png"
        filepath = self.unknown_dir / filename
        self._unknown_counter += 1

    cv2.imwrite(str(filepath), img)
    return str(filepath)
```

- [ ] **Step 2: Test saving**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; r = AIAwareLegendRecognizer(api_key='test', legend_dir='test_legend', unknown_dir='test_unknown'); img = r._load_image('data/Leg/Leg_58.png'); path = r._save_image(img, 'Legendary', 58); print(path)"`
Expected: Saved path printed

- [ ] **Step 3: Cleanup test dirs and commit**

```bash
rm -rf test_legend test_unknown
git add core/legend_recognizer.py
git commit -m "feat: add _save_image with auto-increment naming"
```

---

## Chunk 5: Main Public API

### Task 7: Implement recognize_ai() and recognize_batch_ai()

**Files:**
- Modify: `core/legend_recognizer.py`

- [ ] **Step 1: Write recognize_ai method**

```python
def recognize_ai(self, image_source) -> RecognitionResult:
    """
    识别单张图片

    Args:
        image_source: 文件路径/URL/numpy数组

    Returns:
        RecognitionResult
    """
    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)

    crop = self._crop_image(img)
    result = self._recognize(crop)
    self._save_image(crop, result.rank, result.level)
    return result
```

- [ ] **Step 2: Write recognize_batch_ai**

```python
def recognize_batch_ai(self, sources: List[str]) -> List[RecognitionResult]:
    """批量识别"""
    return [self.recognize_ai(src) for src in sources]
```

- [ ] **Step 3: Test full flow**

Run: `python -c "from core.legend_recognizer import AIAwareLegendRecognizer; import os; r = AIAwareLegendRecognizer(api_key=os.environ.get('VOLCENGINE_API_KEY')); result = r.recognize_ai('data/Leg/Leg_58.png'); print(result)"`
Expected: Full RecognitionResult printed

- [ ] **Step 4: Commit**

```bash
git add core/legend_recognizer.py
git commit -m "feat: add recognize_ai and recognize_batch_ai methods"
```

---

## Chunk 6: Module Export

### Task 8: Update __init__.py

**Files:**
- Create: `core/__init__.py`

- [ ] **Step 1: Write exports**

```python
from .legend_recognizer import AIAwareLegendRecognizer, RecognitionResult

__all__ = ["AIAwareLegendRecognizer", "RecognitionResult"]
```

- [ ] **Step 2: Test import**

Run: `python -c "from core import AIAwareLegendRecognizer, RecognitionResult; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add core/__init__.py
git commit -m "feat: add core module exports"
```

---

## Plan complete and saved to `docs/superpowers/plans/2026-03-21-legend-recognizer-plan.md`. Ready to execute?