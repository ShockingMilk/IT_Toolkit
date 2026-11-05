# Architecture

## Overview

The application is organized around modular responsibilities.

    main.py
        |
        v
    Application
        |
        v
    DetectionManager
        |
        +---- WindowsDetector
        |
        +---- LinuxDetector
        |
        +---- MacOSDetector
        |
        +---- PythonDetector
        |
        +---- PowerShellDetector
        |
        v
    SystemProfile
        |
        v
    CapabilityManager
        |
        v
    ReportManager

## Responsibilities

### Core

Coordinates application execution.

### Enums

Contains centralized standardized values.

### Models

Defines application data structures.

### Detectors

Collects system and runtime information.

### Managers

Coordinates detection, capability evaluation,
and reporting.

### Platform

Contains operating-system-specific implementations.

### Utils

Provides reusable generic functions.

## Switch Function

The centralized switch function routes operations
to their appropriate platform implementations.

Avoid duplicating platform-selection logic.

## SystemProfile

SystemProfile is the common contract between
detection and all future toolkit modules.

Modules should consume this object instead of
independently detecting the operating system.
