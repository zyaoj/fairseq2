# **Generalized Builder-Reviewer Framework**

This framework abstracts agent roles into a modular protocol. By using the filesystem as a shared state, you can swap "Builders" and "Reviewers" seamlessly by simply reassigning their roles in a configuration file.

## **1\. The Core Architecture: "State-Based Handshake"**

Agents do not talk to each other; they read and write to the **Project State**.

* **The Builder (Role: Actor):** Modifies source code and ensures functional correctness via tests.  
* **The Reviewer (Role: Critic):** Audits changes for non-functional requirements (security, style, performance).  
* **The Filesystem (Role: Bus):** The single source of truth (.agents/ directory).

## **2\. Universal Role Modularization**

To make agents swappable, we define a **Role Contract**. Any tool assigned a role must follow these I/O rules.

### **Builder Contract (The "Doer")**

* **Input:** Current code \+ review.json (if exists).  
* **Action:** Write code \+ Write tests.  
* **Output:** Updated source \+ test\_results.log.  
* **Command Signal:** npm run build:start or manual trigger.

### **Reviewer Contract (The "Checker")**

* **Input:** git diff \+ test\_results.log.  
* **Action:** Analyze diff \+ Analyze test coverage.  
* **Output:** review.json (STRICT SCHEMA).  
* **Command Signal:** npm run review:start.

## **3\. Unified Implementation Map (Modular)**

Use this table to pick your "Stack." Changing your stack only requires updating the **Role Actuator**.

| Agent Tech | Skill/Command to Assign Role | Ideal Role | Strengths |
| :---- | :---- | :---- | :---- |
| **Windsurf** | Activate "Flow" mode | **Builder** | High-speed multi-file editing |
| **Cursor** | Composer (Ctrl+I) | **Builder** | Context-aware UI components |
| **Claude CLI** | claude \-p "Review this..." | **Reviewer** | Strict adherence to JSON output |
| **Codex CLI** | codex "Audit diff..." | **Reviewer** | Deep security/logic analysis |
| **Aider** | aider \--message "Fix review.json" | **Builder** | Rapid terminal-based iteration |

## **4\. The Role Actuator (.agents/roles.json)**

Store this file in your root directory. It tells the current active agent what its job is.

{  
  "current\_session": "refactor-auth-logic",  
  "roles": {  
    "builder": {  
      "active\_tool": "Windsurf",  
      "instruction": "You are the Builder. Focus on implementing the logic in CHALLENGE.md. You must write tests for every function. Once tests pass, signal the Reviewer."  
    },  
    "reviewer": {  
      "active\_tool": "Codex",  
      "instruction": "You are the Reviewer. Do not write code. Audit the git diff. You MUST output a JSON array of issues to review.json. Focus on security and performance."  
    }  
  },  
  "status": "AWAITING\_REVIEW"  
}

## **5\. Swapping Roles at Will (Workflow)**

To change your stack mid-project (e.g., from Windsurf to Cursor):

1. **Modify Configuration:** Update active\_tool in .agents/roles.json.  
2. **Role Activation Prompt:** Paste this into the new tool's prompt:"Check .agents/roles.json. Identify your role. If you are the **Builder**, your goal is to clear the issues in review.json. If you are the **Reviewer**, your goal is to generate a new review.json based on the latest changes."

## **6\. The Reviewer Output Schema (Standardized)**

Regardless of the tool used (Codex, Claude, etc.), the **Reviewer** must output this exact JSON format so the **Builder** can consume it:

{  
  "status": "FAIL",  
  "reviewer": "agent-name-here",  
  "issues": \[  
    {  
      "file": "src/auth.ts",  
      "line": 12,  
      "severity": "high",  
      "category": "security",  
      "description": "Potential SQL injection point.",  
      "suggestion": "Use parameterized queries."  
    }  
  \]  
}

## **7\. Execution Logic**

1. **Activate Builder:** "Builder, your role is active. See .agents/roles.json. Start work."  
2. **Handoff:** Builder finishes, runs tests, and sets status to AWAITING\_REVIEW.  
3. **Activate Reviewer:** "Reviewer, your role is active. Audit the diff. Write to review.json."  
4. **Loop:** If review.json has "high" issues, set status to AWAITING\_FIX and point the **Builder** to it.