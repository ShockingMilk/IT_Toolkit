# Development Guide

## Environment

Python 3.10 or newer.

No third-party dependencies are required for Phase 1.

## Repository Rules

- Keep responsibilities separated.
- Centralize enums.
- Use models for shared data structures.
- Use managers for orchestration.
- Use the switch function for platform routing.
- Keep configuration separate from implementation.
- Keep machine-specific output outside source control.
- Write tests for new functionality.

## Adding a Detector

1. Create the detector under detectors/.
2. Return an appropriate model.
3. Register it with the DetectionManager.
4. Add or update tests.

## Adding a Platform Implementation

Create the implementation under:

    platform/<operating_system>/

Avoid embedding machine-specific values.

## Adding Configuration

Place shared configuration in:

    config/

Do not hardcode configurable requirements.
