# 保存功能增强设计文档

**日期**: 2026-03-22
**状态**: 设计中
**作者**: Claude

## 概述

增强 `AIAwareLegendRecognizer` 的图片保存功能：
1. 使用二进制标志位灵活控制是否保存 Legendary/Unknown 图片
2. 当保存 Unknown 图片时，可选择是否在文件名中添加原始 URL

## 动机

用户反馈 Unknown 图片需要人工审核原图，希望：
- 能灵活控制是否保存各类图片，节省存储空间
- 保存 Unknown 时能记录原始 URL，便于追溯

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
    save_flags: int = SAVE_ALL,          # 新增：保存选项标志
    save_unknown_with_url: bool = False, # 新增：Unknown 文件名是否包含 URL
    legend_counter: int = 0,             # 新增：Legendary 计数器初始值
    unknown_counter: int = 0,            # 新增：Unknown 计数器初始值
):
    # 验证 save_flags 参数
    if not isinstance(save_flags, int) or save_flags < 0 or save_flags > self.SAVE_ALL:
        raise ValueError(
            f"save_flags must be one of: "
            f"SAVE_NONE({self.SAVE_NONE}), SAVE_UNKNOWN({self.SAVE_UNKNOWN}), "
            f"SAVE_LEGENDARY({self.SAVE_LEGENDARY}), SAVE_ALL({self.SAVE_ALL})"
        )
    self._save_flags = save_flags
    self._save_unknown_with_url = save_unknown_with_url
    self._legend_counter = legend_counter
    self._unknown_counter = unknown_counter
```

### 3. 识别方法参数扩展

```python
def recognize_ai(
    self,
    image_source,
    save_flags: int = None  # 临时覆盖初始化设置
) -> RecognitionResult

def recognize_batch_ai(
    self,
    sources: List[str],
    save_flags: int = None
) -> List[RecognitionResult]

async def recognize_ai_async(
    self,
    image_source,
    save_flags: int = None
) -> RecognitionResult

async def recognize_batch_ai_async(
    self,
    sources: List[str],
    save_flags: int = None
) -> List[RecognitionResult]
```

## 使用示例

```python
from rank_detector_core import AIAwareLegendRecognizer

# 默认行为：保存所有图片，Unknown 文件名不包含 URL
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
)

# Unknown 文件名包含 URL
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
    save_unknown_with_url=True,
)
result = recognizer.recognize_ai("https://example.com/screenshot.png")
# Unknown: Unknown_001_url_https_example.com_screenshot.png
# Legendary: Legend_1898_000.png (Legendary 不添加 URL)

# 只保存 Unknown
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
    save_flags=AIAwareLegendRecognizer.SAVE_UNKNOWN,
)

# 调用时临时只保存 Legendary
result = recognizer.recognize_ai(
    "test.png",
    save_flags=AIAwareLegendRecognizer.SAVE_LEGENDARY
)
```

## 实现细节

### 1. URL 提取函数

```python
def _extract_url(self, image_source) -> Optional[str]:
    """从 image_source 中提取 URL（仅当它是 HTTP(S) URL 时）"""
    from pathlib import Path

    # 字符串 URL
    if isinstance(image_source, str):
        if image_source.startswith("http://") or image_source.startswith("https://"):
            return image_source
    # Path 对象不视为 URL
    return None
```

### 2. URL 清理函数

```python
def _sanitize_url(self, url: str) -> str:
    """清理 URL 使其适合作为文件名"""
    from urllib.parse import unquote

    # 移除协议前缀
    url = url.replace("http://", "").replace("https://", "")

    # URL 解码（处理 %20 等）
    url = unquote(url)

    # 替换不安全字符
    unsafe_chars = '/:?#\\\'"<>|*'
    for char in unsafe_chars:
        url = url.replace(char, '_')

    # 限制长度（避免文件名过长）
    return url[:100].strip()
```

### 3. `_save_image` 方法修改

```python
def _save_image(
    self,
    img: np.ndarray,
    rank: str,
    level: int,
    original_url: str = None,  # 新增：原始 URL
    save_flags: int = None     # 新增：临时覆盖保存标志
) -> Optional[str]:
    """保存图片到对应目录，返回文件路径或 None

    注意：计数器仅在成功保存后递增，不保存时计数器不变
    """

    # 使用传入的 save_flags 或实例默认值
    flags = save_flags if save_flags is not None else self._save_flags

    # 确定是否需要保存
    if rank == "Legendary":
        should_save = flags & self.SAVE_LEGENDARY
    else:  # Unknown 或其他值都视为 Unknown
        should_save = flags & self.SAVE_UNKNOWN

    if not should_save:
        return None

    # 构建文件名（在确认保存后才递增计数器，避免编号断层）
    if rank == "Legendary":
        filename = f"Legend_{level}_{self._legend_counter:03d}"
        self._legend_counter += 1
    else:
        filename = f"Unknown_{self._unknown_counter:03d}"
        self._unknown_counter += 1

        # Unknown 图片：如果启用且存在 URL，添加到文件名
        if self._save_unknown_with_url and original_url:
            clean_url = self._sanitize_url(original_url)
            if clean_url:  # 只有清理后有内容才添加
                filename = f"{filename}_url_{clean_url}"

    filename += ".png"

    # 确定保存目录并保存
    save_dir = self.legend_dir if rank == "Legendary" else self.unknown_dir
    filepath = save_dir / filename

    try:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(filepath), img_bgr)
    except OSError as e:
        print(f"Warning: Failed to save image to {filepath}: {e}")
        return None

    return str(filepath)
```

### 4. 识别方法修改

```python
def recognize_ai(self, image_source, save_flags: int = None):
    # 提取 URL（如果是网络图片）
    original_url = self._extract_url(image_source)

    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)

    crop = self._crop_image(img) if self.auto_crop else img
    result = self._recognize(crop)

    # 保存时传递原始 URL 和 save_flags
    self._save_image(crop, result.rank, result.level, original_url, save_flags)

    return result


# 批量识别方法（所有图片使用相同的 save_flags）
def recognize_batch_ai(self, sources: List[str], save_flags: int = None):
    results = []
    for source in sources:
        result = self.recognize_ai(source, save_flags)
        results.append(result)
    return results


# 异步识别方法（逻辑相同）
async def recognize_ai_async(self, image_source, save_flags: int = None):
    original_url = self._extract_url(image_source)
    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)
    crop = self._crop_image(img) if self.auto_crop else img
    result = await self._arecognize(crop)
    self._save_image(crop, result.rank, result.level, original_url, save_flags)
    return result


async def recognize_batch_ai_async(self, sources: List[str], save_flags: int = None):
    tasks = [self.recognize_ai_async(src, save_flags) for src in sources]
    return await asyncio.gather(*tasks)
```

## 向后兼容性

- 默认 `save_flags=SAVE_ALL`，保持当前行为（保存所有图片）
- 默认 `save_unknown_with_url=False`，保持当前文件名格式
- `save_flags` 是可选参数，现有代码无需修改
- `_save_image` 返回类型从 `str` 变为 `Optional[str]`（私有方法，影响有限）

**批量方法行为**: 批量识别方法对批次内所有图片应用相同的 `save_flags`。如需为每张图片设置不同的保存行为，请单独调用 `recognize_ai`。

## 文件名格式

| 类型 | save_unknown_with_url=False | save_unknown_with_url=True |
|------|----------------------------|----------------------------|
| Legendary | `Legend_1898_000.png` | `Legend_1898_000.png` (不变) |
| Unknown (URL) | `Unknown_001.png` | `Unknown_001_url_example.com_screenshot.png` |
| Unknown (本地) | `Unknown_001.png` | `Unknown_001.png` (无 URL) |

## 线程安全

- `save_flags` 参数通过方法传递，不修改实例变量，线程安全
- `save_unknown_with_url` 是初始化配置，实例变量只读
- **计数器**: `_legend_counter` 和 `_unknown_counter` 在多线程环境下可能产生竞态条件
  - 单线程使用场景：无问题
  - 多线程使用场景：如需严格递增，可使用 `threading.Lock` 保护计数器（当前未实现）

## 错误处理

- **save_flags 验证**: 初始化时验证，非整数或超出范围抛出 `ValueError`
- **目录创建失败**: 捕获 `OSError`，打印警告并返回 `None`
- **文件名过长**: URL 清理后限制在 100 字符，避免超过系统限制（Windows 260 字符）
- **磁盘空间不足**: 由 `cv2.imwrite` 抛出异常，捕获后打印警告

## 计数器生命周期

- 计数器在实例化时初始化，默认为 0
- 每次成功保存图片后递增，不保存时不变
- 实例销毁后计数器状态丢失
- 如需持久化，可通过 `legend_counter` 和 `unknown_counter` 参数恢复：
  ```python
  # 保存计数器状态
  legend_count = recognizer._legend_counter
  unknown_count = recognizer._unknown_counter

  # 新实例恢复计数器
  recognizer = AIAwareLegendRecognizer(
      ...,
      legend_counter=legend_count,
      unknown_counter=unknown_count
  )
  ```

## 测试考虑

1. 测试各个 `save_flags` 组合的保存行为
2. 测试 `save_unknown_with_url=True` 时的文件名生成
3. 测试 URL 的提取和清理
4. 测试本地文件（无 URL）的行为
5. 测试 Legendary 图片不受 `save_unknown_with_url` 影响
6. 测试调用时 `save_flags` 临时覆盖功能
7. 测试异步方法的同等功能
