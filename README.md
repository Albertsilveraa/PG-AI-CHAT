# PGAI-CHAT
About System Based on AI Agents for the Transformation of procedural language and Insertion SQL Queries into Natural language through local connections. Remotes coming soon


## Description

PGAI-CHAT is a virtual assistant that converts natural language questions into SQL queries, PL/pgSQL procedures, and function calls for a PostgreSQL database. This system is designed to interact with a PostgreSQL database easily and efficiently, using the OpenAI API to process natural language and generate the corresponding queries.

## Requirements

1. **Python 3.7+**
2. **Python Libraries**:
   - `psycopg2`: for interacting with PostgreSQL.
   - `dotenv`: for loading environment variables from a `.env` file.
   - `langchain`: for OpenAI integration and natural language processing.
3. **PostgreSQL**: a running PostgreSQL database.
4. **OpenAI API**: API key for using OpenAI's language model.

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/Albertsilveraa/nsertGen-JSON-to-SQL-Insert-Generato.git
   cd sqlbot
Create a virtual environment (optional but recommended):

 ```bash

python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
Install the dependencies:
 ```


 ```bash

pip install -r requirements.txt
Create a .env file in the root of the project with the following environment variables:

init

OPENAI_API_KEY=your_openai_api_key

DB_NAME=your_database_name

DB_USER=your_database_user

DB_PASSWORD=your_database_password

DB_HOST=localhost  # Or your server's address

DB_PORT=5432       # Or the appropriate port

Usage
Make sure your PostgreSQL database is running.

Run the main script:

```

python main.py
Interact with the SQLBot assistant. You can ask questions in natural language related to your database, such as:

"Show all users with age greater than 30"
"Insert a new user with name X, email Y, and age Z"
"Describe the users table"
"Create an addresses table related to users"
"Create a function to calculate the average age of users"
"Call the function calculate_average_age"
To end the session, simply type exit.

Features
SQL Query Generation: The bot can generate standard SQL queries, PL/pgSQL statements, and function calls.
Natural Language Interaction: You can interact with the bot in natural language and get direct answers related to your database.
Table and Function Creation: If needed, the bot can generate SQL to create tables or functions in the database.
Example of Use
vbnet

Hello! I am SQLBOT, your assistant connected to the database with conversation memory.
You can ask me natural language questions related to the database, for example:
  - 'Show all users with age greater than 30'
  - 'Insert a new user with name X, email Y, and age Z'
  - 'Describe the users table'
  - 'Create an addresses table related to users'
  - 'Create a function to calculate the average age of users'
  - 'Call the function calculate_average_age'

If you want to exit, type 'exit'.
Example Interaction
User: "Show all users with age greater than 30"

SQLBot: Generates the corresponding SQL query and displays the results.

Contributions
If you'd like to improve this project, you can contribute by opening a pull request or creating an issue to discuss new ideas or problems.

License
This project is licensed under the MIT License. See the LICENSE file for more details.
