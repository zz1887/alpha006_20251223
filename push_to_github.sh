#!/bin/bash
# 推送到GitHub的脚本

echo "==================================="
echo "准备推送代码到GitHub"
echo "==================================="

# 检查Git状态
echo -e "\n1. 检查Git状态..."
git status

# 显示将要推送的内容
echo -e "\n2. 显示提交历史..."
git log --oneline -5

# 显示远程仓库
echo -e "\n3. 远程仓库配置..."
git remote -v

echo -e "\n==================================="
echo "推送方式选择:"
echo "==================================="
echo "方式1: HTTPS + Token (推荐)"
echo "  - 需要GitHub Personal Access Token"
echo "  - 适合没有SSH密钥的情况"
echo ""
echo "方式2: SSH密钥"
echo "  - 需要配置SSH密钥"
echo "  - 适合长期使用"
echo ""
echo "方式3: GitHub CLI"
echo "  - 需要安装gh命令"
echo "  - 最简单的方式"
echo "==================================="

read -p "选择推送方式 (1/2/3): " choice

case $choice in
    1)
        echo -e "\n使用HTTPS方式推送..."
        echo "请按以下步骤操作:"
        echo "1. 访问 https://github.com/settings/tokens"
        echo "2. 创建Token并复制"
        echo "3. 运行: git push https://YOUR_TOKEN@github.com/zz1887/alpha006_20251223.git master"
        ;;
    2)
        echo -e "\n使用SSH方式推送..."
        echo "请按以下步骤操作:"
        echo "1. 生成SSH密钥: ssh-keygen -t rsa -b 4096 -C 'your_email@example.com'"
        echo "2. 查看公钥: cat ~/.ssh/id_rsa.pub"
        echo "3. 添加到GitHub: https://github.com/settings/keys"
        echo "4. 切换远程: git remote set-url origin git@github.com:zz1887/alpha006_20251223.git"
        echo "5. 推送: git push -u origin master"
        ;;
    3)
        echo -e "\n使用GitHub CLI..."
        echo "请按以下步骤操作:"
        echo "1. 安装: sudo apt install gh (Ubuntu/Debian)"
        echo "2. 登录: gh auth login"
        echo "3. 推送: git push -u origin master"
        ;;
    *)
        echo "无效选择"
        ;;
esac

echo -e "\n==================================="
echo "如果以上方式都不行，您也可以:"
echo "==================================="
echo "1. 在浏览器中访问: https://github.com/zz1887/alpha006_20251223"
echo "2. 点击 'Upload files'"
echo "3. 上传整个项目文件夹"
echo "==================================="
