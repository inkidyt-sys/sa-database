import os
from PIL import Image

def bmp_to_jpg_converter(directory_path="."):
    """
    将指定目录下（包括子目录）的所有 .bmp 文件转换为 .jpg 格式。

    :param directory_path: 要处理的目录路径，默认为当前目录。
    """
    # 遍历目录及其子目录
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            # 检查文件是否是 .bmp 格式（不区分大小写）
            if file.lower().endswith(".bmp"):
                # 构造完整的文件路径
                bmp_file_path = os.path.join(root, file)
                
                # 构造新的文件名和路径 (替换扩展名为 .jpg)
                # os.path.splitext(file) 会将文件名分割成 (name, ext)
                base_name = os.path.splitext(file)[0]
                jpg_file_path = os.path.join(root, base_name + ".jpg")
                
                try:
                    # 使用 Pillow 打开 BMP 图像
                    img = Image.open(bmp_file_path)
                    
                    # 转换并保存为 JPG
                    # 注意: JPEG 格式不支持透明度，如果原图是 RGBA 模式，
                    # 最好先转换为 RGB 模式，否则保存时可能会报错或效果不佳。
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                        
                    # 保存为 JPG 格式
                    # quality 参数范围 1(差) 到 95(好), 默认是 75。
                    img.save(jpg_file_path, 'JPEG', quality=90)
                    
                    print(f"成功转换: {bmp_file_path} -> {jpg_file_path}")
                    
                    # 如果需要，可以在转换成功后删除原 BMP 文件，取消下面一行的注释即可：
                    # os.remove(bmp_file_path) 
                    
                except Exception as e:
                    print(f"转换失败: {bmp_file_path}, 错误信息: {e}")

# ----------------- 使用方法 -----------------
# 1. 如果你想转换脚本所在目录下的 BMP 文件：
# bmp_to_jpg_converter()

# 2. 如果你想指定一个目录（例如 'C:/MyImages' 或 './images'）：
# 将下面的路径替换成你实际的目录
target_directory = "."  # 默认为脚本当前目录

# 如果你想让用户输入目录，可以使用 input()
# target_directory = input("请输入要转换的目录路径 (留空则默认为当前目录): ") or "."

bmp_to_jpg_converter(target_directory)
print("\n批量转换完成。")