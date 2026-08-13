# 商品管理设计验收

## 商品卡片列表

- 参考图：`C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-53513273-fdb7-4d3b-a8a1-039a25a0e399.png`
- 实现截图：`C:\Users\Administrator\Documents\Codex\2026-08-04\new-chat\work\greenwind-erp\implementation-product-cards-viewport.png`
- 浏览器状态：已登录，商品管理页，验证 180# / 350# 规格切换与库存弹窗。
- 结果：三列图片卡片、规格标签、编辑和库存入口符合参考结构；保留当前 ERP 导航、字体和配色。
- 交互：规格切换与库存弹窗正常；控制台无错误。

## 新建商品编辑器

- 参考图：`C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-c884860e-d2ac-4fb8-89b0-f5a876848cfd.png`
- 实现截图：`C:\Users\Administrator\Documents\Codex\2026-08-04\new-chat\work\greenwind-erp\implementation-product-editor-normalized.png`
- 并排对比：`C:\Users\Administrator\Documents\Codex\2026-08-04\new-chat\work\greenwind-erp\design-qa-product-editor-comparison.png`
- 浏览器视口：1661 × 1150 CSS px；设备像素比 0.8。
- 参考图尺寸：1727 × 856 px；实现原始截图：2076 × 1438 px；归一化截图：1328 × 920 px。
- 验证状态：新建商品弹窗，两个规格行，第二行设为默认规格。

### 全局结构

实现与参考图保持相同的信息层级：上方是“基础信息”，下方是横向“规格信息”表格，规格表下方居中添加规格，底部集中放置返回和保存按钮。实现沿用绿风 ERP 当前弹窗、侧栏和绿色视觉体系，没有复制旧系统中与当前业务无关的字段。

### 细节核对

- 字体：沿用项目的 `DM Sans / Noto Sans SC`，中文标签和表头清晰。
- 间距：基础信息采用三列主表单加右侧图片区；规格表保持连续横向对齐。
- 颜色：标题、按钮、默认规格状态均使用现有绿色令牌，危险操作使用红色。
- 图片：商品主图和每个规格均有独立上传入口及预览位置。
- 文案：基础信息、采购/库存/项目单位及换算关系、规格编码、采购价、销售价、最低售价、换花成本、月租价、库存和排序均已覆盖。

### 交互验证

- “添加规格”可新增规格行。
- “设为默认”可在规格行之间切换，并保证只有一个默认规格。
- 删除默认规格后会自动提升剩余第一条为默认规格。
- 新建商品草稿未保存，不会产生测试数据。
- 浏览器控制台错误：无。

### 差异与结论

- 无 P0/P1/P2 问题。
- P3：当前实现字段比参考图更完整、表格更密集；这是采购、库存和项目计价需要的业务字段，予以保留。
- 对比历史：首次并排核对即通过，无需再做结构性修正。

final result: passed
