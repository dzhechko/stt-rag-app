---
name: idea2prd-manual
description: >
  Полный цикл от проблемы/идеи до документации для Vibe Coding с контрольными точками.
  Автоматически определяет тип входа: проблема → Analyst pipeline → идея → PRD pipeline.
  Использует внешние скиллы explore, goap-research-ed25519, problem-solver-enhanced (полностью).
  Включает Pseudocode generation, Test Scenarios, Completion Checklist.
  Режим MANUAL — запрашивает подтверждение между каждой фазой (9 checkpoints).
  Триггеры: "сделай PRD пошагово", "idea to prd manual", "prd with checkpoints".
---

# Idea2PRD Manual: Full-Cycle Documentation with Checkpoints

Скилл полного цикла: от проблемы или идеи до готовой документации с **Pseudocode** и **Completion Checklist**. **С контрольными точками (9 checkpoints)** — пользователь подтверждает каждую фазу.

## What's New in v2

| Feature | Benefit |
|---------|---------|
| **Phase 4.5: Pseudocode** | +99% code quality (research-backed) |
| **Phase 5: Test Scenarios** | TDD-ready Gherkin specs |
| **Phase 6: Completion** | CI/CD, deployment, monitoring |
| **9 Checkpoints** | Full control over each phase |

## Bundled Components

```
idea2prd-manual/
├── SKILL.md                              # Этот файл (оркестратор)
├── scripts/
│   ├── c4_generator.py                   # Генератор C4 диаграмм
│   ├── fitness_validator.py              # Валидатор Fitness Functions
│   ├── pseudocode_generator.py           # [NEW] Генератор pseudocode
│   └── ai_context_builder.py             # Сборщик .ai-context/
└── references/
    ├── ddd-patterns.md                   # DDD patterns
    ├── adr-catalog.md                    # ADR templates
    ├── c4-model.md                       # C4 guidelines
    ├── fitness-functions-catalog.md      # Fitness Functions
    ├── pseudocode-style.md               # [NEW] Pseudocode conventions
    └── completion-checklist-template.md  # [NEW] Completion template
```

## External Skills Dependencies

**Для Analyst Pipeline используются внешние скиллы (full execution):**

| Phase | External Skill | Path | Mode |
|-------|----------------|------|------|
| Phase A | `explore` | `/mnt/skills/user/explore/SKILL.md` | Full with questions |
| Phase B | `goap-research-ed25519` | `/mnt/skills/user/goap-research-ed25519/SKILL.md` | Full research |
| Phase C | `problem-solver-enhanced` | `/mnt/skills/user/problem-solver-enhanced/SKILL.md` | All 9 modules |

## When to Use AUTO vs MANUAL

| Use AUTO when | Use MANUAL when |
|---------------|-----------------|
| Проблема/идея ясна | Много неизвестных |
| Нужен быстрый результат | Критически важный продукт |
| Готовы к defaults | Нужен контроль |
| MVP / прототип | Production system |

## Full Pipeline with Checkpoints

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: Проблема ИЛИ Идея                                       │
│                         ↓                                       │
│  GATE 0: Problem or Idea? (auto-detect)                         │
│  → Проблема? → ANALYST PIPELINE (full)                          │
│  → Идея? → Skip to PRD PIPELINE                                 │
│                         ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ANALYST PIPELINE (external skills, with checkpoints)   │    │
│  │                                                         │    │
│  │  Phase A: view(explore) → questions → Task Brief        │    │
│  │  ⏸️ CHECKPOINT A: Confirm Task Brief                    │    │
│  │                                                         │    │
│  │  Phase B: view(goap-research) → research → Findings     │    │
│  │  ⏸️ CHECKPOINT B: Confirm Research                      │    │
│  │                                                         │    │
│  │  Phase C: view(problem-solver) → ALL 9 modules → Idea   │    │
│  │  ⏸️ CHECKPOINT C: Confirm Product Idea                  │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  PRD PIPELINE (embedded, with checkpoints)              │    │
│  │                                                         │    │
│  │  Phase 1: Requirements → PRD.md                         │    │
│  │  ⏸️ CHECKPOINT 1: Confirm Requirements                  │    │
│  │                                                         │    │
│  │  Phase 2: DDD Strategic → bounded-contexts              │    │
│  │  ⏸️ CHECKPOINT 2: Confirm DDD Strategic                 │    │
│  │                                                         │    │
│  │  Phase 3: ADR + C4 → 10+ ADRs, diagrams                 │    │
│  │  ⏸️ CHECKPOINT 3: Confirm Architecture                  │    │
│  │                                                         │    │
│  │  Phase 4: DDD Tactical → aggregates, schema             │    │
│  │  ⏸️ CHECKPOINT 4: Confirm Tactical Design               │    │
│  │                                                         │    │
│  │  Phase 4.5: Pseudocode → algorithm logic [NEW]          │    │
│  │  ⏸️ CHECKPOINT 4.5: Confirm Pseudocode                  │    │
│  │                                                         │    │
│  │  Phase 5: Validation → fitness, tests, .ai-context/     │    │
│  │  ⏸️ CHECKPOINT 5: Confirm Tests & Validation            │    │
│  │                                                         │    │
│  │  Phase 6: Completion → deploy, CI/CD [NEW]              │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         ↓                                       │
│  OUTPUT: Complete docs/ + .ai-context/ + Executive Summary      │
└─────────────────────────────────────────────────────────────────┘
```

**Total Checkpoints: 9** (3 Analyst + 6 PRD)

---

## Gate 0: Auto-Detection

**Автоматически определяет тип входа:**

| Тип | Индикаторы | Action |
|-----|------------|--------|
| **ПРОБЛЕМА** | Боль, негатив, "как?", нет решения | → Analyst Pipeline |
| **ИДЕЯ** | Конкретный продукт, функции, аудитория | → PRD Pipeline |

**При неясности — max 1 вопрос:**
```
Уточни: это проблема для решения или готовая идея продукта?
```

---

## ANALYST PIPELINE (Full Execution with Checkpoints)

**ВАЖНО:** Claude загружает внешние скиллы через `view` tool и выполняет ПОЛНОСТЬЮ, с контрольными точками.

### Phase A: Explore

**Действие Claude:**
```
1. view("/mnt/skills/user/explore/SKILL.md")
2. Выполнить explore полностью:
   - Задать необходимые вопросы
   - Получить ответы от пользователя
3. Сформировать Task Brief
4. ⏸️ CHECKPOINT A
```

**Checkpoint A Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE A COMPLETE: Task Brief
═══════════════════════════════════════════════════════════

## Task Brief

**Проблема:** [описание]
**Контекст:** [детали]
**Цели:** [что хотим достичь]
**Ограничения:** [если есть]

───────────────────────────────────────────────────────────
⏸️ Подтвердите Task Brief для продолжения к Research.
   Ответьте "ok" или внесите корректировки.
═══════════════════════════════════════════════════════════
```

### Phase B: Research

**Действие Claude:**
```
1. view("/mnt/skills/user/goap-research-ed25519/SKILL.md")
2. Выполнить research:
   - Web searches
   - Competitor analysis
   - Technology options
3. Сформировать Research Findings
4. ⏸️ CHECKPOINT B
```

**Checkpoint B Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE B COMPLETE: Research Findings
═══════════════════════════════════════════════════════════

## Research Findings

**Competitors:** [список]
**Market Insights:** [ключевые находки]
**Technology Options:** [рекомендации]
**Gaps Identified:** [возможности]

───────────────────────────────────────────────────────────
⏸️ Подтвердите Research для продолжения к Problem-Solver.
   Ответьте "ok" или запросите дополнительное исследование.
═══════════════════════════════════════════════════════════
```

### Phase C: Solve (Full Problem-Solver)

**Действие Claude:**
```
1. view("/mnt/skills/user/problem-solver-enhanced/SKILL.md")
2. Выполнить ВСЕ 9 модулей:
   - First Principles
   - Root Cause (5 Whys)
   - Constraint Analysis
   - SCQA
   - Game Theory
   - Second-Order Effects
   - TRIZ
   - Devil's Advocate
   - Synthesis
3. Сформировать Product Idea
4. ⏸️ CHECKPOINT C
```

**Checkpoint C Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE C COMPLETE: Product Idea
═══════════════════════════════════════════════════════════

## Product Idea

**Название:** [название]
**Описание:** [что это]
**Target Audience:** [для кого]
**Core Features:** [ключевые функции]
**Differentiation:** [чем отличается]

## Problem Analysis Highlights

| Module | Key Insight |
|--------|-------------|
| Root Cause | [finding] |
| Game Theory | [finding] |
| TRIZ | [finding] |

───────────────────────────────────────────────────────────
⏸️ Подтвердите Product Idea для продолжения к PRD Pipeline.
   Ответьте "ok" или скорректируйте направление.
═══════════════════════════════════════════════════════════
```

---

## PRD PIPELINE (with Checkpoints)

### Phase 1: Requirements

**Генерирует:**
- 10+ Functional Requirements (MoSCoW)
- 5+ Non-Functional Requirements
- 5+ User Stories
- 2+ User Journeys
- Constraints & Assumptions

**Checkpoint 1 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 1 COMPLETE: Requirements
═══════════════════════════════════════════════════════════

## Summary

| Type | Count |
|------|-------|
| Functional Requirements | [N] |
| Non-Functional Requirements | [N] |
| User Stories | [N] |
| User Journeys | [N] |

## Key Requirements

**Must Have:**
- [FR-001] [description]
- [FR-002] [description]
...

**User Stories Preview:**
- US-001: As a [user], I want [action], so that [benefit]
...

───────────────────────────────────────────────────────────
⏸️ Подтвердите Requirements для продолжения к DDD Strategic.
   Ответьте "ok" или внесите корректировки.
═══════════════════════════════════════════════════════════
```

### Phase 2: DDD Strategic

**Генерирует:**
- 3+ Bounded Contexts
- Ubiquitous Language per context
- Context Map with relationships
- Subdomains (Core/Supporting/Generic)
- 5+ Strategic Domain Events

**Checkpoint 2 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 2 COMPLETE: DDD Strategic Design
═══════════════════════════════════════════════════════════

## Bounded Contexts

| Context | Type | Responsibility |
|---------|------|----------------|
| [Context1] | Core | [what it does] |
| [Context2] | Supporting | [what it does] |
...

## Context Map

[Mermaid diagram]

───────────────────────────────────────────────────────────
⏸️ Подтвердите DDD Strategic для продолжения к Architecture.
   Ответьте "ok" или пересмотрите границы контекстов.
═══════════════════════════════════════════════════════════
```

### Phase 3: ADR + C4

**Генерирует:**
- 10+ ADRs
- C4 Level 1: System Context
- C4 Level 2: Container
- C4 Level 3: Component

**Checkpoint 3 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 3 COMPLETE: Architecture
═══════════════════════════════════════════════════════════

## ADRs Summary

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | [Architecture]: [choice] | Accepted |
| ADR-002 | [Database]: [choice] | Accepted |
...

## C4 Diagrams

- Level 1: System Context ✅
- Level 2: Container ✅
- Level 3: Component ✅

───────────────────────────────────────────────────────────
⏸️ Подтвердите Architecture для продолжения к DDD Tactical.
   Ответьте "ok" или оспорьте ADRs.
═══════════════════════════════════════════════════════════
```

### Phase 4: DDD Tactical

**Per Bounded Context генерирует:**
- 1-3 Aggregates
- Entities with identity
- Value Objects
- Domain Events (detailed)
- Repository interfaces
- Services
- Database Schema (SQL)

**Checkpoint 4 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 4 COMPLETE: DDD Tactical Design
═══════════════════════════════════════════════════════════

## Aggregates

| Context | Aggregate | Entities | Events |
|---------|-----------|----------|--------|
| [Ctx1] | [Agg1] | [N] | [N] |
...

## Key Aggregate Methods

**[AggregateName]:**
- create(...): [description]
- [method](...): [description]
...

───────────────────────────────────────────────────────────
⏸️ Подтвердите Tactical Design для продолжения к Pseudocode.
   Ответьте "ok" или скорректируйте агрегаты.
═══════════════════════════════════════════════════════════
```

---

### Phase 4.5: Pseudocode Generation [NEW]

**Reference:** `references/pseudocode-style.md`

**КРИТИЧЕСКИ ВАЖНО для качества генерации кода (+99% по исследованиям).**

**Действие Claude:**
```
1. Для каждого Aggregate из Phase 4:
   - Для каждого public метода → сгенерировать pseudocode
   
2. Для каждого Domain Service:
   - Для каждого метода → сгенерировать pseudocode
   
3. Output: docs/pseudocode/{AggregateName}.pseudo
4. ⏸️ CHECKPOINT 4.5
```

**Pseudocode Style:**

```pseudocode
FUNCTION methodName(param1: Type, param2: Type) -> ReturnType:
    // Pre-conditions
    VALIDATE param1 is not empty
    
    // Main logic
    FOR each item IN collection:
        IF condition THEN
            DO action
        END IF
    END FOR
    
    // Side effects
    EMIT DomainEvent(data)
    
    RETURN result
END FUNCTION
```

**Checkpoint 4.5 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 4.5 COMPLETE: Pseudocode
═══════════════════════════════════════════════════════════

## Pseudocode Files Generated

| File | Aggregate/Service | Methods |
|------|-------------------|---------|
| OrderAggregate.pseudo | Order | 5 |
| PaymentService.pseudo | PaymentService | 3 |
...

## Sample: OrderAggregate.placeOrder

```pseudocode
FUNCTION placeOrder(items, customer) -> OrderId:
    VALIDATE items not empty
    VALIDATE customer.isVerified
    
    FOR each item IN items:
        CHECK inventory.hasStock(item)
    END FOR
    
    total = CALCULATE subtotal + tax
    order = CREATE Order(customer, items, total)
    
    EMIT OrderPlacedEvent(order.id, total)
    RETURN order.id
END FUNCTION
```

───────────────────────────────────────────────────────────
⏸️ Подтвердите Pseudocode для продолжения к Tests.
   Ответьте "ok" или скорректируйте алгоритмы.
═══════════════════════════════════════════════════════════
```

---

### Phase 5: Validation, Tests & AI Context [ENHANCED]

**Генерирует:**
- 5+ Fitness Functions
- 5+ Gherkin Test Scenarios
- 8 .ai-context/ files

**Test Scenarios (Gherkin):**

```gherkin
Feature: Order Placement
  Scenario: Successfully place order
    Given I am a verified customer
    And all items are in stock
    When I place the order
    Then the order should be created
    And I should receive confirmation
```

**Checkpoint 5 Output:**
```
═══════════════════════════════════════════════════════════
✅ PHASE 5 COMPLETE: Validation & Tests
═══════════════════════════════════════════════════════════

## Fitness Functions

| ID | Rule | Target |
|----|------|--------|
| FF-01 | BC Independence | 100% |
| FF-02 | Aggregate Size | ≤7 entities |
...

## Test Scenarios

| Feature | Scenarios | Coverage |
|---------|-----------|----------|
| Order Placement | 3 | Happy + 2 Error |
| Payment | 2 | Happy + 1 Error |
...

## .ai-context/ Files

✅ 8 files generated:
- README.md
- architecture-summary.md
- key-decisions.md
- domain-glossary.md
- bounded-contexts.md
- coding-standards.md
- fitness-rules.md
- pseudocode-index.md

───────────────────────────────────────────────────────────
⏸️ Подтвердите Tests & Validation для продолжения к Completion.
   Ответьте "ok" или добавьте test scenarios.
═══════════════════════════════════════════════════════════
```

---

### Phase 6: Completion Checklist [NEW]

**Генерирует deployment-ready документацию:**
- Development environment setup
- CI/CD pipeline templates
- Docker/K8s manifests
- Monitoring configuration
- Security checklist
- Pre-launch checklist

**Output file:** `docs/completion/COMPLETION_CHECKLIST.md`

**После Phase 6 — финальный Executive Summary (без checkpoint).**

---

## Executive Summary Template

После генерации выводится:

```
═══════════════════════════════════════════════════════════════
✅ DOCUMENTATION COMPLETE: [Product Name]
═══════════════════════════════════════════════════════════════

## Input Processing

**Input Type:** [Problem | Idea]
**Analyst Pipeline:** [Executed | Skipped]
**Checkpoints Passed:** [N]/9

## Summary

| Category | Count |
|----------|-------|
| Functional Requirements | [N] |
| Non-Functional Requirements | [N] |
| User Stories | [N] |
| Bounded Contexts | [N] |
| ADRs | [N] |
| C4 Diagrams | [N] |
| Aggregates | [N] |
| Domain Events | [N] |
| **Pseudocode Files** | [N] |
| **Test Scenarios** | [N] |
| Fitness Functions | [N] |
| .ai-context/ files | 8 |

## Files Generated

docs/
├── prd/PRD.md
├── ddd/strategic/[files]
├── ddd/tactical/[files]
├── adr/[10+ files]
├── c4/[files]
├── pseudocode/[files]           # [NEW]
├── tests/[feature files]        # [NEW]
├── fitness/[files]
├── completion/COMPLETION_CHECKLIST.md  # [NEW]
└── INDEX.md

.ai-context/
└── [8 files]

## Vibe Coding Quick Start

\`\`\`bash
# Implement with pseudocode guidance
claude "Implement OrderAggregate using docs/pseudocode/OrderAggregate.pseudo"

# Generate tests
claude "Generate tests from docs/tests/*.feature"

# Deploy
claude "Follow docs/completion/COMPLETION_CHECKLIST.md"
\`\`\`

═══════════════════════════════════════════════════════════════
```

---

## Output Structure

```
project-root/
├── docs/
│   ├── prd/PRD.md
│   ├── ddd/
│   │   ├── strategic/
│   │   └── tactical/
│   ├── adr/
│   ├── c4/
│   ├── pseudocode/              # [NEW]
│   │   ├── {Aggregate1}.pseudo
│   │   └── {Service1}.pseudo
│   ├── tests/                   # [NEW]
│   │   └── {feature}.feature
│   ├── fitness/
│   ├── completion/              # [NEW]
│   │   └── COMPLETION_CHECKLIST.md
│   └── INDEX.md
├── .ai-context/
│   └── [8 files]
└── README.md
```

## Quality Minimums (Enforced)

| Artifact | Minimum |
|----------|---------|
| Functional Requirements | 10 |
| Non-Functional Requirements | 5 |
| User Stories | 5 |
| Bounded Contexts | 3 |
| ADRs | 10 |
| C4 Diagrams | 3 |
| Aggregates | 5 |
| Domain Events | 5 |
| **Pseudocode Files** | 3 |
| **Test Scenarios** | 5 |
| Fitness Functions | 5 |
| .ai-context/ files | 8 |

## Checkpoint Commands

| Command | Action |
|---------|--------|
| `ok` / `продолжай` | Proceed to next phase |
| `скорректируй X` | Modify specific element |
| `добавь Y` | Add missing element |
| `пересмотри Z` | Reconsider decision |
| `стоп` | Pause and save progress |

## Comparison: Auto vs Manual

| Aspect | idea2prd-auto | idea2prd-manual |
|--------|---------------|-----------------|
| **Time** | 20-40 min | 60-120 min |
| **User input** | 0-4 questions | **9 checkpoints** |
| **Control** | Low | **High** |
| **External skills** | Full execution | Full execution |
| **Pseudocode** | ✅ Auto | ✅ With review |
| **Test Scenarios** | ✅ Auto | ✅ With review |
| **Completion** | ✅ Auto | ✅ With review |
| **Best for** | MVPs, clear ideas | **Critical systems** |

## Dependencies

- External skills: explore, goap-research-ed25519, problem-solver-enhanced
- Mermaid (C4 diagrams)
- web_search (for Research phase)
