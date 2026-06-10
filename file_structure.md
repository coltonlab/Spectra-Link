# Spectra-Link Dependency Tree

This document outlines the architectural hierarchy of the Spectra-Link application, starting from the entry point and tracing how modules are imported and utilized across the system.

```text
main.py (Application Entry Point)
├── ui/sidebar.py (Navigation & Connection)
│   ├── utils/project_manager.py (Session & JSON Management)
│   ├── utils/network_service.py (SMB/Network Scanning)
│   ├── utils/app_logger.py (Global Logging)
│   ├── utils/validators.py (Input Validation)
│   ├── ui/theme.py (Theme State)
│   ├── ui/toggle_switch.py
│   └── ui/dialogs.py
├── ui/discovery_tab.py (Data Mapping & Selection)
│   ├── utils/discovery_data_mapper.py (UI <-> JSON Synchronization)
│   │   ├── utils/project_manager.py
│   │   └── config/techniques.py (Experiment Configurations)
│   ├── utils/project_manager.py
│   ├── utils/app_logger.py
│   ├── ui/theme.py
│   └── config/techniques.py
├── ui/analysis_tab.py (Interactive Processing)
│   ├── processors/factory.py (Dynamic Processor Loading)
│   │   └── processors/abs_processor.py (Specific Math Logic)
│   │       ├── processors/base_processor.py
│   │       ├── processors/public/read_colton_files.py (Data Parsing)
│   │       │   └── processors/public/colton_math_functions.py (Scientific Math)
│   │       └── utils/project_manager.py
│   └── ui/analysis_settings_panel.py
├── ui/modeling_tab.py (Advanced Data Modeling Orchestrator)
│   ├── ui/modeling_settings_panel.py (Floating Parameter Window)
│   └── modeling_engines/factory.py (Plugin Loader)
│       ├── modeling_engines/base_engine.py (Plugin Interface)
│       └── modeling_engines/fk_engine.py (Franz-Keldysh Implementation)
├── ui/comparison_tab.py (Data Staging & Overlay)
│   ├── ui/comparison_settings_panel.py
│   ├── processors/factory.py
│   ├── utils/project_manager.py
│   └── utils/app_logger.py
├── utils/app_logger.py (Global Logging Service)
├── ui/theme.py (Shared Styling)
└── ui/stylesheets.py (QSS Generation)
```

*Generated to assist in understanding the modular architecture of Spectra-Link.*