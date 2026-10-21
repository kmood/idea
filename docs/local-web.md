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
- 按关键词、资料类型、证据等级和状态筛选。
- 查看仓库 Markdown 详情；未知信息保持未知，不按零值展示。
- `GET /api/catalog` 返回统一目录；`GET /api/documents/{kind}/{id}` 返回安全渲染的详情。
- 服务只接受 `GET` 和 `HEAD`，详情路径限定在仓库允许目录，页面不加载外部资源。

收藏、忽略和准备验证属于私人状态，当前切片暂未开放。后续会接入本机 records-history 状态存储，不使用浏览器临时状态代替。

## 验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests/local_web -p 'test_*.py' -v
```

2026-10-20 已在 320、768、1440 像素宽度检查布局，无横向溢出，浏览器控制台无错误。2026-10-21 再次读取 `/api/catalog`，确认真实目录显示 23 个来源、1 个趋势和 10 个点子。
