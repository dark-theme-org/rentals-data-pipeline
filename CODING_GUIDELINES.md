# Coding Guidelines

Contributions to this project are encouraged since we know that different developers will enrich our codebases :punch:. However, absorbing all contributions as-is might lead to difficulties in the maintenance of the codebase that is left unchecked. Collaborative codebases often establish guidelines for contributors to ensure that code remains maintainable over time.

The purpose of this guide is to *SET A STANDARD FOR CONTRIBUTIONS*! These guidelines are not intended to limit the tools at your disposal nor to rewire the way you think, but rather to encourage better practices.

## :earth_americas: Language

We use *ENGLISH* as the main language. Things like source code, comments, documentation, commit messages, review comments and any other kind of contribution *MUST BE WRITTEN IN ENGLISH*. We do this in order to be consistent throughout the project and to be considerate with devs that don't speak the same native language.

## :arrow_right_hook: Branches

After the prefix, the slug must be *AT MOST THREE SEGMENTS LONG, all **LOWERCASE LETTERS AND DIGITS**, **HYPHEN-SEPARATED*** (e.g. `feature/add-scraper`, `fix/null-pointer`, `release/1-2-0`). This convention is enforced by CI on every pull request.

### Allowed prefixes

| Prefix | When to use | Example |
| ------ | ----------- | ------- |
| `feature/*` | New functionality that did not exist before | `feature/add-zillow-scraper` |
| `enhancement/*` | Improvement to existing functionality | `enhancement/faster-dedup` |
| `fix/*` | Patch for unwanted or broken behavior | `fix/null-price-crash` |
| `refactor/*` | Code restructuring with no behavior change | `refactor/bronze-loader` |
| `hotfix/*` | Urgent patch for a production issue | `hotfix/auth-token-leak` |
| `release/*` | Release preparation (version bump, changelog) | `release/v1-2-0` |
| `backport/*` | **Auto-generated only** — do not create manually; opened by CI to sync `main` back into `develop` after each merge | `backport/2026-06-04-16-30-00` |

### Target-branch rules

The allowed prefixes depend on which branch you are merging into:

* **→ `develop`**: all six prefixes above are allowed;
* **→ `main`**: only `hotfix/*` and `release/*` — direct feature or fix work must go through `develop` first.

## :gem: Code Quality

The goal of our rules is to manage the complexity of our development environment, keeping the codebase manageable while still allowing developers to work productively. On a general basis, we use code quality guides to keep the style of our projects aligned. When we need something more customized, we add quality rules to our [.pre-commit-config.yaml](.pre-commit-config.yaml) file.

## :speech_balloon: Comments

Code comments are hard to write, not because the words are difficult to produce but because it is hard to make relevant comments. Too much of it and people won't read them (not to mention that it obfuscates code reading). Too little of it leaves you with the single option of reading large portions of the codebase to get an insight as to what a feature or code block is doing. Both situations are undesirable and efforts should be made at all times to have a pleasant comment-reading experience. As a general rule you would have to comment on decisions you made while coding that are not part of any specification.

* *When you SHOULD comment:*

  * Departs from common wisdom or convention (The why's are necessary);
  * Takes a significant amount of time to produce. A good rule of thumb here is that if you spent more than 1 hour thinking about how to produce a fragment of code that took 2 minutes to write, you should document your thinking to aid the reader and allow for validation;
  * Needs to preserve properties of the implementation. This is the case of performance-sensitive portions of the codebase, coroutines synchronization, implementations of security primitives, congestion control algorithms, etc.

* *When you SHOULD NOT comment:*

  * On structure of programs that are already part of a convention, specified or otherwise;
  * Having pedantic explanations of behavior that can be found by immediate examination of the surrounding code artifacts;
  * Behaviors you can not attest to.

## :octocat: Commits

In all commits, remember to use one of the prefixes defined in our `.pre-commit-config.yaml` (`analysis`, `change`, `feature`, `fix`, `refactor`, `test`) with a *CLEAR MESSAGE* about the proposed changes. Commits such as "fix: tests", "feature: etl" and many other common messages we find usually in code *WON'T BE ACCEPTED*. These rules will be enforced on external contributions, though we may consider accepting contributions with small deviations from what's stated here.

## :information_source: CHANGELOG

In each version of a project please remember to *honour* the following [KEEP A CHANGELOG](https://keepachangelog.com/en) guideline:

1. Changelogs are for humans :busts_in_silhouette:, not machines :robot:;
2. There should be an entry for *EVERY SINGLE VERSION*;
3. The same *types of changes* should be grouped;
4. Versions and sections should be linkable.
5. The *LATEST VERSION* should come first.
6. The release date of each version is displayed in the format YYYY-MM-DD.

### Types of change

* Added: For new features or improvement of existed ones;
* Changed: Significant changes in existing functionality;
* Deprecated: For features marked for removal in a future release;
* Removed: When features are erased;
* Fixed: For any bug fixes;
* Security: In case of vulnerabilities.

## :robot: AI Code Assistant

This project uses [Claude Code](https://claude.com/claude-code) as its AI code assistant. Project-specific context — architecture, version pins, conventions, and intentional dependency ceilings — lives in [CLAUDE.md](CLAUDE.md), which Claude loads automatically at the start of every session. Custom workflows are defined as skills in `.claude/skills/` and invoked with `/skill-name` (e.g. `/setup`).

AI-generated contributions are held to the same rules as human ones:

* :mag: Review AI-generated changes the same way you would review a human contributor's work;
* :hammer_and_wrench: AI-generated commits *MUST* follow the prefix conventions defined above and pass every hook in [.pre-commit-config.yaml](.pre-commit-config.yaml);
* :file_folder: Per-contributor Claude settings live in `.claude/settings.local.json` (gitignored); the shared `.claude/settings.json` holds project-wide configuration.
