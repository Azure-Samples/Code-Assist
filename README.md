# Code Assist - The Multi-Agent Code Assistant Tool

## Overview
Code Assist is a multi-agent tool that allows the user to analyze large code bases quickly and extract useful information quickly, generating useful documents on the go. Currently it support:
- Code documentation generation (technical and business documentation) in `.md` and `.docx` formats
- PPT Slides generation based on the business documentation
- Code risk analysis to flag potential security issues early on

## Usage
### Prerequisites
To use the tool follow these steps:

1. Make sure you have Python (3.12.x) installed on your system
2. Login using `az login` and select the subscription on which your AI Foundry project is hosted
3. *(Optional)* Create a virtual environment and activate it 
    - `python -m venv env-name` 
    - `.\env-name\Scripts\Activate.ps1`

4. Install the required packages: 
    - `pip install -r requirements.txt`

5. Update `.env` file (see section below)
6. Run "Agent.py" file: 
    - `python Agent.py`

### Environment variables
You need to set some environment variables in the `.env` file first, as follows:

- `CONN_STR`: AI Foundry Agent Service project connection string (agents will be created automatically)
- `CODE_DIRECTORY`: Path to the codebase directory
- `OUTPUT_DIR`: Path to output diretory in which documents will be generated
- `PPT_OUTPUT_PATH`: Name of the generated `.pptx` file
- `MODEL_ID`: Model ID as found in your AOAI service connected to your AI Agent Service *(Note: agents seemed to not support all reasoning models, but it definitely works for GPT-4o)*

**Note:** Code sample is copied from [Eleuther AI LLM Evaluation Tool](xx)

All other values should be left unchanged.
