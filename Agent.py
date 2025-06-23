from code_documentation_generator import CodeDocumentationGenerator
from CodeGuard import CodeGuard
from ppt_generation import PPTGenerator

def main():
    # Method 1: Using environment variables from a .env file
    print("Runnin Agent: Code Documentation Generator")
    generator = CodeDocumentationGenerator(env_file=".env")
    generator.generate_documentation()

    print("Running Agent: Code Guard")
    code_guard = CodeGuard()
    code_guard.run()

    print("Running Agent: PPT Generator")
    ppt_generator = PPTGenerator(env_file=".env")
    ppt_generator.run()

if __name__ == "__main__":
    main()