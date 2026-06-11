# CLAUDE.md

## 项目简介

智能竞品分析Agent - 基于LLM的自动化竞品分析系统，支持多源数据采集、结构化分析和智能报告生成。

## 技术栈

- **Python**: 3.12+
- **LLM框架**: LangChain + LangGraph
- **向量数据库**: Chroma
- **后端**: FastAPI
- **前端**: Streamlit
- **爬虫**: Selenium + BeautifulSoup
- **数据验证**: Pydantic V2
- **LLM**: MIMO (OpenAI兼容格式)

## 目录结构

```
agent/          - Agent核心（LangGraph状态图、节点、工具）
api/            - FastAPI接口层
collector/      - 数据采集（搜索、爬取、清洗）
config/         - 配置管理（设置、Prompt模板）
display/        - Streamlit前端界面
examples/       - 使用示例
knowledge/      - 知识库（向量存储、Embedding、RAG）
models/         - 数据模型（Pydantic）
report/         - 报告生成
tests/          - 单元测试
utils/          - 工具类
```

## 开发规范

### Git规范

- 每完成一个小功能就提交一次，不要攒大提交
- 提交信息格式：`类型: 简短描述`
  - `feat`: 新功能
  - `fix`: 修复bug
  - `docs`: 文档更新
  - `test`: 测试相关
  - `refactor`: 重构
- 示例：`feat: 添加用户评价采集功能`、`fix: 修复价格提取正则表达式`

### 文档同步更新

每次开发新功能时，必须同步更新：
1. **CLAUDE.md** - 更新模块状态、新增命令等
2. **DEVELOPMENT_PROGRESS.md** - 更新开发进度
3. **README.md** - 如有目录结构变更
4. **TECHNICAL_ARCHITECTURE.md** - 如有架构变更

### 代码规范

- 使用异步模式（async/await）处理IO操作
- 使用Pydantic V2的`@field_serializer`替代已废弃的`json_encoders`
- 使用`logging`模块记录日志，不用`print`
- 类型注解必须完整
- 中文注释和文档字符串

### 测试规范

- 每个模块都要有对应的测试文件
- 使用`pytest`和`pytest-asyncio`
- Mock外部依赖（LLM、API、数据库）
- 测试文件命名：`tests/test_<模块名>.py`

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行全部测试
pytest tests/test_models.py tests/test_knowledge_simple.py tests/test_collector.py tests/test_agent.py -v

# 运行单个模块测试
pytest tests/test_agent.py -v

# 运行示例
python examples/models_demo.py
python examples/knowledge_demo.py
python examples/collector_demo.py
python examples/agent_demo.py

# 启动API服务（待开发）
# uvicorn api.app:app --reload

# 启动前端（待开发）
# streamlit run display/app.py
```

## 环境配置

复制`.env.example`为`.env`，填写以下配置：

```env
OPENAI_API_KEY=your-mimo-api-key
OPENAI_API_BASE=https://api.mimo.com/v1
SERPAPI_KEY=your-serpapi-key
```

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| models/ | ✅ 完成 | 数据模型（竞品、分析、报告） |
| knowledge/ | ✅ 完成 | 知识库（向量存储、RAG） |
| collector/ | ✅ 完成 | 数据采集（搜索、爬取、清洗） |
| config/ | ✅ 完成 | 配置管理 |
| agent/ | ✅ 完成 | Agent核心（LangGraph状态图） |
| report/ | ⏳ 待开发 | 报告生成 |
| api/ | ⏳ 待开发 | FastAPI接口 |
| display/ | ⏳ 待开发 | Streamlit前端 |
| utils/ | ⏳ 待开发 | 工具类 |

## 测试统计

- 测试文件：5个
- 测试用例：50个
- 状态：全部通过
