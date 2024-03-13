# PERPETUAL-SMS PROJECT
_A sponsorship management web application developed in Django_

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
    cd perpetualx/backend
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