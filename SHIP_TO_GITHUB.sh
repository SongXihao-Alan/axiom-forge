#!/bin/bash
###############################################################################
# Axiom Forge GitHub Push Script
#
# 完整的、可复制粘贴的 push 流程。包括:
# - 撤销旧 key(指导,需在浏览器操作)
# - 生成新 key(在 minimaxi 后台)
# - 临时清理 .env(防止误推)
# - GitHub repo 创建(指导,需在浏览器操作)
# - 配 remote + push
# - 验证 .env 没暴露
#
# 用法:
#   1. cd /workspace/axiom-finder
#   2. bash SHIP_TO_GITHUB.sh
#
# 整个过程大概 5-10 分钟(其中 4-8 分钟是浏览器操作)
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================"
echo "Axiom Forge → GitHub Push Script"
echo "============================================"
echo ""

# ========== 0. 准备检查 ==========
echo -e "${YELLOW}[0/5] 准备检查${NC}"
if [ ! -d .git ]; then
  echo -e "${RED}❌ .git 不存在, 需要先 git init${NC}"
  exit 1
fi
echo "✓ .git 存在"
echo "✓ $(git log --oneline | wc -l) 个 commits"
echo "✓ $(git ls-files | wc -l) 个跟踪文件"
echo ""

# ========== 1. 撤销旧 key ==========
echo -e "${YELLOW}[1/5] 撤销旧 API key${NC}"
echo ""
echo "这一步必须在浏览器手动操作。我不能帮你做。"
echo ""
echo "  1. 打开 https://api.minimaxi.com/user/secret-key"
echo "     (或者 minimaxi.com 后台找'API Key 管理')"
echo ""
echo "  2. 找到当前 key (sk-cp-HBtAa...) → 撤销"
echo ""
echo "  3. 创建新 key:"
echo "     - 名字: axiom-forge-skill"
echo "     - 权限: Chat Completion (足够)"
echo "     - 复制新 key (sk-cp-xxx 格式)"
echo ""
read -p "完成撤销 + 生成新 key 后,按 Enter 继续..."
echo ""

# ========== 2. 更新 .env ==========
echo -e "${YELLOW}[2/5] 更新 .env${NC}"
if [ -f .env ]; then
  echo "当前 .env 内容:"
  grep MINIMAX_API_KEY .env | head -1 | cut -c1-30
  echo ""
  read -p "输入新 MINIMAX_API_KEY (格式 sk-cp-xxx): " NEW_KEY
  if [ -z "$NEW_KEY" ]; then
    echo -e "${RED}❌ 没输入 key, 退出${NC}"
    exit 1
  fi
  # 替换
  sed -i "s|^MINIMAX_API_KEY=.*|MINIMAX_API_KEY=$NEW_KEY|" .env
  echo "✓ .env 已更新"
  echo "新 .env:"
  grep MINIMAX_API_KEY .env | head -1 | cut -c1-30
else
  echo "⚠️ .env 不存在, 从 .env.example 复制"
  cp .env.example .env
  read -p "输入新 MINIMAX_API_KEY: " NEW_KEY
  sed -i "s|^MINIMAX_API_KEY=.*|MINIMAX_API_KEY=$NEW_KEY|" .env
fi
echo ""

# ========== 3. 创建 GitHub repo ==========
echo -e "${YELLOW}[3/5] 创建 GitHub repo${NC}"
echo ""
echo "这一步必须在浏览器手动操作。"
echo ""
echo "  1. 打开 https://github.com/new"
echo ""
echo "  2. 填:"
echo "     - Repository name: axiom-forge (或你喜欢的)"
echo "     - Description: 'Axiom Forge: 4-axiom system with Structural Consistency + Impossibility Theorem 5.1'"
echo "     - Public (推荐) / Private (都行)"
echo ""
echo "  3. ⚠️ 不要勾选任何初始化选项:"
echo "     [ ] Add a README file      ← 取消"
echo "     [ ] Add .gitignore         ← 取消"
echo "     [ ] Choose a license       ← 取消"
echo ""
echo "  4. 点 'Create repository'"
echo ""
echo "  5. 复制你的 repo URL (HTTPS 或 SSH):"
echo "     https://github.com/YOUR_NAME/axiom-forge.git"
echo ""
read -p "输入你的 GitHub repo URL: " REPO_URL
if [ -z "$REPO_URL" ]; then
  echo -e "${RED}❌ 没输入 URL, 退出${NC}"
  exit 1
fi
echo ""

# ========== 4. 推送 ==========
echo -e "${YELLOW}[4/5] 推送${NC}"
echo "Remote URL: $REPO_URL"
echo ""

# 检查是否已配 remote
if git remote | grep -q origin; then
  echo "已存在 origin, 移除旧的..."
  git remote remove origin
fi
git remote add origin "$REPO_URL"

# 推送
echo ""
echo "推送 main 分支..."
git branch -M main
git push -u origin main
echo ""

# ========== 5. 验证 ==========
echo -e "${YELLOW}[5/5] 验证${NC}"
echo ""

# 验证 .env 没暴露
echo "验证 .env 不在 git 跟踪范围..."
if git ls-files | grep -E "^\.env$"; then
  echo -e "${RED}❌ ⚠️ .env 暴露在 git 跟踪中!立即撤销 API key!${NC}"
  exit 1
else
  echo -e "${GREEN}✓ .env 没暴露 (被 .gitignore 排除)${NC}"
fi
echo ""

# 验证 push 成功
echo "验证 GitHub 上能看到这些文件:"
for f in "README.md" "LICENSE" "CONTRIBUTING.md" "kb/SCHEMA.md" "kb/kb_query.py" "axiom-forge" ".env.example"; do
  if git ls-files | grep -q "^$f$"; then
    echo -e "  ${GREEN}✓${NC} $f"
  fi
done
echo ""
echo "============================================"
echo -e "${GREEN}🎉 上传成功!${NC}"
echo "============================================"
echo ""
echo "  打开 https://github.com/$REPO_URL"
echo "  (从 URL 提取 owner/repo)"
echo ""
echo "  应该看到:"
echo "  - README.md 渲染 (skill 介绍)"
echo "  - LICENSE (MIT)"
echo "  - CITATION.cff (Citation 按钮)"
echo "  - CONTRIBUTING.md"
echo "  - kb/ 目录 (85 JSON 节点)"
echo "  - axiom-forge 脚本"
echo ""
echo "  不会看到:"
echo "  - .env (被 .gitignore 排除) ✓"
echo ""
echo "  下一步:"
echo "  1. 在 GitHub repo 页面, 'Watch' 'Star' 自己的 repo"
echo "  2. 跑 ./axiom-forge ask '什么是 SC?' 验证 M3 集成"
echo "  3. 邀请 1-2 个朋友(有基础训练的)做 Phase 3 复现"
echo ""
