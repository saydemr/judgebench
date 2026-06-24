import json
import logging
import os
import time
from pathlib import Path


class BaseEvaluator:
    """
    Base class for evaluation methods containing common utility methods.
    Reduces code redundancy between MultiAgentEvaluation and PromptEvaluator.
    """

    def __init__(self, input_path: Path, output_path: Path, method: str):
        self.input_path = input_path
        self.output_path = output_path
        self.method = method
        self.token_json_path = output_path.parent / Path(
            output_path.stem + "_token.json"
        )

    @staticmethod
    def open_json(file_path):
        """Load JSON from file."""
        with open(file_path, "r") as file:
            return json.load(file)

    def passed_time(self, start_time, logging_format=True):
        """
        Calculate elapsed time for logging.
        
        Args:
            start_time: Start time from time.time()
            logging_format: If True, return formatted string; else return dict
            
        Returns:
            Formatted string or dict with time_min and time_sec
        """
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        if logging_format:
            return f"{minutes} minutes, {seconds} seconds"
        else:
            return {"time_min": minutes, "time_sec": seconds}

    def json_parser_correction(self, input_str):
        """
        Attempt to correct common LLM JSON output errors and convert decision strings to boolean.
        Uses robust parsing with multiple fallback strategies.
        
        Args:
            input_str: JSON string from LLM output
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            # Handle code block notation
            if input_str.startswith("```") and input_str.endswith("```"):
                input_str = input_str.strip("```").strip()

            # Remove 'json\n' prefix if present
            if input_str.startswith("json\n"):
                input_str = input_str[len("json\n") :]

            # Clean up escaped quotes
            input_str = input_str.replace("\\'", "'")

            # Validate JSON structure
            if not (input_str.startswith("{") and input_str.endswith("}")):
                raise ValueError("Input does not appear to be valid JSON.")

            # Load the JSON
            answer = json.loads(input_str)

            # Transform decision string to boolean
            if "decision" in answer:
                if isinstance(answer["decision"], str):
                    if answer["decision"].lower() == "true":
                        answer["decision"] = True
                    elif answer["decision"].lower() == "false":
                        answer["decision"] = False

        except json.JSONDecodeError as e:
            logging.error("JSON Decode Error: %s", e)
            logging.error("Original content: %s", input_str)
            return None
        except ValueError as e:
            logging.error("JSON parsing error: %s", e)
            return None

        return answer

    def append_to_json_file(self, data):
        """
        Append data to JSON file. Creates file if it doesn't exist.
        
        Args:
            data: Dictionary to append to JSON array
        """
        if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
            with open(self.output_path, "r+") as file:
                current_list = json.load(file)
                current_list.append(data)
                file.seek(0)
                json.dump(current_list, file, indent=4)
        else:
            with open(self.output_path, "w") as file:
                json.dump([data], file, indent=4)

    def determine_starting_point(self, dataset_length):
        """
        Determine starting point for evaluation based on existing results.
        
        Args:
            dataset_length: Total length of dataset
            
        Returns:
            Tuple of (start_block, start_query)
        """
        start_block = 0
        start_query = 0
        if os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
            with open(self.output_path, "r") as file:
                existing_results = json.load(file)
                start_block = existing_results[-1]["block_index"]
                start_query = existing_results[-1]["query_index"] + 1

                if start_query >= 5:
                    start_query = 0
                    start_block += 1

            logging.info(
                f"Starting again from user Block: {start_block}, system block: {start_query}"
            )
        else:
            logging.info(f"Number of blocks: {dataset_length}")

        return start_block, start_query

    def determine_tokens_used(self):
        """
        Load or initialize token usage tracking dictionary.
        
        Returns:
            Dictionary with token counts for each model
        """
        if self.token_json_path.exists():
            return json.load(open(self.token_json_path))
        else:
            return {
                "gpt-35-turbo": {"input_tokens": 0, "output_tokens": 0},
                "gpt-4": {"input_tokens": 0, "output_tokens": 0},
                "gpt-4o": {"input_tokens": 0, "output_tokens": 0},
                "gpt-4.1": {"input_tokens": 0, "output_tokens": 0},
                "gpt-4o-mini": {"input_tokens": 0, "output_tokens": 0},
                "o3-mini": {"input_tokens": 0, "output_tokens": 0},
                "o4-mini": {"input_tokens": 0, "output_tokens": 0},
                "o3": {"input_tokens": 0, "output_tokens": 0},
                "o1": {"input_tokens": 0, "output_tokens": 0},
                "Meta-Llama-3-8B-Instruct": {"input_tokens": 0, "output_tokens": 0},
                "Meta-Llama-3-405B-Instruct": {"input_tokens": 0, "output_tokens": 0},
                "mistral-nemo": {"input_tokens": 0, "output_tokens": 0},
                "mistral-large-2407": {"input_tokens": 0, "output_tokens": 0},
                "DeepSeek-R1-qcbar": {"input_tokens": 0, "output_tokens": 0},
                "DeepSeek-V3-0324": {"input_tokens": 0, "output_tokens": 0},
            }

    def dump_token_usage(self, token_usage, query_index, block_index):
        """
        Save token usage statistics to file.
        
        Args:
            token_usage: Dictionary with token counts
            query_index: Current query index
            block_index: Current block index
        """
        token_usage["query_index"] = query_index
        token_usage["block_index"] = block_index

        json.dump(token_usage, open(self.token_json_path, "w"), indent=4)
