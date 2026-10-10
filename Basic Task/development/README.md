# 开发区域

本地大模型推理服务的部署、测量、优化与调度。**基础阶段与进阶阶段的全部内容都在本目录。**

## 一句话说明

为一台 12GB 显存的笔记本部署 Qwen3-4B 本地推理服务，
建立可复现的测量方法，找出真正有效的优化，并实现请求调度。

## 快速开始

```bash
# 1) 启动推理服务（需要 WSL + CUDA，详见 configs/env.md）
/root/work/llama.cpp/build/bin/llama-server \
  -m /root/work/models/Qwen3-4B-Q4_K_M.gguf \
  -ngl 99 -c 16384 --host 0.0.0.0 --port 8888 -cram 0 --metrics

# 2) 启动展示界面，浏览器打开 http://localhost:8000
cd "Basic Task/development"
python3 src/frontend.py
```

## 目录说明

| 目录 | 内容 |
| --- | --- |
| [src](src/README.md) | 全部源码（9 个文件，见下表） |
| [configs](configs/README.md) | 环境实况、场景与固定负载、指标口径、服务与优化配置 |
| [tests](tests/README.md) | 输入核查与功能验证 |
| [results](results/README.md) | 原始记录与汇总，按实验分组 |
| [reports](reports/README.md) | 整合报告与配图 |

## 源码一览

| 文件 | 职责 |
| --- | --- |
| `src/runner.py` | 固定负载压测：输入核查、发送请求、逐条记录、多轮次并发、流式测 TTFT |
| `src/supervisor.py` | 服务管理：健康检测、进程重启、就绪确认、事件时间线 |
| `src/fault_test.py` | 故障实验：运行途中杀进程，验证三类请求路径 |
| `src/check_quality.py` | 输出质量核查：条款引用真实性、问题覆盖、代码可执行性 |
| `src/scheduler.py` | 请求调度模块：FIFO / 优先级 / 优先级+缓存亲和 |
| `src/replay.py` | 按参考序列回放，比较调度策略（每轮清空缓存） |
| `src/frontend.py` | 展示界面服务端 |
| `src/web/index.html` | 界面（原生 HTML/JS，无外部依赖） |
| `src/compare_optimization.py` | 配置级优化对比汇总 |

另有 `src/build_workload.py`（从题包生成固定负载）、`src/make_figures.py`（生成报告配图）。

**全部源码仅使用 Python 标准库**，不需要 `pip install` 任何依赖。

## 系统结构

```
浏览器 ──▶ 前端展示服务（:8000）
                │ 读取
                ▼
        results/runs/*.jsonl
                ▲
                │ 写入
压测程序（src/runner.py）──▶ llama-server（:8888）
服务管理（src/supervisor.py）──▶ 进程生命周期
调度模块（src/scheduler.py + src/replay.py）──▶ 请求顺序
```

## 环境依赖

| 项目 | 版本 |
| --- | --- |
| GPU | NVIDIA RTX 5070 Ti Laptop（12227 MiB，计算能力 12.0） |
| 驱动 / CUDA | 610.62 / 13.4 |
| WSL / Linux | WSL2 + Ubuntu 22.04 |
| llama.cpp | 0.6.0-dev，commit `d8880160413fc77f63d6a73a5b1ac21ac65e36e1` |
| 构建参数 | `cmake -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120` |
| Python | 3.10.12（仅标准库；`check_quality.py` 调用系统的 pytest） |

完整信息见 [configs/env.md](configs/env.md)。

## 模型获取与校验

| 项目 | 内容 |
| --- | --- |
| 模型 | Qwen3-4B GGUF，Q4_K_M |
| 文件 | `Qwen3-4B-Q4_K_M.gguf`，2497280256 字节 |
| SHA256 | `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5` |
| 来源 | https://huggingface.co/Qwen/Qwen3-4B-GGUF |

该 SHA256 与上游文件完全一致（已核验）。模型权重不进仓库，由 `.gitignore` 排除。

## 运行方法

```bash
cd "Basic Task/development"

python3 src/runner.py            # 只拼装不发送，核查输入（dry-run）
python3 src/runner.py run 3 1    # 3 轮、并发 1
python3 src/runner.py run 3 4    # 3 轮、并发 4

python3 src/check_quality.py <运行编号>     # 输出质量核查
python3 -u src/fault_test.py                # 故障与服务恢复实验
python3 src/compare_optimization.py         # 优化对比汇总
python3 -u src/replay.py all 3              # 调度策略对比（会自动重启服务清空缓存）
python3 src/make_figures.py                 # 生成报告配图
```

## 测试方法

| 测试 | 命令 | 说明 |
| --- | --- | --- |
| 输入核查 | `python3 src/runner.py` | 打印实际将发送的消息，人工核对 |
| 功能验证 | `python3 src/check_quality.py` | 条款引用核对 + 代码实际运行 |
| 异常与恢复 | `python3 -u src/fault_test.py [--no-restart]` | 覆盖等待中/已发送/失败三类请求 |

## 前端访问

```bash
python3 src/frontend.py          # 默认端口 8000
```

浏览器打开 `http://localhost:8000`，可查看服务状态、运行列表、
逐请求记录（含模型原始输出）、性能统计、错误记录与基线对比。

## 报告与数据位置

| 内容 | 位置 |
| --- | --- |
| **整合报告** | [reports/report.md](reports/report.md) |
| 报告配图 | `reports/figures/` |
| 环境实况 | `configs/env.md` |
| 场景定义 | `configs/scenario.md` |
| 固定负载 | `configs/workload.json` |
| 指标口径 | `configs/metrics.md` |
| 基线原始记录 | `results/runs/*.jsonl`（含每次运行的显卡状态快照 `*.env.json`） |
| 优化对比 | `results/optimization/` |
| 输出质量核查 | `results/quality_check/` |
| 故障与恢复 | `results/fault_test/` |
| 调度实验 | `results/advanced/` |

## 完成与未完成

| 项目 | 状态 |
| --- | :-: |
| WSL 中 GPU 推理、GPU 驻留证据 | ✅ |
| 固定负载、指标口径、场景定义 | ✅ |
| 压测程序（单/多并发、多轮、流式 TTFT） | ✅ |
| 基线（并发 1/4 各 3 轮） | ✅ |
| 配置级优化对比与 KV 容量测量 | ✅ |
| 输出质量核查 | ✅ |
| 错误记录与服务恢复 | ✅ |
| 前端展示 | ✅ |
| 进阶题：请求调度 | ✅ |
| KV 量化对输出质量的影响 | ❌ 未测 |
| 并发下的调度行为 | ❌ 未测 |
| 更高并发（8/10） | ❌ 未测 |

未完成项的说明与后续验证方向见报告第 1.2、9.4、12.2 节。
