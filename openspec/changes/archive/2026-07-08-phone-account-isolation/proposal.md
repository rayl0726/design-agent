## Why

当前系统没有账号体系，所有会话和项目数据混在一起，无法区分不同使用者的资料。为了支持多人使用并保证数据隔离，需要引入基于手机号的账号体系。

## What Changes

- 在 Java 服务（agent-api）中新增账号模块，支持手机号注册/登录。
- 用户资料（项目、会话、反馈等）按账号隔离，不同账号之间不可见。
- 登录流程采用"手机号 + 短信验证码"，验证码统一固定为 `8888`，不调用真实短信接口，但保留短信发送能力的扩展点。
- 新增登录/注册/发送验证码 API，并在现有需要用户身份的操作中接入账号上下文。
- 无已有账号体系，本次为新增功能，对现有匿名使用方式构成 **BREAKING** 变更：后续所有操作均需要登录态。

## Capabilities

### New Capabilities

- `phone-account-isolation`: 基于手机号的账号体系，包含注册、登录、验证码、资料隔离。

### Modified Capabilities

- 无

## Impact

- **agent-api**: 新增账号相关的 Entity、Repository、Service、Controller；现有项目/会话/反馈等表增加 `user_id` 关联。
- **前端**: 新增登录页，并在请求中携带 token。
- **数据库**: MySQL 新增 `users` 表，并给 `projects`、`session_messages`、`feedbacks` 等表增加 `user_id` 字段。
