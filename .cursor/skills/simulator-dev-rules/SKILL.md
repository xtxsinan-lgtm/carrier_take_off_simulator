---
name: simulator-dev-rules
description: >-
  航母起飞仿真项目的开发规范：每个函数需有单元测试、功能改动需有 e2e 测试、注释一律中文。
  在本仓库新增或修改 Python/前端/测试代码时使用。
---

# 航母起飞仿真 — 开发规范

## 三条硬性规则

1. **所有 function 必须有 unit test**
2. **功能改动需要有 e2e test**
3. **所有注释用中文**

## 实施流程

每次改代码前复制此清单并逐项完成：

```
- [ ] 新增/修改的每个 function 都有对应 unit test
- [ ] 若是功能改动，已补充 e2e test
- [ ] 注释、docstring、行内说明均为中文（模块 docstring 亦用中文）
- [ ] 若改了 utils/simulators/CSV：已运行 python3 scripts/build_all.py
- [ ] 已运行 python3 -m pytest tests/ -m "not e2e" -q（含前端产物同步检查）
```

**禁止手改**（一律由 build 生成）：

- `docs/js/physics.js`
- `miniprogram/utils/physics.js`
- `docs/data.json` / `docs/py/**`（由 `build_docs` 生成）
- `miniprogram/data/data.json`（由 `build_miniprogram` 生成）

## 1. 单元测试

**范围**：项目中每一个 `def`（含模块内私有函数 `_foo`、类方法）。

**位置**：`tests/<模块名>_test.py`，测试函数命名 `test_<行为>`。

**示例**：

| 被测代码 | 测试文件 |
|---------|---------|
| `utils/trajectory.py` | `tests/trajectory_test.py` |
| `apps/web_simulator.py` 中 `_capture_trajectory` | `tests/trajectory_test.py` 或 `tests/web_simulator_test.py` |
| `utils/ski_jump_geometry.py` 中 `deck_height_at_s` | `tests/ski_jump_geometry_test.py` |

**运行**（跳过慢速 e2e）：

```bash
python3 -m pytest tests/ -m "not e2e" -v
```

## 2. E2E 测试

**何时需要**：任何**功能改动**（新 API 字段、新仿真行为、新 Web 输出等），不仅是重构。

**写法**：

- 文件放在 `tests/e2e/test_<功能>_e2e.py`
- 测试函数加 `@pytest.mark.e2e`
- 走完整链路（如 `run_simulation` → 断言输出结构与关键数值）

**现有 e2e 类型**：

| 类型 | 文件 | 用途 |
|-----|------|------|
| 数值快照回归 | `tests/sim_snapshots_test.py` | 对照 `data/baseline_before.json` |
| 功能链路 | `tests/e2e/test_trajectory_e2e.py` | 轨迹等新功能的端到端断言 |

**运行全量（含 e2e，约 3 分钟）**：

```bash
python3 run_tests.py
```

**更新数值基线**（有意改变仿真数值时）：

```bash
python3 verify_refactor_baseline.py
```

## 3. 中文注释

- 模块顶部 docstring、函数 docstring、非显然逻辑的行内注释：**一律中文**
- 避免英文 docstring（如 ~~`Unit tests for ...`~~ → `"""轨迹采样单元测试。"""`）
- 标识符（变量名、函数名）可保持英文；**说明性文字**用中文

## 项目测试结构速查

```
tests/
  *_test.py          # 单元 / 集成测试
  e2e/
    test_*_e2e.py    # 功能级 e2e（@pytest.mark.e2e）
run_tests.py         # 一键跑全部
verify_refactor.py   # 等价于 sim_snapshots e2e
pytest.ini           # e2e marker 定义
```

## 反例（禁止）

- 新增 `def foo()` 但无 `test_foo` 或等价覆盖
- 新增 Web 返回字段 `trajectory` 但无 e2e 断言
- 在源码中写 `# skip sampling when None` 而非中文说明
