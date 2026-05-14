# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased] - 2026-05-09

### Added

- Set repository architecture with **core folders/files**;
- Create `/data/scrapers` features to fetch and extract **properties** data;
- Define `/entrypoints` for main scripts during task execution;
- Creating `/utils` python objects to be used in multiple modules;
- Use `/terraform` as IaaC to manage cloud resources;
- Add `/cloud` folder to manage `/tasks` (as *Cloud Run Jobs* interface) and `/workflows` (as *Cloud Workflows* interface) to properly config dags and pipelines.

### Changed

- Adapt `.gitignore` to project needs;
- New `README.md` template for properly project introduction.

### Deprecated

### Removed

### Fixed

### Security
