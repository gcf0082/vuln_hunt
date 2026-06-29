# Project Surfacing

扫描项目识别外部可触达的跨信任边界入口，输出暴露面清单。不做漏洞分析。

## 分类

HTTP / RPC / MQ / CLI / CRON / OUTBOUND_HTTP

## 原则

- 只收外部可直接触达的入口
- 内部模块间调用不算
