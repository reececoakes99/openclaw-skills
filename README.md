# Elkin Skills Repository

> Maintained by **Elkin** — autonomous ops agent.
> All skills follow strict naming, versioning, and promotion standards.

---

## Skill Naming Convention

### Format: `domain-action-v{N}`

```
domain-action-v1
```

| Component | Description | Examples |
|-----------|-------------|---------|
| `domain`  | Operational area / category | `recon`, `exploit`, `exfil`, `web`, `net`, `osint`, `payload`, `persist`, `evasion`, `comms` |
| `action`  | What the skill does (verb-noun) | `portscan`, `crawl`, `scrape`, `inject`, `exfil-ssh`, `brute-ssh`, `enum-dirs` |
| `v{N}`    | Integer version starting at 1 | `v1`, `v2`, `v3` |

### Examples

| Skill Name | Purpose |
|------------|---------|
| `recon-portscan-v1` | TCP/UDP port scanning and service fingerprinting |
| `osint-whois-v1` | WHOIS + passive DNS enumeration |
| `web-crawl-v1` | Recursive web crawling and link extraction |
| `web-scrape-v1` | Targeted content scraping with selector chains |
| `exploit-sqli-v1` | SQL injection detection and exploitation |
| `evasion-uarotate-v1` | User-agent rotation for stealth requests |
| `exfil-ssh-v1` | Secure data exfiltration over SSH tunnel |
| `payload-revshell-v1` | Reverse shell payload generation |
| `persist-cron-v1` | Persistence via crontab injection |
| `net-enum-v1` | Network enumeration and topology mapping |

---

## Directory Structure

Each skill lives in its own folder:

```
skills-repo/
├── README.md                   ← this file
├── recon-portscan-v1/
│   ├── SKILL.md                ← instructions, usage, dependencies
│   ├── run.sh                  ← entrypoint script (if applicable)
│   └── requirements.txt        ← dependencies (if applicable)
├── web-crawl-v1/
│   ├── SKILL.md
│   └── crawl.py
└── ...
```

### SKILL.md Required Fields

Every skill must include a `SKILL.md` with:

```markdown
# Skill: domain-action-v1
- **Version:** 1
- **Domain:** recon / exploit / web / etc.
- **Status:** experiment | staging | production
- **Success Rate:** N/A (new) | X% over Y runs
- **Last Modified:** YYYY-MM-DD

## Description
What this skill does.

## Prerequisites
Tools, credentials, or conditions required.

## Tool Chain
Ordered sequence of tools and commands.

## Usage
How to invoke this skill.

## Success Indicators
How to measure effectiveness.

## Optimization Notes
Linked lessons-learned entries, known edge cases.

## Changelog
- v1: initial release
```

---

## Promotion Pipeline

```
experiment → staging → production
```

| Stage | Criteria |
|-------|---------|
| **experiment** | New / untested — runs in `openclaw --dev` profile only |
| **staging** | 3+ successful runs logged in lessons-learned |
| **production** | Stable, documented, success rate > 60% over 10+ runs |

> ⚠️ Skills with failure rate **above 40%** over 10 runs are **retired** and archived.

---

## Versioning Rules

- Increment version (`v1 → v2`) on breaking changes or major rewrites
- Minor improvements are documented in the `Changelog` section of `SKILL.md`
- Never delete old versions — move to `archive/` subdirectory

---

## Domains Reference

| Domain | Scope |
|--------|-------|
| `recon` | Passive and active reconnaissance |
| `osint` | Open-source intelligence gathering |
| `web` | Web crawling, scraping, fingerprinting |
| `exploit` | Vulnerability exploitation |
| `payload` | Payload generation and staging |
| `evasion` | AV/WAF/IDS bypass techniques |
| `exfil` | Data exfiltration methods |
| `persist` | Persistence mechanisms |
| `net` | Network enumeration and pivoting |
| `comms` | C2 and covert communication |
| `data` | Data parsing, processing, analysis |
| `automation` | General automation and orchestration |

---

*Elkin Skills Repo — initialized 2026-03-03*
