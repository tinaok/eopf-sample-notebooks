[<img src="./notebooks/static/ESA_EOPF_logo_2025_COLOR_ESA_blue_reduced.png">](https://zarr.eopf.copernicus.eu/)

# EOPF Sentinel Zarr Samples - Sample Notebooks

Main project website: https://zarr.eopf.copernicus.eu/

This repository contains, in the notebooks folder, a collection of Python notebooks demonstrating the usage of the [EOPF-CPM library](https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm) and the new Sentinel data in [Zarr](https://zarr.dev) format.

Rendered version of the notebooks deployed via GitHub actions are available here: https://eopf-sample-service.github.io/eopf-sample-notebooks/

## Technical Guideline for Developing and Publishing EOPF Sample Notebooks

This document outlines the process for creating, reviewing, and publishing sample notebooks in the EOPF Sample Notebooks project. It defines responsibilities, procedures, and tools used throughout the workflow to ensure quality, consistency, and reproducibility.

### 1. Repository Overview

- **Sample Notebooks Repository (this)**:
  - https://github.com/EOPF-Sample-Service/eopf-sample-notebooks
  - Hosts all sample Jupyter notebooks developed for the EOPF Sentinel Zarr Samples project.
- **Sample Data Repository**
  - https://github.com/EOPF-Sample-Service/eopf-sample-data
  - Used for managing dataset requirements and conversions (e.g., to Zarr format).

### 2. Notebook Development Workflow
#### 2.1 Issue Creation

For each notebook to be developed, create a new GitHub Issue in the eopf-sample-notebooks repository.
The issue must include:
- A clear description of the notebook’s purpose and expected content.
- Assignment of a responsible contributor.

#### 2.2 Requirement Analysis

The assigned contributor must:

1. Analyze the content requirements.
2. Identify all required datasets.
3. Create a corresponding Issue in the eopf-sample-data repository listing the datasets to be prepared and converted to Zarr format.

#### 2.3 Notebook Implementation
2.3.1 Data Availability
- Notebook development should begin only after the necessary data is available in the required format (Zarr).

2.3.2 Template Compliance
- All notebooks must adhere to the [standardized template](https://github.com/EOPF-Sample-Service/eopf-sample-notebooks/blob/main/notebooks/template/template.ipynb).
- The template ensures consistency in structure, formatting and metadata.
- Contributors should refer to the existing notebooks available in the repository before starting implementation.

2.3.3 Submission
Once the implementation is complete:
- Submit a Pull Request (PR) against the `/dev` branch.
- Reference the original issue in the PR description.

#### 2.4 Quality Assurance
2.4.1. Automated Checks
- GitHub Actions are configured to run:
 - Code formatting checks.
 - Code quality tests.
 - Validation against the notebook template (where applicable).


#### 2.5 Peer Review and Pre-Publication

After passing automated checks, the notebook will be reviewed by the team.

Once approved, the PR is merged into the `/dev` branch.

This triggers automatic deployment to the development preview site:
https://dev-eopf-sample-notebooks.netlify.app/

The development site allows:
- Verification of notebook rendering.
- Internal feedback and issue tracking.

#### 2.6 Final Publication
After all feedback has been addressed, merge the changes from the `/dev` branch into the `/main` branch.
This publishes the notebook to the official GitHub Pages site:
https://eopf-sample-service.github.io/eopf-sample-notebooks/
