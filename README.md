# 巴西 TikTok 内容探索

面向巴西受众，探索由国内个人运营、AI 辅助生产的 TikTok 内容账号。先建立内容能力和受众理解，再评估商业合作。

仓库：[zbw-ai/-tiktok-](https://github.com/zbw-ai/-tiktok-)

## 当前状态

- **当前阶段：普通账号与内容验证。** 暂不推进带货、CPF、收款或公司设立。
- 账号尚未在本项目中注册或验证；尚无已发布内容和真实运营指标。
- 已完成首轮商业与平台规则调研；其商业建议作为后续参考，当前优先级以最新决策为准。
- 账号定位、名称、葡语审稿方式、投入预算及发布时间仍待确定。
- 项目维护方式：每轮完成更新后提交，并自动推送 GitHub。

## 阅读顺序

1. [背景与约束](docs/background.md)
2. [当前目标与阶段安排](docs/goals.md)
3. [决策：先普通账号、后商业化](docs/decisions/001-content-first.md)
4. [普通账号启动指南](docs/operations/account-start.md)
5. [从零开始：设备、安装、网络、注册与语言](docs/operations/zero-to-account.md)
6. [第一轮内容实验草案](experiments/001-content-pilot.md)
7. [首轮市场与商业可行性调研](docs/research/2026-10-21-brazil-feasibility.md)

## 仓库结构

```text
docs/          背景、目标、决策、调研、操作说明
content/       选题、脚本、配文与制作模板
experiments/   实验假设、安排与复盘
assets/        可公开的小型图片和素材说明
data/          数据口径及可公开的汇总数据
src/           后续业务工具代码
scripts/       仓库维护和同步工具
tests/         工具的验证用例
.githooks/     提交后自动推送的 Git hook
AGENTS.md      后续 AI 协作的持久工作规则
CHANGELOG.md   项目阶段与重要更新记录
```

## 更新与自动同步

在这个仓库中完成一轮内容或代码更新后，AI 协作者按照 [AGENTS.md](AGENTS.md) 检查、提交并推送。普通 `git commit` 完成后，已安装的 hook 也会自动推送当前分支。

新电脑克隆后，需要安装本仓库的 hook：

```sh
git clone https://github.com/zbw-ai/-tiktok-.git
cd -- -tiktok-
git config core.hooksPath .githooks
```

一次完成“提交 + 推送 + 远端验证”：

```sh
python3 scripts/sync.py "docs: 更新内容实验记录"
```

同步单位是**完成的一轮更新/一次 Git 提交**。没有安装文件保存监听器；手工保存但尚未提交的文件不会自动上传。手工编辑后可以运行上面的命令。网络失败保留本地提交，恢复后运行 `python3 scripts/sync.py --push-only`。远端有新提交时停止并提示人工合并，不自动覆盖。

完整说明见 [GitHub 同步工作流](docs/operations/git-sync.md)。

## 验证

运行环境：Git、Python 3.9+。同步工具只使用 Python 标准库。推送需要你已有的 GitHub Git 认证。

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

## 公开内容范围

仓库当前公开。项目说明、去标识调研、脚本和公开汇总可入库；密码、令牌、身份文件、银行卡信息、客户数据和未授权原片存放于忽略目录或其他合适位置。原视频等大文件的存储方式等出现实际需求后再决定。

事实和平台规则需标注来源及核查日期；建议、假设、草案与已执行结果明确区分。
