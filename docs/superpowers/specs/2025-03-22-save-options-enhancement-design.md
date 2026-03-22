# 保存功能增强设计文档

**日期**: 2025-03-22
**状态**: 设计中
**作者**: Claude

## 概述

增强 `AIAwareLegendRecognizer` 的图片保存功能，支持：
1. 灵活控制是否保存 Legendary/Unknown 图片
2. 为保存的图片添加自定义后缀（如 URL，便于人工审核追溯）

## 动机

当前实现总是保存所有图片，且文件名格式固定。用户反馈：
- Unknown 图片需要人工审核原图，需要记录 URL 追溯
- 希望能灵活控制是否保存各类图片，节省存储空间

## API 设计

### 1. 保存标志常量

```python
class AIAwareLegendRecognizer:
    # 保存选项标志位（二进制组合）
    SAVE_NONE = 0b00       # 都不保存
    SAVE_UNKNOWN = 0b01    # 只保存 Unknown
    SAVE_LEGENDARY = 0b10  # 只保存 Legendary
    SAVE_ALL = 0b11        # 都保存（默认）
```

### 2. 初始化参数

```python
def __init__(
    self,
    api_key: str,
    api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    api_model: str = "doubao-seed-2-0-pro-260215",
    api_type: str = None,
    legend_dir: str = "data/legend",
    unknown_dir: str = "data/unknown",
    auto_crop: bool = False,
    save_flags: int = SAVE_ALL,  # 新增：保存选项标志
):
```

### 3. 识别方法参数扩展

```python
def recognize_ai(
    self,
    image_source,
    suffix: str = None,      # 新增：自定义文件名后缀
    save_flags: int = None   # 新增：临时覆盖初始化设置
) -> RecognitionResult

def recognize_batch_ai(
    self,
    sources: List[str],
    suffix: str = None,
    save_flags: int = None
) -> List[RecognitionResult]

async def recognize_ai_async(
    self,
    image_source,
    suffix: str = None,
    save_flags: int = None
) -> RecognitionResult

async def recognize_batch_ai_async(
    self,
    sources: List[str],
    suffix: str = None,
    save_flags: int = None
) -> List[RecognitionResult]
```

## 使用示例

```python
from rank_detector_core import AIAwareLegendRecognizer

# 默认行为：保存所有图片
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
    api_base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_model="doubao-seed-2-0-pro-260215",
)

# 只保存 Unknown 图片
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
    save_flags=AIAwareLegendRecognizer.SAVE_UNKNOWN
)

# 保存带 URL 后缀的图片
result = recognizer.recognize_ai(
    "https://example.com/screenshot.png",
    suffix="url_example.com_screenshot"
)
# 结果文件名: Unknown_001_url_example.com_screenshot.png

# 调用时临时只保存 Legendary
result = recognizer.recognize_ai(
    "test.png",
    save_flags=AIAwareLegendRecognizer.SAVE_LEGENDARY
)
```

## 实现细节

### 1. 实例变量

```python
self._save_flags = save_flags  # 存储保存标志
```

### 2. `_save_image` 方法修改

```python
def _save_image(
    self,
    img: np.ndarray,
    rank: str,
    level: int,
    suffix: str = None
) -> Optional[str]:
    """保存图片到对应目录，返回文件路径或 None"""

    # 确定是否需要保存
    if rank == "Legendary":
        should_save = self._save_flags & self.SAVE_LEGENDARY
    else:
        should_save = self._save_flags & self.SAVE_UNKNOWN

    if not should_save:
        return None

    # 构建文件名
    if rank == "Legendary":
        filename = f"Legend_{level}_{self._legend_counter:03d}"
        self._legend_counter += 1
    else:
        filename = f"Unknown_{self._unknown_counter:03d}"
        self._unknown_counter += 1

    # 添加后缀
    if suffix:
        filename = f"{filename}_{suffix}"

    filename += ".png"

    # 确定保存目录
    filepath = self.legend_dir / filename if rank == "Legendary" else self.unknown_dir / filename

    # 保存图片
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(filepath), img_bgr)

    return str(filepath)
```

### 3. 识别方法中的参数处理

```python
def recognize_ai(self, image_source, suffix: str = None, save_flags: int = None):
    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)

    crop = self._crop_image(img) if self.auto_crop else img
    result = self._recognize(crop)

    # 处理 save_flags 参数
    original_flags = self._save_flags
    if save_flags is not None:
        self._save_flags = save_flags

    self._save_image(crop, result.rank, result.level, suffix)

    # 恢复原始设置
    self._save_flags = original_flags

    return result
```

## 向后兼容性

- 默认 `save_flags=SAVE_ALL`，保持当前行为
- `suffix` 和 `save_flags` 都是可选参数，现有代码无需修改
- 批量识别方法支持统一后缀（所有图片使用相同后缀）

## 错误处理

- `suffix` 参数自动清理不安全的文件名字符（如 `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`）
- 后缀过长时进行截断（建议限制在 100 字符以内）
- 无效的 `save_flags` 值抛出 `ValueError`

## 测试考虑

1. 测试各个 `save_flags` 组合的保存行为
2. 测试 `suffix` 参数的文件名生成
3. 测试调用时 `save_flags` 临时覆盖功能
4. 测试后缀中的特殊字符处理
5. 测试异步方法的同等功能
