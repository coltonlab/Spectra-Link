# 🔬 Spectra-Link

**A High-Performance Modular Dashboard for Spectroscopic Data Analysis**

Spectra-Link is a robust, Python-based graphical environment tailored for physics and materials science researchers. It provides a seamless interface to organize, process, and dynamically visualize complex spectroscopic datasets, bridging the gap between local data processing and remote laboratory network servers.

## 🚀 Download the Latest Version

You can download the latest stable release of Spectra-Link from our GitHub Releases page.

*   **Windows:** [Download Spectra-Link v1.0.0 for Windows](https://github.com/coltonlab/Spectra-Link/releases/download/v1.0.0/SpectraLink-Windows-v1.0.0.zip)
*   **macOS:** [Download Spectra-Link v1.0.0 for macOS](https://github.com/coltonlab/Spectra-Link/releases/download/v1.0.0/SpectraLink-macOS-v1.0.0.zip)

---
**Looking for older versions or release notes?** Visit the [Releases page](https://github.com/coltonlab/Spectra-Link/releases).


---

## ✨ Key Features

* **High-Speed Interactive Visualization:** Leverages `PyQtGraph` for real-time, hardware-accelerated plotting, ensuring fluid interactions even with massive spectroscopic datasets.
* **Distributed Metadata Management:** Employs a decentralized approach using local `metadata.json` files embedded directly within experiment folders. This guarantees that analysis parameters and raw data remain perfectly synchronized and highly portable.
* **Plugin-Based Processor Architecture:** Designed for modularity. Features dynamic processors tailored to specific experimental math and plotting logic (e.g., *Absorption*, *Electro-Absorption*, *Circular Dichroism*), allowing for unique treatment of different data types.
* **Seamless Remote Integration:** Native support for connecting to network shares (SMB/CIFS), enabling instantaneous transitions between local drive storage and secure lab servers without breaking workflow.
* **The Comparison Basket:** A dedicated, centralized staging area that allows researchers to select, store, and overlay datasets from entirely different experiments and sessions for rigorous comparative analysis.

## 🏗 System Architecture

Spectra-Link is built on a modern, responsive stack prioritizing both computational efficiency and user experience.

| Component | Technology | Description |
| --- | --- | --- |
| **GUI Framework** | `PyQt6` | Drives the main application window, custom widgets, sidebar navigation, and the interactive Analysis tab. |
| **Plotting Engine** | `PyQtGraph` | Handles all scientific graphing, axis manipulation, and high-performance rendering. |
| **Data Processing** | `NumPy`, `SciPy` | Provides the computational backbone for array manipulation and scientific math operations. |
| **Data Model** | `JSON` + Raw Formats | Non-destructive data handling; original files remain untouched while metadata handles state. |

## 🚀 Installation

### Prerequisites

Ensure you have Python 3.9 or higher installed on your system. Access to institutional network servers may be required to utilize remote data-fetching features.

### Setup Instructions

1. **Clone the repository**
```bash
git clone https://github.com/coltonlab/Spectra-Link.git
cd Spectra-Link

```


2. **Create a virtual environment (Recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

```


3. **Install dependencies**
```bash
pip install -r requirements.txt

```



## 💻 Usage Guide

1. **Launch the Application**
```bash
python main.py

```


2. **Establish Data Connection**
Use the built-in Connection Manager to map your workspace. You can point the application to a local directory or authenticate with a remote network server.
3. **Navigate the Experiment Tree**
Browse through your hierarchical data structure using the sidebar. Spectra-Link will automatically parse the `metadata.json` files to present clean, readable experiment details.
4. **Analyze and Compare**
Push individual runs to the **Analysis Tab** to apply experiment-specific math. Send notable results to the **Comparison Basket** to cross-examine data across multiple trials.

## 🧩 Extending the Software

Spectra-Link is built to grow alongside your research. To add support for a novel experiment type, utilize the modular processor architecture:

1. Navigate to the `/processors` directory.
2. Create a new subclass inheriting from the base processor template.
3. Override the data parsing and mathematical operation methods to suit your specific spectroscopic technique.
4. Register the new processor in the `/config/settings.py` global configuration. The GUI will automatically detect and integrate the new module.

---
