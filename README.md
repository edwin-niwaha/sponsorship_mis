# Project Name
# Sponsorship & Donor Management Software (SDMS)

[![Coverage Status](https://codecov.io/gh/edwin-niwaha/sponsorship_mis/branch/main/graph/badge.svg)](https://codecov.io/gh/edwin-niwaha/sponsorship_mis)

[![codecov](https://codecov.io/gh/edwin-niwaha/sponsorship_mis/graph/badge.svg?token=S0TZOCC74E)](https://codecov.io/gh/edwin-niwaha/sponsorship_mis)


SDMS is a simple yet powerfull tool, built with django which is a Python-based free and open-source web framework that follows the model–template–views architectural pattern.

## Requirements
Make sure you have python and Node js installed on your system:
- [Python version 3.9.13](https://www.python.org/downloads/release/python-3913/) 
- [Node version 16.7.1](https://nodejs.org/en/download/)

## Note Create a new application inside apps folder
cd backend
- django-admin startapp my_new_app

## Project Setup

- Clone the repository in a local folder
```bash
    git clone https://github.com/edwin-niwaha
    ```
- Open terminal and verify python version
  ```bash
    python --version
    ```
- Verify if node and npm are installed
  ```bash
    node --version
    npm -version
    ```
## Setup Backend
- Nvaigate to cloned project directory
  ```bash
    cd spsonsorship-mis/backend
    ```
- Create a python virtual environment for backend
  ```bash
    $ python -m venv .venv
    ```
- Activate the virtual environment
  ```bash
  # For winodws
    source .venv/Scripts/activate
    
  # For linux
    source .venv/bin/activate
    ```
- Install python libraries
  ```bash
   cd backend
   pip install -r requirements.txt
   pip freeze > requirements.txt
    ```
- Start Django server
  ```bash
   python manage.py runserver
    ```
- Django backend server will start on http://localhost:8000/
```

## TSTING THE WEB APP
- pip install coverage


##  Running Tests
a) Running All Tests
You can run all tests in your project with the following command:
- python manage.py test
* This command discovers and runs tests from all apps listed in INSTALLED_APPS, including those in tests directories.

b) Running Tests from a Specific App
- python manage.py test app_name
For example:
- python manage.py test child
This command runs tests specifically in the apps/child/tests/ directory.

c) Running Tests from a Specific File
- python manage.py test app_name.tests.test_file
For example:
- python manage.py test child.tests.test_models

# Run Coverage on a Specific Module
coverage run --source='apps.child.models' manage.py test
coverage run --source='apps' manage.py test

# Generate Coverage Report
coverage report

# Generate HML Report
- coverage html

# Generate XML Report
- coverage xml
