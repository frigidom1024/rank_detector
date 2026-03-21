"""
快速测试 YOLOv8 图标检测模型
"""
from ultralytics import YOLO
import cv2
from pathlib import Path

# 类别名称映射
CLASS_NAMES = {
    0: "Bronze_1", 1: "Bronze_2", 2: "Bronze_3", 3: "Bronze_4", 4: "Bronze_5",
    5: "Silver_1", 6: "Silver_2", 7: "Silver_3", 8: "Silver_4", 9: "Silver_5",
    10: "Gold_1", 11: "Gold_2", 12: "Gold_3", 13: "Gold_4", 14: "Gold_5",
    15: "Diamond_1", 16: "Diamond_2", 17: "Diamond_3", 18: "Diamond_4", 19: "Diamond_5",
    20: "Legendary_0",  # Legendary 后续用OCR识别排名
}

# 段位颜色
COLORS = {
    "Bronze": (205, 127, 50),   # 棕色
    "Silver": (192, 192, 192),  # 银色
    "Gold": (255, 215, 0),      # 金色
    "Diamond": (185, 242, 255), # 钻蓝色
    "Legendary": (255, 0, 255), # 紫色
}


def get_rank_name(class_name):
    """从类别名称获取段位名称"""
    return class_name.split("_")[0]


def test_model(image_path, model_path="d:/project/rank_detector/runs/rank_detector4/weights/best.pt"):
    """
    测试模型检测

    Args:
        image_path: 测试图片路径
        model_path: 模型权重路径
    """
    # 加载模型
    print(f"加载模型: {model_path}")
    model = YOLO(model_path)

    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图片 {image_path}")
        return

    print(f"图片尺寸: {image.shape}")

    # 运行检测
    print("\n开始检测...")
    results = model(image, verbose=False)

    # 获取检测结果
    result = results[0]
    boxes = result.boxes
    classes = boxes.cls  # 类别ID
    confidences = boxes.conf  # 置信度

    # 绘制结果
    annotated = image.copy()

    print(f"\n检测到 {len(boxes)} 个图标:")
    print("-" * 50)

    if len(boxes) == 0:
        print("未检测到任何图标")
        return

    for i, (box, cls, conf) in enumerate(zip(boxes, classes, confidences)):
        # 获取边界框坐标
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        # 获取类别信息
        class_id = int(cls)
        class_name = CLASS_NAMES.get(class_id, f"Unknown_{class_id}")
        rank_name = get_rank_name(class_name)

        # 获取颜色
        color = COLORS.get(rank_name, (0, 255, 0))

        # 绘制边界框
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

        # 绘制标签
        label = f"{class_name} {conf:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(annotated, (int(x1), int(y1) - label_size[1] - 10), (int(x2), int(y1)), color, -1)
        cv2.putText(annotated, label, (int(x1) + 5, int(y1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 打印结果
        print(f"  [{i+1}] {class_name}")
        print(f"      位置: ({int(x1)}, {int(y1)}) -> ({int(x2)}, {int(y2)})")
        print(f"      置信度: {conf:.4f}")
        print()

    # 保存结果
    output_path = Path(image_path).stem + "_result" + Path(image_path).suffix
    output_path = Path(image_path).parent / output_path
    cv2.imwrite(str(output_path), annotated)
    print(f"结果已保存到: {output_path}")

    # 显示结果（如果在支持的环境中）
    try:
        cv2.imshow("Detection Result", annotated)
        print("\n按任意键关闭窗口...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except:
        pass

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 命令行指定图片
        image_path = sys.argv[1]
    else:
        # 使用默认测试图片
        # 从训练集中随机选一张测试
        import random
        test_images = list(Path("d:/project/rank_detector/dataset/images/val").glob("*.jpg"))
        if test_images:
            image_path = str(random.choice(test_images))
        else:
            print("错误: 没有找到测试图片")
            print("使用方法: python test_model.py <图片路径>")
            sys.exit(1)

    print("=" * 50)
    print("YOLOv8 图标检测模型测试")
    print("=" * 50)
    print(f"输入图片: {image_path}")
    print("=" * 50)

    test_model(image_path)
