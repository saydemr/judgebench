import json
import logging
import os
import re
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from azure.ai.inference.models import SystemMessage
from json_repair import repair_json
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from utils.scores import context_calculate_accuracy

from .utils import (
    ContextOutput,
    GPSData,
    OpeningHours,
    SystemBlockInput,
    UserBlockInput,
    cot_1_new,
    cot_3_new,
    cot_5_new,
    io_new,
)

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PromptEvaluator:
    def __init__(
        self,
        llm,
        method,
        testing,
        input_path: Path,
        output_path: Path,
        self_consistency=False,
        loops=3,
        cot_shots=1,
    ):
        self.llm = llm
        self.method = method
        self.input_path = input_path
        self.output_path = output_path
        self.token_json_path = output_path.parent / Path(
            output_path.stem + "_token.json"
        )
        self.self_consistency = self_consistency
        self.loops = loops
        self.cot_shots = cot_shots

    @staticmethod
    def open_json(file_path):
        with open(file_path, "r") as file:
            return json.load(file)

    def passed_time(self, start_time, logging=True):
        """
        Calculates passed time for logging
        """
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        if logging:
            return f"{minutes} minutes, {seconds} seconds"
        else:
            return {"time_min": minutes, "time_sec": seconds}

    def json_parser_correction(self, input):
        """
        Tries to correct common mistakes from LLM output and transform decision strings to boolean
        """
        try:
            # Handle the case where input is wrapped in code block notation ```
            if input.startswith("```") and input.endswith("```"):
                input = input.strip("```").strip()

            # Remove 'json\n' prefix if it exists
            if input.startswith("json\n"):
                input = input[len("json\n") :]

            # Ensure the input is valid JSON by checking the first and last characters
            if not (input.startswith("{") and input.endswith("}")):
                raise ValueError("Input does not appear to be valid JSON.")

            # Load the input JSON
            answer = json.loads(input)

            # Transform decision
            if "decision" in answer:
                if isinstance(answer["decision"], str):
                    if answer["decision"].lower() == "true":
                        answer["decision"] = True
                    elif answer["decision"].lower() == "false":
                        answer["decision"] = False

        except json.JSONDecodeError as e:
            logging.error("JSON Decode Error:", e)
            logging.error("Original content:", input)
            return None

        return answer

    def append_to_json_file(self, data):
        """
        Appends data to a JSON file. If the file does not exist or is empty, creates a new file with the data.
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
        Determine the starting point for evaluation based on existing results.
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
        token_usage["query_index"] = query_index
        token_usage["block_index"] = block_index

        json.dump(token_usage, open(self.token_json_path, "w"), indent=4)


    # Tests context understanding
    def context_understanding_single_turn(self, user_block, system_block):
        """
        Evaluate a single interaction case between user and system.
        """
        pydantic_parser = PydanticOutputParser(pydantic_object=ContextOutput)
        format_instructions = pydantic_parser.get_format_instructions()

        # method template
        if self.method == "input_output":
            template = io_new
        elif self.method == "chain_of_thought":
            if self.cot_shots == 1:
                template = cot_1_new
            elif self.cot_shots == 3:
                template = cot_3_new
            elif self.cot_shots == 5:
                template = cot_5_new

        # Generate prompt using template and input
        prompt = ChatPromptTemplate.from_template(template=template)
        filled_prompt_template = prompt.format_messages(
            current_gps_user_block=user_block.current_gps,
            date=user_block.date,
            time=user_block.time,
            user_utterance=user_block.user_utterance,
            name=system_block.name,
            current_gps_system_block=system_block.current_gps,
            cost=system_block.cost,
            opening_hours=system_block.opening_hours,
            cuisine_type=system_block.cuisine_type,
            menu=system_block.menu,
            rating=system_block.rating,
            distance_km=system_block.distance_km,
            duration_min=system_block.duration_min,
            format_instructions=format_instructions,
        )

        # Determine the LLM model name (for both OpenAI and non-OpenAI models)
        llm_model_name = (
            self.llm.deployment_name
            if hasattr(self.llm, "deployment_name")
            else self.llm.get_model_info().model_name
            if hasattr(self.llm, "get_model_info")
            else self.llm.model_name
            if hasattr(self.llm, "model_name")
            else "unknown"
        )

        max_tries = 5
        attempts = 0
        cleaned_json = None

        # While loop for possible parsing or generation errors
        while attempts < max_tries:
            attempts += 1

            # Run for both OpenAI and non-OpenAI models
            if llm_model_name in [
                "gpt-35-turbo",
                "gpt-4",
                "gpt-4.1",
                "gpt-4o",
                "gpt-4o-mini",
                "o4-mini",
                "o3-mini",
                "o3",
                "o1",
                "DeepSeek-R1-qcbar",
                "DeepSeek-V3-0324",
            ]:
                output = self.llm.invoke(filled_prompt_template)
                if llm_model_name in ["DeepSeek-R1-qcbar"]:
                    cleaned_json = repair_json(output.content, return_objects=True)
                    if isinstance(cleaned_json, list):
                        cleaned_json = max(cleaned_json, key=len)
                else:
                    cleaned_json = self.json_parser_correction(output.content)
            else:
                messages = [SystemMessage(content=str(filled_prompt_template))]
                output = self.llm.complete(messages=messages)
                cleaned_json = self.json_parser_correction(
                    output["choices"][0]["message"]["content"]
                )

            if cleaned_json is not None:
                break
            else:
                logging.error(f"Attempt {attempts} failed to generate valid JSON.")

        if cleaned_json is None:
            logging.error("Failed to generate valid JSON after maximum attempts.")

        cleaned_json["llm_model"] = llm_model_name

        # Token usage for OpenAI models
        if llm_model_name in [
            "gpt-35-turbo",
            "gpt-4",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "o4-mini",
            "o3-mini",
            "o3",
            "o1",
            "DeepSeek-R1-qcbar",
            "DeepSeek-V3-0324",
        ]:
            tokens = {
                "input_tokens": output.response_metadata["token_usage"].get(
                    "prompt_tokens", 0
                ),
                "output_tokens": output.response_metadata["token_usage"].get(
                    "completion_tokens", 0
                ),
                "model": llm_model_name,
            }
        else:
            tokens = {
                "input_tokens": output["usage"].get("prompt_tokens", 0),
                "output_tokens": output["usage"].get("completion_tokens", 0),
                "model": llm_model_name,
            }

        return cleaned_json, tokens

    def context_understanding_multi_turn(self):
        """
        Evaluate a full dataset of user and system blocks for context understanding
        """
        start_time = time.time()
        token_count_history = self.determine_tokens_used()
        dataset = self.open_json(self.input_path)

        # Determine starting point
        start_block, start_query = self.determine_starting_point(len(dataset))
        if start_block == len(dataset):
            logging.info("Evaluation already completed - Choose a different path")

        system_block_id = 1

        for block_index in range(start_block, len(dataset)):
            block = dataset[block_index]
            try:
                user_block_input = UserBlockInput(
                    current_gps=GPSData(**block["user_block"]["context"]["location"]),
                    date=block["user_block"]["context"]["date"],
                    time=block["user_block"]["context"]["time"],
                    user_utterance=block["user_block"]["user_utterance"]["utterance"],
                )

                # Determine starting point in user block
                if block_index == start_block:
                    system_blocks = block["system_block"][start_query:]
                else:
                    system_blocks = block["system_block"]

                for query_index, system_block_sample in enumerate(
                    system_blocks,
                    start=start_query if block_index == start_block else 0,
                ):
                    system_block_input = SystemBlockInput(
                        name=system_block_sample["system_block"]["name"],
                        current_gps=GPSData(
                            **system_block_sample["system_block"]["current_gps"]
                        ),
                        cost=system_block_sample["system_block"]["cost"],
                        opening_hours=OpeningHours(
                            **system_block_sample["system_block"]["opening_hours"]
                        ),
                        cuisine_type=system_block_sample["system_block"][
                            "cuisine_type"
                        ],
                        menu=system_block_sample["system_block"]["menu"],
                        rating=system_block_sample["system_block"]["rating"],
                        distance_km=system_block_sample["system_block"]["distance_km"],
                        duration_min=system_block_sample["system_block"][
                            "duration_min"
                        ],
                    )

                    # Initialize list for self-consistency
                    self_consistency_list = []
                    loops = self.loops if self.self_consistency else 1

                    for _ in range(loops):
                        llm_decision, tokens = self.context_understanding_single_turn(
                            user_block_input, system_block_input
                        )
                        self_consistency_list.append(llm_decision)
                        # Update token count history for the specific model
                        llm_model_name = tokens["model"]
                        token_count_history[llm_model_name]["input_tokens"] += tokens[
                            "input_tokens"
                        ]
                        token_count_history[llm_model_name]["output_tokens"] += tokens[
                            "output_tokens"
                        ]

                    if self.self_consistency:
                        sample_decision_list = [
                            entry["decision"] for entry in self_consistency_list
                        ]
                        decision_count = Counter(sample_decision_list)
                        max_vote = decision_count.most_common(1)[0]
                        max_count = max_vote[1]
                        ratio = max_count / self.loops

                        # Collect reasonings
                        reasonings = [
                            entry["reasoning"] for entry in self_consistency_list
                        ]
                        combined_reasoning = " ".join(reasonings)

                        decision = {
                            "id": system_block_id,
                            "decision": max_vote[0],
                            "ratio": np.round(ratio, 2),
                            "reasoning": combined_reasoning,
                            "predicted_label": self_consistency_list[0][
                                "error_category"
                            ],
                            "label": system_block_sample["definition_type"],
                        }
                    else:
                        decision = {
                            "id": system_block_id,
                            "decision": self_consistency_list[0]["decision"],
                            "reasoning": self_consistency_list[0]["reasoning"],
                            "predicted_label": self_consistency_list[0][
                                "error_category"
                            ],
                            "label": system_block_sample["definition_type"],
                        }

                    decision["query_index"] = query_index
                    decision["block_index"] = block_index
                    system_block_id += 1
                    self.append_to_json_file(decision)
                    self.dump_token_usage(token_count_history, query_index, block_index)

                start_query = 0
                logging.info(
                    f"Block {block_index + 1}/{len(dataset)} evaluated - Passed time: {self.passed_time(start_time)}"
                )

            except Exception as e:
                logging.error(
                    f"Error in user block {block_index}, system block {query_index} - {str(e)}"
                )
                logging.error(traceback.format_exc())

        # Eval finished
        info = {
            "testing_date": datetime.now().strftime("%d/%m/%Y"),
            "time": self.passed_time(start_time, logging=False),
            "token_count_history": token_count_history,
            "deployment_name": (
                self.llm.deployment_name
                if hasattr(self.llm, "deployment_name")
                else self.llm.get_model_info().model_name
                if hasattr(self.llm, "get_model_info")
                else self.llm.model_name
                if hasattr(self.llm, "model_name")
                else "unknown"
            ),
        }
        self.append_to_json_file(info)
        logging.critical(
            f"Accuracy scores: {context_calculate_accuracy(self.open_json(self.output_path), multi_agent=False)}"
        )

    # Main function
    def run_evaluation(self):
        self.context_understanding_multi_turn()
