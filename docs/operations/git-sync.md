# GitHub 同步工作流

目标仓库：https://github.com/zbw-ai/-tiktok- 。当前为公开仓库，默认工作分支为 main。

## 自动同步的含义

每轮已完成的更新 → 检查 → Git 提交 → 推送 origin 当前分支 → 核对远端提交。

AGENTS.md 要求后续 AI 协作者每轮更新完成后执行。安装 .githooks/post-commit 后，普通 git commit 也会触发推送。没有后台文件保存监听或定时任务；尚未提交的手工编辑不会被上传。

## 首次使用

需要 Git、Python 3.9+ 和有效 GitHub Git 认证。新克隆不会自动启用 hook，需在仓库根目录执行：

```sh
git config core.hooksPath .githooks
```

如果当前 core.hooksPath 已有自定义配置，应先检查整合，不能直接覆盖已有工作流。Git 认证由本机管理，不进入仓库。

## 日常更新

```sh
git status --short
git diff
python3 scripts/sync.py "docs: 更新第一轮内容实验"
```

sync.py 会将当前工作区所有未忽略改动提交，包括新增、修改和删除，所以应先检查工作区。若混有其他人的未完成工作，应显式 git add 本轮文件，然后 git commit，由 hook 推送。

仅重试推送已有提交：

```sh
python3 scripts/sync.py --push-only
```

只提交本地、暂不触发 hook 的显式操作：

```sh
TIKTOK_SYNC_SKIP_PUSH=1 git commit -m "暂存的本地工作"
```

## 失败行为

- 网络或认证失败：文件和已创建提交保留，命令返回非零；恢复后重试。
- 远端包含本地没有的提交：停止；检查差异，人工决定合并或其他正常整合方式，再推送。不会 force push。
- detached HEAD、未完成 merge/rebase 等操作，或任何未解决的索引冲突（包括 stash pop 冲突）：不自动暂存或提交，先处理 Git 状态。
- 并发同步：使用 .git/tiktok-sync.lock 阻止同时运行。异常终止留下锁时，先确认没有同步进程，再手动移除空锁目录。
- Git 的 post-commit hook 失败不会撤销已完成提交，也不保证外层 git commit 返回失败；因此必须阅读同步结果。sync.py 会返回同步失败并检查远端实际提交。
- 没有无限后台重试。失败会在当前命令中报告，下次完整更新或显式 push-only 可以重试。

## 验证

工具测试使用临时本地 Git 仓库，不操作正式 GitHub 远端：

```sh
python3 -m unittest discover -s tests -v
```

覆盖首次同步、忽略本地凭据文件、无改动重试、普通提交 hook、远端分叉、连接失败后保留提交、detached HEAD，以及保留 stash pop 未解决的二进制冲突。

实际推送后比较本地 HEAD 与远端当前分支；只有相同才报告云端同步完成。
