# GitHub 上传说明

当前电脑已安装 Git，但没有安装 GitHub CLI，所以有两种上传方式。

## 方式一：网页创建仓库 + 命令推送

1. 打开 GitHub。
2. 新建一个仓库，例如：

```text
greenwind-erp
```

3. 仓库先不要勾选 README、.gitignore、License。
4. 创建后复制仓库地址，例如：

```text
https://github.com/你的用户名/greenwind-erp.git
```

5. 在项目目录执行：

```bash
git remote add origin https://github.com/你的用户名/greenwind-erp.git
git branch -M main
git push -u origin main
```

如果提示登录，就按 GitHub 弹窗登录。

## 方式二：安装 GitHub CLI

安装 GitHub CLI 后执行：

```bash
gh auth login
gh repo create greenwind-erp --private --source=. --remote=origin --push
```

## 注意

- 数据库文件不会上传 GitHub。
- `.env` 不会上传 GitHub。
- `node_modules` 不会上传 GitHub。
- 飞牛 NAS 部署时需要自己复制 `.env.example` 为 `.env` 并修改。
