# Semgrep 规则集参考

## 完整规则集目录

### 安全导向的规则集

| 规则集 | 描述 | 使用场景 |
|--------|------|----------|
| `p/security-audit` | 综合漏洞检测，较高误报率 | 手动审计、安全审查 |
| `p/secrets` | 硬编码凭证、API 密钥、令牌 | 始终包含 |
| `p/owasp-top-ten` | OWASP Top 10 Web 应用漏洞 | Web 应用安全 |
| `p/cwe-top-25` | CWE Top 25 最危险软件弱点 | 通用安全 |
| `p/sql-injection` | SQL 注入模式和污点数据流 | 数据库安全 |
| `p/insecure-transport` | 确保代码使用加密信道 | 网络安全 |
| `p/gitleaks` | 硬编码凭证检测（gitleaks 移植） | 密钥扫描 |
| `p/findsecbugs` | FindSecBugs Java 规则包 | Java 安全 |
| `p/phpcs-security-audit` | PHP 安全审计规则 | PHP 安全 |

### CI/CD 规则集

| 规则集 | 描述 | 使用场景 |
|--------|------|----------|
| `p/default` | 默认规则集，平衡覆盖 | 首次使用者 |
| `p/ci` | 高置信度安全 + 逻辑 Bug，低误报 | CI 流水线 |
| `p/r2c-ci` | 低误报，CI 安全 | CI/CD 阻断 |
| `p/r2c` | 社区喜爱，Semgrep 精选（618k+ 下载）| 通用扫描 |
| `p/auto` | 基于检测到的语言/框架自动选择规则 | 快速扫描 |
| `p/comment` | 评论相关规则 | 代码审查 |

### 第三方规则集

| 规则集 | 描述 | 维护者 |
|--------|------|--------|
| `p/gitlab` | GitLab 维护的安全规则 | GitLab |

---

## 规则集选择算法

根据检测到的语言和框架，按此算法选择规则集。

### 第 1 步：始终包含安全基线

```json
{
  "baseline": ["p/security-audit", "p/secrets"]
}
```

- `p/security-audit`——综合漏洞检测（始终包含）
- `p/secrets`——硬编码凭证、API 密钥、令牌（始终包含）

### 第 2 步：添加语言特定规则集

对于每种检测到的语言，添加主要规则集。如果检测到框架，也添加其规则集。

**GA 语言（生产就绪）：**

| 检测项 | 主要规则集 | 框架规则集 | Pro 规则数量 |
|--------|-----------|-----------|-------------|
| `.py` | `p/python` | `p/django`、`p/flask`、`p/fastapi` | 710+ |
| `.js`、`.jsx` | `p/javascript` | `p/react`、`p/nodejs`、`p/express`、`p/nextjs`、`p/angular` | 250+（JS）、70+（JSX） |
| `.ts`、`.tsx` | `p/typescript` | `p/react`、`p/nodejs`、`p/express`、`p/nextjs`、`p/angular` | 230+ |
| `.go` | `p/golang` | `p/go`（别名） | 80+ |
| `.java` | `p/java` | `p/spring`、`p/findsecbugs` | 190+ |
| `.kt` | `p/kotlin` | `p/spring` | 60+ |
| `.rb` | `p/ruby` | `p/rails` | 40+ |
| `.php` | `p/php` | `p/symfony`、`p/laravel`、`p/phpcs-security-audit` | 50+ |
| `.c`、`.cpp`、`.h` | `p/c` | - | 150+ |
| `.rs` | `p/rust` | - | 40+ |
| `.cs` | `p/csharp` | - | 170+ |
| `.scala` | `p/scala` | - | 社区 |
| `.swift` | `p/swift` | - | 60+ |

**Beta 语言（推荐 Pro）：**

| 检测项 | 主要规则集 | 备注 |
|--------|-----------|------|
| `.ex`、`.exs` | `p/elixir` | 需要 Pro 获得最佳覆盖 |
| `.cls`、`.trigger` | `p/apex` | Salesforce；需要 Pro |

**实验性语言：**

| 检测项 | 主要规则集 | 备注 |
|--------|-----------|------|
| `.sol` | 无官方规则集 | 使用 Decurity 第三方规则 |
| `Dockerfile` | `p/dockerfile` | 有限的规则 |
| `.yaml`、`.yml` | `p/yaml` | K8s、GitHub Actions、docker-compose 模式 |
| `.json` | `r/json.aws` | AWS IAM 策略；使用 `r/json.*` 获取特定规则 |
| Bash 脚本 | - | 社区支持 |
| Cairo、Circom | - | 实验性，智能合约 |

**框架检测提示：**

| 框架 | 检测信号 | 规则集 |
|------|---------|--------|
| Django | `settings.py`、`urls.py`、requirements 中的 `django` | `p/django` |
| Flask | requirements 中的 `flask`、`@app.route` | `p/flask` |
| FastAPI | requirements 中的 `fastapi`、`@app.get/post` | `p/fastapi` |
| React | `package.json` 中 react 依赖、`.jsx`/`.tsx` 文件 | `p/react` |
| Next.js | `next.config.js`、`pages/` 或 `app/` 目录 | `p/nextjs` |
| Angular | `angular.json`、`@angular/` 依赖 | `p/angular` |
| Express | package.json 中 `express`、`app.use()` 模式 | `p/express` |
| NestJS | `@nestjs/` 依赖、`@Controller` 装饰器 | `p/nodejs` |
| Spring | `pom.xml` 中的 spring、`@SpringBootApplication` | `p/spring` |
| Rails | `Gemfile` 中的 rails、`config/routes.rb` | `p/rails` |
| Laravel | `composer.json` 中的 laravel、`artisan` | `p/laravel` |
| Symfony | `composer.json` 中的 symfony、`config/packages/` | `p/symfony` |

### 第 3 步：添加基础设施规则集

| 检测项 | 规则集 | 描述 |
|--------|--------|------|
| `Dockerfile` | `p/dockerfile` | 容器安全、最佳实践 |
| `.tf`、`.hcl` | `p/terraform` | IaC 错误配置、CIS 基准、AWS/Azure/GCP |
| k8s 清单 | `p/kubernetes` | K8s 安全、RBAC 问题 |
| CloudFormation | `p/cloudformation` | AWS 基础设施安全 |
| GitHub Actions | `p/github-actions` | CI/CD 安全、密钥暴露 |
| `.yaml`、`.yml` | `p/yaml` | 通用 YAML 模式（K8s、docker-compose） |
| AWS IAM JSON | `r/json.aws` | IAM 策略错误配置（使用 `--config r/json.aws`） |

### 第 4 步：添加第三方规则集

这些**不是可选的**。当语言匹配时自动包含：

| 语言 | 来源 | 为什么必需 |
|------|------|-----------|
| Python、Go、Ruby、JS/TS、Terraform、HCL | [Trail of Bits](https://github.com/trailofbits/semgrep-rules) | 来自真实安全审计的模式（AGPLv3） |
| C、C++ | [0xdea](https://github.com/0xdea/semgrep-rules) | 内存安全、底层漏洞 |
| Solidity、Cairo、Rust | [Decurity](https://github.com/Decurity/semgrep-smart-contracts) | 智能合约漏洞、DeFi 利用 |
| Go | [dgryski](https://github.com/dgryski/semgrep-go) | 额外的 Go 特定模式 |
| Android（Java/Kotlin） | [MindedSecurity](https://github.com/mindedsecurity/semgrep-rules-android-security) | OWASP MASTG 衍生的移动安全规则 |
| Java、Go、JS/TS、C#、Python、PHP | [elttam](https://github.com/elttam/semgrep-rules) | 安全咨询模式 |
| Dockerfile、PHP、Go、Java | [kondukto](https://github.com/kondukto-io/semgrep-rules) | 容器和 Web 应用安全 |
| PHP、Kotlin、Java | [dotta](https://github.com/federicodotta/semgrep-rules) | 渗透测试衍生的 Web/移动应用规则 |
| Terraform、HCL | [HashiCorp](https://github.com/hashicorp-forge/semgrep-rules) | HashiCorp 基础设施模式 |
| Swift、Java、Cobol | [akabe1](https://github.com/akabe1/akabe1-semgrep-rules) | iOS 和遗留系统模式 |
| Java | [Atlassian Labs](https://github.com/atlassian-labs/atlassian-sast-ruleset) | Atlassian 维护的 Java 规则 |
| Python、JS/TS、Java、Ruby、Go、PHP | [Apiiro](https://github.com/apiiro/malicious-code-ruleset) | 恶意代码检测、供应链 |

### 第 5 步：验证规则集

在最终确定之前，验证官方规则集可加载：

```bash
# 快速验证（退出码 0 表示有效）
semgrep --config p/python --validate --metrics=off 2>&1 | head -3
```

或在 [Semgrep 注册表](https://semgrep.dev/explore) 中浏览。

### 输出格式

```json
{
  "baseline": ["p/security-audit", "p/secrets"],
  "python": ["p/python", "p/django"],
  "javascript": ["p/javascript", "p/react", "p/nodejs"],
  "docker": ["p/dockerfile"],
  "third_party": ["https://github.com/trailofbits/semgrep-rules"]
}
```
