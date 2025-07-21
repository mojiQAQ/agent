# 火山引擎图生图API使用指南

## 1. 环境准备

### 安装依赖
```bash
# 安装基础依赖
pip install requests pillow

# 可选：安装官方SDK（推荐）
pip install volcengine
```

### 获取访问密钥
1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 进入访问控制 > 访问密钥管理
3. 创建或获取您的 Access Key ID 和 Secret Access Key

## 2. 配置访问密钥

### 方法1: 环境变量（推荐）
```bash
export VOLCENGINE_ACCESS_KEY_ID="your_access_key_id"
export VOLCENGINE_SECRET_ACCESS_KEY="your_secret_access_key"
```

### 方法2: 直接在代码中配置
```python
ACCESS_KEY_ID = "your_access_key_id"
SECRET_ACCESS_KEY = "your_secret_access_key"
```

## 3. 使用方法

### 基本使用
```python
from volcengine_img2img_official import generate_image_from_url

# 从图片URL生成新图片
saved_path = generate_image_from_url(
    image_url="https://example.com/input.jpg",
    output_path="output/generated.jpg",
    access_key_id="your_access_key_id",
    secret_access_key="your_secret_access_key",
    prompt="高质量人像写真，专业摄影",
    gpen=0.4,        # 人脸增强
    skin=0.3,        # 皮肤平滑
    gen_mode="portrait",  # 生成模式
    width=1024,
    height=1024
)
print(f"生成成功: {saved_path}")
```

### 高级使用
```python
from volcengine_img2img_official import VolcengineImg2ImgOfficial

# 创建客户端
client = VolcengineImg2ImgOfficial(access_key_id, secret_access_key)

# 提交异步任务
submit_result = client.image_to_image(
    image_url="https://example.com/input.jpg",
    prompt="艺术肖像，油画风格",
    gen_mode="creative"
)

# 获取任务ID
task_id = submit_result["data"]["task_id"]

# 等待任务完成
final_result = client.get_task_result(task_id)

# 保存结果
saved_path = client.save_result(final_result, "output/result.jpg")
```

## 4. 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| image_url | str | 必需 | 输入图片的URL |
| prompt | str | "" | 生成提示词 |
| gpen | float | 0.4 | 人脸增强强度 (0.0-1.0) |
| skin | float | 0.3 | 皮肤平滑程度 (0.0-1.0) |
| skin_unifi | float | 0.0 | 皮肤统一程度 (0.0-1.0) |
| width | int | 1024 | 输出图片宽度 |
| height | int | 1024 | 输出图片高度 |
| gen_mode | str | "creative" | 生成模式 |
| seed | int | -1 | 随机种子，-1表示随机 |

### 生成模式说明
- `creative`: 创意模式，适合艺术创作
- `portrait`: 人像模式，适合人像写真
- `professional`: 专业模式，适合商务用途
- `artistic`: 艺术模式，适合艺术创作

## 5. 文件说明

- `volcengine_img2img_official.py`: 基于官方SDK的实现
- `volcengine_img2img_simple.py`: 简化版实现
- `test_volcengine_img2img.py`: 测试脚本
- `VOLCENGINE_SETUP.md`: 本使用指南

## 6. 运行测试

```bash
# 设置环境变量
export VOLCENGINE_ACCESS_KEY_ID="your_key"
export VOLCENGINE_SECRET_ACCESS_KEY="your_secret"

# 运行测试
python test_volcengine_img2img.py
```

## 7. 注意事项

1. **API限制**: 请注意API的调用频率限制
2. **图片格式**: 支持常见的图片格式 (JPG, PNG, WEBP等)
3. **图片大小**: 输入图片建议不超过10MB
4. **网络连接**: 确保网络可以访问火山引擎API和图片URL
5. **异步处理**: 图生图是异步任务，需要轮询获取结果

## 8. 错误处理

常见错误及解决方案：

- **认证失败**: 检查访问密钥是否正确
- **网络超时**: 检查网络连接，增加超时时间
- **图片下载失败**: 确认图片URL可访问
- **任务失败**: 检查输入参数是否合理

## 9. API文档参考

- [火山引擎Python SDK](https://github.com/volcengine/volc-sdk-python)
- [图生图3.0-人像写真文档](https://www.volcengine.com/docs/85128/1602212)
- [Python SDK使用指南](https://www.volcengine.com/docs/6444/1340578)