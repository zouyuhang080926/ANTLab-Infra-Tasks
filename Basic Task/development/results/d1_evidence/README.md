# 第 1 天证据说明

本目录保存 2026-10-08 首次跑通基线服务时的原始记录。

## 文件清单

| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `load_gpu_evidence.log` | llama-server 启动日志（trace 级） | 含层分配、显存缓冲、模型元数据 |
| `Qwen3-4B-Q4_K_M.sha256` | 模型文件校验值 | 与 HuggingFace 上游一致 |
| `cold_request.json` | 服务启动后第一条请求的完整响应 | 冷启动数据 |
| `warm_request.json` | 紧随其后的同内容请求的完整响应 | 预热 + 前缀缓存命中数据 |

## 一、GPU 驻留证据

来自 `load_gpu_evidence.log`：

```
load_tensors: offloading output layer to GPU
load_tensors: offloading 35 repeating layers to GPU
load_tensors: offloaded 37/37 layers to GPU
load_tensors:   CPU_Mapped model buffer size =   304.28 MiB
load_tensors:        CUDA0 model buffer size =  2375.91 MiB
llama_context:  CUDA_Host  output buffer size =     2.32 MiB
llama_kv_cache:      CUDA0 KV buffer size =  1152.00 MiB
sched_reserve:      CUDA0 compute buffer size =    85.01 MiB
sched_reserve:  CUDA_Host compute buffer size =    28.02 MiB
```

结论：

- 37/37 层全部 offload 到 GPU；
- 权重（2375.91 MiB）与 KV（1152.00 MiB）均在 CUDA0；
- `CPU_Mapped 304.28 MiB` 为 mmap 主机侧文件映射，非 CPU 计算回退，由下述对照实验佐证。

KV 容量手算校验：

```
2 (K和V) × 36 (层) × 8 (KV头) × 128 (头维度) × 2 (f16 字节) = 147456 字节/token
147456 × 8192 token = 1207959552 字节 ≈ 1152 MiB  ← 与日志一致
```

## 二、CPU 与 GPU 对照

同模型、同参数，`llama-bench -p 128 -n 32`：

| 配置 | pp128 | tg32 |
| --- | ---: | ---: |
| 纯 CPU（`-ngl 0`） | 465.08 t/s | 16.25 t/s |
| 全 GPU（`-ngl 99`） | 4642.08 t/s | 156.83 t/s |
| 倍数 | 10.0× | 9.7× |

若存在实质性 CPU 计算回退，整体加速比会被显著拉低；实测接近 10 倍，确认计算在 GPU 执行。

## 三、冷启动与预热差异

两条请求内容完全相同（关闭思考模式）。服务端 `timings` 字段：

**冷启动（`cold_request.json`）**

```json
"timings": {"cache_n":0, "prompt_n":21, "prompt_ms":35.519, "prompt_per_second":591.23,
            "predicted_n":43, "predicted_ms":276.046, "predicted_per_second":152.15}
```

**预热后（`warm_request.json`）**

```json
"timings": {"cache_n":20, "prompt_n":1, "prompt_ms":6.669, "prompt_per_second":149.95,
            "predicted_n":43, "predicted_ms":264.605, "predicted_per_second":158.73}
```

两个独立现象同时出现，必须分开理解：

1. **前缀缓存命中**：`cache_n` 从 0 变为 20，`prompt_n` 从 21 降到 1。
   第二条请求的 21 个 token 中，20 个直接复用，只有 1 个需要重新计算。
   注意此时 `prompt_per_second` 从 591 掉到 150，这不是变慢了——分母只剩 1 个 token，
   该字段在缓存命中时失去参考意义，应改看 `prompt_ms`（35.5 ms → 6.7 ms）。
2. **CUDA 预热**：首次请求需完成算子加载与计算图捕获，属一次性开销。

对后续实验的要求：

- 正式测量前必须先预热，否则首轮数据不可用；
- 所有性能结论需标明属于冷启动或预热后；
- 比较不同请求时须注意前缀是否重合，避免把"缓存命中"误读为"方法变快"。

## 四、复现方式

```bash
cd /root/work/llama.cpp

./build/bin/llama-server \
  -m /root/work/models/Qwen3-4B-Q4_K_M.gguf \
  -ngl 99 -c 8192 \
  --host 0.0.0.0 --port 8080 \
  -lv 4 -cram 0 --metrics
```

随后向 `http://127.0.0.1:8080/v1/chat/completions` 连续发送两次相同请求，
请求体见 `server_baseline.md`《模型行为约定》一节。
