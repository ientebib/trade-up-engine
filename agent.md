# AI Agent Briefing (`agents.md`)

This document provides essential context and instructions for AI coding assistants working on the Trade-up Engine project. Adhering to these guidelines will ensure generated code is consistent, correct, and aligned with project standards.

## 1. Project Overview

- **Purpose**: The Trade-Up Engine is a FastAPI-based web application that calculates optimal vehicle trade-up offers for customers. It includes a user interface for running simulations, configuring engine parameters, and viewing results.
- **Modes**: The application has two primary execution modes:
    - **Development (`dev`)**: Uses mock data from local CSV files (`customer_data.csv`, etc.) and is intended for local testing and development.
    - **Production (`prod`)**: Connects to a live Redshift database to pull real customer and inventory data.

## 2. Core Technologies

- **Backend**: Python 3.12 with FastAPI
- **Frontend**: Standard HTML5, CSS3, and modern vanilla JavaScript (ES6+). No complex frameworks are used.
- **Data Handling**: Pandas is used extensively for data manipulation.
- **Configuration**: Engine parameters are managed through `engine_config.json`.
- **Dependencies**: Key libraries are listed in `requirements.txt`.

## 3. How to Run the Application

Refer to the `EXECUTION_GUIDE.md` for full details.

- **Setup (First time only)**:
  ```bash
  ./run_local.sh setup
  ```
- **Run Development Server**:
  ```bash
  # This is the default
  ./run_local.sh
  ```
- **Run Production Server**:
  ```bash
  ./run_local.sh prod
  ```
The server will be available at `http://localhost:8000`.

## 4. Key Files & Architecture

- `main.py`: Entry point for the **production** application.
- `main_dev.py`: Entry point for the **development** application.
- `run_local.sh`: The master script for setting up and running the server in different modes.
- `core/`: Contains the main business logic.
    - `core/engine.py`: The heart of the offer calculation logic. This is where the multi-phase offer generation and range optimization happens.
    - `core/calculator.py`: Contains financial calculations (NPV, payments, etc.).
    - `core/config_manager.py`: Handles loading and saving `engine_config.json`.
    - `core/data_loader.py`: Handles data loading from Redshift (production).
    - `core/data_loader_dev.py`: Handles data loading from CSVs (development).
- `app/`: Contains the FastAPI web application.
    - `app/api/routes.py`: Defines all API endpoints (`/api/...`).
    - `app/templates/`: Jinja2 HTML templates for the frontend.
    - `app/static/`: CSS and JavaScript files.
        - `app/static/js/main.js`: Contains all frontend JavaScript logic for user interactions.

## 5. Agent Instructions & Conventions

- **Style**: Follow PEP 8 for Python. Use modern JavaScript (const/let, arrow functions, async/await).
- **Clarity over cleverness**: Write straightforward, readable code.
- **Error Handling**: Be proactive in adding error handling and logging.
- **Endpoint Creation**: When adding new features, first define the backend API endpoint in `app/api/routes.py`, then implement the corresponding frontend `fetch` call in `app/static/js/main.js`.
- **Testing**: When asked to create tests, place the test file in the same directory as the module being tested and use the `_test.py` suffix (e.g., `core/engine_test.py`).

## 6. Example Task Prompts

Here are examples of well-defined tasks for this project:

1.  **Performance Optimization**: "The 'Range Optimization' in `core/engine.py` is slow. Refactor it from a brute-force grid search to use a more efficient algorithm like Bayesian Optimization or a gradient-based method to find the optimal parameters (`service_fee`, `cxa_pct`, `cac_bonus`) faster."
2.  **Bug Fix & Refactor**: "The configuration is reloaded from `engine_config.json` on almost every API call, causing excessive I/O. Refactor the application to use a centralized, in-memory configuration singleton that is loaded once at startup. Ensure the `/api/save-config` endpoint correctly updates this singleton and persists it to disk."
3.  **New Feature**: "Implement a persistent caching layer using a lightweight, file-based solution like `diskcache` or a simple SQLite database to store the results of `generate_offers`. The cache key should be based on the customer ID and the engine configuration. Add a 'Clear Cache' button to the UI."
4.  **Code Quality & Testing**: "The `core/calculator.py` module lacks sufficient test coverage. Analyze the functions within it and write a comprehensive suite of unit tests using Pytest. Place them in `core/calculator_test.py` and ensure edge cases are covered."
5.  **Data Strategy**: "The production data loader in `core/data_loader.py` fetches all data from Redshift every time. Modify it to use a more efficient, incremental loading strategy. Use timestamps or a versioning column in Redshift to only fetch new or updated records since the last run."