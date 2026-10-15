# 数值 KR：至少达到 / 不超过

`type=1` 的 `target` 支持 `operator: "gte" | "lte"`，省略时按 `gte` 解释。
`gte` 目标值必须大于 0；`lte` 允许 0。两者要求非空单位、有限数值和非负当前值。
未记录 (`current_value=null`) 不等同于已记录 0，不判定为达标。

`gte` 保留原有比例进度；`lte` 当前达标计 100，否则计 0。`usage_percent` 为上限使用比例，允许超过 100，零上限或未记录时返回 null。
目标和仪表盘均以 progress 等权平均得到当前达成度；达标数量用 is_achieved，不能用四舍五入后的百分比判断。
前端上限型展示额度使用和达标状态，活跃周期用“达标中”，归档页用“已达成”。

## 升级

已有数据库在启动新后端之前，使用与服务相同的环境配置运行：

```sh
python -m app.migrate
```

命令幂等，只新增可空的 `progress_record.target_snapshot`，不会改写旧记录。新库的 `sql/init.sql` 和 ORM 已包含该字段。
先迁移，再发布后端和桌面前端。旧客户端省略 operator 更新目标时保留已有 operator。
旧移动端无法正确展示上限型；移动端升级之前不要在移动端使用上限型 KR。

新数值记录保存当时完整 target；改动规则/目标/单位且有当前值时，追加一次重新判定记录。
历史记录保留原始 is_achieved，不能使用现在的 target 重算。
旧记录缺少快照，只展示原始数值和判定，不能恢复其当时的目标值或单位。
归档页仍使用归档 KR 的配置与当前值；进度明细使用逐条快照。

## 验证

```sh
python -m pytest -q
```

本地联调启用 aSSO 后端 :8000、aSSO 前端 :5173、OKR 后端 :8001，以及匹配 FRONTEND_URL 的 OKR 前端。
测试账号参见 tidal/Readme/test.md，通过 /api/auth/sso/login 登录。
核对未记录、0、6、10、11、11 改回 6、零上限、修改目标和规则、旧 gte 数据、历史快照与归档显示。

真实 HTTP 回归需要安装 httpx，设置 `SSO_TEST_USERNAME`、`SSO_TEST_PASSWORD` 为测试文档中的账号，再运行：

```sh
OKR_LIVE_TEST=1 python -m pytest -q tests/test_numeric_live.py
```

该用例通过真实 SSO 登录、授权码与回调取得身份；只操作自己新建的联调周期，结束后将其归档。
默认测试集跳过这个会写入测试数据的用例。

2026-10-15 验证：87 项单元测试通过；单独启用的真实 SSO/HTTP 回归通过；桌面前端构建和 React 静态渲染/展示逻辑检查通过。
浏览器自动化无法取得窗口，未进行浏览器视觉和点击回归。现有 Pydantic 配置产生一条弃用警告。
