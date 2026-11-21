# 免费 · Free

模型、编程 Agent、VPS 的免费额度放在同一个静态站里。三个路径：

| 路径 | 内容 |
| --- | --- |
| `/provider/` | 模型、网关、API 额度（原来的 Providers） |
| `/agent/` | 编程 Agent、CLI、IDE 的免费额度（原来的 Agents） |
| `/vps/` | 免费 VPS、DMIT / 搬瓦工补货、黑五优惠 |

`/` 打开 `/provider/`。手机上三个 tab 固定在顶部。

页面标题是「免费 · 模型」「免费 · Agent」「免费 · VPS」。根页面是「免费 · Free」。

## 地址

- Netlify：https://scoheart-free.netlify.app/
- GitHub Pages：仓库改名为 `free` 之后是 https://scoheart.github.io/free/

Vite 使用相对资源路径。同一份构建产物支持域名根路径和 `/free/` 子路径。

## 平台链接

模型和 Agent 默认展示全部活动，按截止时间从近到远排序。未标明截止时间的活动排在后面。选中一个平台后，列表与搜索只显示该平台的活动。选择「全部平台」可以取消平台筛选。

选中的平台写在 **hash** 上，不写成多出来的路径（静态托管没有 `/provider/groq` 这个文件）：

- `/provider/#groq`
- `/agent/#opencode`

带不带目录斜杠都可以。服务器如果把 `/provider` 补成 `/provider/`，hash 会留下来，结果一样。

旧链接会自动换成上面的形式，并保持平台选中：

| 旧 hash | 打开 |
| --- | --- |
| `#providers/groq` | `/provider/#groq` |
| `#agents/opencode` | `/agent/#opencode` |
| `#providers` | `/provider/` |
| `#agents` | `/agent/` |
| `#groq` | 这个平台所在的栏目。两边都有时进 `/provider/` |
| `#opencode` | `/agent/#opencode` |

写错栏目也会纠正：`/agent/#groq` 会到 `/provider/#groq`，因为 Groq 在模型页。`/vps/#providers/groq` 同样会离开 VPS 页。

## 数据源

| 文件 | 数据 |
| --- | --- |
| `provider/index.json` | 模型、网关和 API 额度条目数组 |
| `agent/index.json` | 编程 Agent、CLI 和 IDE 条目数组 |
| `vps/index.json` | VPS 免费情报、库存和黑五数据对象 |

日更将条目写入对应栏目的文件，然后运行 `./build-site.sh`。模型和 Agent 的条目格式相同，所属栏目由文件决定。页面首次打开时加载当前栏目的 JSON。旧链接需要定位到另一个栏目，或搜索在当前栏目没有结果时，页面按需读取另一个栏目。

## VPS 数据

当 `"sample": true` 时，页面会显示「示例数据，等待首次同步」。下面的生成脚本写入 `"sample": false` 的监控数据。

`vps/index.json` 顶层字段如下。

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 固定 `1` |
| `sample` | `true` 时页面显示示例提示 |
| `updated_at_beijing` | 页头的最后更新时间，取三份扫描时间里最晚的一个 |
| `scanned_at_beijing` | `stock` / `black_friday` / `free_vps` 各自的扫描时间 |
| `free_vps` | 免费 VPS 情报，只保留 `genuine: true` |
| `stock.providers` | 固定两家：DMIT、搬瓦工 |
| `stock.source_notes` | 监控源异常的短说明 |
| `black_friday.official` | 各厂商官方状态 |
| `black_friday.leads` | 第三方线索，页面标明「仅线索，未经官方确认」 |
| `black_friday.date_note` | 日期说明 |

免费条目：`id`、`provider`、`type`（`always_free` / `trial` / `student` / `paas` / `other`）、`type_label`（一直免费、试用额度、学生额度、非 root 的 PaaS）、`specs[]`（`label` + `value`）、`free_conditions`（`card_required`、`card_notes`、`region_limits`、`idle_reclaim`、`deadline`、`deadline_note`）、`official_url`、`posts[]`（`url`、`time_beijing`、`author`、`role`）、`notes`。X 上的帖子显示为「据 X 上的帖子」。

补货套餐：`key`、`display_name`、`config`、`specs[]`、`price`、`stock`（`in_stock` 绿色「有货」，其他灰色「缺货」）、`limited`、`last_restock`、`order_urls[]`（`label` + `url`）。搬瓦工同时给 `bandwagonhost.com` 和 `bwh81.net`。对不上目录时价格和链接留空，页面不会编一个价格。

厂商上还有 `checked_at_beijing`、`official_url`、`sources[]`（`name`、`url`、`checked_at_beijing`）。DMIT 看来源 `vpsrestock.com` 和 `t.me/dmitnews`，搬瓦工看 `vpsrestock.com` 和 `stock.bwg.la`。

黑五官方：`provider`、`status`、`status_label`（现在能下单 / 预告未开卖 / 今年不办）、`status_kind`（`now` / `soon` / `off`）、`orderable_now`、`summary`、`sources[]`、`sale_hub`、`plans[]`（`name`、`price`、`specs`、`url`）。

## 从监控目录更新 VPS 数据

```bash
python3 scripts/build_vps.py --in /path/to/vps-watch --out vps/index.json
```

`--in` 里只读这三个文件（`schema_version` 1，时间字段是北京时间 `*_beijing`）：

- `stock-state.json`：`scanned_at_beijing`、`dmit`、`bandwagonhost`。套餐在 `watched_plans`。搬瓦工的价格和下单链接不在套餐上，脚本用 `pid`、`display_name`、`aliases` 去 `catalog_stock_bwg_la` 和 `catalog_vpsrestock` 里对。先对 `pid`，再对规范化后的名字。对不上就留空。
- `bf-seen.json`：`official`、`leads_third_party_only`、`black_friday_2026_date_note`。
- `free-vps-seen.json`：`items`。只输出 `genuine` 为 true 的条目。`dropped` 和 `watch_accounts` 不输出。

同目录的 `signups.json` 不会被打开。缺字段就空着。邮箱、密码、密钥样式的字符串不会写进结果。

然后：

```bash
./build-site.sh
```

## 开发

前端使用 React、TypeScript、Vite 和 Radix UI。 Vite 的页面入口在 `web/`。

- `web/src/catalog/` 包含模型和 Agent 的分类、搜索、排序与界面。
- `web/src/vps/` 包含 VPS 数据类型、页面和样式。
- `web/src/shared/` 提供通用布局和文本处理。
- `scripts/build_vps.py` 接收监控目录，`scripts/vps/` 负责整理公开数据。
- `tests/` 包含页面渲染、路由和 VPS 数据测试。

安装 Node.js 22.12 或更新版本。Python 3 用于 VPS 数据生成和测试。

```bash
npm ci
npm run dev
```

运行 `npm test` 执行回归测试。

## 部署

- GitHub Pages 从 `main` 根目录发布。`./build-site.sh` 生成 `dist/`，并同步根目录的页面和资源文件。
- Netlify 由 `npm run build` 生成 `dist/`。手动发布时上传整个 `dist/`。关联 Git 的构建读取 `netlify.toml`。

Netlify 的跳转规则写在 `web/public/_redirects`，构建时复制到发布目录。运行 `npm run preview` 可预览产物。

两种部署都在对应栏目目录下提供 `index.json`。构建也从这三份 JSON 生成 `data.js` 和 `vps-data.js` 供已有消费者加载。
