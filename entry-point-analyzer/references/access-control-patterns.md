# Access Control Patterns — General Reference

## Access Classification Levels

| Level | Meaning | Examples |
|-------|---------|----------|
| **Public (Unrestricted)** | No authentication or authorization required | Login page, public API, health check |
| **Authenticated** | Any authenticated user can access | User profile, dashboard (after login) |
| **Role-Restricted** | Requires specific role, permission, or group | Admin panel, data export, user management |
| **Review Required** | Ambiguous or custom access control patterns | Dynamic permission checks, custom ACL, hardcoded addresses |
| **Internal-Only** | Only accessible by internal components | Private methods, IPC without external exposure, service-internal APIs |

## Authentication Detection Patterns

### Decorator/Annotation-Based

| Framework | Public Pattern | Authenticated Pattern | Role Pattern |
|-----------|---------------|----------------------|--------------|
| **Flask (Python)** | No decorator | `@login_required` | `@admin_required`, `@role_required('admin')` |
| **FastAPI (Python)** | No dependency | `Depends(get_current_user)` | `Depends(RoleChecker('admin'))` |
| **Django (Python)** | No decorator | `@login_required`, `LoginRequiredMixin` | `@permission_required('app.can_edit')` |
| **Spring Boot (Java)** | `permitAll()` | `authenticated()` | `hasRole('ADMIN')`, `hasAuthority('EDIT')` |
| **ASP.NET Core (C#)** | `[AllowAnonymous]` | `[Authorize]` | `[Authorize(Roles="Admin")]` |
| **Express (Node.js)** | No middleware | `app.use(auth)` | `auth.required('admin')` |
| **Gin (Go)** | No middleware | `r.Use(authMiddleware)` | `auth.RequiredRole("admin")` |
| **NestJS (TypeScript)** | `@Public()` | No decorator (global guard) | `@Roles('admin')` + `@UseGuards(RolesGuard)` |
| **Actix-web (Rust)** | No guard | `.wrap(AuthMiddleware)` | Custom extractor + guard |
| **Phoenix (Elixir)** | No plug | `plug :authenticate` | `plug :require_role` |

### Middleware-Level Patterns

| Pattern | What It Means |
|---------|---------------|
| `app.use(authMiddleware)` | Global auth — all routes require authentication |
| `router.use(auth)` | Group-level auth — all routes in this group are authenticated |
| `route-specific middleware` | Only this route uses auth — check other routes |
| `exception pattern` | `app.use(auth).except(['/health', '/login'])` — routes explicitly excluded |
| `conditional middleware` | `if feature_enabled: app.use(auth)` — auth gated by config |

### Inline/Procedural Patterns

```python
# Python example — inline auth
def transfer(request):
    if not request.user.is_authenticated:
        return redirect('/login')
    if not request.user.has_perm('finance.transfer'):
        return abort(403)
```

```javascript
// Node.js example — inline role check
app.post('/api/admin/action', (req, res) => {
  if (!req.user) return res.status(401).send('Unauthorized');
  if (!req.user.roles.includes('admin')) return res.status(403).send('Forbidden');
  // ... admin action
});
```

```java
// Java example — inline permission
@PostMapping("/transfer")
public ResponseEntity<?> transfer(@RequestBody TransferRequest req) {
    User user = SecurityContextHolder.getContext().getAuthentication();
    if (user == null) return ResponseEntity.status(401).build();
    if (!user.getAuthorities().contains(new SimpleGrantedAuthority("TRANSFER"))) {
        return ResponseEntity.status(403).build();
    }
    // ... transfer logic
}
```

## Role/Permission Detection Patterns

### Common Role Names

| Role Category | Typical Names |
|---------------|---------------|
| **Superadmin** | `admin`, `root`, `superuser`, `super_admin`, `sysadmin` |
| **Administrator** | `admin`, `administrator`, `operator`, `manager` |
| **Governance** | `governance`, `board`, `council`, `steward` |
| **Security** | `guardian`, `security`, `auditor`, `monitor` |
| **Finance** | `finance`, `treasury`, `accountant`, `paymaster` |
| **Operations** | `operator`, `keeper`, `maintainer`, `relayer` |
| **Development** | `developer`, `deployer`, `engineer` |
| **Read-only** | `viewer`, `reader`, `observer`, `monitor` |
| **Limited actions** | `minter`, `creator`, `editor`, `contributor` |

### Permission Check Patterns

| Pattern Type | Examples |
|-------------|----------|
| **Role check** | `hasRole('admin')`, `user.role == 'admin'`, `is_admin(user)` |
| **Permission check** | `hasPermission('transfer.execute')`, `user.can('edit')` |
| **ACL check** | `acl.allowed(user, resource, action)`, `access_control_list` |
| **Ownership check** | `resource.owner == user.id`, `doc.created_by == current_user` |
| **Group check** | `user.groups.includes('finance-team')`, `in_group(user, 'admins')` |
| **Attribute check** | `user.level >= 3`, `user.clearance == 'top_secret'` |
| **Capability check** | `user.has_capability('can_sign')`, `capabilities.include('approve')` |
| **Flag check** | `config.admin_only`, `feature_flags.is_enabled('beta')` |
| **Hardcoded address** | `if msg.sender == 0x1234...` (contracts) / `if user.id == ADMIN_ID` |

### Framework-Specific Role Mechanisms

| Framework | Role Mechanism |
|-----------|---------------|
| **Spring Security** | `@PreAuthorize("hasRole('ADMIN')")`, method security |
| **ASP.NET Core** | `[Authorize(Roles = "Admin,Manager")]` |
| **Django** | `@permission_required('app.permission')`, Groups |
| **FastAPI** | Custom `RoleChecker` dependency |
| **Flask-Security** | `@roles_required('admin')` |
| **express-jwt-permissions** | `permissions: ['admin:write']` |
| **Casbin** | Policy file (`sub, obj, act` model) |
| **Pundit (Ruby)** | Policy class per resource |
| **CanCanCan (Ruby)** | `Ability.rb` — ability definitions |
| **Amazon IAM** | Policy documents (JSON) with Action/Resource/Effect |
| **Kubernetes RBAC** | Role/ClusterRole + RoleBinding |
| **NATS** | Subject-level permissions per user/account |

## Review-Required Patterns (Ambiguous)

Flag these for manual review — they may be secure or may be bypassable:

| Pattern | Why Ambiguous |
|---------|---------------|
| `if user.id in authorized_users` | Dynamic set — who controls the set? |
| `hmac.verify(signature, key)` | Signature verification — is the key properly managed? |
| `require(msg.sender == contract.owner())` | Ownership — can ownership change? |
| `if request.ip in ALLOWED_IPS` | IP allowlist — can be spoofed? |
| `if request.headers['X-Internal']` | Header-based — can be forged? |
| `check_access(user, action)` | Custom function — implementaion details matter |
| `user.level >= threshold` | Numeric level — how is level assigned? |
| JWT token without audience/issuer validation | Token — attacker can forge? |
| API key without rate limiting | Key — is it securely stored? |
| Self-service role assignment | Role assignment — can user escalate? |

## Extraction Strategy

1. **Identify auth mechanism**: Determine if auth is annotation-based, middleware-based, or inline
2. **Map public routes**: Find all routes/entry points with no auth
3. **Map authenticated routes**: Find all routes requiring any authentication
4. **Map role-restricted routes**: Find all routes with specific role/permission requirements
5. **Flag ambiguous patterns**: Mark dynamic/conditional checks for manual review
6. **Trace role definitions**: Find where roles are defined, assigned, and checked

## Common Gotchas

1. **Middleware ordering**: Auth middleware applied after route handler — bypass possible
2. **Error handling leaks**: 401 vs 403 disclosure — attacker learns valid vs invalid credentials
3. **Default-deny vs default-allow**: Framework may default to allow if auth middleware fails to load
4. **Rate limiting ≠ auth**: Rate limiting doesn't prevent unauthorized access
5. **CORS ≠ auth**: CORS prevents browser-based access but not direct API calls
6. **OAuth scopes**: Different scopes for different endpoints — not all tokens have all scopes
7. **Token introspection**: Stateless JWTs without revocation — leaked tokens are permanent
8. **Admin interface discovery**: Admin routes on non-standard ports or hidden paths
