"""
图标截取工具
用于从游戏截图批量截取段位图标，供后续训练使用

使用方法:
    # 单张图片
    python crop_tool.py screenshot.png

    # 批量处理目录
    python crop_tool.py ./screenshots/

    # 指定输出目录
    python crop_tool.py screenshot.png -o ./output/

    # 指定区域 (会覆盖配置文件中的默认值)
    python crop_tool.py screenshot.png --region 0.0 0.0 0.1 0.25
"""
import cv2
import numpy as np
import sys
import os
import glob
import argparse
from pathlib import Path
from datetime import datetime

# ============================================
# 区域配置 (调整这些值来修改截取区域)
# ============================================
DEFAULT_REGION = {
    "name": "段位图标",
    "x1": 0.00,  # 左侧起始 (0.0 = 左边缘, 1.0 = 右边缘)
    "y1": 0.00,  # 顶部起始
    "x2": 0.10,  # 右侧结束
    "y2": 0.25,  # 底部结束
}

# 输出配置
OUTPUT_BASE = "d:/project/rank_detector/training_data/raw_crops"
# ============================================


class IconCropper:
    """图标截取器"""

    def __init__(self, region=None, output_dir=None):
        self.region = region or DEFAULT_REGION
        self.output_dir = output_dir or OUTPUT_BASE
        os.makedirs(self.output_dir, exist_ok=True)

    def get_crop_params(self, img_shape):
        """根据图片尺寸和百分比计算实际像素坐标"""
        h, w = img_shape[:2]
        x1 = int(w * self.region["x1"])
        y1 = int(h * self.region["y1"])
        x2 = int(w * self.region["x2"])
        y2 = int(h * self.region["y2"])
        return x1, y1, x2, y2

    def crop_image(self, image_path, save_debug=False):
        """
        截取单张图片的图标区域

        Args:
            image_path: 图片路径
            save_debug: 是否保存调试图片

        Returns:
            dict: 包含截取结果的字典
        """
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": f"无法读取图片: {image_path}"}

        h, w = img.shape[:2]
        x1, y1, x2, y2 = self.get_crop_params(img.shape)
        crop_w, crop_h = x2 - x1, y2 - y1

        # 截取
        roi = img[y1:y2, x1:x2]

        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(image_path).stem
        output_name = f"{base_name}_{timestamp}.png"
        output_path = os.path.join(self.output_dir, output_name)

        # 保存
        cv2.imwrite(output_path, roi)

        result = {
            "success": True,
            "input_path": image_path,
            "output_path": output_path,
            "image_size": (w, h),
            "crop_size": (crop_w, crop_h),
            "crop_region": (x1, y1, x2, y2),
        }

        # 保存调试图片
        if save_debug:
            self._save_debug_image(img, roi, x1, y1, x2, y2, base_name)

        return result

    def _save_debug_image(self, img, roi, x1, y1, x2, y2, base_name):
        """保存调试图片"""
        debug_dir = os.path.join(self.output_dir, "_debug")
        os.makedirs(debug_dir, exist_ok=True)

        # 缩放原图
        scale = 0.5
        img_small = cv2.resize(img, (int(img.shape[1]*scale), int(img.shape[0]*scale)))
        x1_s, y1_s, x2_s, y2_s = int(x1*scale), int(y1*scale), int(x2*scale), int(y2*scale)

        # 画框
        cv2.rectangle(img_small, (x1_s, y1_s), (x2_s, y2_s), (0, 255, 0), 3)

        # 放大ROI，保持相同高度
        target_height = img_small.shape[0]
        roi_scale = target_height / roi.shape[0]
        target_width = int(roi.shape[1] * roi_scale)
        roi_large = cv2.resize(roi, (target_width, target_height), interpolation=cv2.INTER_NEAREST)

        # 拼接
        debug_img = np.hstack([img_small, roi_large])
        debug_path = os.path.join(debug_dir, f"{base_name}_debug.png")
        cv2.imwrite(debug_path, debug_img)

    def process_batch(self, input_paths, save_debug=False):
        """
        批量处理图片

        Args:
            input_paths: 图片路径列表
            save_debug: 是否保存调试图片

        Returns:
            list: 处理结果列表
        """
        results = []
        success_count = 0
        fail_count = 0

        for i, path in enumerate(input_paths):
            print(f"[{i+1}/{len(input_paths)}] 处理: {path}")
            result = self.crop_image(path, save_debug)
            results.append(result)

            if result["success"]:
                success_count += 1
                print(f"  [OK] 成功 ({result['crop_size'][0]}x{result['crop_size'][1]}px)")
            else:
                fail_count += 1
                print(f"  [FAIL] 失败: {result.get('error', '未知错误')}")

        return results, success_count, fail_count

    def process_directory(self, dir_path, pattern="*.png", save_debug=False):
        """
        处理目录下的所有图片

        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            save_debug: 是否保存调试图片

        Returns:
            tuple: (results, success_count, fail_count)
        """
        # 查找图片
        patterns = [pattern] if pattern else ["*.png", "*.jpg", "*.jpeg", "*.webp"]
        input_paths = []

        for p in patterns:
            input_paths.extend(glob.glob(os.path.join(dir_path, p)))
            input_paths.extend(glob.glob(os.path.join(dir_path, p.upper())))

        input_paths = sorted(set(input_paths))

        if not input_paths:
            print(f"警告: 在 {dir_path} 中没有找到匹配 {pattern} 的图片")
            return [], 0, 0

        print(f"找到 {len(input_paths)} 张图片")
        print("=" * 60)

        return self.process_batch(input_paths, save_debug)


def main():
    parser = argparse.ArgumentParser(
        description="图标截取工具 - 从游戏截图截取段位图标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python crop_tool.py screenshot.png
  python crop_tool.py ./screenshots/
  python crop_tool.py screenshot.png -o ./output/
  python crop_tool.py screenshot.png --region 0.0 0.0 0.1 0.25
  python crop_tool.py ./screenshots/ -d  # 保存调试图片
        """
    )

    parser.add_argument("input", help="输入图片路径或目录")
    parser.add_argument("-o", "--output", help="输出目录 (默认: %(default)s)", default=OUTPUT_BASE)
    parser.add_argument("-d", "--debug", action="store_true", help="保存调试图片")
    parser.add_argument("-p", "--pattern", default="*.png", help="目录模式 (默认: %(default)s)")
    parser.add_argument("--region", nargs=4, type=float,
                        metavar=("X1", "Y1", "X2", "Y2"),
                        help="覆盖区域配置 (0-1的小数)")

    args = parser.parse_args()

    # 解析区域配置
    region = DEFAULT_REGION.copy()
    if args.region:
        region["x1"] = args.region[0]
        region["y1"] = args.region[1]
        region["x2"] = args.region[2]
        region["y2"] = args.region[3]
        print(f"使用自定义区域: x=[{region['x1']}, {region['x2']}], y=[{region['y1']}, {region['y2']}]")

    # 创建截取器
    cropper = IconCropper(region=region, output_dir=args.output)

    print("=" * 60)
    print("图标截取工具")
    print("=" * 60)
    print(f"输出目录: {args.output}")
    print(f"截取区域: x=[{region['x1']*100:.1f}%-{region['x2']*100:.1f}%], "
          f"y=[{region['y1']*100:.1f}%-{region['y2']*100:.1f}%]")
    print("=" * 60)

    # 判断输入类型
    input_path = args.input
    if os.path.isdir(input_path):
        # 目录
        results, success, fail = cropper.process_directory(input_path, args.pattern, args.debug)
    elif os.path.isfile(input_path):
        # 单文件
        results, success, fail = cropper.process_batch([input_path], args.debug)
    else:
        print(f"错误: 输入不存在: {input_path}")
        sys.exit(1)

    # 打印统计
    print()
    print("=" * 60)
    print("处理完成!")
    print(f"成功: {success}")
    print(f"失败: {fail}")
    print(f"输出目录: {args.output}")
    print("=" * 60)

    # 列出输出文件
    output_files = os.listdir(args.output)
    image_files = [f for f in output_files if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    print(f"\n共生成 {len(image_files)} 个截取文件")
    if image_files:
        print("前10个文件:")
        for f in sorted(image_files)[:10]:
            print(f"  {f}")


if __name__ == "__main__":
    main()
