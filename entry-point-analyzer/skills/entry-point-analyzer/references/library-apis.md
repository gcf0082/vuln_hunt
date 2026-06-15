# Library / API Surface Entry Point Detection

## Exported API Surface

Libraries expose entry points through exported functions, public classes/methods, and trait implementations. These represent the integration contract — once published, they can be called by any consumer (internal or external).

### Entry Point Detection by Language

| Language | Entry Point Patterns | Detection |
|----------|---------------------|-----------|
| **Python** | Module-level functions, `__all__`, `@public` decorator | Scan `def` at module level; check `__init__.py` exports |
| **JavaScript/TypeScript** | `export function`, `export class`, `export default` | Check `package.json` `exports` field, `index.ts` barrel files |
| **Go** | Exported functions (capital letter), interface methods | `^func [A-Z]`, `^type [A-Z]` types with exported methods |
| **Rust** | `pub fn`, `pub struct` with `pub` methods | `pub fn`, `pub(crate)` vs `pub` visibility |
| **Java** | `public` class + `public` methods | File is `.java` with `public class`; methods marked `public` |
| **C#** | `public` class + `public` methods | Assembly exports; `public` access modifier |
| **C/C++** | Header declarations, `__declspec(dllexport)`, `.def` files | `extern` declarations, `DLL_EXPORT`, `__attribute__((visibility("default")))` |
| **Ruby** | Module methods, `def` at top level | `module_function`, `extend self` |
| **PHP** | Namespaced functions, public class methods | `namespace App; function doThing()` |

### Plugin / Extension System Entry Points

Plugin systems allow external code to register handlers at well-defined extension points.

| Pattern | Detection | Example |
|---------|-----------|---------|
| **Plugin interface** | Abstract class / trait / protocol | `class PluginBase { abstract function execute(); }` |
| **Hook registration** | Registry pattern, event bus | `hooks.register('filter.post', handler)` |
| **Middleware stack** | Chain-of-responsibility | `app.use(handler)`, `pipeline.add(step)` |
| **Decorator registration** | Annotation scanning | `@Plugin(id="my-plugin")` |
| **Service provider** | Dependency injection registration | `container.register(Interface, Implementation)` |
| **Route registration** | Plugin-defined routes | `plugin.registerRoute('/custom', handler)` |
| **Callback registration** | Function pointer/vtable | `on_event.addListener(myHandler)` |
| **Module system** | Dynamic import/load | `importlib.import_module('plugin')`, `dlopen` |

### Dynamic Invocation Entry Points

These are entry points reached through reflection, dynamic dispatch, or metaprogramming.

| Mechanism | Detection | Risk |
|-----------|-----------|------|
| **Reflection** | `getattr(obj, name)`, `invoke(obj, method)` | Can call any method on object |
| **eval / exec** | `eval(expr)`, `exec(code)` | Arbitrary code execution |
| **Callbacks** | `callback(data)` passed as param | Depends on caller trust |
| **__call__** (Python) | `obj.__call__()` | Object callable from outside |
| **Dynamic dispatch** | `dispatch[msg.type](msg.data)` | All registered handlers exposed |
| **Method missing** (Ruby) | `method_missing(name, *args)` | Catches any method call |
| **__call / __apply** (Lua) | Metamethods | Can make table callable |
| **Operator overloading** | C++ `operator()` / Python `__call__` | Function-object pattern |

### Serialization Entry Points

Deserialization entry points are high-risk as they can be exploited with crafted payloads.

| Mechanism | Detection | Risk Level |
|-----------|-----------|------------|
| **pickle (Python)** | `pickle.loads(data)` | Critical — arbitrary code execution |
| **JSON (standard)** | `json.loads(data)` | Low — data only, no code execution |
| **YAML** | `yaml.load(data)` without SafeLoader | Critical — arbitrary code execution |
| **XML** | `xml.etree.ElementTree.fromstring(data)` | Medium — XXE, billion laughs |
| **Java deserialization** | `ObjectInputStream.readObject()` | Critical — gadget chain RCE |
| **.NET deserialization** | `BinaryFormatter.Deserialize()` | Critical — gadget chain RCE |
| **PHP unserialize** | `unserialize($data)` | Critical — gadget chain RCE |
| **Protobuf** | `Message.ParseFrom(data)` | Low — schema-constrained |
| **MessagePack** | `msgpack.unpackb(data)` | Medium — depends on raw option |
| **CBOR** | `cbor.loads(data)` | Medium — similar to MessagePack |

### Configuration-Driven Entry Points

Configuration files can define entry points that get dynamically loaded.

| Source | Detection | Example |
|--------|-----------|---------|
| **Plugin registry** | YAML/JSON/TOML config listing plugins | `plugins: ["auth_ldap", "storage_s3"]` |
| **Module autodiscovery** | Filesystem scan for certain patterns | `__init__.py` imports, `plugins/` directory scan |
| **Dependency injection** | XML/annotation-based bean definitions | Spring `applicationContext.xml` |
| **Scripting hooks** | Config defines scripts to run at events | `on_deploy: "./post_deploy.sh"` |
| **Router config** | Config maps URL paths to handlers | `routes: {"POST /webhook": "webhook.Handler"}` |

### Extraction Strategy

1. **Scan exported surface**: For each source file, identify all `pub`/`public`/`export` declarations
2. **Plugin discovery**: Check for plugin registration points — interfaces, hooks, service providers
3. **Dynamic dispatch**: Search for `dispatch`, `invoke`, `call`, `execute` patterns with string/runtime-determined targets
4. **Deserialization sinks**: Search for `loads`, `unpack`, `deserialize`, `readObject`, `ParseFrom`
5. **Configuration analysis**: Read config files for plugin/module/hook definitions

### Classification Guidelines

| Entry Point Type | Typical Classification | Notes |
|-----------------|----------------------|-------|
| Public exported function | Public (Unrestricted) | If no doc/annotation says otherwise |
| Protected/internal method | Internal-Only | Language visibility restricts callers |
| Plugin hook point | Public (by design) | Integration contract |
| Deserialization handler | Public (Unrestricted) | Unless auth-gated at the caller level |
| Configuration-loaded entry | Public | Config-controlled but still externally reachable |
| Callback parameter | Review Required | Depends on who provides the callback |
