from pathlib import Path

here = Path(__file__).resolve()
dev = here.parent.parent

print("本文件位置：", here)
print("开发目录：", dev)
import json

cfg_path = dev / "configs" / "workload.json"
data = json.loads(cfg_path.read_text(encoding="utf-8"))

print("版本：", data["workload_version"])
print("冻结日期：", data["frozen_at"])
print("任务数：", len(data["tasks"]))
print()
print("任务清单：")

for t in data["tasks"]:
    line = f'{t["id"]}  {t["title"]}  输出上限 {t["max_tokens"]}'
    if t["file"]:
        fpath = dev.parent / "提示词与输入文档" / "输入文档" / t["file"]
        content = fpath.read_text(encoding="utf-8")
        line += f'   资料：{t["file"]}（{len(content)} 字符）'
    print(line)