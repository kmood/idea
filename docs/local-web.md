# 本机研究看板操作说明

## 启动

在仓库根目录执行：

```bash
PYTHONPATH=src python3 -m local_web --root . --host 127.0.0.1 --port 8765
```

浏览器访问 `http://127.0.0.1:8765`。看板直接读取 `sources/`、`trends/`、`ideas/` 和 `research/STATE.md`，刷新页面即可看到 Markdown 的最新内容。

需要在可信局域网内从其他设备访问时，显式监听所有网卡：

```bash
PYTHONPATH=src python3 -m local_web --root . --host 0.0.0.0 --port 8765
```

然后访问 `http://<运行电脑的局域网地址>:8765`。当前服务没有登录认证，只应在受信任的家庭或个人局域网内使用；不要把端口映射到公网。

## 当前能力

- 总览来源、趋势和点子数量。
- 按关键词、资料类型、证据等级和状态筛选；配置本机 records 数据库后，可按“本人适用性”排除或仅查看已标记为“本人不适用”的点子。
- 查看仓库 Markdown 详情；未知信息保持未知，不按零值展示。
- `GET /api/catalog` 返回统一目录；`GET /api/documents/{kind}/{id}` 返回安全渲染的详情。
- `GET /api/personal-states` 只返回已标记 `ignored=true` 的点子 ID，不返回备注或其他私人字段。
- 资料接口只接受 `GET` 和 `HEAD`；私人标记接口额外接受受限的 `POST /api/personal-state`，详情路径限定在仓库允许目录，页面不加载外部资源。

点子详情支持“标记本人不适用”。需要保存私人操作时，启动时显式传入已初始化并完成资料迁移的本机 records 数据库：

```bash
PYTHONPATH=src python3 -m local_web --root . --host 127.0.0.1 --port 8765 --db .local/records.sqlite3
```

操作写入 records-history 的 `ignored=true`，保留版本历史与操作幂等信息，不修改 Markdown、不进入研究导出，也不使用浏览器临时状态。未传 `--db` 时页面仍可只读浏览，操作按钮会说明无法保存。

页面刷新时读取上述私人 ID 列表；未配置 `--db` 或数据库不可读时，适用性筛选默认显示全部点子，公开资料仍可正常浏览。

收藏、准备验证、私人备注和反馈仍未开放。

## 验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/local_web -p 'test_*.py' -v
```

2026-10-20 已在 320、768、1440 像素宽度检查布局，无横向溢出，浏览器控制台无错误。2026-10-21 再次读取 `/api/catalog`，确认真实目录显示 30 个来源、1 个趋势和 20 个点子。
