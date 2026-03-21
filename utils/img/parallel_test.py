"""
并行测试所有裁切后的图标
"""
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2

sys.path.insert(0, str(Path(__file__).parent))
from doubao_recognizer import recognize_from_array, encode_image_from_array

DATA_DIR = Path("d:/project/rank_detector/data")

def get_expected_rank(path: Path) -> tuple:
    """从路径解析期望的段位和等级"""
    folder = path.parent.name
    name = path.stem

    rank_map = {
        "Bro": "Bronze",
        "Sli": "Silver",
        "Gold": "Gold",
        "Dia": "Diamond",
        "Leg": "Legendary",
    }

    rank = rank_map.get(folder, "")

    # 从文件名提取等级
    # 格式: Bro_1.png, Leg_4.png
    parts = name.split("_")
    if len(parts) >= 2:
        level = int(parts[1])
    else:
        level = 0

    return rank, level

def load_image(path: Path):
    """读取图片 (支持中文路径)"""
    img = cv2.imread(str(path))
    if img is None:
        # 尝试用 PIL 读取再转换
        from PIL import Image
        pil_img = Image.open(str(path))
        pil_img = pil_img.convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img

def test_image(path: Path):
    """测试单张图片"""
    expected_rank, expected_level = get_expected_rank(path)

    # 读取图片
    img = load_image(path)
    if img is None:
        return {
            "path": str(path),
            "expected": f"{expected_rank}_{expected_level}",
            "recognized": "FAILED",
            "confidence": 0,
            "correct": False,
            "error": "Cannot load image"
        }

    # 识别
    result = recognize_from_array(img, auto_crop=False)

    if result:
        correct = (result.rank == expected_rank and result.level == expected_level)
        return {
            "path": str(path),
            "expected": f"{expected_rank}_{expected_level}",
            "recognized": f"{result.rank}_{result.level}",
            "confidence": result.confidence,
            "correct": correct,
            "error": None
        }
    else:
        return {
            "path": str(path),
            "expected": f"{expected_rank}_{expected_level}",
            "recognized": "FAILED",
            "confidence": 0,
            "correct": False,
            "error": "Recognition failed"
        }

def main():
    # 收集所有图片
    images = list(DATA_DIR.glob("*/*.png"))
    print(f"Found {len(images)} images")

    results = []
    correct_count = 0
    fail_count = 0

    # 并行测试
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_image, img): img for img in images}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            status = "[OK]" if result["correct"] else "[FAIL]"
            print(f"{status} {Path(result['path']).name}: expected={result['expected']}, got={result['recognized']} ({result['confidence']:.0%})")

            if result["correct"]:
                correct_count += 1
            else:
                fail_count += 1

    print(f"\n========== Results ==========")
    print(f"Total: {len(images)}")
    print(f"Correct: {correct_count} ({correct_count/len(images)*100:.1f}%)")
    print(f"Failed: {fail_count} ({fail_count/len(images)*100:.1f}%)")

    # 按错误类型分组
    errors = [r for r in results if not r["correct"]]
    if errors:
        print(f"\n========== Errors ==========")
        for r in errors:
            print(f"  {Path(r['path']).name}: expected={r['expected']}, got={r['recognized']}")

if __name__ == "__main__":
    main()