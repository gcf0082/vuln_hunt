---
name: config-spotter
description: 凭文件名从安全视角找非代码文件（配置/密钥/凭证/鉴权/基础设施），通过搜索列出所有匹配文件，不读文件内容。
---

# config-spotter

给定目标目录，搜索安全相关的非代码文件。**永不读文件内容**，排除测试和 CI 构建代码。

## 执行流程

### 1. 确定目标目录

从用户消息提取目标目录。如果用户没给，就反问"扫哪个目录？"。

### 2. 逐组搜索

对每组模式，用 `find` 命令搜索目标目录，排除路径用 `! -path` 过滤。所有结果收集到列表中。

**搜索命令模板**（用 `-o` 连接同一组的多个模式）：

```bash
find {目标目录} -type f \( -name "*.pem" -o -name "*.key" -o -name "*.p12" \) \
  ! -path "*/test/*" ! -path "*/tests/*" ! -path "*/__tests__/*" \
  ! -path "*/spec/*" ! -path "*/.github/*" ! -path "*/ci/*" \
  ! -path "*/.gitlab/*" ! -path "*/build/*" \
  ! -path "*/node_modules/*" ! -path "*/vendor/*" \
  ! -path "*/lib/*" ! -path "*/third_party/*" \
  2>/dev/null | sort
```

**注意**：同一个文件可能匹配多个模式，只记入第一次出现的类别，略过后面的。

### 3. 设定理由

每个文件根据文件名和所在路径，按以下规则设定理由。**理由不读文件内容，仅凭路径/名称推断**：

| 类别 | 理由规则 |
|---|---|
| 密钥凭证 | `文件名表明包含凭证或密钥信息`（通用）；`.env` → `环境变量文件，可能含密钥或连接串`；`*.pem` → `SSL 私钥文件`；`secrets.*` → `secrets 文件，典型凭证存储文件` |
| 鉴权/身份 | `*oauth*` → `OAuth 鉴权配置，控制第三方登录流程`；`*password*` → `密码相关配置，可能存储账户凭证`；`*auth*` → `鉴权配置文件`；`database.yml` → `数据库连接配置，包含连接串和凭证`（注：database.yml 归在高风险鉴权类） |
| 安全策略 | `*cors*` → `CORS 策略配置，错误配置可导致跨域攻击`；`*security*` → `安全策略配置文件`；`*csrf*` → `CSRF 防护配置`；`*firewall*` → `防火墙规则配置` |
| 应用配置 | `application*.{yml,properties}` → `应用配置，可泄露数据库/服务连接等敏感信息`；`settings*.{py,yml}` → `应用设置文件`；`bootstrap.*` → `Spring 启动配置，可获取服务注册/配置中心地址` |
| 基础设施 | `nginx.conf` → `Nginx 配置，可发现反向代理规则与上游服务`；`.htaccess` → `Apache 访问控制，可发现认证方式与 IP 限制`；`Dockerfile*` → `Docker 构建配置`；`docker-compose*` → `容器编排配置，可发现服务架构与端口映射` |
| 数据库 | `migration*` → `数据库迁移脚本，可了解表结构与权限分配`；`schema.sql` → `数据库 schema 文件；`init.sql` → `数据库初始化脚本` |
| 服务配置 | `logback*` / `log4j*` → `日志配置，可发现日志路径与级别`；`ehcache.xml` → `缓存配置，可了解缓存策略` |
| 依赖清单 | `requirements*.txt` → `可识别 Python 第三方库版本及已知漏洞`；`go.mod` → `可识别 Go 模块依赖版本`；`Gemfile` → `可识别 Ruby 依赖版本`；`Cargo.toml` → `可识别 Rust 依赖与 features 组合`；`composer.json` → `可识别 PHP 依赖版本`；`build.gradle*` → `可识别构建依赖与插件`；`package.json` → `可识别 Node.js 依赖版本与脚本` |

如果有多个文件同类别同理由，**每个文件独立条目，不合并**。

### 4. 排序与去重

- 按风险等级排序：高 → 中 → 低
- 同风险内按文件路径字母序
- 同一个文件只出现一次（按最早匹配的类别）

### 5. 输出

输出全部结果，一个文件一条，`---` 分隔。

```
---
风险: 高
类别: 密钥凭证
文件路径: config/credentials.yml
理由: 文件名表明包含凭证或密钥信息
---
风险: 高
类别: 密钥凭证
文件路径: .env.production
理由: 环境变量文件，可能含密钥或连接串
---
风险: 高
类别: 鉴权/身份
文件路径: security/oauth-config.yml
理由: OAuth 鉴权配置，控制第三方登录流程
---
风险: 高
类别: 鉴权/身份
文件路径: config/database.yml
理由: 数据库连接配置，包含连接串和凭证
---
风险: 中
类别: 安全策略
文件路径: config/security/cors-config.xml
理由: CORS 策略配置，错误配置可导致跨域攻击
---
风险: 中
类别: 应用配置
文件路径: src/main/resources/application-prod.properties
理由: 应用配置，可泄露数据库/服务连接等敏感信息
---
风险: 低
类别: 数据库
文件路径: db/migration/V1__init.sql
理由: 数据库迁移脚本，可了解表结构与权限分配
---
风险: 低
类别: 数据库
文件路径: db/migration/V2__add_indexes.sql
理由: 数据库迁移脚本，可了解表结构与权限分配
---
风险: 低
类别: 依赖清单
文件路径: requirements.txt
理由: 可识别 Python 第三方库版本及已知漏洞
---
风险: 低
类别: 依赖清单
文件路径: package.json
理由: 可识别 Node.js 依赖版本与脚本
```

**有结果就全部列出，一个不落。没有结果时输出**：
```
---
风险: -
类别: -
文件路径: (无匹配项)
理由: 目标目录中未找到安全相关的非代码文件
```

## 排除路径

```
/test/ /tests/ /__tests__/ /spec/ /.github/ /ci/ /.gitlab/ /build/ /node_modules/ /vendor/ /lib/ /third_party/
```

## 风险等级

| 等级 | 覆盖分组 |
|---|---|
| **高** | 密钥凭证、鉴权/身份（含 database.yml） |
| **中** | 安全策略、应用配置、基础设施 |
| **低** | 数据库（schema/migration）、服务配置、依赖清单 |

## 不遗漏检查

- [ ] 8 组模式都已用 `find` 搜索过
- [ ] 排除路径已过滤
- [ ] 结果中无重复文件路径
- [ ] 所有匹配文件都已列出（不是只列一部分）
- [ ] 无匹配时输出了 (无匹配项)
- [ ] 未读任何文件内容
