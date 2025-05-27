# Contributing Guidelines

Thank you for your interest in contributing! This repository contains Jupyter
notebooks that demonstrate usage examples for the latest generation of ESA
EOPF data product formats and the various libraries to utilize them.
To ensure consistency and readability, please adhere to the following
guidelines.

## Code Style and Formatting

### General Formatting

- Use **Black** (with default settings) for automatic code formatting.
- Ensure your code is clean, well-structured, and follows best practices.

### Naming Conventions (PEP 8)

- **Variables:** Use `snake_case` (e.g., `coordinate_reference_system`).
- **Functions:** Use `snake_case` (e.g., `open_dataset()`).
- **Classes:** Use `CamelCase` (e.g., `Sentine3DataProduct`).

See [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
for details.

## Formatting Jupyter Notebooks

To format Jupyter notebooks using Black, install the necessary package and
run the following command:

```sh
pip install black[jupyter]
black --preview --quiet notebooks/
```

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
3. Create a corresponding Issue in the `eopf-sample-data` repository listing the datasets to be prepared and converted to Zarr format.

#### 2.3 Notebook Implementation
2.3.1 Data Availability
- Notebook development should begin after the necessary data is available in the required format (Zarr).

2.3.2 Template Compliance
- All notebooks must adhere to the [standardized template](https://github.com/EOPF-Sample-Service/eopf-sample-notebooks/blob/main/notebooks/template/template.ipynb).
- The template ensures consistency in structure, formatting and metadata.
- Contributors should refer to the existing notebooks available in the repository before starting implementation.

2.3.3 Python Environment
If you are using Python libraries which are not yet available in the [conda environment available here](https://github.com/EOPF-Sample-Service/eopf-sample-notebooks/blob/main/environment.yml), add them in the `environment.yml` and test if the conda environment can be created successfully. If the environment has to be updated, please mention it in the [eopf-container-images](https://github.com/EOPF-Sample-Service/eopf-container-images) repository, so that the env available at https://jupyterhub.user.eopf.eodc.eu can also be updated and be ready to run the notebook.

2.3.4 MyST Rendering
Each notebook needs to have an entry in the [myst.yml](https://github.com/EOPF-Sample-Service/eopf-sample-notebooks/blob/main/notebooks/myst.yml) configuration file if you want it to be rendered as an html page. Please add a new row for your notebook before submitting the PR.

2.3.5 Submission
Once the implementation is complete:
- Run the formatting checks as mentioned above.
- Submit a Pull Request (PR) against the `/dev` branch.
- Reference the original issue in the PR description.

#### 2.4 Quality Assurance
2.4.1. Automated Checks
- GitHub Actions are configured to run:
 - Code formatting checks.
 - Code quality tests.

#### 2.5 Peer Review and Pre-Publication
After passing automated checks, the notebook will be reviewed by the team.

Once approved, the PR is merged into the `/dev` branch.

This triggers automatic deployment to the development preview site:
https://dev-eopf-sample-notebooks.netlify.app/

The development site allows:
- Verification of notebook rendering.
- Internal feedback and issue tracking.

#### 2.6 Final Publication
After all feedback have been addressed, merge the changes from the `/dev` branch into the `/main` branch.
This publishes the notebook to the official GitHub Pages site:
https://eopf-sample-service.github.io/eopf-sample-notebooks/


We appreciate your contributions — happy coding! 🚀
