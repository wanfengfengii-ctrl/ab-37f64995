# 加速器束流脉冲复核台

对两块采集卡记录的脉冲事件流进行**对时复核**的全栈工作台：工程师在页面上
编辑或导入两条事件流，设定允许的初始偏移范围、固定跳变量与最低命中数，
经 FastAPI 业务 API 发起裁决，并逐对核对时间、事件码与跳变前后偏移。

## 业务规则

- 每条流含 **2–80** 个事件；时间为 **0…10¹² 的严格递增整数**；
  事件码为 **1–8 位大写字母或数字**（`[A-Z0-9]{1,8}`）。
- 配对必须**保持两侧顺序**且**事件码相同**；两侧未匹配事件可任意跳过。
- 合法方案选择一个允许范围内的整数**初始偏移** d₀
  （约定 `tA = tB + offset`），并可在**两个已匹配事件之间至多一次**
  把偏移永久改为 d₀+J 或 d₀−J；匹配后两侧时间必须**完全相等**。
- 裁决目标：
  1. **最大化匹配数**；未达到最低命中数即判无解；
  2. 同分时按规范序确定首解：
     `初始偏移升序 → 无跳变优先 → 减优先于加 → 跳变前匹配数升序 → 配对索引序列字典序`；
  3. 准确区分**唯一 / 歧义**；歧义时额外返回规范序第二份方案作为**见证**。

## 算法要点（`backend/app/solver.py`）

- 仅同码事件对可能成边；按差值 d=tA−tB 分组，候选初始偏移至多 6400 个。
- 固定差值下用树状数组（Fenwick 求前缀最大）计算保序最长链的
  `pre/suf`，并以二维后缀转移表
  `cross[e]=max{e 之后 d₁ 边的后缀链}`、
  `w[q][e]` 求“q 条 d₀ 前缀 + d₁ 后缀”的最大匹配，O(nm log n)。
- 只对达到最大匹配数的方案空间做最多两份方案的 DFS 枚举（强剪枝），
  据此得到规范首解并判定唯一/歧义。80+80 规模实测毫秒级。
- `backend/tests/test_solver.py` 内置一个完全独立的朴素暴力预言机，
  含 1500+ 轮随机对拍与全解枚举，校验最大匹配数、规范首解与见证。

## 目录结构

```
backend/            FastAPI 应用、核心解算器、pytest
  app/main.py       HTTP 接口 /health、/api/adjudicate
  app/solver.py     裁决算法
  scripts/          容器健康检查
frontend/           React 18 + Vite + TypeScript（nginx 托管 + 反代 /api）
scripts/verify.sh   verify 一次性服务执行的检查脚本
Dockerfile.verify   verify 镜像（Python 测试 + 前端构建 + HTTP 冒烟）
docker-compose.yml  api / frontend / verify 三个服务
```

## 启动（Docker Compose）

```bash
cp .env.example .env        # 可改宿主机端口、健康检查参数
docker compose build
docker compose up -d
```

- 前端：http://localhost:8080 （`FRONTEND_HOST_PORT` 可配置）
- API：http://localhost:8000 （`API_HOST_PORT` 可配置）
- 健康检查路径可通过 `HEALTH_PATH`、`FRONTEND_HEALTH_PATH` 配置；
  间隔/超时通过 `HEALTH_INTERVAL`、`HEALTH_TIMEOUT` 配置。

### verify 一次性服务

```bash
docker compose run --rm verify
```

它会等待 api 与 frontend 健康，然后依次执行并自行退出：

1. 后端代码测试（pytest）；
2. 前端构建检查（`tsc -b && vite build`）；
3. HTTP 冒烟（健康检查、首页、真实 `POST /api/adjudicate` 裁决）。

**全部通过退出码为 0，任一失败为 1**；也可用
`docker compose up verify` 后 `docker compose ps -a` 查看退出码。

## API

`POST /api/adjudicate`

```json
{
  "streamA": [{"time": 100, "code": "TRIG"}],
  "streamB": [{"time": 100, "code": "TRIG"}],
  "minOffset": -20,
  "maxOffset": 20,
  "jump": 5,
  "minHits": 3
}
```

成功时返回 `feasible`、`matchCount`、`uniqueness`、规范首解 `solution`，
歧义时附带 `witness`；每个配对包含 `timeA/timeB/code`、跳变前后偏移
（`offsetBefore/offsetAfter`）与所在时段。无解时返回
`feasible:false` 与 `reason`。参数非法返回 422。

## 本地开发

```bash
# 后端
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
python -m pytest

# 前端
cd frontend && npm install
npm run dev      # /api 代理到 http://localhost:8000
```
