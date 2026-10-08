# 环境实况

记录日期：2026-10-08

## 一、硬件

| 项目 | 实测值 |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti Laptop GPU，显存 12227 MiB，计算能力 12.0（Blackwell，sm_120） |
| 显卡驱动 | 610.62（Windows 侧） |
| CPU | AMD Ryzen 9 8940HX，16 核 32 线程 |
| 内存 | 主机 31.2 GB；WSL 上限配置为 24 GB（实测可用约 23 GB） |
| 磁盘 | WSL 根分区约 950 GB 可用 |

## 二、系统与软件

| 项目 | 实测值 |
| --- | --- |
| 运行环境 | WSL2 + Ubuntu 22.04，内核 6.18.40.1-microsoft-standard-WSL2 |
| CUDA Toolkit | 13.4（`/usr/local/cuda`） |
| 编译器 | g++ 11.4.0 |
| 构建工具 | CMake 3.22.1 |
| GPU 透传 | WSL 内 `nvidia-smi` 可见同一张卡 |

## 三、推理引擎

| 项目 | 实测值 |
| --- | --- |
| 引擎 | llama.cpp（llama-server / llama-bench） |
| 版本 | 0.6.0-dev（构建时无 git 元数据，版本号取自源码快照） |
| 源码 commit | d8880160413fc77f63d6a73a5b1ac21ac65e36e1（master，2026-10-08 拉取） |
| 源码获取方式 | 源码压缩包（codeload），非 git clone |
| 构建命令 | `cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_BUILD_TYPE=Release` |
| 目标架构 | sm_120a（Blackwell） |
| 构建产物 | `build/bin/llama-server`、`build/bin/llama-bench`、`libggml-cuda.so.0.26.0` |

构建说明：编译时 llama.cpp 尝试下载内置网页界面（llama-ui）失败（HuggingFace 不可达），
因此在无内置 UI 的情况下完成构建。本项目使用自建前端，不影响功能。

## 四、模型

| 项目 | 实测值 |
| --- | --- |
| 模型 | Qwen3-4B |
| 量化格式 | Q4_K_M |
| 文件名 | Qwen3-4B-Q4_K_M.gguf |
| 文件大小 | 2497280256 bytes |
| SHA256 | 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5 |
| 来源 | https://huggingface.co/Qwen/Qwen3-4B-GGUF |
| 来源核验 | 与上游文件大小及 SHA256 完全一致（`x-linked-etag` 比对） |
| 模型元数据 | block_count 36；context_length 40960；embedding_length 2560；attention.head_count 32；attention.head_count_kv 8 |

## 五、已验证的关键结论

1. **模型全部在 GPU 上执行**：加载日志 `offloaded 37/37 layers to GPU`。
2. **权重与 KV 均在显存**：CUDA0 model buffer 2375.91 MiB、CUDA0 KV buffer 1152.00 MiB。
3. **KV 容量与手算一致**：`2 × 36 × 8 × 128 × 2 bytes = 147456 bytes/token`，
   × 8192 token = 1152 MiB，与日志一致。
4. **计算确实由 GPU 承担**：同一模型纯 CPU 与全 GPU 对照，pp128 提升 10.0×，tg32 提升 9.7×。
5. **日志中 `CPU_Mapped 304.28 MiB` 为 mmap 主机侧文件映射**，非 CPU 计算回退；
   由第 4 条对照结果佐证。
6. **冷启动与预热差异显著**：同一请求冷启动 prompt 108 t/s，预热后 1352 t/s（约 12×）。
   后续所有性能测试须区分冷启动与预热，并在正式测试前预热。

## 六、本机网络注意事项

- Windows `hosts` 文件存在指向 `127.0.0.1` 的屏蔽记录（含 github.com、huggingface.co），
  导致浏览器与命令行均无法访问；WSL 侧已通过改用公共 DNS（223.5.5.5 / 119.29.29.29）绕过。
- 访问 huggingface.co 使用镜像 https://hf-mirror.com。
- 到 github.com 的连接速率较低（约 150 KB/s），大体积拉取建议改用源码压缩包或加超时。
- **端口冲突**：Windows 侧 8080 端口被 Steam 的 `steamwebhelper.exe` 占用，
  浏览器访问 `localhost:8080` 会指向 Steam 的调试页面而非本服务。
  本项目服务固定使用 **8888** 端口，详见 `server_baseline.md` 第七节。
