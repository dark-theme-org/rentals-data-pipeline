# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- Set repository architecture with **core folders/files**;
- Add `/cloud` folder to manage `/tasks` (as *Cloud Run Jobs* interface) and `/workflows` (as *Cloud Workflows* interface) to properly config pipelines.
- Folder `/scripts` to help deployment and local configurations;
- Create `/src/data` features to fetch and extract **properties** data and manage the ETL steps with cloud resources;
- Define `/src/entrypoints` for main scripts during task execution;
- Develop `/src/utils` with python objects to be used in multiple modules;
- Use `/terraform` as IaaC to manage cloud resources;
- Agregate `/tests` using *pytests* for Quality Assurance.

### Changed

- Adapt `.gitignore` to project needs;
- New `README.md` template for properly project introduction.

### Deprecated

### Removed

### Fixed

### Security
