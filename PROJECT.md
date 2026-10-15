# PROJECT.md — CC-ZH 简明中文

## 定位

给大模型的中文受控写作规范(CC-ZH),灵感来自 ASD-STE100 与 Karpathy 的推文。
差异:三档提示词复制即用、配额制(限量不禁用)、零依赖 linter、覆盖图/网页/视频层。

- 代码路径:`~/Projects/cc-zh/`
- 仓库:github.com/nonlinearHuman/cc-zh

## 状态

2026-10-15:v1.0 发布。README(10 规则 + 禁用清单 + 配额表 + 三档)、prompt.md、linter.py。

## Next Tasks

- [ ] 观察 issue 反馈,校准配额数字(v1.1 候选)
- [ ] 用 3-5 篇真实 AI 生成文章跑 linter,记录误报率
- [ ] 传播:X 文案已备,发布后可写公众号长文「我如何给 AI 立中文规矩」

## Completed

- [x] 赛道调研(5 个竞品,定位差异化)
- [x] CC-ZH 规范优化(融入 mingwen 草稿的配额制、linter、30 秒上手、同赛道对照)
- [x] v1.0 发布(README + prompt + linter,自检硬违规 0)

## 决策记录

- 以 Alex 提供的 CC-ZH 为主体;mingwen 草稿保留在 `~/Projects/mingwen`,未发布
- 不做白名单词表,做黑名单 + 配额(中文构词灵活,白名单维护不可行)
- 表格/代码块/示例行不查(v1 简化,README 已声明)
- B5 数法:汉字逐字,连续英文/数字串算 1 字(linter 与规范一致)
