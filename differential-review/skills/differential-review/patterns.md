# 通用漏洞模式

差异代码审查中常见安全问题的快速参考。

---

## 1. 安全回归

**模式：** 之前因安全问题移除的代码被重新加入。

**检测：**
```bash
# 查找曾被 security/fix/CVE 相关提交移除的模式
git log -S "pattern" --all --grep="security\|fix\|CVE"
```

**红旗标志：**
- 提交消息包含 "security"、"fix"、"CVE"、"vulnerability"
- 代码在 6 个月内被移除了
- 当前 PR 未解释为何重新加入

**示例：**
```python
# 在 commit abc123 中被移除："Fix SQL injection vulnerability"
# 在当前 PR 中被重新加入
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # 回归！SQL 注入
    cursor.execute(query)
```

```java
// 在 commit abc123 中被移除："Fix SQL injection vulnerability"
// 在当前 PR 中被重新加入
public User getUser(String userId) {
    String query = "SELECT * FROM users WHERE id = " + userId;  // 回归！SQL 注入
    Statement stmt = connection.createStatement();
    return stmt.executeQuery(query);
}
```

**风险：** 已知漏洞被重新引入，之前的修复被推翻。

---

## 2. 注入（Injection）

**模式：** 用户输入被拼接到 SQL 查询、系统命令或 LDAP 查询中，未经正确转义或参数化。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "execute\(|exec\(|Runtime\.exec|ProcessBuilder|eval\(|subprocess\.call"
```

**示例：**
```diff
 def get_user(user_id):
-    cursor.execute("SELECT * FROM users WHERE id = ?", [user_id])
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    cursor.execute(query)
```

```diff
 public User getUser(String userId) {
-    String sql = "SELECT * FROM users WHERE id = ?";
-    return jdbcTemplate.queryForObject(sql, User.class, userId);
+    String sql = "SELECT * FROM users WHERE id = " + userId;
+    Statement stmt = connection.createStatement();
+    return stmt.executeQuery(sql);
 }
```

**风险：** 攻击者可读取/修改/删除数据库记录，执行系统命令，或获取未授权数据。

---

## 3. 授权失效（Broken Access Control / IDOR）

**模式：** API 或函数缺少访问控制检查，用户可直接通过参数引用其他用户的资源。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "@GetMapping|@PostMapping|\.route\(|\.addResourceHandler"
# 确认是否添加了权限校验
git diff <range> | grep -iE "PreAuthorize|has_role|has_permission|is_admin|@login_required"
```

**示例：**
```diff
 @RestController
 public class UserController {
+
+    @GetMapping("/api/users/{id}/orders")
+    public List<Order> getUserOrders(@PathVariable Long id) {
+        return orderService.getOrdersByUserId(id);
+    }
 }
```

```diff
 @app.route('/api/users/<int:id>/orders')
+@login_required
 def get_user_orders(id):
     orders = Order.query.filter_by(user_id=id).all()
     return orders_schema.jsonify(orders)
```

**风险：** 用户 A 可访问用户 B 的私密数据（订单、个人信息、支付记录）。

---

## 4. 认证缺陷（Authentication Failures）

**模式：** JWT 验证被绕过、密码哈希被替换为明文、会话管理被削弱。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "jwt\.decode|verify=false|hashlib|BCrypt|PasswordEncoder|plain.?text"
```

**示例：**
```diff
 def verify_token(token):
-    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
+    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], verify=False)
```

```diff
 public boolean checkPassword(String rawPassword, String encodedPassword) {
-    return BCrypt.checkpw(rawPassword, encodedPassword);
+    return rawPassword.equals(encodedPassword);  // 明文比较！
 }
```

**风险：** 身份验证可被绕过，攻击者可冒充任意用户。

---

## 5. SSRF（服务端请求伪造）

**模式：** 服务器根据用户提供的 URL 发起请求，未对目标地址做校验。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "requests\.get\(|requests\.post\(|URL\(|openConnection|WebClient|RestTemplate"
```

**示例：**
```diff
 def fetch_metadata(url):
-    if not is_allowed_host(url):
-        raise ValueError("URL not allowed")
     resp = requests.get(url)
     return resp.text
```

```diff
 public String fetchUrl(String urlString) {
-    URI uri = new URI(urlString);
-    if (!uri.getHost().endsWith(".trusted.com")) {
-        throw new SecurityException("Untrusted host");
-    }
     URL url = new URL(urlString);
     return IOUtils.toString(url.openStream());
 }
```

**风险：** 攻击者可扫描内网、访问云元数据端点（如 AWS `169.254.169.254`）、读取内部服务。

---

## 6. 反序列化漏洞（Deserialization）

**模式：** 来自用户输入的数据未经安全处理直接被反序列化。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "pickle\.loads|yaml\.load\(|ObjectInputStream|readObject|@RequestBody"
```

**示例：**
```diff
 def load_config(data):
-    config = json.loads(data)
+    import yaml
+    config = yaml.load(data)  # unsafe load
```

```diff
 public Object deserialize(byte[] data) {
     ByteArrayInputStream bis = new ByteArrayInputStream(data);
     ObjectInputStream ois = new ObjectInputStream(bis);
-    ois.setObjectInputFilter(new SafeFilter());
     return ois.readObject();
 }
```

**风险：** 攻击者可触发远程代码执行（RCE）或拒绝服务攻击。

---

## 7. 安全配置错误（Security Misconfiguration）

**模式：** 调试模式在生产环境启用、CORS 设置为任意域名、默认凭据未修改。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "debug=True|allowedOrigins|\.env|application\.properties|default.?password"
```

**示例：**
```diff
 def create_app():
+    app.run(debug=True)
```

```diff
 @Configuration
 public class CorsConfig {
     public void addCorsMappings(CorsRegistry registry) {
         registry.addMapping("/api/**")
-            .allowedOrigins("https://trusted.example.com");
+            .allowedOrigins("*");
     }
 }
```

**风险：** 调试信息泄露、CSRF 防护失效、内网接口暴露。

---

## 8. 路径遍历（Path Traversal）

**模式：** 用户输入被直接用于文件路径拼接，未对 `../` 等路径跳转做过滤。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "open\(|Path\.of|getResource|File\(|\.read\(\).*\)"
```

**示例：**
```diff
 def read_file(filename):
-    if "../" in filename or filename.startswith("/"):
-        raise ValueError("Invalid path")
     path = f"/var/data/{filename}"
     with open(path) as f:
         return f.read()
```

```diff
 public String readFile(String fileName) {
     Path path = Paths.get("/var/data/" + fileName);
-    if (!path.normalize().startsWith("/var/data/")) {
-        throw new SecurityException("Invalid path");
-    }
     return Files.readString(path);
 }
```

**风险：** 攻击者可读取任意系统文件（`/etc/passwd`、配置文件、密钥文件）。

---

## 9. 敏感信息泄露（Sensitive Data Exposure）

**模式：** 硬编码的 API 密钥、密码、令牌，或异常堆栈信息直接返回给用户。

**检测：**
```bash
git diff <range> | grep "^+" | grep -iE "sk-[a-zA-Z0-9]|AKIA[0-9A-Z]|password\s*=|secret\s*=|api_key|printStackTrace"
```

**示例：**
```diff
+API_KEY = "sk-abc123def456ghij789klmn"
+# 硬编码 API 密钥提交到代码库
```

```diff
 @ExceptionHandler(Exception.class)
 public ResponseEntity handleError(Exception e) {
+    return ResponseEntity.status(500).body(e.getMessage() + " " + Arrays.toString(e.getStackTrace()));
 }
```

**风险：** 密钥暴露导致第三方服务被滥用；堆栈信息暴露攻击者可利用的框架/库版本。

---

## 10. XSS / CSRF

**模式：** 用户输入未转义直接渲染到页面（XSS），或对状态变更请求缺少 CSRF 令牌验证。

**检测：**
```bash
# XSS：模板中直接插入用户输入
git diff <range> | grep "^+" | grep -iE "render_template_string|Markup|@ResponseBody|\.html\("
# CSRF：缺少令牌验证
git diff <range> | grep "^+" | grep -iE "@PostMapping|@PutMapping|@DeleteMapping|\.post\(|\.delete\("
```

**示例：**
```diff
 @app.route('/search')
 def search():
     query = request.args.get('q')
-    return render_template('search.html', query=query)
+    return render_template_string(f"<h1>搜索结果: {query}</h1>")
```

```diff
 @Configuration
 public class SecurityConfig {
+    @Override
+    protected void configure(HttpSecurity http) {
+        http.csrf().disable();  // CSRF 防护被禁用
+    }
 }
```

**风险（XSS）：** 攻击者在用户浏览器中执行任意脚本，窃取 Cookie/会话令牌。
**风险（CSRF）：** 攻击者诱导用户执行非本意的状态变更操作（改密、转账）。

---

## 快速检测命令

**查找移除的安全检查：**
```bash
git diff <range> | grep "^-" | grep -iE "check|validate|assert|verify|authenticate|authorize"
```

**查找新的外部调用：**
```bash
git diff <range> | grep "^+" | grep -iE "requests\.|RestTemplate|WebClient|openConnection|http\.get|http\.post"
```

**查找硬编码凭据：**
```bash
git diff <range> | grep "^+" | grep -iE "password|secret|apikey|token|credential" | grep -v "test\|mock\|example"
```

**查找移除的访问控制：**
```bash
git diff <range> | grep "^-" | grep -iE "login_required|PreAuthorize|hasRole|isAdmin|@Secured"
```

---

**详细的攻击场景构建方法，参见 [adversarial.md](adversarial.md)**
**完整分析工作流，参见 [methodology.md](methodology.md)**
