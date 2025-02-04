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

## How to Contribute

1. Ensure your code follows the style guidelines outlined above.
2. Run all notebook cells to verify correctness before submitting.
3. Always create a **pull request**—do not push directly to the `main` branch.
4. Open a pull request with a clear description of your changes.

We appreciate your contributions — happy coding! 🚀

