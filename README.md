# Sponsorship & Donor Management Software (SDMS)
_A sponsorship Management Information System developed in Django_
<br />
Perpetual-X is a simple yet powerfull tool, built with django which is a Python-based free and open-source web framework that follows the model–template–views architectural pattern.

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
    ```
- Start Django server
  ```bash
   python manage.py runserver
    ```
- Django backend server will start on http://localhost:8000/
