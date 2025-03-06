# 心理问卷自动填写工具

这是一个用于自动填写心理问卷的Python工具。该工具使用AI辅助完成问卷答题，支持自动登录、获取问卷内容、AI分析和自动填写答案等功能。

## 功能特点

- 自动登录系统
- 自动获取问卷列表
- 解析问卷内容和问题
- 使用AI（GPT）分析并生成答案
- 自动填写问卷答案
- 支持随机答题延迟，模拟真实答题行为
- 完整的错误处理和重试机制

## 安装要求

- Python 3.7+
- Chrome 浏览器
- DrissionPage
- BeautifulSoup4
- python-dotenv
- requests

## 安装步骤

1. 克隆项目到本地：
```bash
git clone [项目地址]
cd [项目目录]
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
   - 复制 `.env.example` 文件并重命名为 `.env`
   - 填写必要的配置信息

## 环境变量配置说明

在 `.env` 文件中配置以下参数：

### AI配置
- `OPENAI_BASE_URL`: OpenAI API的基础URL地址
- `OPENAI_API_KEY`: OpenAI API密钥
- `GPT_MODEL`: 使用的GPT模型版本
- `TEMPERATURE`: AI回答的温度参数(0-1)

### 系统配置
- `LOGIN_URL`: 系统登录地址
- `API_ENDPOINT`: API接口地址
- `USERNAME`: 登录用户名
- `PASSWORD`: 登录密码

### 运行参数
- `BATCH_SIZE`: 每批处理的数据量
- `BATCH_DELAY`: 批处理之间的延迟时间
- `MAX_RETRIES`: 最大重试次数
- `RETRY_DELAY`: 重试之间的延迟时间
- `PAGE_LOAD_DELAY`: 页面加载延迟时间
- `MIN_ANSWER_DELAY`: 答题最小延迟时间
- `MAX_ANSWER_DELAY`: 答题最大延迟时间
- `FINAL_DELAY`: 完成后的最终延迟时间

## 使用方法

1. 确保所有环境变量已正确配置

2. 运行程序：
```bash
python main.py
```

3. 程序将自动执行以下步骤：
   - 登录系统
   - 获取问卷列表
   - 逐个处理问卷
   - 使用AI生成答案
   - 自动填写答案

## 注意事项

- 请确保网络连接稳定
- 建议设置适当的延迟时间，避免操作过快
- 使用前请确保已正确配置所有必要的环境变量
- 程序运行过程中可能需要人工确认某些操作

## 免责声明

本工具仅供学习和研究使用，请勿用于其他用途。使用本工具产生的任何后果由使用者自行承担。 