# 基线服务配置

冻结日期：2026-10-08（首次冻结，后续如有调整需另存版本并说明）

## 一、启动命令

```bash
cd /root/work/llama.cpp

./build/bin/llama-server \
  -m /root/work/models/Qwen3-4B-Q4_K_M.gguf \
  -ngl 99 \
  -c 8192 \
  --host 0.0.0.0 --port 8080 \
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
