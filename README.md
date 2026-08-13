# 绿风环境花卉 ERP 管理系统

基于原管理软件抓取资料重建的新一代 ERP。当前版本包含登录、后台布局、仪表盘、权限校验基础能力和模块路由骨架。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、ECharts
- 后端：FastAPI、SQLAlchemy、SQLite（开发环境）
- 测试：Pytest、FastAPI TestClient、前端 TypeScript 构建检查

## 快速启动

Windows 用户可以直接双击：

1. `01-初始化环境.bat`（首次运行一次）
2. `02-启动后端.bat`
3. `03-启动前端.bat`

也可以在 PowerShell 中执行：

首次执行：

```powershell
.\scripts\setup.ps1
```

分别启动后端和前端：

```powershell
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

访问 `http://127.0.0.1:5173`。

开发账号：`admin` / `admin123`

> 开发账号只供本地测试，上线前必须修改密码和密钥。

## 当前里程碑

- 登录认证与本地开发账号
- ERP 主布局与完整一级菜单
- 仪表盘指标、趋势图、订单构成和待办事项
- 后端健康检查与认证保护接口
- 业务模块路由骨架
- 自动化测试、生产构建和依赖安全审计

下一阶段建议优先实现：物料管理（分类、列表、新增编辑、库存流水）。

