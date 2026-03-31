# Skill: payload-patts-lookup-v1

- **Version:** 1
- **Domain:** payload
- **Status:** production
- **Success Rate:** N/A (lookup skill)
- **Last Modified:** 2026-04-01
- **Author:** Elkin

---

## Description

Primary lookup interface for PayloadsAllTheThings repository — a comprehensive
collection of offensive security payloads, bypasses, and exploitation techniques.
This skill provides structured access to 60+ attack categories including SQLi,
XSS, SSTI, SSRF, XXE, command injection, deserialization gadgets, and more.

---

## Prerequisites

- PayloadsAllTheThings cloned at: `openclaw-skills/repos/PayloadsAllTheThings/`
- Read access to markdown files in the repo

---

## Trigger Conditions

Activate this skill when the task involves any of:

- SQL injection payloads or bypass strings
- XSS payloads or filter bypasses
- SSTI detection and exploitation strings
- SSRF payloads and bypass techniques
- XXE payloads
- Command injection strings
- File inclusion (LFI/RFI) payloads
- Deserialization gadgets
- Privilege escalation checklists (Linux/Windows)
- Password lists or hash cracking references
- JWT attacks
- OAuth bypasses
- CORS misconfigurations
- Open redirect payloads
- Any other offensive technique with a matching subdirectory in the repo

---

## Execution Flow

```
1. Confirm PayloadsAllTheThings exists at openclaw-skills/repos/PayloadsAllTheThings/
2. Navigate to repository root and check README.md for category index
3. Identify matching subdirectory by name (e.g., "SQL Injection", "XSS Injection")
4. Read the relevant README.md and any payload .txt files in that subdirectory
5. Extract applicable payloads, bypasses, and methodology
6. Return content grounded entirely in those files
7. Cite exact file path in output
```

---

## Tool Chain

```
openclaw-skills/repos/PayloadsAllTheThings/README.md  → category index
│
├─ <Category>/README.md                              → technique description
└─ <Category>/Payloads/<file>.txt                    → raw payload lists
```

---

## Repository Structure

Key categories (60+ total):

**Injection Attacks**
- SQL Injection, XSS Injection, Command Injection, SSTI
- LDAP Injection, NoSQL Injection, XPATH Injection, GraphQL Injection
- XXE Injection, XSLT Injection, SSI Injection

**Server-Side Attacks**
- SSRF, File Inclusion (LFI/RFI), Deserialization
- Insecure Direct Object References, Mass Assignment

**Client-Side Attacks**
- XSS Injection, CORS Misconfiguration, CSRF, Clickjacking
- DOM Clobbering, Open Redirect, Tabnabbing

**Exploitation**
- CVE Exploits, Upload Insecure Files, Race Conditions
- Type Juggling, Prototype Pollution, Regular Expression DoS

**Bypasses & Evasion**
- Brute Force Rate Limit, Business Logic Errors
- Request Smuggling, Web Cache Deception, Virtual Hosts

**Authentication/Authorization**
- JWT, OAuth Misconfiguration, SAML Injection
- Account Takeover, Insecure Randomness

---

## Usage

```
When user asks for a payload:

User: "Give me a SQL injection payload for MySQL"

Response:
[Source: PayloadsAllTheThings/SQL Injection/README.md]

# MySQL SQL Injection Payloads

... (content from file) ...
```

---

## Output Format

Always prefix payload responses with:

```
[Source: PayloadsAllTheThings/<Subdirectory>/<File>]
```

Example citations:
- `[Source: PayloadsAllTheThings/SQL Injection/README.md]`
- `[Source: PayloadsAllTheThings/Command Injection/Payloads/linux.txt]`
- `[Source: PayloadsAllTheThings/XSS Injection/README.md]`

---

## Success Indicators

- Response includes valid source citation
- Payload/technique content comes directly from repo files
- No reconstruction from general training memory
- Clear distinction between repo-sourced content and fallback knowledge

---

## Failure Handling

| Scenario | Response |
|----------|---------|
| Subdirectory not found | State: "Technique not covered in PayloadsAllTheThings" then fall back to general knowledge |
| File not found | Check sibling files or README.md in same directory |
| Repo not cloned | Clone first: `git clone https://github.com/swisskyrepo/PayloadsAllTheThings.git` |

---

## Optimization Notes

- Cache README.md index for faster category lookup
- For common categories (SQLi, XSS), the payloads are at the bottom of README.md
- Some categories have separate `Payloads/` subdirectories with `.txt` files
- Check `_LEARNING_AND_SOCIALS/` for methodology guides and resources

---

## Changelog

- **v1** — Initial release: PayloadsAllTheThings lookup skill with 60+ attack categories,
           structured execution flow, mandatory source citation protocol