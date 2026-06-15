# Web API Entry Point Detection

## Entry Point Identification

Web entry points are HTTP endpoints, RPC methods, WebSocket handlers, and middleware functions that process external requests.

### RESTful API Patterns

| Framework/Language | Entry Point Pattern | Example |
|--------------------|-------------------|---------|
| **Express (Node.js)** | `app.get/post/put/delete('/path', handler)` | `app.get('/api/users', auth, handler)` |
| **Fastify (Node.js)** | `fastify.get/post('/path', handler)` | `fastify.post('/webhook', {preHandler: auth}, handler)` |
| **Koa (Node.js)** | `router.get/post('/path', ctx => ...)` | `router.get('/admin', auth, ctx => ...)` |
| **Flask (Python)** | `@app.route('/path', methods=['GET'])` + function | `@app.route('/admin', methods=['POST'])` |
| **FastAPI (Python)** | `@app.get/post('/path')` + async def | `@app.post('/api/transfer')` |
| **Django (Python)** | `urlpatterns = [path('route/', view)]` | `path('admin/', admin_view)` |
| **Spring Boot (Java)** | `@GetMapping/@PostMapping/@RequestMapping` | `@PostMapping("/transfer")` |
| **JAX-RS (Java)** | `@GET/@POST @Path("/path")` | `@POST @Path("/order")` |
| **Gin (Go)** | `r.GET/POST/PUT/DELETE('/path', handler)` | `r.POST('/webhook', handler)` |
| **Echo (Go)** | `e.GET/POST('/path', handler)` | `e.GET('/admin', adminAuth, handler)` |
| **ASP.NET Core (C#)** | `[HttpGet]/[HttpPost]` + controller method | `[Authorize] [HttpPost("transfer")]` |
| **Actix-web (Rust)** | `.route("/path")` + handler fn | `.route("/webhook").post(handler)` |
| **Axum (Rust)** | `.route("/path", method_handler)` | `.route("/api/users", get(list_users))` |
| **Phoenix (Elixir)** | `get/post/put "/path", Controller, :action` | `post "/transfer", TransferController, :create` |

### RPC Patterns

| Framework | Pattern | Example |
|-----------|---------|---------|
| **gRPC** | Service method in `.proto` file | `rpc Transfer(TransferRequest) returns (TransferResponse)` |
| **Thrift** | Service method in `.thrift` file | `string ping(1: string msg)` |
| **dubbo (Java)** | `@DubboService` + interface method | `interface TransferService { void transfer(...); }` |
| **JSON-RPC** | Method dispatch in handler | `{"method": "transfer", "params": [...]}` |
| **XML-RPC** | Method name dispatch | `<methodName>transfer</methodName>` |
| **tRPC (TypeScript)** | `router.query/mutation('name')` | `t.router({transfer: t.procedure.input(z.object({...})).mutation(...)})` |

### WebSocket Patterns

| Framework | Pattern | Example |
|-----------|---------|---------|
| **ws/websockets (Node)** | `wss.on('connection', ws => ...)` | `ws.on('message', handler)` |
| **FastAPI WebSocket** | `@app.websocket('/path')` | `@app.websocket('/ws/chat')` |
| **Spring WebSocket** | `@MessageMapping` handler | `@MessageMapping("/trade")` |
| **Gorilla WebSocket (Go)** | `upgrader.Upgrade(w, r, nil)` + read loop | `conn.ReadMessage()` |

### GraphQL Patterns

| Framework | Entry Point | Example |
|-----------|-------------|---------|
| **Apollo (Node.js)** | `resolvers.Query/Mutation` | `Mutation: { transfer(parent, args, ctx) }` |
| **Graphene (Python)** | `Mutation` class with `mutate` method | `class Transfer(Mutation): def mutate(...)` |
| **gqlgen (Go)** | Generated resolver function | `func (r *mutationResolver) Transfer(ctx, input)` |

### Authentication/Authorization Detection

| Mechanism | Detection Pattern |
|-----------|------------------|
| **Decorator/Annotation** | `@auth`, `@login_required`, `@Authenticated`, `[Authorize]` |
| **Middleware** | `app.use(authMiddleware)`, `router.use(auth)` |
| **Function-level** | `if !authenticated { return 401 }` |
| **Role check** | `@require_role('admin')`, `[Authorize(Roles="admin")]` |
| **JWT** | `jwt.verify(token)`, `extract_jwt(req)` |
| **Session** | `req.session.userId`, `session.get('user')` |
| **API Key** | `req.headers['x-api-key']`, `api_key` validation |
| **RBAC** | `if !hasPermission(user, 'transfer')` |
| **ACL** | `acl.check(req, 'transfer')` |

### Extraction Strategy

1. Scan for route registrations: `app.get/post/put/delete`, `router.get/post`, `@app.route`, `@GetMapping`, `r.POST`, `add_resource`
2. Extract handler function/method names
3. Record middleware chains for each route (auth/role indicators)
4. For GraphQL: find all `Mutation` and `Query` resolver definitions
5. For gRPC: parse `.proto` service definitions
6. Classify by access control:
   - No auth middleware → Public (Unrestricted)
   - Has auth middleware → Authenticated
   - Has role-specific check → Role-Restricted
   - IP whitelist/custom validation → Review Required

### Common Pitfalls

1. **Global middleware ≠ per-route security**: Auth middleware applied globally may have bypasses (static files, health checks)
2. **Handler-only auth**: Route registered without middleware but auth is inside handler — easy to miss
3. **GraphQL introspection**: Public introspection leaks the full schema; individual resolvers may have different auth
4. **Overloaded routes**: Same route, different HTTP methods — each method may have different auth
5. **Wildcard routes**: `/api/*` or `/:param` routes can shadow more specific routes
6. **CORS misconfiguration**: Public CORS doesn't mean public access, but enables CSRF-like attacks
