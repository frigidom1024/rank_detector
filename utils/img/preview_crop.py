"""
预览截取区域工具
用法: python preview_crop.py <图片路径> [x1% y1% x2% y2%]
示例: python preview_crop.py screenshot.png 0.0 0.0 0.08 0.15
      python preview_crop.py screenshot.png 0.85 0.0 1.0 0.15
"""
import cv2
import numpy as np
import sys
import os

# ============================================
# 区域配置 (调整这些值来修改截取区域)
# ============================================
DEFAULT_REGION = {
    "name": "段位图标",
    "x1": 0.00,  # 左侧起始 (0.0 = 左边缘, 1.0 = 右边缘)
    "y1": 0.00,  # 顶部起始
    "x2": 0.1,  # 右侧结束
    "y2": 0.25,  # 底部结束
}

OUTPUT_DIR = "d:/project/rank_detector/crops"  # 输出目录
# ============================================


def parse_args():
    """解析命令行参数"""
    if len(sys.argv) < 2:
        print("用法: python preview_crop.py <图片路径> [x1% y1% x2% y2%]")
        print("示例: python preview_crop.py screenshot.png 0.0 0.0 0.08 0.15")
        sys.exit(1)

    image_path = sys.argv[1]

    # 解析可选的区域参数
    if len(sys.argv) >= 6:
        try:
            DEFAULT_REGION["x1"] = float(sys.argv[2])
            DEFAULT_REGION["y1"] = float(sys.argv[3])
            DEFAULT_REGION["x2"] = float(sys.argv[4])
            DEFAULT_REGION["y2"] = float(sys.argv[5])
        except ValueError:
            print("错误: 区域参数必须是数字")
            sys.exit(1)

    return image_path


def create_output_dir():
    """创建输出目录"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_crop_params(img_shape):
    """根据图片尺寸和百分比计算实际像素坐标"""
    h, w = img_shape[:2]
    x1 = int(w * DEFAULT_REGION["x1"])
    y1 = int(h * DEFAULT_REGION["y1"])
    x2 = int(w * DEFAULT_REGION["x2"])
    y2 = int(h * DEFAULT_REGION["y2"])
    return x1, y1, x2, y2


def draw_region(img, x1, y1, x2, y2):
    """在图片上绘制截取区域"""
    h, w = img.shape[:2]
    display = img.copy()

    # 计算缩放比例（使图片适应屏幕）
    max_width = 1280
    max_height = 720
    scale = min(max_width / w, max_height / h, 1.0)

    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        display = cv2.resize(display, (new_w, new_h))
        # 缩放坐标
        x1, y1, x2, y2 = int(x1*scale), int(y1*scale), int(x2*scale), int(y2*scale)

    # 颜色
    color = (0, 255, 0)  # 绿色

    # 画矩形边框
    cv2.rectangle(display, (x1, y1), (x2, y2), color, 3)

    # 标注文字
    name = DEFAULT_REGION["name"]
    label = f"{name} [{x1}:{x2}, {y1}:{y2}]"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2

    # 文字背景
    (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
    bg_x1 = x1
    bg_y1 = max(0, y1 - text_h - 10)
    bg_x2 = x1 + text_w
    bg_y2 = y1
    cv2.rectangle(display, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)

    # 文字
    cv2.putText(display, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness)

    return display, scale


def extract_and_save_crop(img, x1, y1, x2, y2, image_path):
    """截取并保存区域"""
    # 确保坐标有效
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    # 截取
    roi = img[y1:y2, x1:x2]

    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    ext = ".png"
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_crop{ext}")

    # 保存
    cv2.imwrite(output_path, roi)
    print(f"已保存截取图片: {output_path}")

    # 放大保存
    roi_large = cv2.resize(roi, (roi.shape[1] * 4, roi.shape[0] * 4), interpolation=cv2.INTER_NEAREST)
    output_large_path = os.path.join(OUTPUT_DIR, f"{base_name}_crop_large{ext}")
    cv2.imwrite(output_large_path, roi_large)
    print(f"已保存放大版: {output_large_path}")

    return output_path, roi


def create_comparison_view(img, roi, x1, y1, x2, y2):
    """创建对比视图"""
    h, w = img.shape[:2]

    # 缩放原图
    scale = 0.5
    img_small = cv2.resize(img, (int(w*scale), int(h*scale)))
    x1_s, y1_s, x2_s, y2_s = int(x1*scale), int(y1*scale), int(x2*scale), int(y2*scale)

    # 缩放ROI
    roi_display = cv2.resize(roi, (roi.shape[1]*2, roi.shape[0]*2), interpolation=cv2.INTER_NEAREST)

    # 在缩略图上画框
    cv2.rectangle(img_small, (x1_s, y1_s), (x2_s, y2_s), (0, 255, 0), 2)

    # 拼接到一起
    top = img_small
    bottom = roi_display

    # 添加标题
    header = np.full((40, top.shape[1], 3), (0, 100, 0), dtype=np.uint8)
    cv2.putText(header, "原图 (缩放50%)", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    header2 = np.full((40, bottom.shape[1], 3), (0, 100, 0), dtype=np.uint8)
    cv2.putText(header2, f"截取区域 (放大400%) - {roi.shape[1]}x{roi.shape[0]}px", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    top = np.vstack([header, top])
    bottom = np.vstack([header2, bottom])

    # 如果宽度不同，填充到一致
    if top.shape[1] != bottom.shape[1]:
        max_w = max(top.shape[1], bottom.shape[1])
        top_padded = np.zeros((top.shape[0], max_w, 3), dtype=np.uint8)
        bottom_padded = np.zeros((bottom.shape[0], max_w, 3), dtype=np.uint8)
        top_padded[:, :top.shape[1]] = top
        bottom_padded[:, :bottom.shape[1]] = bottom
        top = top_padded
        bottom = bottom_padded

    comparison = np.vstack([top, bottom])

    return comparison


def main():
    create_output_dir()

    image_path = parse_args()

    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误: 无法读取图片 {image_path}")
        sys.exit(1)

    h, w = img.shape[:2]

    print("=" * 60)
    print("预览截取区域工具")
    print("=" * 60)
    print(f"图片: {image_path}")
    print(f"尺寸: {w}x{h}px")
    print()
    print("当前区域配置:")
    print(f"  名称: {DEFAULT_REGION['name']}")
    print(f"  左边界: {DEFAULT_REGION['x1']*100:.1f}% (x={int(w*DEFAULT_REGION['x1'])})")
    print(f"  上边界: {DEFAULT_REGION['y1']*100:.1f}% (y={int(h*DEFAULT_REGION['y1'])})")
    print(f"  右边界: {DEFAULT_REGION['x2']*100:.1f}% (x={int(w*DEFAULT_REGION['x2'])})")
    print(f"  下边界: {DEFAULT_REGION['y2']*100:.1f}% (y={int(h*DEFAULT_REGION['y2'])})")
    print()
    print("调整方法: 修改脚本顶部的 DEFAULT_REGION 字典")
    print("=" * 60)

    # 计算像素坐标
    x1, y1, x2, y2 = get_crop_params(img.shape)
    pixel_w = x2 - x1
    pixel_h = y2 - y1

    print(f"\n截取尺寸: {pixel_w}x{pixel_h}px")

    # 绘制预览
    display, scale = draw_region(img, x1, y1, x2, y2)

    # 显示预览窗口
    print("\n显示预览窗口...")
    cv2.imshow("Crop Preview - 按任意键显示截取结果", display)

    # 等待按键
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 截取并保存
    output_path, roi = extract_and_save_crop(img, x1, y1, x2, y2, image_path)

    # 创建对比视图
    comparison = create_comparison_view(img, roi, x1, y1, x2, y2)
    cv2.imwrite(os.path.join(OUTPUT_DIR, "comparison.png"), comparison)
    print(f"已保存对比图: comparison.png")

    # 显示对比视图
    print("\n显示对比视图...")
    cv2.imshow("Comparison - 按任意键关闭所有窗口", comparison)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("\n完成!")


if __name__ == "__main__":
    main()
