---
name: config-spotter
description: 凭文件名直觉从安全视角找非代码文件（配置/密钥/凭证/鉴权/基础设施），不读文件内容。
---

# config-spotter

给定目标目录，根据文件路径和名称找出安全相关的非代码文件。**永不读文件内容**，排除测试和 CI 构建代码。

## 搜索模式

| 分组 | 匹配文件名模式 |
|---|---|
| 密钥凭证 | `*.pem` `*.key` `*.p12` `*.jks` `*.keystore` `secrets.*` `credential*` `secret*` `*.env` `.env*` |
| 鉴权/身份 | `*auth*` `*oauth*` `*saml*` `*oidc*` `*ldap*` `.htpasswd` `rbac.*` `*password*` `*login*` |
| 安全策略 | `*cors*` `*csrf*` `*csp*` `*security*` `*firewall*` `*waf*` `*rate-limit*` |
| 应用配置 | `application*.yml` `application*.properties` `bootstrap.*` `config.*` `settings*.py` `settings*.yml` |
| 基础设施 | `Dockerfile*` `docker-compose*` `nginx.conf` `.htaccess` `apache.conf` `web.xml` `struts.xml` `*-servlet.xml` |
| 数据库 | `database.yml` `liquibase*` `flyway*` `migration*` `schema.sql` `init.sql` |
| 服务配置 | `logback*` `log4j*` `ehcache.xml` |
| 依赖清单 | `requirements*.txt` `go.mod` `Cargo.toml` `Gemfile` `composer.json` `package.json` `build.gradle*` |

## 排除路径

路径含以下片段的文件不纳入：

```
/test/ /tests/ /__tests__/ /spec/ /.github/ /ci/ /.gitlab/ /build/ /node_modules/ /vendor/ /lib/ /third_party/
```

## 风险等级

| 等级 | 覆盖分组 |
|---|---|
| **高** | 密钥凭证、鉴权/身份、database.yml |
| **中** | 安全策略、应用配置、基础设施（nginx/apache/web.xml 等） |
| **低** | 数据库（schema/migration）、服务配置、依赖清单 |

## 输出格式

按风险高→中→低排序，分组内按文件路径字母序。每组最后一条后不加 `---`（分组边界自然空行即可）。

```
---
风险: 高
类别: 密钥凭证
文件路径: config/credentials.yml
理由: 文件名表明包含凭证或密钥信息
---
风险: 高
类别: 鉴权/身份
文件路径: security/oauth-config.yml
理由: OAuth 鉴权配置，控制第三方登录流程
---
风险: 中
类别: 安全策略
文件路径: config/cors-config.xml
理由: CORS 策略配置，错误配置可导致跨域攻击
---
风险: 中
类别: 应用配置
文件路径: src/main/resources/application-prod.properties
理由: 应用核心配置，可能含数据库/服务连接信息
---
风险: 低
类别: 数据库
文件路径: db/migration/V1__init.sql
理由: 数据库迁移脚本，可了解表结构与权限
---
风险: 低
类别: 依赖清单
文件路径: requirements.txt
理由: 可识别第三方库版本及已知漏洞
```

## 不遗漏检查

- [ ] 8 组模式逐组搜索过
- [ ] 排除路径已过滤
- [ ] 无重复条目
- [ ] 每个条目有风险 + 类别 + 文件路径 + 理由
- [ ] 未读过任何文件内容
