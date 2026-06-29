# 单文件可检测安全模式

每组包含：风险等级 | 类别 | grep 搜索模式（ERE） | 理由模板

## 不安全协议

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | 不安全协议 | `"https?://[^\"']*"` 且非 `https://` | 使用明文 HTTP 协议，数据未加密传输，可被中间人窃取或篡改 |
| 高 | 不安全协议 | `"ftp://` | 使用明文 FTP 协议，凭证和文件传输均未加密 |
| 高 | 不安全协议 | `"telnet://` | 使用明文 Telnet 协议，所有通信均未加密 |

## 弱加密/哈希算法

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | 弱加密/哈希 | `"MD[245]"`（非注释行） | 该哈希算法已不被视为安全，易受碰撞攻击 |
| 高 | 弱加密/哈希 | `"SHA-?1"` `"SHA1"` | SHA-1 已不适用于安全场景，存在 SHAttered 碰撞攻击 |
| 高 | 弱加密/哈希 | `"DES[Ee]?[^C]"` `"DESede"` | DES/3DES 密钥长度不足，已被 NIST 弃用 |
| 高 | 弱加密/哈希 | `"RC[24]"` | RC2/RC4 存在已知攻击，已被弃用 |
| 高 | 弱加密/哈希 | `"Blowfish"` | Blowfish 仅 64 位块大小，存在生日攻击风险 |
| 高 | 弱加密/哈希 | `"AES/ECB/"` | ECB 模式不隐藏模式，相同明文块产生相同密文 |
| 中 | 弱加密/哈希 | `"PBEWithMD[245]And(DES\|TripleDES)"` | 基于 MD5 的 PBE 算法安全性不足 |
| 中 | 弱加密/哈希 | `"getInstance\(\"(DES\|RC[24]\|MD[245]\|SHA1?\)"` | Java JCA 中使用了不安全的算法名称 |

## 不安全随机数

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | 不安全随机数 | `new Random\(\)`（非 test 目录） | Random 非加密安全，用于安全上下文时可被预测 |
| 中 | 不安全随机数 | `Math\.random\(\)`（与安全相关上下文） | Math.random() 不被视为加密安全的随机数 |

## TLS 降级/绕过

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | TLS 降级/绕过 | `TrustAllCertificates\|trustAllCerts\|TrustAllTrustManager` | 信任所有证书的 TrustManager，MITM 攻击者可伪造证书 |
| 高 | TLS 降级/绕过 | `ALLOW_ALL_HOSTNAME_VERIFIER\|allowAllHostnameVerifier` | 忽略主机名校验，MITM 攻击者可使用任何证书 |
| 高 | TLS 降级/绕过 | `setHostnameVerifier.*true` | 设置了绕过主机名校验的 HostnameVerifier |
| 中 | TLS 降级/绕过 | `SSLContext\.getInstance\("(SSL\|TLS[^v]\|TLSv1[^.]\))` | 使用了不安全或过时的 TLS/SSL 协议版本 |
| 中 | TLS 降级/绕过 | `"SSLv[23]?` | 使用了已弃用的 SSL 协议版本字面量 |
| 中 | TLS 降级/绕过 | `"TLSv1\.[01]` | 使用了 TLS 1.0/1.1，存在已知协议级漏洞 |

## 硬编码凭证

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | 硬编码凭证 | `password\s*=\s*"[^"{}\[\]]{4,}"`（非示例/占位符值） | 密码硬编码在源码中，泄露即被提权 |
| 高 | 硬编码凭证 | `secret\s*=\s*"[^"{}\[\]]{8,}"` | 密钥硬编码在源码中，泄露可解密敏感数据 |
| 高 | 硬编码凭证 | `api[Kk]ey\s*=\s*"[^"{}\[\]]{8,}"` | API 密钥硬编码在源码中 |
| 高 | 硬编码凭证 | `jdbc:[^:]+://[^:]+:([^@]+)@`（密码非占位符） | JDBC URL 中包含明文密码 |
| 高 | 硬编码凭证 | `new UsernamePasswordCredentials\("[^"]+",\s*"[^"]{2,}"` | 凭证对象中使用了硬编码的用户名和密码 |

## 文件权限 777

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | 文件权限 | `chmod\s+777\|chmod\s+0777`（shell） | 文件设为全局可写权限，任何进程可篡改 |
| 高 | 文件权限 | `0o777\|0o755\|511`（Python os.chmod） | 文件权限过于宽松，应使用最小权限原则 |
| 中 | 文件权限 | `setReadable\(true,?\s*false\)\|setWritable\(true,?\s*false\)\|setExecutable\(true,?\s*false\)` | Java File API 设为全局可访问，应指定仅所有者可操作 |

## CORS 过于宽松

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | CORS 过于宽松 | `origins\s*=\s*"\*"\|allowedOrigins\s*=\s*"\*"` | CORS 允许所有来源，任何站点可跨域请求 |
| 中 | CORS 过于宽松 | `Access-Control-Allow-Origin\s*[=:]\s*"\*"` | HTTP header 设置了通配符跨域来源 |
| 中 | CORS 过于宽松 | `allowedOrigins\("\*"\)\|allowedOrigins\("\*"\)` | Spring/allowedOrigins 配置允许所有来源 |

## CSRF 禁用

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | CSRF 禁用 | `\.csrf\(\)\.disable\(\)\|csrf\.disable\(\)\|csrf\(\)\.disable\(\)` | CSRF 防护被全局禁用，跨站请求伪造不受保护 |
| 中 | CSRF 禁用 | `csrf\(false\)` | CSRF 防护被显式关闭 |

## 调试/信息泄露

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | 信息泄露 | `\.printStackTrace\(\)` | 打印完整堆栈跟踪到标准输出，可能泄露内部路径和逻辑 |
| 中 | 信息泄露 | `debug\s*[=:]\s*true`（非 test/非注释行） | 调试模式在生产环境开启会泄露详细错误信息 |
| 中 | 信息泄露 | `dev\s*[=:]\s*true`（非 test 目录） | 开发模式配置残留到生产环境可能暴露敏感端点 |
| 中 | 信息泄露 | `spring\.devtools\.restart\.enabled\s*=\s*true` | Spring DevTools 自动重启功能不应在生产环境启用 |

## JWT 不安全

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 高 | JWT 不安全 | `"alg".*"none"` | JWT alg:none 签名可被绕过，攻击者可伪造任意 token |
| 高 | JWT 不安全 | `SignatureAlgorithm\.NONE\|signWith\(null\)` | JWT 未设置签名算法，可被任意伪造 |
| 高 | JWT 不安全 | `jwtSecret\s*=\s*"([^"\s]{4,})"\|jwt\.secret\s*=\s*"[^"\s]{4,}"` | JWT 签名密钥硬编码在源码中 |

## 不安全重定向

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | 不安全重定向 | `redirect:.*\+` | URL 拼接的重定向，参数可控时存在开放重定向漏洞 |
| 中 | 不安全重定向 | `sendRedirect\(` + 非固定字符串参数 | 可被攻击者控制重定向目标，用于钓鱼攻击 |

## 日志打印敏感字段

| 风险 | 类别 | grep 模式 | 理由 |
|---|---|---|---|
| 中 | 敏感日志 | `log.*[Pp]assword\|logger.*[Pp]assword` | 日志中记录密码字段，可导致凭证泄露 |
| 中 | 敏感日志 | `log.*[Tt]oken\|logger.*[Tt]oken` | 日志中记录 token 字段，可能导致会话劫持 |
| 中 | 敏感日志 | `log.*[Ss]ecret\|logger.*[Ss]ecret` | 日志中记录 secret 字段，可能导致密钥泄露 |
