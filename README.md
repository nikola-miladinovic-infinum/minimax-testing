# Streamlit App

## Prerequisites
- **Python 3.10+** must be installed on your system.

## Setup & Installation

1. **Install dependencies:**
   Navigate to the project directory and run the following command to install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Create a new file named `.env` in the root directory. You can use the provided example file as a template:
   ```bash
   cp .env.example .env
   ```
   *Make sure to open the `.env` file and fill in all the required keys.*

## Running the Application

Once your environment is set up and dependencies are installed, you can start the application by running:

```bash
streamlit run app.py
```