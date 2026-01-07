# Git 工作流指南

## 仓库信息

**远程仓库**: `git@github.com:zz1887/alpha006_20251223.git`
**当前分支**: `master`
**初始提交**: `106796f` - 完整因子库初始化

---

## 快速开始

### 1. 查看当前状态
```bash
git status              # 查看文件状态
git log --oneline       # 查看提交历史
git diff                # 查看未暂存的修改
```

### 2. 日常开发流程

#### 场景 A: 开发新因子或功能
```bash
# 1. 从主分支创建新分支
git checkout master
git pull origin master                    # 确保最新
git checkout -b feature/alpha-peg-v2      # 创建功能分支

# 2. 开发和修改
# ... 编写代码 ...

# 3. 提交修改
git add factors/calculation/alpha_peg.py  # 添加特定文件
git commit -m "feat: 增加alpha_peg因子v2版本"

# 4. 推送到远程
git push origin feature/alpha-peg-v2

# 5. 在GitHub创建Pull Request，等待审查合并
```

#### 场景 B: 修复Bug
```bash
git checkout master
git pull origin master
git checkout -b hotfix/fix-data-loader

# ... 修复代码 ...
git add core/utils/data_loader.py
git commit -m "fix: 修复数据加载器的日期解析问题"
git push origin hotfix/fix-data-loader
```

#### 场景 C: 发布版本
```bash
# 方法1: 从master打标签
git checkout master
git pull origin master
git tag -a v1.2.0 -m "Release v1.2.0: 新增alpha_peg因子"
git push origin v1.2.0

# 方法2: 从develop合并后打标签
git checkout develop
git pull origin develop
git checkout master
git merge develop --no-ff
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin master --tags
```

---

## 因子版本管理最佳实践

### 1. 分支命名规范
```
功能开发: feature/{factor-name}-{version}
         例: feature/alpha-peg-v2

Bug修复: hotfix/{description}
         例: hotfix/fix-outlier-handling

实验分支: experiment/{description}
         例: experiment/zscore-normalization

发布分支: release/{version}
         例: release/v1.2.0
```

### 2. 提交信息规范
```
类型: 描述

可用类型:
- feat: 新功能/新因子
- fix: Bug修复
- refactor: 重构（不影响功能）
- docs: 文档更新
- test: 测试相关
- perf: 性能优化
- style: 代码格式调整
- chore: 构建/工具相关

示例:
feat: 增加alpha_peg因子支持多版本参数
fix: 修复数据加载器的内存泄漏问题
docs: 更新因子公式文档
```

### 3. 因子版本发布流程

```bash
# 1. 确保所有测试通过
python -m pytest tests/factors/

# 2. 更新版本号（遵循语义化版本）
# 修改 factors/versioning/metadata.py 中的版本号

# 3. 创建发布分支
git checkout -b release/v1.2.0

# 4. 生成变更日志
# 运行: python scripts/versioning/generate_changelog.py

# 5. 提交并打标签
git add .
git commit -m "release: v1.2.0"
git tag -a v1.2.0 -m "因子版本 v1.2.0: 支持行业中性化"

# 6. 推送
git push origin release/v1.2.0
git push origin v1.2.0

# 7. 合并到master
git checkout master
git merge release/v1.2.0 --no-ff
git push origin master
```

---

## 常用命令速查

### 查看历史
```bash
git log --oneline --graph --all          # 图形化历史
git log --author="zcy" --since="1 week"  # 特定作者和时间
git show <commit-hash>                   # 查看具体提交
```

### 撤销操作
```bash
git reset HEAD~1                         # 撤销上次提交（保留修改）
git checkout -- <file>                   # 丢弃文件修改
git revert <commit-hash>                 # 创建撤销提交
```

### 分支管理
```bash
git branch                               # 查看本地分支
git branch -a                            # 查看所有分支
git branch -d <branch-name>              # 删除已合并分支
git branch -D <branch-name>              # 强制删除分支
```

### 远程操作
```bash
git fetch origin                        # 获取远程更新
git pull origin master                  # 拉取并合并
git push origin <branch>                # 推送到远程
git push --force origin <branch>        # 强制推送（慎用）
```

---

## 与版本管理系统的集成

### 因子版本追踪

当您实现版本管理系统后，可以将 Git 与因子元数据关联：

```python
# 在因子版本创建时
version = VersionManager.create_version(
    factor_name="alpha_peg",
    code_hash=get_git_commit_hash(),  # 获取当前Git提交哈希
    ...
)

# 在版本信息中
{
    "version": "1.2.0",
    "git_commit": "abc1234...",
    "git_branch": "feature/alpha-peg-v2",
    ...
}
```

### 自动化工作流

创建 `.git/hooks/pre-commit` 钩子：

```bash
#!/bin/bash
# 预提交检查

echo "Running tests..."
python -m pytest tests/factors/ --tb=short

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi

echo "All checks passed!"
```

---

## 注意事项

### ⚠️ 永远不要提交的内容
- `data/` 目录下的原始数据和缓存
- `results/` 目录下的输出结果
- `logs/` 和 `errors/` 日志文件
- `.env` 环境变量文件
- 本地配置文件（如 `config/database_local.py`）

### ✅ 应该提交的内容
- 所有因子代码（`factors/`）
- 配置文件（`config/` 中非本地的）
- 文档（`docs/`）
- 测试代码（`tests/`）
- 脚本（`scripts/`）
- `.gitignore` 文件

### 🔒 安全提示
- 不要在代码中硬编码数据库密码
- 使用环境变量存储敏感信息
- 检查提交内容：`git diff --cached`

---

## 故障排除

### 问题: 提交了不应该提交的文件
```bash
# 从Git中移除但保留本地文件
git rm --cached data/large_file.csv
echo "data/large_file.csv" >> .gitignore
git add .gitignore
git commit -m "chore: 移除大文件并更新gitignore"
```

### 问题: 需要撤销最后一次提交
```bash
# 保留修改
git reset HEAD~1

# 完全丢弃
git reset --hard HEAD~1
```

### 问题: 分支冲突
```bash
git pull origin master
# 解决冲突
git add <resolved-files>
git commit -m "Merge conflict resolved"
```

---

## 下一步

现在仓库已经初始化完成，您可以：

1. **开始开发**: 创建新分支开发因子
2. **推送代码**: `git push origin master`（首次推送需要 `-u` 参数）
3. **实施版本管理**: 按照计划文件 `/home/zcy/.claude/plans/cheeky-wobbling-wolf.md` 实现版本管理系统

**重要**: 首次推送到远程时使用：
```bash
git push -u origin master
```

这将建立本地分支与远程分支的追踪关系。
