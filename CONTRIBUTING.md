# Contributing to SignalRoom AI

感谢你对 SignalRoom AI 的关注。欢迎提交文档修正、测试改进、Provider 适配器和可观测性改进。

## 开发流程

1. Fork 项目并创建独立分支。
2. 复制 .env.example 为 .env；不要提交真实 API Key、数据库凭据或本地运行数据。
3. 保持变更聚焦，新增行为必须包含测试。
4. 在提交前运行 Backend pytest、Ruff、Mypy，以及 Frontend lint、typecheck、build。
5. Pull Request 请说明动机、变更范围、验证命令和已知限制。

## 代码原则

- Provider 必须遵循既有接口边界。
- 核心金融评分保持确定性，不把关键数字决策交给 LLM。
- SEC 结论必须保留可打开的来源 URL 和引用上下文。
- 默认测试不得访问外部 API。
- 不要提交 .env、密钥、数据库 dump、Qdrant storage 或构建产物。

## Pull Request 检查清单

- [ ] 变更范围与 Issue 或目标一致。
- [ ] 已补充或更新测试。
- [ ] Backend 和 Frontend 质量检查通过。
- [ ] 文档、环境变量示例和错误处理已同步。
- [ ] 未提交任何敏感信息。
