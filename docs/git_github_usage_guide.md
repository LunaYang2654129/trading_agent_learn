# Git 与 GitHub 使用指南：SSH 版本

本文档面向当前项目：

```text
C:\Users\10136\Desktop\trading_agent_learn
```

当前推荐远程仓库地址：

```text
git@github.com:1snek0da/trading_agent_learn.git
```

本指南只保留 SSH 方式绑定 GitHub，不依赖 GitHub CLI。

重点内容：

- 配置 Git 用户信息。
- 生成并绑定 SSH key。
- 把本地仓库 remote 改为 SSH 地址。
- 使用分支进行日常开发、提交、推送和合并。

参考资料：

- GitHub SSH key 文档：https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account
- GitHub Flow 文档：https://docs.github.com/en/get-started/using-github/github-flow

## 1. Git 与 GitHub 的关系

`Git` 是本地版本控制工具，负责记录文件变化、提交历史和分支。

`GitHub` 是远程代码托管平台，负责保存远程仓库、协作、Pull Request 和代码审查。

推荐工作流：

```text
本地修改 -> git add -> git commit -> git push -> GitHub 远程分支 -> Pull Request -> 合并到主分支
```

## 2. 检查 Git

```powershell
git --version
```

如果命令不存在，需要先安装 Git：

```text
https://git-scm.com/downloads
```

## 3. 配置 Git 用户信息

首次使用 Git 时，设置提交作者信息：

```powershell
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

查看全局配置：

```powershell
git config --global --list
```

如果只想对当前项目设置：

```powershell
git config user.name "你的GitHub用户名"
git config user.email "你的GitHub邮箱"
```

## 4. 检查是否已有 SSH key

```powershell
Get-ChildItem ~/.ssh
```

常见文件：

```text
id_ed25519
id_ed25519.pub
```

说明：

- `id_ed25519` 是私钥，不能泄露。
- `id_ed25519.pub` 是公钥，可以添加到 GitHub。

如果已经有可用的 `id_ed25519.pub`，可以跳到第 6 节。

## 5. 生成 SSH key

把邮箱替换为自己的 GitHub 邮箱：

```powershell
ssh-keygen -t ed25519 -C "你的GitHub邮箱"
```

默认保存路径通常是：

```text
C:\Users\你的用户名\.ssh\id_ed25519
```

建议：

- 路径直接回车，使用默认路径。
- passphrase 可设置，也可以直接回车留空。
- 如果提示覆盖已有 key，先确认旧 key 是否还在其他项目使用。

## 6. 启动 ssh-agent 并添加私钥

启动 Windows 的 ssh-agent：

```powershell
Start-Service ssh-agent
```

添加私钥：

```powershell
ssh-add ~/.ssh/id_ed25519
```

检查已加载的 key：

```powershell
ssh-add -l
```

如果 `Start-Service ssh-agent` 报权限问题，可以用管理员 PowerShell 执行：

```powershell
Set-Service -Name ssh-agent -StartupType Automatic
Start-Service ssh-agent
```

## 7. 复制 SSH 公钥

```powershell
Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard
```

也可以直接查看并手动复制：

```powershell
Get-Content ~/.ssh/id_ed25519.pub
```

只复制 `.pub` 文件内容，不要复制私钥文件。

## 8. 在 GitHub 添加 SSH key

打开 GitHub 网页：

```text
Settings -> SSH and GPG keys -> New SSH key
```

填写：

```text
Title: 当前电脑名称，例如 Windows Laptop
Key type: Authentication Key
Key: 粘贴 id_ed25519.pub 内容
```

保存后，这台电脑就可以通过 SSH 访问你的 GitHub 仓库。

## 9. 测试 SSH 连接

```powershell
ssh -T git@github.com
```

第一次连接可能提示是否信任 GitHub host：

```text
Are you sure you want to continue connecting?
```

输入：

```text
yes
```

成功时通常会看到类似：

```text
Hi 用户名! You've successfully authenticated...
```

## 10. 进入当前项目

```powershell
cd C:\Users\10136\Desktop\trading_agent_learn
```

检查是否是 Git 仓库：

```powershell
git status
```

如果提示：

```text
fatal: not a git repository
```

说明当前目录不是 Git 仓库，需要先初始化：

```powershell
git init
```

## 11. 查看远程仓库

```powershell
git remote -v
```

当前项目应该使用 SSH 地址：

```text
git@github.com:1snek0da/trading_agent_learn.git
```

## 12. 绑定或修改为 SSH remote

如果还没有 `origin`：

```powershell
git remote add origin git@github.com:1snek0da/trading_agent_learn.git
```

如果已经有 `origin`，改成 SSH：

```powershell
git remote set-url origin git@github.com:1snek0da/trading_agent_learn.git
```

再次检查：

```powershell
git remote -v
```

期望看到：

```text
origin  git@github.com:1snek0da/trading_agent_learn.git (fetch)
origin  git@github.com:1snek0da/trading_agent_learn.git (push)
```

## 13. 第一次提交并推送

查看修改：

```powershell
git status
```

添加文件：

```powershell
git add .
```

提交：

```powershell
git commit -m "Initial project setup"
```

推送到远程主分支：

```powershell
git push -u origin main
```

如果本地默认分支叫 `master`，可以改为 `main`：

```powershell
git branch -M main
```

## 14. 分支管理核心概念

建议规则：

- `main`：稳定主分支，只放已经验证过的代码。
- `dev`：阶段集成分支，可选。
- `feature/...`：新功能分支。
- `fix/...`：缺陷修复分支。
- `docs/...`：文档分支。
- `codex/...`：Codex 辅助开发分支。

分支命名示例：

```text
feature/technical-agent
fix/llm-connection-check
docs/git-github-guide
codex/upload-multiple-agent-finance
```

当前项目所在分支：

```text
codex/upload-multiple-agent-finance
```

## 15. 查看、创建、切换分支

查看当前分支：

```powershell
git branch --show-current
```

查看本地分支：

```powershell
git branch
```

查看本地和远程分支：

```powershell
git branch -a
```

创建并切换到新分支：

```powershell
git switch -c feature/technical-agent
```

切换到已有分支：

```powershell
git switch main
```

从远程分支创建本地跟踪分支：

```powershell
git switch -c feature/technical-agent origin/feature/technical-agent
```

## 16. 推荐分支开发流程

每个功能单独开分支：

```powershell
git switch main
git pull origin main
git switch -c feature/your-task
```

开发完成后：

```powershell
git status
git add .
git commit -m "Implement your task"
git push -u origin feature/your-task
```

然后在 GitHub 网页上创建 Pull Request，把 `feature/your-task` 合并到 `main` 或 `dev`。

## 17. 拉取远程更新

切到目标分支：

```powershell
git switch main
```

拉取远程更新：

```powershell
git pull origin main
```

如果当前功能分支需要同步主分支：

```powershell
git switch feature/your-task
git fetch origin
git merge origin/main
```

如果团队要求线性历史，也可以使用 rebase：

```powershell
git switch feature/your-task
git fetch origin
git rebase origin/main
```

说明：

- `merge` 会保留分支合并记录，适合多数初学场景。
- `rebase` 会改写当前分支提交历史，推送共享分支前要谨慎。

## 18. 合并分支

本地合并：

```powershell
git switch main
git pull origin main
git merge feature/your-task
git push origin main
```

更推荐通过 GitHub Pull Request 合并：

```text
feature branch -> Pull Request -> review/test -> merge -> main
```

## 19. 删除分支

删除本地分支：

```powershell
git branch -d feature/your-task
```

强制删除本地分支：

```powershell
git branch -D feature/your-task
```

删除远程分支：

```powershell
git push origin --delete feature/your-task
```

## 20. 撤销与回退

查看工作区修改：

```powershell
git diff
```

取消暂存：

```powershell
git restore --staged 文件路径
```

撤销某个文件的未提交修改：

```powershell
git restore 文件路径
```

撤销最近一次提交但保留文件修改：

```powershell
git reset --soft HEAD~1
```

创建反向提交来撤销某个历史提交：

```powershell
git revert 提交哈希
```

注意：不要随意执行 `git reset --hard`，它会丢弃未保存的修改。

## 21. `.gitignore` 管理

敏感文件和运行产物不要提交：

```text
.env
__pycache__/
.pytest_cache/
outputs/
data/raw/
```

检查某个文件为什么被忽略：

```powershell
git check-ignore -v 文件路径
```

## 22. 常见错误

### 22.1 `Permission denied (publickey)`

通常是 SSH key 没配好。检查：

```powershell
ssh -T git@github.com
ssh-add -l
git remote -v
```

确认 remote 必须是 SSH 格式：

```text
git@github.com:1snek0da/trading_agent_learn.git
```

### 22.2 `remote origin already exists`

说明已经绑定过 `origin`。查看：

```powershell
git remote -v
```

改成 SSH：

```powershell
git remote set-url origin git@github.com:1snek0da/trading_agent_learn.git
```

### 22.3 推送新分支失败

第一次推送新分支时要建立 upstream：

```powershell
git push -u origin 当前分支名
```

查看当前分支名：

```powershell
git branch --show-current
```

### 22.4 本地分支落后远程

先拉取远程更新：

```powershell
git pull origin 当前分支名
```

如有冲突，解决冲突后：

```powershell
git add .
git commit -m "Resolve merge conflicts"
git push origin 当前分支名
```

## 23. 本项目推荐日常命令

进入项目：

```powershell
cd C:\Users\10136\Desktop\trading_agent_learn
```

确保 remote 是 SSH：

```powershell
git remote set-url origin git@github.com:1snek0da/trading_agent_learn.git
git remote -v
```

查看状态：

```powershell
git status
git branch --show-current
```

创建文档分支：

```powershell
git switch -c docs/git-github-guide
```

提交文档：

```powershell
git add docs/git_github_usage_guide.md
git commit -m "Add Git and GitHub SSH usage guide"
```

推送分支：

```powershell
git push -u origin docs/git-github-guide
```

然后在 GitHub 网页上创建 Pull Request。

## 24. 推荐团队规范

- 所有开发从 `main` 拉新分支，不直接在 `main` 上开发。
- 每个功能一个分支，每个分支只解决一个明确问题。
- 提交信息使用动词开头，例如 `Add`、`Fix`、`Update`、`Refactor`。
- PR 合并前至少运行一次测试或编译检查。
- `.env`、API key、数据原始文件、报告输出文件不提交到 GitHub。
- 合并 PR 后及时删除已经完成的远程分支。
