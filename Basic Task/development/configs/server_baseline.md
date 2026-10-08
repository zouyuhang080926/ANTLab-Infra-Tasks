# 基线服务配置

冻结日期：2026-10-08（首次冻结，后续如有调整需另存版本并说明）

## 一、启动命令

```bash
cd /root/work/llama.cpp

./build/bin/llama-server \
  -m /root/work/models/Qwen3-4B-Q4_K_M.gguf \
  -ngl 99 \
  -c 8192 \
  --host 0.0.0.0 --port 8888 \
  -lv 4 \
  -cram 0 \
  --metrics
```

## 二、参数说明

| 参数 | 取值 | 作用 | 选用理由 |
| --- | --- | --- | --- |
| `-m` | Qwen3-4B-Q4_K_M.gguf | 模型文件 | Q4_K_M 在 12GB 显存下留出足够 KV 与并发空间 |
| `-ngl` | 99 | 卸载到 GPU 的层数 | 实测 37/37 全部 offload |
| `-c` | 8192 | 统一 KV 池总容量（token） | 基础容量起点，后续做容量优化时对比 |
| `-np` | 未指定（auto=4） | slot 数量 | 当前为本版本默认值；`kv_unified=true`，4 个 slot 共享 8192 token 池 |
| `--port` | 8888 | 服务监听端口 | **不用 8080**：Windows 上该端口已被 Steam 的 `steamwebhelper.exe` 占用，浏览器访问会打到 Steam 的调试页面而不是本服务。详见第六节 |
| `-cram` | 0 | 关闭主机内存 prompt cache | 基础阶段要求缓存工作集驻留显存 |
| `-lv` | 4 | trace 级日志 | 默认 3 级不打印层分配与 KV 大小，无法采集 GPU 驻留证据 |
| `--metrics` | 开 | 启用 /metrics | 服务端指标采集 |

## 三、实测资源占用

| 项目 | 数值 |
| --- | --- |
| CUDA0 model buffer（权重） | 2375.91 MiB |
| CUDA0 KV buffer | 1152.00 MiB |
| CUDA0 compute buffer | 85.01 MiB |
| CUDA_Host output buffer | 2.32 MiB |
| CPU_Mapped（mmap 文件映射，不占显存） | 304.28 MiB |

## 四、模型行为约定

**关闭思考模式**：所有请求在 body 中传

```json
"chat_template_kwargs": {"enable_thinking": false}
```

原因：Qwen3 为推理型模型，默认先输出 `reasoning_content`，在小输出预算下会导致
`content` 为空、`finish_reason` 为 `length`，输出长度不可控，无法做公平的性能对比。

## 五、服务端计时字段

非流式响应的 `timings` 字段由服务端产生，可用于交叉校验客户端测量：

```json
"timings": {
  "cache_n": 0,
  "prompt_n": 21,
  "prompt_ms": 15.531,
  "prompt_per_second": 1352.13,
  "predicted_n": 53,
  "predicted_ms": ...,
  "predicted_per_second": ...
}
```

- `prompt_*` 对应 prefill 阶段（读题），与客户端 TTFT 相关；
- `predicted_*` 对应 decode 阶段（写字），与客户端 TPOT 相关；
- `cache_n` / `usage.cached_tokens` 为前缀缓存命中计数。

## 六、基线速度参考

`llama-bench`，`-p 128 -n 32 -r 2`：

| 配置 | pp128 | tg32 |
| --- | ---: | ---: |
| 纯 CPU（`-ngl 0`） | 465.08 t/s | 16.25 t/s |
| 全 GPU（`-ngl 99`） | 4642.08 t/s | 156.83 t/s |

注：`-r 2` 轮数偏少且未预热，pp 项波动较大（±1378）。正式基线需提高轮数并预热后重测。

## 七、端口选择说明（环境限制）

**结论：本项目固定使用 8888 端口，不使用 llama-server 的惯用默认端口 8080。**

原因：本机 Windows 侧的 8080 端口已被 Steam 的浏览器组件占用。

```
$ netstat 查询结果
监听地址: 127.0.0.1:8080
进程名:   steamwebhelper.exe
路径:     F:\Game\steam\bin\cef\cef.win64\steamwebhelper.exe
```

表现：

| 访问位置 | 结果 |
| --- | --- |
| WSL 内 `http://127.0.0.1:8080/health` | 正常返回 `{"status":"ok"}`（服务本身没问题） |
| Windows 浏览器 `http://localhost:8080/` | 返回 Steam 的 CEF 调试页面，**不是本服务** |

也就是说，服务在 WSL 内部一直是好的，但 Windows 侧的 `localhost:8080` 被 Steam 抢先占用，
导致浏览器永远访问不到本服务。这是"服务正常但访问不到"的典型排查点。

**排查方法（通用）**：先分清是"服务没起来"还是"路被占了"。

```bash
# 在 WSL 里确认服务活着（这一步和 Windows 无关）
curl -s http://127.0.0.1:8888/health
```

```powershell
# 在 Windows PowerShell 里查谁占了端口
Get-NetTCPConnection -LocalPort 8888 -State Listen |
  Select-Object LocalAddress, LocalPort, OwningProcess |
  ForEach-Object { Get-Process -Id $_.OwningProcess }
```

**验证记录**：改用 8888 后，从 Windows 侧访问 `localhost:8888/health` 返回
`{"status":"ok"}`，并能成功完成一次真实推理请求（输出 43 个 token），确认通路正常。

## 八、网页界面说明

本编译产物**不包含 llama.cpp 自带的网页界面**（编译时其 UI 资源需从 HuggingFace
下载，当时超时失败，日志中有 `UI: embedded 0 assets`）。

因此浏览器打开 `http://localhost:8888/` 会返回 404 `File Not Found`，这是预期行为。

本项目的展示界面按考核要求自行开发，不依赖引擎自带界面。
