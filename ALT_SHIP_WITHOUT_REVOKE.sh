#!/bin/bash
###############################################################################
# ⚠️ 备用方案: 撤销不了旧 key 时的 push
#
# 这不是理想方案. 你应该尝试先撤销.
# 但如果平台不允许/找不到/你没时间,这个方案保证 .env 不暴露
###############################################################################

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================"
echo "⚠️ 备用 Push 方案(撤销不了旧 key)"
echo "============================================"
echo ""
echo "策略: 用 DUMMY key 替换 .env 里的真 key, push 完再换回"
echo "  - Push 出去的是 dummy key, 没人能用"
echo "  - 推送后, 把 .env 改回真 key (本地, 不会被 push)"
echo "  - 之后用真 key 跑时, 监控账号"
echo ""

read -p "确认用备用方案? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "取消, 请尝试撤销旧 key"
  exit 1
fi

# 备份 .env
cp .env .env.backup
echo "✓ .env 已备份到 .env.backup"

# 替换为 dummy
sed -i "s|^MINIMAX_API_KEY=.*|MINIMAX_API_KEY=sk-cp-DUMMY-DO-NOT-USE-REPLACE-LATER|" .env
echo "✓ .env 里的 key 改成 DUMMY"

# 确认 .gitignore 还是排除 .env
if ! grep -q "^\.env$" .gitignore; then
  echo ".env" >> .gitignore
  echo "✓ .gitignore 加了 .env"
fi

# 验证 .env 不在 git
if git ls-files | grep -E "^\.env$"; then
  echo -e "${RED}❌ ⚠️ .env 暴露!立即手动 git rm --cached .env${NC}"
  exit 1
fi

# 配 remote
read -p "输入 GitHub repo URL: " REPO_URL
if [ -z "$REPO_URL" ]; then
  echo "❌ 没 URL, 退出"
  exit 1
fi
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git branch -M main

# Push
echo ""
echo "推送..."
git push -u origin main

# 验证
echo ""
echo "验证 .env 没暴露..."
git ls-files | grep -E "^\.env$" && echo -e "${RED}❌ 暴露!⚠️${NC}" || echo -e "${GREEN}✓ .env 没暴露${NC}"

# 还原 .env
echo ""
echo "还原 .env (用回真 key)..."
mv .env.backup .env
echo "✓ .env 已还原"
echo ""
echo "============================================"
echo -e "${GREEN}推送完成${NC}"
echo "============================================"
echo ""
echo "⚠️ 警告: 你的旧 key 还活着! 用真 key 时, 监控账号用量"
echo "⚠️ 建议: 改完 push, 立刻去 minimaxi 后台尝试撤销"
echo ""
