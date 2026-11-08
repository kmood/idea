# 本地看板部署与运行

本文记录本地研究看板的初始化、迁移、启动、检查、停止和备份命令。所有命令均从仓库根目录 `/data/code/idea` 执行。

## 1. 初始化 records 数据库

先创建本机运行目录并初始化 SQLite 数据库：

```bash
cd /data/code/idea
mkdir -p .local
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 init
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 status
```

`init` 只创建数据库结构，不会把 Markdown 研究资料导入数据库。数据库中没有对应的研究记录时，页面上的“标记本人不适用”无法保存。

## 2. 导入当前 Markdown 资料

正式迁移应先生成预览，检查 `unresolved` 为空，再应用到新数据库：

```bash
PYTHONPATH=src python3 -m records \
  legacy-preview \
  --root /data/code/idea \
  --mapping research/migrations/2026-10-15-records-map.json \
  --output .local/legacy-preview.json

PYTHONPATH=src python3 -m records \
  --db .local/records.sqlite3 \
  legacy-apply \
  --root /data/code/idea \
  --input .local/legacy-preview.json \
  --operation-id migrate-current-markdown-YYYYMMDD
```

预览出现 `REVISION_CONFLICT` 或 `unresolved` 时，不要直接强行导入；应更新映射、重新生成预览并复核。`--db` 必须指向已初始化且包含当前点子记录的数据库；只传入一个不存在的路径不会自动完成初始化和迁移。

## 3. 前台启动

仅本机访问：

```bash
PYTHONPATH=src python3 -m local_web \
  --root /data/code/idea \
  --db /data/code/idea/.local/records.sqlite3 \
  --host 127.0.0.1 \
  --port 8765
```

访问：<http://127.0.0.1:8765/>

允许局域网访问：

```bash
PYTHONPATH=src python3 -m local_web \
  --root /data/code/idea \
  --db /data/code/idea/.local/records.sqlite3 \
  --host 0.0.0.0 \
  --port 8765
```

访问地址为 `http://<服务器IP>:8765/`。`0.0.0.0` 只能作为监听地址，不能作为浏览器访问地址。

看板当前没有登录认证。监听 `0.0.0.0` 会将公开研究内容和私人标记操作暴露给能够访问该端口的设备；仅在可信局域网使用，并通过防火墙限制来源，不建议直接暴露到公网。

## 4. 后台启动、查看和停止

```bash
mkdir -p /data/code/idea/.local
nohup env PYTHONPATH=src python3 -m local_web \
  --root /data/code/idea \
  --db /data/code/idea/.local/records.sqlite3 \
  --host 0.0.0.0 \
  --port 8765 \
  > /data/code/idea/.local/local_web.log 2>&1 &
echo $! > /data/code/idea/.local/local_web.pid
```

查看启动日志和进程：

```bash
tail -f /data/code/idea/.local/local_web.log
ps -fp "$(cat /data/code/idea/.local/local_web.pid)"
```

停止后台服务：

```bash
kill "$(cat /data/code/idea/.local/local_web.pid)"
```

如果端口已被占用，先停止旧进程或换端口，例如 `--port 8766`，然后使用 `http://<服务器IP>:8766/` 访问。

## 5. 运行检查

```bash
PYTHONPATH=src python3 -m records --db .local/records.sqlite3 status
curl -i http://127.0.0.1:8765/api/consistency
curl -i http://127.0.0.1:8765/api/catalog
```

重点确认：

- `status` 中 `researchRecords` 大于 0；
- `privateStates` 在首次标记前可以为 0；
- `/api/consistency` 返回 `ok: true`；
- 页面详情中的“标记本人不适用”操作返回保存成功。

## 6. 备份与恢复

备份包含本机私人状态，不得上传或提交到 Git：

```bash
mkdir -p .local/backups
PYTHONPATH=src python3 -m records \
  --db .local/records.sqlite3 \
  backup \
  --output .local/backups/records-$(date +%Y%m%d-%H%M%S).sqlite3
```

恢复到一个新的目标文件：

```bash
PYTHONPATH=src python3 -m records restore \
  --input .local/backups/records-YYYYMMDD-HHMMSS.sqlite3 \
  --output .local/restored.sqlite3
```

恢复完成后，先检查 `.local/restored.sqlite3` 的 `status`，确认无误后再将看板的 `--db` 指向该文件；不要覆盖正在运行的数据库。
