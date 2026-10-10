# ANTLab Infra 方向考核提交

## 提交信息

| 项目 | 内容 |
| --- | --- |
| **所选方向** | **Infra（大模型推理优化）** |
| 完成阶段 | 基础阶段 + 进阶阶段 |
| **最终分支** | `master` |
| **最终版本标签** | `submission-v1` |
| 最终 commit SHA | 见标签 `submission-v1` 指向的提交，或收集表中登记的 SHA |
| 完成日期 | 2026-10-10 |

**定位入口**：本仓库的实际工作在 `Basic Task/development/` 目录下。

| 内容 | 位置 |
| --- | --- |
| **整合报告**（基础 + 进阶） | [`Basic Task/development/reports/report.md`](Basic%20Task/development/reports/report.md) |
| 开发说明与运行入口 | [`Basic Task/development/README.md`](Basic%20Task/development/README.md) |
| 全部源码 | `Basic Task/development/src/`（仅用 Python 标准库） |
| 场景、固定负载、指标口径、环境 | `Basic Task/development/configs/` |
| 全部原始实验记录 | `Basic Task/development/results/` |
| 报告配图 | `Basic Task/development/reports/figures/` |

### 做了什么

在一台 12GB 显存的笔记本上，用 WSL + llama.cpp 部署 Qwen3-4B 本地推理服务，
建立可复现的测量方法，完成了：

- **基线**：单并发与四并发各 3 轮（吞吐 76.0 → 156.4 token/秒，首字延迟 0.05 → 0.55 秒）
- **优化**：KV 量化在同等显存下把容量从 16384 翻倍到 32768 token；
  实测 Flash Attention 在本机为负优化，未保留
- **输出质量核查**：条款引用 0 处编造；发现模型"能诊断缺陷但不能修复缺陷"
- **故障与服务恢复**：运行途中杀进程，覆盖等待中/已发送/失败三类请求路径
- **进阶题**：实现请求调度模块，优先级调度使期限达成率从 56% 提升到 100%
- **前端展示**：服务状态、逐请求记录、性能统计、错误记录与基线对比

### 快速开始

```bash
# 启动推理服务（需 WSL + CUDA，详见 configs/env.md）
/root/work/llama.cpp/build/bin/llama-server \
  -m /root/work/models/Qwen3-4B-Q4_K_M.gguf \
  -ngl 99 -c 16384 --host 0.0.0.0 --port 8888 -cram 0 --metrics

# 启动展示界面，浏览器打开 http://localhost:8000
cd "Basic Task/development" && python3 src/frontend.py
```

**未完成的部分**已如实列在报告第 1.2、9.4、12.2 节
（主要是 KV 量化对输出质量的影响、并发下的调度行为、更高并发未测）。

---

# ANTLab Infra Tasks

ANTLab Infra 方向的开发考核任务。当前包含大模型推理优化的基础任务与进阶任务，围绕 llama.cpp／llama-server 完成系统开发、性能测量和优化验证，并通过 GitHub 提交代码、测试数据和书面报告。

## 任务入口

| 阶段 | 任务内容 | 文档入口 |
| --- | --- | --- |
| Basic Task · 基础任务 | 为不超过 10 人的小公司或工作室搭建本地 GPU 推理服务，开发性能测试、文件存储、前端展示、报错记录与服务恢复功能，并优化一项或多项指标 | [任务首页](Basic%20Task/README.md) · [任务介绍](Basic%20Task/任务介绍.md) · [提交标准](Basic%20Task/提交标准.md) |
| Advanced Task · 进阶任务 | 自行选择有实际价值的推理优化问题，完成开发并验证效果；KV 缓存管理与复用、请求优先级判断与调度、自主探索三条方向提供选题参考 | [任务首页](Advanced%20Task/README.md) · [任务介绍](Advanced%20Task/任务介绍.md) · [提交标准](Advanced%20Task/提交标准.md) |

## 开发与学习

自行查找资料学习，使用 AI 辅助编码工具，并核验关键代码、测试方法和结果。根据硬件条件选择模型，准备具有相应显存容量的独立显卡，在 WSL 中使用 GPU 运行推理服务。

- **基础任务**：模型权重与 KV 全部放在显存中，完成单并发与多并发测试，记录基线、优化过程和效果。可关注 TTFT、TPOT、吞吐、KV 容量（以 token 为单位）等指标。
- **进阶任务**：结合场景确定问题、指标和实现方案，可以扩展基础任务或改造开源项目。KV 存储层次按方案设计，记录收益、资源代价和输出效果。

各阶段的具体环境、功能、测试和提交要求以对应任务文档为准。

## 项目组织

```text
ANTLab Infra Tasks/
├─ README.md
├─ Basic Task/
│  ├─ README.md
│  ├─ 任务介绍.md
│  ├─ 提交标准.md
│  ├─ 报告模板/
│  ├─ 提示词与输入文档/
│  └─ development/            # 基础任务的开发、测试、结果与报告
└─ Advanced Task/
   ├─ README.md
   ├─ 任务介绍.md
   ├─ 提交标准.md
   ├─ 选题参考/
   ├─ 参考测试（仅作参考）/
   ├─ 报告模板/
   └─ development/            # 内部结构自行设计
```

阶段文档中的 `development/` 均指该阶段目录内的开发区域。

进阶任务重点提交自己实现或修改的部分，可以采用自编模块、适配代码、补丁或 fork 差异等形式。依赖的开源项目注明来源、版本或 commit，以及获取和运行方法。配置、测试、原始数据和报告的位置自行安排，在开发 README 中列出入口。

## 开展与提交

1. Fork 本仓库，在自己的仓库中完成对应阶段任务。
2. 阅读该阶段的任务介绍与提交标准，在开发 README 中说明选题、环境、实现范围和运行方法。
3. 按开发过程组织 Git 提交，保留功能开发、问题修复与性能优化的记录。
4. 保存测试原始数据和优化结果，参考报告模板完成书面报告。
5. 在截止时间前推送完成的作品，提交 GitHub 仓库链接、最终分支、commit SHA，以及对应阶段的运行说明、报告和数据位置。

每个阶段的任务周期为一周，具体截止日期和时间以发布通知为准。
