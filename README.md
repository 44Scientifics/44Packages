<!-- filepath: /Users/checomart/Dropbox/GitHub/Python Libraries/44Packages/README.md -->
# FortyFour

This package puts together all the tools I have created.

## Description

`FortyFour` is a Python library containing reusable code modules for various tasks, including Finance, Geospace, and general utilities.

## Installation

To install the package, you can clone the repository and install it using pip:

```bash
git clone https://github.com/44Scientifics/44Packages.git
cd 44Packages
pip install .
```

Alternatively, if the package is hosted on PyPI, you might be able to install it directly:
```bash
pip install FortyFour
```
(Please verify if the package is available on PyPI and update this instruction accordingly.)

## Modules

The package is organized into the following main modules:

*   **`FortyFour.Finance`**: Contains tools and utilities related to financial analysis.
    *   `company.py`: Likely contains classes/functions for company-related financial data.
    *   `company_v3.py`: Potentially a newer version or extension of `company.py`.
    *   `etf.py`: Tools for working with Exchange Traded Funds.
    *   `utils.py`: Utility functions specific to the Finance module.
*   **`FortyFour.Geospace`**: Includes tools for geospatial data and operations.
    *   `utils.py`: Utility functions specific to the Geospace module.
*   **`FortyFour.Utils`**: Provides general utility functions.
    *   `aws.py`: Helper functions for interacting with AWS services.
    *   `colors.py`: Utilities for color manipulation or colored terminal output.
    *   `helpers.py`: General helper functions.

## Dependencies

The main dependencies for this project are listed in `requirements.txt` and include:

```
boto3==1.38.23
botocore==1.38.23
certifi==2025.4.26
charset-normalizer==3.4.2
colorclass==2.2.2
docopt==0.6.2
idna==3.10
jmespath==1.0.1
narwhals==1.40.0
numpy==2.2.6
packaging==25.0
pandas==2.2.3
pip-upgrader==1.4.15
plotly==6.1.1
python-dateutil==2.9.0.post0
pytz==2025.2
requests==2.32.3
s3transfer==0.13.0
setuptools==80.8.0
six==1.17.0
terminaltables==3.1.10
tzdata==2025.2
urllib3==2.4.0
```

## Author

44 SCIENTIFICS LTD (44scientifics@gmail.com)

## Repository

[https://github.com/44Scientifics/44Packages.git](https://github.com/44Scientifics/44Packages.git)

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have suggestions or find bugs.

## License

Please specify a license for your project (e.g., MIT, Apache 2.0). You can add a `LICENSE` file to your repository and update this section.
