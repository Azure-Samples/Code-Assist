import os
import time
import logging
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Union
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, MessageAttachment, FilePurpose, CodeInterpreterTool
from azure.identity import DefaultAzureCredential


class PPTGenerator:
    """
    A class to generate PowerPoint presentations from documentation files using Azure AI Projects.
    This class encapsulates all the functionality needed to create slides from documentation.
    """

    def __init__(
        self,
        ppt_agent_name: str = "PPTSlidesAgent2",
        code_agent_name: str = "CodeRunner",
        credential=None,
        logger=None,
        env_file: Optional[str] = None,
    ):
        """
        Initialize the PPT Generator with configuration settings.
        
        Args:
            connection_string: Azure AI Projects connection string
            ppt_agent_name: Name of the PowerPoint generation agent
            code_agent_name: Name of the code execution agent
            model: AI model to use (e.g., gpt-4o)
            credential: Azure credential object, defaults to DefaultAzureCredential
            logger: Optional logger, defaults to basic logging configuration
        """
        # Load environment variables if env_file is provided
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)

        self.conn_str = os.environ['CONN_STR']
        self.model = os.environ['MODEL_ID']
        self.ppt_agent_name = ppt_agent_name
        self.code_agent_name = code_agent_name
        self.credential = credential or DefaultAzureCredential()
        
        # Set up logging
        self.logger = logger or self._setup_logger()
        
        # Initialize client and other properties to None
        self.project_client = None
        self.ppt_agent = None
        self.code_agent = None
        self.thread = None

    def _setup_logger(self) -> logging.Logger:
        """Set up and configure a logger for the class."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def initialize_client(self) -> bool:
        """
        Initialize the Azure AI Project client.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.project_client = AIProjectClient.from_connection_string(
                credential=self.credential,
                conn_str=self.conn_str,
            )
            self.logger.info("✅ Client initialized successfully.")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error initializing client: {e}")
            return False

    def initialize_ppt_agent(self) -> bool:
        """
        Initialize or retrieve the PowerPoint generation agent.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to find the agent by name
            agents = self.project_client.agents.list_agents()
            for existing_agent in agents.data:
                if existing_agent.name == self.ppt_agent_name:
                    self.ppt_agent = existing_agent
                    self.logger.info(f"✅ Agent found: {self.ppt_agent.name}")
                    return True

            # If not found, create a new agent
            vector_store = self.project_client.agents.create_vector_store(name="md_vectorstore")
            self.logger.info(f"Created vector store, vector store ID: {vector_store.id}")

            file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
            self.ppt_agent = self.project_client.agents.create_agent(
                model=self.model,
                name=self.ppt_agent_name,
                description="An agent that transforms documentation into PowerPoint slides.",
                instructions="You are an AI agent that analyzes documentation and creates PowerPoint slides. \
                            The provided document is the business logic of the project. \
                            Your task is to summarize its content and generate a slide deck.",
                tools=file_search_tool.definitions,
                tool_resources=file_search_tool.resources,
            )
            self.logger.info(f"✅ Agent created: {self.ppt_agent.name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error checking/creating PPT agent: {e}")
            return False

    def initialize_code_agent(self) -> bool:
        """
        Initialize or retrieve the code execution agent.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to find the agent by name
            agents = self.project_client.agents.list_agents()
            for existing_agent in agents.data:
                if existing_agent.name == self.code_agent_name:
                    self.code_agent = existing_agent
                    self.logger.info(f"✅ Agent found: {self.code_agent.name}")
                    return True

            # If not found, create a new agent
            code_interpreter = CodeInterpreterTool()
            self.code_agent = self.project_client.agents.create_agent(
                model=self.model,
                name=self.code_agent_name,
                description="An agent that executes code generated.",
                instructions="You are an AI agent that executes code and stores the output files as required.",
                tools=code_interpreter.definitions,
                tool_resources=code_interpreter.resources,
            )
            self.logger.info(f"✅ Agent created: {self.code_agent.name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error checking/creating code agent: {e}")
            return False

    def create_thread(self) -> bool:
        """
        Create a communication thread for the agents.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.thread = self.project_client.agents.create_thread()
            self.logger.info("✅ Thread created.")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error creating thread: {e}")
            return False

    def generate_code_summary(self, code_dir: str) -> str:
        """
        Generate a summary of code files in a directory.
        
        Args:
            code_dir: Directory containing code files
            
        Returns:
            str: Formatted summary of code files
        """
        code_summary = ""
        for root, dirs, files in os.walk(code_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith((".py", ".md", ".txt")) or file in ("Dockerfile", ".env.example"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            relative_path = os.path.relpath(file_path, code_dir)
                            code_summary += f"\n\n### File: {relative_path}\n```{file.split('.')[-1]}\n{content}\n```\n"
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to read {file_path}: {e}")
        return code_summary

    def run_ppt_generation(
        self, 
        input_file: str, 
        code_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the PowerPoint generation process using the PPT agent.
        
        Args:
            input_file: Path to the input documentation file
            code_dir: Optional path to code directory to include in generation
            
        Returns:
            dict: Agent response messages
        """
        # Upload the input file
        message_file = self.project_client.agents.upload_file_and_poll(
            file_path=input_file, 
            purpose=FilePurpose.AGENTS
        )
        self.logger.info(f"Uploaded file, file ID: {message_file.id}")
        attachment = MessageAttachment(file_id=message_file.id, tools=FileSearchTool().definitions)

        # Create the content prompt
        if code_dir:
            code_summary = self.generate_code_summary(code_dir)
            content = f"""You are provided with the content of a markdown file in the file {input_file}. You are also provided with code files from the same project.
            Generate a powerpoint slide deck based on those files and store it in .pptx format.
            Generate a Python script that creates this slide deck using the python-pptx library.
            Use font size no bigger than 20 for the slide content. Titles can have bigger font.
            Add customization to parts of text, for example, if you have points that are in bold (between ** in the content), generate them as bold font in the slide. Make sure to remove the asterisks (**) in the slides.
            Use a professional theme with blue palette for the slides.

            Follow these steps:
            1. Generate a structure of the content of the slides based on the provided files. Be descriptive and include all the important points.
            2. Generate a markdown file based on the structure you created.
            3. Convert the markdown file into a PowerPoint slide deck using the python-pptx library.
            4. In the code make sure to save the pptx file in the end.

            Summary of the code files: 
            {code_summary}
            """
        else:
            content = f"""You are provided with the content of a markdown file in the file {input_file}.
            Generate a powerpoint slide deck based on that file and store it in .pptx format.
            Generate a Python script that creates this slide deck using the python-pptx library.
            Use font size no bigger than 20 for the slide content. Titles can have bigger font.
            Add customization to parts of text, for example, if you have points that are in bold (between ** in the content), generate them as bold font in the slide. Make sure to remove the asterisks (**) in the slides.
            Use a professional theme with blue palette for the slides.

            Follow these steps:
            1. Generate a structure of the content of the slides based on the provided file. Be descriptive and include all the important points.
            2. Generate a markdown file based on the structure you created.
            3. Convert the markdown file into a PowerPoint slide deck using the python-pptx library.
            4. In the code make sure to save the pptx file in the end.
            """

        # Create and process the message
        message = self.project_client.agents.create_message(
            thread_id=self.thread.id,
            role="user",
            content=content,
            attachments=[attachment]
        )
        self.logger.info(f"Created message, message ID: {message.id}")

        # Run the PPT generation agent
        run = self.project_client.agents.create_and_process_run(
            thread_id=self.thread.id, 
            agent_id=self.ppt_agent.id
        )
        self.logger.info(f"Created run, run ID: {run.id}")

        # Get the messages from the run
        messages = self.project_client.agents.list_messages(
            thread_id=self.thread.id, 
            run_id=run.id
        )
        return messages

    def run_code_execution(self, ppt_agent_messages: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run code execution using the code agent on the PPT agent's output.
        
        Args:
            ppt_agent_messages: Messages from the PPT agent
            
        Returns:
            dict: Agent response messages
        """
        # Create the message to execute the code
        message2 = self.project_client.agents.create_message(
            thread_id=self.thread.id,
            role="user",
            content="You are provided with the output of the previous PPT slides agent. Extract the code from their response and execute it, then store the output files in the thread. If the file name is not given, use as you see appropriate.\n\n###Content:\n" + ppt_agent_messages['data'][0]['content'][0]['text']['value'],
        )
        self.logger.info(f"Created message, message ID: {message2.id}")

        # Run the code execution agent
        run2 = self.project_client.agents.create_and_process_run(
            thread_id=self.thread.id, 
            agent_id=self.code_agent.id
        )
        self.logger.info(f"Run finished with status: {run2.status}")

        # Get the messages from the code agent
        messages2 = self.project_client.agents.list_messages(thread_id=self.thread.id)
        return messages2

    def save_presentation(self, code_agent_messages: Dict[str, Any], output_file: str, output_dir: str) -> bool:
        """
        Save the generated presentation to a file.
        
        Args:
            code_agent_messages: Messages from the code agent
            output_file: Path to save the generated presentation
            
        Returns:
            bool: True if successful, False otherwise
        """
        if os.path.exists(output_file):
            os.remove(output_file)
            self.logger.info(f"Removed existing file: {output_file}")

        try:
            self.project_client.agents.save_file(
                file_id=code_agent_messages['data'][0]['attachments'][0]['file_id'], 
                file_name=output_file,
                target_dir=output_dir
            )
            self.logger.info(f"Saved presentation file to: {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving presentation: {e}")
            return False

    def generate_ppt(
        self, 
        input_file: str, 
        output_file: str, 
        code_dir: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> bool:
        """
        Generate a PowerPoint presentation from a documentation file.
        
        This is the main method that orchestrates the entire process.
        
        Args:
            input_file: Path to the input documentation file
            output_file: Path to save the generated presentation
            code_dir: Optional path to code directory to include in generation
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Initialize the client and agents
        if not self.initialize_client():
            return False
            
        time.sleep(0.5)  # Small delay for API stability
        
        if not self.initialize_ppt_agent():
            return False
            
        if not self.initialize_code_agent():
            return False
            
        if not self.create_thread():
            return False

        # Run the PPT generation agent
        ppt_messages = self.run_ppt_generation(input_file, code_dir)
        
        # Run the code execution agent
        code_messages = self.run_code_execution(ppt_messages)
        
        # Save the presentation
        return self.save_presentation(code_messages, output_file, output_dir)

    def run(self):
        input_file = os.environ['OUTPUT_DIR'] + '/' + os.environ['PPT_INPUT_PATH']
        output_file = os.environ['OUTPUT_DIR'] + '/' + os.environ['PPT_OUTPUT_PATH']
        output_dir = os.environ['OUTPUT_DIR'] 
        code_dir = None
        
        # Generate the presentation
        success = self.generate_ppt(input_file, output_file, code_dir, output_dir)

        return success

# Example of how to use the class when script is run directly
if __name__ == "__main__":
    # Create an instance of the PPTGenerator
    generator = PPTGenerator()

    input_file = os.environ['OUTPUT_DIR'] + r'\\' + os.environ['PPT_INPUT_PATH']
    output_file = os.environ['OUTPUT_DIR'] + r'\\' + os.environ['PPT_OUTPUT_PATH']
    code_dir = None
    
    # Generate the presentation
    success = generator.generate_ppt(input_file, output_file, code_dir)
