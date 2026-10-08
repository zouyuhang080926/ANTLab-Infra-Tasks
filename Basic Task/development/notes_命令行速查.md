# WSL 与命令行速查手册

写给本项目使用。遇到不认识的命令或报错，先来这里翻。

---

## 一、先看懂提示符

```
root@DESKTOP-0B0ORN8:~#
│    │                │ └── # = 当前是 root 用户（普通用户会显示 $）
│    │                └──── ~ = 当前目录（~ 代表主目录，这里是 /root）
│    └───────────────────── 电脑名字
└────────────────────────── 当前登录的用户名
```

提示符本身就是状态报告：**谁、在哪台机器、站在哪个目录、什么权限**。

不确定的时候，随时敲：

```bash
pwd
```

---

## 二、绝对路径 vs 相对路径（最容易出错的地方）

这是 Linux 新手 90% 报错的总根源，单独放在前面。

| 写法 | 名字 | 从哪里开始算 | 特点 |
| --- | --- | --- | --- |
| `/root/work/llama.cpp` | 绝对路径 | 从根目录 `/` 开始 | **站着哪都能用** |
| `./build/bin/llama-server` | 相对路径 | 从**你当前站的地方**开始 | 站错地方就找不到 |
| `../logs` | 相对路径 | 上一层目录 | 同上 |
| `~/work` | 展开后是绝对路径 | `~` = `/root` | 好用 |

**你当前站在哪，决定了相对路径指向哪里。**

例如同一句 `./build/bin/llama-server`：

| 你站的地方 | 实际找的文件 | 结果 |
| --- | --- | --- |
| `/root/work/llama.cpp` | `/root/work/llama.cpp/build/bin/llama-server` | ✅ 找到 |
| `/mnt/c/Users/X` | `/mnt/c/Users/X/build/bin/llama-server` | ❌ 找不到 |

**排查三板斧**：`pwd` 看在哪 → `ls` 看这有什么 → 不对就 `cd` 过去。

**懒人做法**：直接写绝对路径，站着哪都不怕。

---

## 三、WSL 专用命令（在 **Windows 的 PowerShell** 里敲）

**这批命令不能在 Ubuntu 里敲**，会报 `command not found`。

| 命令 | 作用 |
| --- | --- |
| `wsl` | 进入默认发行版 |
| `wsl -d Ubuntu` | 进入指定发行版 |
| `wsl -l -v` | 列出所有发行版及状态 |
| `wsl --shutdown` | 关闭整个 Linux（改 `.wslconfig` 后必须执行） |
| `wsl --terminate Ubuntu` | 只关闭某一个发行版 |
| `wsl --install -d Ubuntu` | 安装新发行版 |
| `wsl --version` | 查看 WSL 自身版本 |

**为什么要重启 WSL**：改了 `.wslconfig`、DNS 配置、或网络出问题时，需要
`wsl --shutdown` 才能真正生效。

**一个有用的技巧**：WSL 会继承从 Windows 启动时所在的目录。你在
`C:\Users\X` 下敲 `wsl`，进去就站在 `/mnt/c/Users/X`。

---

## 四、Linux 基础命令

### 4.1 看路和走路

| 命令 | 作用 |
| --- | --- |
| `pwd` | 我在哪个目录 |
| `ls` | 这里有什么 |
| `ls -lh` | 带大小、带可读单位 |
| `cd 路径` | 走过去 |
| `cd ..` | 回上一级 |
| `cd ~` | 回主目录 |

### 4.2 搬东西

| 命令 | 作用 | 注意 |
| --- | --- | --- |
| `mkdir -p a/b` | 建目录 | `-p` = 不存在才建，已存在不报错 |
| `cp 源 目标` | 复制 | |
| `cp -r 目录 目标` | 复制整个目录 | |
| `mv 源 目标` | 移动或改名 | |
| `rm 文件` | 删文件 | |
| `rm -rf 目录` | 强制删目录 | **危险**，没有回收站 |

### 4.3 看和改内容

| 命令 | 作用 |
| --- | --- |
| `cat 文件` | 全部打印（小文件） |
| `head -20 文件` | 前 20 行 |
| `tail -20 文件` | 后 20 行 |
| `tail -f 文件` | 实时跟踪（`Ctrl+C` 退出，不影响被跟踪的进程） |
| `nano 文件` | 编辑：`Ctrl+O` 保存 → `Enter` → `Ctrl+X` 退出 |
| `grep 关键词 文件` | 挑出含关键词的行 |
| `grep -aE "A|B" 文件` | 挑出含 A 或 B 的行 |
| `wc -l 文件` | 数行数 |

### 4.4 进程、端口、资源

| 命令 | 作用 |
| --- | --- |
| `ps -ef \| grep xxx` | 找进程 |
| `pgrep -af xxx` | 找进程（含完整命令行） |
| `kill PID` | 按编号杀进程 |
| `pkill -f xxx` | 按名字杀进程 |
| `free -g` | 内存（单位 GB） |
| `df -h` | 磁盘 |
| `ss -ltnp` | 哪个程序占了哪个端口 |
| `top` | 实时资源监视（`q` 退出） |

---

## 五、本项目专用命令（AI 推理主战场）

| # | 命令 | 作用 | 什么时候用 |
| --- | --- | --- | --- |
| 1 | `nvidia-smi` | 看显卡与显存 | **核心仪表盘**，判断模型在不在 GPU |
| 2 | `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` | 只要显存数字 | 记录数据时 |
| 3 | `nvcc --version` | CUDA 版本 | 排错第一问 |
| 4 | `cmake -B build -DGGML_CUDA=ON ...` | 生成构建方案 | 首次编译或改了编译选项 |
| 5 | `cmake --build build -j 16` | 实际编译 | 同上 |
| 6 | `llama-server` | 启动推理服务 | 每次做实验 |
| 7 | `llama-bench` | 标准测速 | 采基线数字 |
| 8 | `curl` | 给服务发请求 | 验证接口、采集响应 |
| 9 | `sha256sum 文件` | 算文件指纹 | 模型校验 |
| 10 | `pkill -f llama-server` | 停服务 | 换配置、做恢复实验 |

### 5.1 启动服务的完整命令

```bash
/root/work/llama.cpp/build/bin/llama-server -m /root/work/models/Qwen3-4B-Q4_K_M.gguf -ngl 99 -c 8192 --host 0.0.0.0 --port 8080 -lv 4 -cram 0 --metrics
```

### 5.2 查看 GPU 驻留证据

```bash
grep -aE "offloaded|buffer size" /root/work/logs/gpu_evidence.log
```

应看到 `offloaded 37/37 layers to GPU`、`CUDA0 model buffer size`、
`CUDA0 KV buffer size` 等行。

### 5.3 发一条请求

```bash
curl -sS http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"local","messages":[{"role":"user","content":"你好"}],"max_tokens":128,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}'
```

---

## 六、常用组合招式

| 想要的效果 | 命令 |
| --- | --- |
| 实时盯日志 | `tail -f 日志文件` |
| 从日志挑关键行 | `grep -aE "关键词1\|关键词2" 日志文件` |
| 给命令加超时（本机必须养成） | `timeout 60 命令` |
| 屏幕显示 + 同时存文件 | `命令 2>&1 \| tee 输出.txt` |
| 存输出（含报错） | `命令 > 输出.txt 2>&1` |
| 后台运行，关终端也不停 | `setsid nohup 命令 > 日志.txt 2>&1 < /dev/null &` |
| 把 JSON 排版再看 | `命令 \| python3 -m json.tool` |
| 统计某项出现次数 | `grep -c 关键词 文件` |

### 关于 `2>&1` 是什么

- `>` 只管"正常输出"，报错信息走另一条道（标准错误），会漏掉；
- `2>&1` 的意思是"把报错也并到正常输出里"，这样才会一起被存下来。

**要留证据时记得加**，否则失败会静悄悄地过去（这一点本项目已经踩过一次坑：
一个 `curl -s ... > 文件` 因为请求失败，产生了一个 0 字节的空文件，却毫无提示）。

---

## 七、报错速查

报错的通用读法：**看它点名了什么**，通常第一行就写清楚了是什么东西不对。

| 报错 | 真实含义 | 怎么办 |
| --- | --- | --- |
| `command not found` | 这个命令不存在，或拼写错了 | 检查拼写；`nvidia -smi` 应为 `nvidia-smi` |
| `No such file or directory` | 路径不对，或站错目录 | `pwd` + `ls` 确认位置；改用绝对路径 |
| `Permission denied` | 权限不够 | 本项目是 root，一般不会遇到；文件不可执行时用 `chmod +x` |
| `invalid argument: xxx` | 有个参数它不认识 | 到命令里找 `xxx`，删掉或改成正确写法 |
| `address already in use` | 端口被别的程序占了 | `pkill -f llama-server`，或换 `--port` |
| `Connection refused` | 服务没在跑，或地址端口不对 | 先 `curl 127.0.0.1:8080/health` 确认服务活着 |
| 命令敲下去一直不动 | 网络卡住，没有超时限制 | `Ctrl+C` 中止，重试时加 `timeout 60` |
| `Killed` | 内存或显存不够，被系统杀掉 | 看 `free -g` 和 `nvidia-smi`，减小 `-c` 或模型 |

### 特别说一个：文档里的记号不要照着敲

| 记号 | 含义 |
| --- | --- |
| `...` | 省略，后面还有内容 |
| `<文件名>` | 换成真实文件名，**尖括号也要去掉** |
| `[选项]` | 可选，不用就整段删掉 |
| `xxx` / `YYY` | 占位符，要替换 |

本项目实际踩过一次：把文档里的 `...` 当成参数敲进 `llama-server`，
得到报错 `error: invalid argument: ...`。

---

## 八、两条纪律

**第一，`rm` 和 `mv` 之前先看清楚路径。**

当前是 root 身份，`/mnt/c`、`/mnt/e` 指向你的 Windows 磁盘，在 WSL 里可以直接
读写。一条写错的删除命令会**直接抹掉 Windows 上的文件，不进回收站**。

**第二，`/mnt/` 是"隔壁办公室"，`/root/` 是你自己的办公桌。**

- `/mnt/c`、`/mnt/e`：Windows 的 C 盘、E 盘，只是"可以走过去"；
- `/root/work`：你的项目、模型、日志真正住的地方；
- 两者之间用 `cp` 搬东西，但**不要把项目直接放在 `/mnt/` 下跑**，读写会慢很多。

---

## 九、本项目当前的目录约定

| 路径 | 内容 |
| --- | --- |
| `/root/work/antlab-infra` | 你的 GitHub 仓库（提交的东西） |
| `/root/work/llama.cpp` | 推理引擎源码与编译产物 |
| `/root/work/models` | 模型文件（不进仓库） |
| `/root/work/logs` | 运行日志 |
| `/mnt/e/codex/2026-10-08/antlab-agent-infra-fork-agent-https` | 工作区（含本手册等资料） |
