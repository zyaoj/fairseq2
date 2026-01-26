---
categories:
  - "[[Projects]]"
project_path: Projects/Urology-Data-Platform
status:
  - active
start: 2026-01-21
url:
people:
  - "[[姚志远]]"
tags:
  - project-moc
  - 泌尿外科
  - 医疗AI
  - FastAPI
  - PostgreSQL
---

# CUA数据库平台

> 中华医学会泌尿外科分会（Chinese Urology Association）多模态患者数据平台

## 概述

**目标**：构建统一的泌尿外科患者数据平台，聚合多模态医疗数据（化验单、影像、手术记录）并结合 AI 进行智能提取与摘要生成。

**核心问题**：泌尿外科医生需要花费大量时间从分散的系统中拼凑患者病史信息。

**解决方案**：提供统一的患者时间线视图，结合 VLM/OCR 智能提取和 LLM 驱动的摘要功能。

**技术栈**：FastAPI, PostgreSQL, Milvus, MinIO, Claude VLM/LLM, Streamlit

**团队**：医疗AI研发组

## 团队贡献者

```dataview
TABLE WITHOUT ID key as "贡献者"
FROM "Projects/Urology-Data-Platform"
WHERE people
FLATTEN people
GROUP BY people
```

## 核心功能（MVP）

1. **手动上传** - 扫描图片 + 数字化 PDF 化验报告
2. **VLM/OCR 提取** - Claude 驱动的结构化数据提取
3. **患者时间线** - 按生命周期阶段组织（问诊 → 手术 → 随访）
4. **AI 摘要** - LLM 驱动的患者病史摘要
5. **语义搜索** - 按化验值和临床上下文查找患者

## 技术架构

| 组件 | 技术选型 |
|------|----------|
| 后端 | FastAPI + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL |
| 向量数据库 | Milvus |
| 文件存储 | MinIO (开发) / S3 (生产) |
| 前端 | Streamlit |
| AI | Claude claude-3-5-sonnet (VLM + LLM) |
| 认证 | JWT + python-jose |

## 架构文档

- [[Projects/Urology-Data-Platform/2026-01-21-设计概览|设计概览]] - 系统架构与数据模型
- [[Projects/Urology-Data-Platform/2026-01-21-实施计划|实施计划]] - 详细的任务级实施指南

## 最近工作

```dataview
TABLE file.name as "条目", created, subtype as "类型", people, tags
FROM "Projects/Urology-Data-Platform"
WHERE subtype AND file.name != "CUA数据库平台"
SORT created DESC
LIMIT 15
```

## 流程

```dataview
TABLE file.name as "流程", status, tags
FROM "/"
WHERE contains(file.frontmatter.categories, "[[Procedures]]")
  AND file.frontmatter.project_path = "Projects/Urology-Data-Platform"
SORT status ASC, file.name ASC
```

## 会议

```dataview
TABLE date, people
FROM "Projects/Urology-Data-Platform/Meetings"
WHERE contains(categories, link("Meetings"))
SORT date DESC
```

## 合规说明

- 混合部署：本地数据，云端 AI
- MVP 专注基础安全（认证 + 加密）
- 正式 HIPAA 合规推迟至 MVP 后

## 相关

- [[Projects/智能问诊与预测/智能问诊与预测|智能问诊与预测]] - 相关医疗 AI 项目
- [[姚志远]] - 项目负责人
