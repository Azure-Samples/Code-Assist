## Import necessary libraries
import os
import time
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import json
import re
from collections import defaultdict

## Load environment variables from .env file
load_dotenv()

## Convert the file into a class
class CodeGuard:
    def __init__(self, conn_str=None, agent_name=None):
        self.conn_str = os.getenv("CONN_STR")
        self.agent_name = os.getenv("GUARD_AGENT_NAME")
        self.code_directory = os.getenv("CODE_DIRECTORY")
        self.output_dir = os.getenv("OUTPUT_DIR")

    def initialize_client(self):
        try:
            project_client = AIProjectClient.from_connection_string(
                credential=DefaultAzureCredential(),
                conn_str=self.conn_str,
            )
            return project_client
        except Exception as e:
            print(f"❌ Error initializing client: {e}")
            return None
        
    ## Get the agent by name
    def get_agent(self, project_client, agent_name):
        try:
            agents = project_client.agents.list_agents()
            for existing_agent in agents.data:
                if existing_agent.name == agent_name:
                    return existing_agent
            print(f"❌ Agent '{agent_name}' not found.")
            return None
        except Exception as e:
            print(f"❌ Error retrieving agent: {e}")
            return None
        
    ## Create a communication thread with the agent
    def create_thread(self, project_client):
        try:
            thread = project_client.agents.create_thread()
            return thread
        except Exception as e:
            print(f"❌ Error creating thread: {e}")
            return None

    ## Function to send a message to the agent and receive a response
    def send_message_to_agent(self, message, project_client, thread):
        try:
            response = project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=message
            )
            return response
        except Exception as e:
            print(f"❌ Error sending message to agent: {e}")
            return None
    
    ## Read code from directory and print the count of each file type
    def read_code_from_directory(self, directory):
        file_types_count = defaultdict(int)
        code_files = []
        prompt_content = "*** Code Files:\n"

        try:
            for root, dirs, files in os.walk(directory):
                print(f"🔍 Searching in directory: {directory}")
                for file in files:
                    file_extension = os.path.splitext(file)[1]
                    if file_extension in ['.py', '.js', '.java', '.cpp', '.c', '.html', '.yaml']:
                        full_path = os.path.join(root, file)
                        code_files.append(os.path.join(root, file))
                        file_types_count[file_extension] += 1
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content_lines = f.readlines()

                        content_lines = "".join(
                            f"{i + 1} {line}" for i, line in enumerate(content_lines)
                        )
                        prompt_content += (
                            f"** File Name: {file}\n"
                            f"** File Path: {full_path}\n"
                            f"** Content:\n{content_lines}\n\n"
                        )     
            print(f"✅ Found {len(code_files)} code files.")
            for file_type, count in file_types_count.items():
                print(f"File type '{file_type}': {count} files")
        except Exception as e:
            print(f"❌ Error reading code from directory: {e}")
        return prompt_content

    def run(self):
        project_client = self.initialize_client()
        agent = self.get_agent(project_client, self.agent_name)
        thread = self.create_thread(project_client)
        code_content = self.read_code_from_directory(self.code_directory)

        ## Create a user message
        agent_prompt = f"""You are CodeGuard, an AI agent performing a code review focused on detecting:

        - Potential data leaks
        - Security issues involving external service/API calls or packages that you are aware of using an external calls.
        - Exposure of connection strings or credentials

        ✅ Allowed services:
        - Any Azure service
        - Any locally deployed endpoint

        ❌ Disallowed services:
        - Any external API or service that is not in the allowed services list.
        - Any service that is not part of the Azure ecosystem.

        Your tasks:
        1. Scan the provided code files accurately.
        2. Identify potential data leaks, exposed/hard coded credentials, or unauthorized external connections.
        3. For each issue found:
        - Write a clear description of the issue on a high level.
        - Identify the API/service/Package used, give a brief description about its host/source/company name and what it does.
        - Identify the inputs and outputs to that service if applicable - else None -, such as what data being sent to it (Infer it from var names, any code documentation or from the form of the usage).
        - Categorize the type of data being sent to the service (e.g., PII, sensitive data, Microsoft confedential, etc.).
        - Pinpoint the issue's location as follows:
            - file name
            - full path
            - Specific line number where the service call or connection string exposure occurs.
        - Provide a recommended resolution in a structured format.
        4. Return your findings as a **valid JSON object**, in the following strict JSON format:

        {{
        "issues": [
            {{
            "description": "<description of the issue>",
            "inputs": "<inputs to the service>",
            "outputs": "<outputs from the service>",
            "data_type": "<type of data being sent>",
            "file_name": "<name of the file>",
            "file_path": "<full path to the file>",
            "line_number": "<line number>",
            "service_name": "<name of the service>",
            "service_brief": "<brief description of the service>"
            "resolution": "<recommended resolution>"
            }}
            // more issues...
        ]
        }}


        Code to review: 
        {code_content} 

        ⚠️ Important:
        - Scan the full codebase for potential issues, and concise identification of the issues
        - Only include services that are not allowed when identifying issues.
        - Reply only in the JSON format. Do not include any additional text or explanation.

        Your JSON Response Here:
        """

        ## Send the message to the agent
        try:
            project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=agent_prompt
            )
            print("✅ Message sent.")
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None

        try:
            run = project_client.agents.create_and_process_run(
                thread_id=thread.id,
                agent_id=agent.id
            )
            print("✅ Agent run started.")
        except Exception as e:
            print(f"❌ Error processing run: {e}")
            return None

        time.sleep(0.5)

        ## Retrieve the agent's response
        try:
            response = project_client.agents.list_messages(thread_id=thread.id)
            print("✅ Messages retrieved.")
        except Exception as e:
            print(f"❌ Error retrieving or saving messages: {e}")
            return None

        ## Check if the response is in the expected JSON format
        try:
            if hasattr(response, "data") and response.data:
                sorted_messages = sorted(response.data, key=lambda x: x.created_at)
                full_response = ""

                for msg in sorted_messages:
                    if msg.content and isinstance(msg.content, list):
                        for content_item in msg.content:
                            if content_item["type"] == "text":
                                full_response += content_item["text"]["value"] + "\n"

                print("✅ Full response constructed.")

                ## Extract the JSON block using regex to ensure we catch a proper JSON object
                try:
                    json_response = json.loads(full_response)
                    print(json.dumps(json_response))
                except json.JSONDecodeError:
                    json_block_match = re.search(r"```json\s*(\{.*?\})\s*```", full_response, re.DOTALL)
                    if json_block_match:
                        json_response = json.loads(json_block_match.group(1))  # Use the captured group, not the full match
                        print(json.dumps(json_response))
                    else:
                        json_response = json.loads(full_response[full_response.lower().find("your json response here:")+len("your json response here:"):].strip())
                        print(json.dumps(json_response))

                ## write a json file with the response
                output_file = os.path.join(self.output_dir, "risks.json") if self.output_dir else "risks.json"
                with open(output_file, "w") as json_file:
                    json.dump(json_response, json_file, indent=2)
                    print(f"✅ JSON response saved to {output_file}.")
                
                return json_response
                
        except Exception as e:
            print(f"❌ Error processing messages: {e}")
            return None
