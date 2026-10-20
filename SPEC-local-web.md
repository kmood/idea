# 规格：本机研究看板（local-web）

状态：用户于 2026-10-20 要求继续研究并开发可视化界面；沿用此前“后续不需要确认，直接继续”的授权。本规格对应已批准能力划分中的 `local-web`，首个切片只读，不切换现有 Markdown 权威入口。

## 目标

在用户电脑启动一个轻量网站，集中查看来源、趋势、点子、证据等级、研究状态和最近核验时间；支持搜索与类型筛选，并可在局域网设备访问。页面直接反映仓库当前 Markdown，避免为了界面复制第二份资料真相。

## 技术栈与命令

使用 Python 3.14 标准库、语义化 HTML、原生 CSS/JavaScript，不新增运行依赖。

```bash
PYTHONPATH=src python3 -m local_web --root . --host 127.0.0.1 --port 8765
PYTHONPATH=src python3 -m local_web --root . --host 0.0.0.0 --port 8765
PYTHONPATH=src python3 -m unittest discover -s tests/local_web -p 'test_*.py' -v
```

默认只监听本机；局域网模式必须显式传 `0.0.0.0`。不发布公网、不使用 Sites 托管。

## 结构与接口

- `src/local_web/catalog.py`：读取三个索引，校验相对路径并形成展示模型。
- `src/local_web/markdown.py`：将受限 Markdown 转为经过转义的 HTML。
- `src/local_web/app.py`：只读 HTTP 路由与静态资源。
- `src/local_web/static/`：页面、样式和交互。
- `tests/local_web/`：目录、渲染、HTTP 契约和实际仓库集成测试。

只读接口：

- `GET /api/catalog` → `{meta, records}`；每项含 `id`、`kind`、`title`、`summary`、`marketOrSource`、`evidence`、`status`、`updatedAt` 和 `documentPath`。
- `GET /api/documents/{kind}/{id}` → `{id, kind, title, html, documentPath}`。
- 所有错误返回 `{error:{code,message}}`；不存在为 404，非法路径为 400。

## 样式与交互

界面采用资料编辑台风格：米白纸张背景、深墨文字、蓝绿色强调色和紧凑表格/列表密度。首页直接展示研究状态与资料，不做宣传型首屏。移动端单列，宽屏为侧栏筛选加内容列表；所有控件可用键盘，状态不只依赖颜色表达。

## 测试策略

先用 unittest 验证索引解析、路径限制、HTML 转义、API 结构及真实仓库读取，再用真实浏览器检查 320/768/1440 宽度、筛选、详情、空状态、键盘焦点和控制台错误。静态页面不加载第三方脚本、字体或图片。

## 边界

- 始终：只读仓库允许目录；转义正文；每次 API 请求读取最新 Markdown；保持稳定 ID 和未知值。
- 已授权直接实施：新增本机只读服务、文档、测试和启动说明。
- 后续切片：收藏、忽略、准备验证须调用 records-history 私人状态接口，不能只写浏览器 localStorage。
- 禁止：公网部署、任意文件读取、执行 Markdown 中的 HTML/脚本、把临时 R19 数据冒充正式索引、覆盖用户选择、加入账号/Cookie。

## 成功条件

1. 启动命令后首页能展示三个索引的真实数据，搜索和类型筛选可用。
2. 详情只显示允许目录内的对应 Markdown，脚本和原始 HTML不能执行。
3. 默认仅本机监听，显式局域网监听可从同网设备访问。
4. 自动测试、浏览器运行、响应式和无控制台错误检查通过。

## 开放项

私人操作写入、正式 SQLite 切换、登录态研究采集和网站自动刷新协调不属于首个只读切片，分别在后续任务中接入。
