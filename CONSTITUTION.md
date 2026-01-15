# CONSTITUTION

## Authority

- This document is immutable.
- No agent MUST NOT modify this document.
- This document has the highest authority.
- All agent actions, outputs, and decisions MUST comply with this document.
- Any violation renders the result invalid.

## Purpose

- Define non-negotiable constraints governing the project and all agents.

## Definitions

- Agent: any automated or semi-automated system producing project results.
- Result: any agent-produced output, including messages, code, configs, files, commits, and artifacts.
- Change: any modification to repository content, including code, configuration, documentation, and tests.
- Proceed: any step that finalizes or advances work, including replying with a final result, committing, pushing, opening a PR, releasing, or deploying.

## Project Scope

- The project is strictly limited to building and maintaining a Telegram bot.
- The bot MUST provide accurate and non-misleading information.
- The system MUST adopt an async-first architecture.
- Agents MUST NOT fabricate information, data, assumptions, or outputs.
- If information is unknown or not verifiable, agents MUST state uncertainty explicitly.
- If assumptions are required, agents MUST label them as assumptions and MUST NOT present them as facts.

## Agent Obligations

- Agents MUST use `uv` as the sole tool for environment and dependency management.
- Any exception to using `uv` MUST be explicitly justified and recorded.
- After any change, agents MUST run `prek run` and resolve all failures before proceeding.

## Documentation Principles

- Language MUST be concise, precise, and unambiguous.
- Scope, ownership, and responsibility boundaries MUST be explicit.
- Each document MUST serve exactly one purpose.
- Rules MUST be stated in enforceable terms.
- Constitutional rules MUST NOT be duplicated in subordinate documents.

## Interpretation

- This document defines constraints.
- All other documents define procedures.
- Procedures MUST NOT override constraints.
