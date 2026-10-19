# 受控网络读取（R07）

`research.network.bounded_request` 在可终止子进程内完成 DNS、固定 IP 连接、TLS 和有界正文读取。仅 GET HTTP(S) 默认端口；无代理、认证头、Cookie 或自动重定向。父进程期限上限 30 秒，压缩前后上限 2 MiB。依赖注入只用于 Python 测试，不提供放行内网的配置或 JSON 开关。

`research.fetcher.Fetcher` 通过资料提供方保存 robots 缓存与来源/域名两级请求间隔；robots、重定向及正文分别预占请求预算。最多三跳重定向，每跳重新执行访问约束。robots 缓存最多一天，404/410 视为不存在，其他失败保守延期，robots 本身重定向暂不跟随。robots 另设 64 KiB 上限。Crawl-delay、Request-rate 和 Retry-After 比默认三秒更严格时优先。超限/受限/超时不返回成功正文；没有在此实现无条件自动重试。

保存完整正文及可信读取凭据属于 R08，本层仅返回临时字节。当前在线环境对公开域名返回 198.18.0.0/15 测试地址，因此真实试读被地址检查阻止；没有把离线替身验证称为线上读取成功。

实现依据：[Python HTTPConnection](https://docs.python.org/3.14/library/http.client.html)、[TLS 默认上下文](https://docs.python.org/3.14/library/ssl.html)、[robots 解析器](https://docs.python.org/3.14/library/urllib.robotparser.html)。查阅文档版本 3.14.8，本机运行时保持原有版本，未为此升级依赖。
