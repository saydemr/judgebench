import json
import logging
import os
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from azure.ai.inference.models import SystemMessage
from json_repair import repair_json

# LangChain
from langchain_classic.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.utils.metrics import calculate_accuracy

from src.utils.schemas import (
    ContextOutput,
    ContextOutputRoundtable,
)

from src.utils.prompts import (    
    context_understanding_agent_definitions,
    context_understanding_prompt_template,
    context_understanding_roundtable_cot_5,
)

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MultiAgentEvaluation:
    def __init__(
        self,
        agent_llms,
        input_path: Path,
        output_path: Path,
        method,
        discussion_loops=1,
    ):
        self.agent_llms = agent_llms
        self.input_path = input_path
        self.output_path = output_path
        self.token_json_path = output_path.parent / Path(
            output_path.stem + "_token.json"
        )
        self.method = method
        self.discussion_loops = discussion_loops

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
            cleaned_input = input.replace("```json", "").replace("```", "").strip()
            cleaned_input = cleaned_input.replace("\\'", "'")
            # Load the input JSON
            answer = json.loads(cleaned_input)

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

    def create_input_dict(
        self,
        user_block=None,
        system_block=None,
        user_utterance=None,
        previous_arguments=None,
        format_instructions=None,
    ):
        """
        Creates input dict for invoke agents
        """


        return {
            # User Block data
            "current_gps_user_block_lat": user_block["context"]["location"][
                "latitude"
            ],
            "current_gps_user_block_long": user_block["context"]["location"][
                "longitude"
            ],
            "current_gps_user_block_desc": user_block["context"]["location"][
                "description"
            ],
            "date": user_block["context"]["date"],
            "time": user_block["context"]["time"],
            "user_utterance": user_block["user_utterance"]["utterance"],
            # System Block data
            "name": system_block["system_block"]["name"],
            "current_gps_system_block_lat": system_block["system_block"][
                "current_gps"
            ]["latitude"],
            "current_gps_system_block_long": system_block["system_block"][
                "current_gps"
            ]["longitude"],
            "current_gps_system_block_desc": system_block["system_block"][
                "current_gps"
            ]["description"],
            "cuisine_type": system_block["system_block"]["cuisine_type"],
            "menu": system_block["system_block"]["menu"],
            "cost": system_block["system_block"]["cost"],
            "rating": system_block["system_block"]["rating"],
            "monday": system_block["system_block"]["opening_hours"]["monday"],
            "tuesday": system_block["system_block"]["opening_hours"]["tuesday"],
            "wednesday": system_block["system_block"]["opening_hours"]["wednesday"],
            "thursday": system_block["system_block"]["opening_hours"]["thursday"],
            "friday": system_block["system_block"]["opening_hours"]["friday"],
            "saturday": system_block["system_block"]["opening_hours"]["saturday"],
            "sunday": system_block["system_block"]["opening_hours"]["sunday"],
            "distance_km": system_block["system_block"]["distance_km"],
            "duration_min": system_block["system_block"]["duration_min"],
            # Additional arguments
            "previous_arguments": previous_arguments,
            "format_instructions": format_instructions,
        }

    def create_and_invoke_agent_chain(
        self, agent_template, prompt_template, input_dict, agent_llm
    ):
        """
        Returns agent as chain and token usage.
        """
        # Determine the LLM model name (for both OpenAI and non-OpenAI models)
        llm_model_name = (
            agent_llm.deployment_name
            if hasattr(agent_llm, "deployment_name")
            else agent_llm.get_model_info().model_name
            if hasattr(agent_llm, "get_model_info")
            else agent_llm.model_name
            if hasattr(agent_llm, "model_name")
            else "unknown"
        )

        if self.method == "agent_roundtable":
            agent_template = ""

        # Count tokens for cost transparency
        if llm_model_name in [
            "gpt-35-turbo-1106",
            "gpt-4",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "o3",
            "o4-mini",
            "o3-mini",
            "o1",
            "DeepSeek-R1-qcbar",
            "DeepSeek-V3-0324",
        ]:
            # For OpenAI models
            agent_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", agent_template),
                    ("system", prompt_template),
                ]
            )
            # print(f'Agent prompt {agent_prompt}')

            max_tries = 5
            attempts = 0
            cleaned_json = None

            # While loop for handling potential generation/parsing errors
            while attempts < max_tries:
                attempts += 1
                # Run OpenAI llm
                agent_chain = agent_prompt | agent_llm
                llm_reply = agent_chain.invoke(input_dict)

                cleaned_json = repair_json(llm_reply.content, return_objects=True)
                if type(cleaned_json) is list:
                    cleaned_json = max(cleaned_json, key=len)

                if cleaned_json is not None:
                    break
                else:
                    logging.error(f"Attempt {attempts} failed to generate valid JSON.")

            if cleaned_json is None:
                logging.error("Failed to generate valid JSON after maximum attempts.")

            # Token usage for OpenAI models
            tokens = {
                "input_tokens": llm_reply.response_metadata["token_usage"].get(
                    "prompt_tokens", 0
                ),
                "output_tokens": llm_reply.response_metadata["token_usage"].get(
                    "completion_tokens", 0
                ),
                "model": llm_model_name,
            }
            cleaned_json["llm_model"] = llm_model_name

            return cleaned_json, tokens

        else:
            # For non-OpenAI models like LLAMA or Mistral
            max_tries = 5
            attempts = 0
            cleaned_json = None

            # While loop for handling potential generation/parsing errors
            while attempts < max_tries:
                attempts += 1
                messages = [
                    SystemMessage(content=agent_template),
                    SystemMessage(content=prompt_template.format(**input_dict)),
                ]
                llm_reply = agent_llm.complete(messages=messages)
                cleaned_json = self.json_parser_correction(
                    llm_reply["choices"][0]["message"]["content"]
                )

                if cleaned_json is not None:
                    break
                else:
                    logging.error(f"Attempt {attempts} failed to generate valid JSON.")

            if cleaned_json is None:
                logging.error("Failed to generate valid JSON after maximum attempts.")

            cleaned_json["llm_model"] = llm_model_name

            # Token usage for non-OpenAI models
            tokens = {
                "input_tokens": llm_reply["usage"]["prompt_tokens"],
                "output_tokens": llm_reply["usage"]["completion_tokens"],
                "model": llm_model_name,
            }

            return cleaned_json, tokens

    def decision_list(self, arguments):
        """
        Calculates and returns a list of all decisions made by agents in the last round.
        """
        liste = []

        # Get the last round of arguments
        last_round = max(arguments.keys())  # This gets the last round number

        # Iterate over each agent's decision in the last round
        for agent in arguments[last_round]:
            decision = arguments[last_round][agent].get("decision")
            if decision is not None:
                liste.append(decision)

        return liste

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

    def count_tokens(self, token_count_history, tokens, model_name):
        """
        Updates token count for the specific model.
        """
        if model_name not in token_count_history:
            token_count_history[model_name] = {"input_tokens": 0, "output_tokens": 0}

        # Add tokens for this specific model
        token_count_history[model_name]["input_tokens"] += tokens["input_tokens"]
        token_count_history[model_name]["output_tokens"] += tokens["output_tokens"]

        return token_count_history

    def dump_token_usage(self, token_usage, query_index, block_index):
        token_usage["query_index"] = query_index
        token_usage["block_index"] = block_index

        json.dump(token_usage, open(self.token_json_path, "w"), indent=4)

    def transform_confidence_levels(self, x):
        """
        Confidence level transformation function from roundtable paper
        """
        try:
            # print(x)
            x = float(x)  # Ensure x is a float

        except ValueError:
            logging.error(f"Invalid confidence value: {x}")

        if x <= 0.6:
            return 0.1
        if 0.8 > x > 0.6:
            return 0.3
        if 0.9 > x >= 0.8:
            return 0.5
        if 1 > x >= 0.9:
            return 0.8
        if x == 1:
            return 1

    def calculate_weighted_vote(self, arguments, loop_count):
        """
        Calculate weighted votes for every round
        """
        # Extract decisions and confidence values
        decisions, confidences = self.extract_decisions_and_confidences(
            arguments, loop_count
        )

        # Transform them
        transformed_confidences = [
            self.transform_confidence_levels(c) for c in confidences
        ]

        vote_weights = {"true": 0, "false": 0}
        for i, decision in enumerate(decisions):
            if decision == "true":
                vote_weights["true"] += transformed_confidences[i]
            elif decision == "false":
                vote_weights["false"] += transformed_confidences[i]

        # Round
        vote_weights["true"] = float(np.round(vote_weights["true"], 2))
        vote_weights["false"] = float(np.round(vote_weights["false"], 2))

        return vote_weights

    def extract_decisions_and_confidences(self, arguments, loop_count):
        """
        Extracts decisions and confidence intervals from every agent
        """
        decisions = []
        confidences = []

        # Loop over every agent in arguments
        for agent in arguments[loop_count]:
            agent_data = arguments[loop_count][agent]
            decision = "true" if agent_data["decision"] else "false"
            confidence = agent_data["confidence"]
            decisions.append(decision)
            confidences.append(confidence)

        return decisions, confidences

    # Tests single turn for implicit and context understanding
    def multi_agent_single_turn(
        self,
        agents,
        user_utterance=None,
        user_block=None,
        system_block=None,
        format_instructions=None,
        use_case_template=None,
    ):
        """
        Runs multi_agent for a single data point (evaluation between user block and system block)
        """
        arguments = {}
        token_count_history = self.determine_tokens_used()
        loop_count = 0

        # Run
        while loop_count < self.discussion_loops:
            loop_count += 1
            logging.info(
                f"Start round {loop_count}/{self.discussion_loops} of validation!"
            )

            # Each agent states their argument
            for i, agent in enumerate(agents):
                previous_arguments = ""
                agent_llm = self.agent_llms[i]

                # Fetch previous arguments if it's not the first round
                if loop_count > 1:
                    previous_arguments = "\n".join(
                        [
                            f"Agent {other_agent} argued in round {loop_count - 1}:\n{arguments[loop_count - 1][other_agent]['reasoning']}"
                            for other_agent in arguments[loop_count - 1]
                            if other_agent != agent
                        ]
                    )

                # Create the input dictionary for the agent
                input_dict = self.create_input_dict(
                    user_utterance=user_utterance,
                    user_block=user_block,
                    system_block=system_block,
                    previous_arguments=previous_arguments,
                    format_instructions=format_instructions,
                )

                # Invoke agent chain
                chain_output, tokens = self.create_and_invoke_agent_chain(
                    agent_template=agents[agent],
                    prompt_template=use_case_template,
                    input_dict=input_dict,
                    agent_llm=agent_llm,
                )

                # Save arguments for the current round
                if loop_count not in arguments:
                    arguments[loop_count] = {}
                arguments[loop_count][agent] = chain_output

                # Count tokens
                token_count_history = self.count_tokens(
                    token_count_history, tokens, tokens["model"]
                )

            # Extract decisions and compute ratio
            decision_list = self.decision_list(arguments)
            decision_count = Counter(decision_list)
            max_vote = decision_count.most_common(1)[0]
            max_count = max_vote[1]
            ratio = max_count / len(agents)

            # If all agents found agreement
            if all(x == decision_list[0] for x in decision_list):
                results = {
                    "utterance": user_utterance,
                    "decision": decision_list[0],
                    "round": loop_count,
                    "ratio": ratio,
                    "decision_method": "agreement",
                }
                logging.info(
                    f"Decisions are unanimous: {decision_list[0]}. Validation concludes."
                )

                # Add weighted voting if agent_roundtable method is used
                if self.method == "agent_roundtable":
                    arguments[loop_count]["weighted_voting"] = (
                        self.calculate_weighted_vote(arguments, loop_count)
                    )
                    results["arguments"] = arguments
                else:
                    results["arguments"] = arguments

                return results, token_count_history

            # No agreement - If loop count reaches the limit of discussion_loops
            if loop_count == self.discussion_loops:
                results = {
                    "utterance": user_utterance,
                    "round": loop_count,
                    "ratio": ratio,
                }

                # Check if the method is 'agent_roundtable'
                if self.method == "agent_roundtable":
                    weighted_vote = self.calculate_weighted_vote(arguments, loop_count)
                    arguments[loop_count]["weighted_voting"] = weighted_vote
                    results["arguments"] = arguments

                    # Decide based on which weighted vote (true or false) is higher
                    decision = (
                        "true"
                        if weighted_vote["true"] > weighted_vote["false"]
                        else "false"
                    )
                    results["decision"] = decision
                    results["decision_method"] = "weighted_voting"
                    logging.info(f"Weighted voting decision: {decision}")

                # If the method is not 'agent_roundtable', use max vote
                else:
                    results["arguments"] = arguments
                    results["decision"] = max_vote[0]
                    results["decision_method"] = "max_vote"
                    logging.info(f"Max-Vote decision: {max_vote[0]}")

                return results, token_count_history

            logging.info(
                f"Decisions are not unanimous. Proceeding to round {loop_count + 1} of {self.discussion_loops}."
            )

    def context_understanding_multi_turn(self):
        """
        Evaluate a full dataset of user and system blocks
        """
        start_time = time.time()
        token_count_history = self.determine_tokens_used()
        dataset = self.open_json(self.input_path)

        # Determine starting point
        start_block, start_query = self.determine_starting_point(len(dataset))
        if start_block == len(dataset):
            logging.info("Evaluation already completed - Choose different path")

        # Set format instructions dependent on method
        if self.method in ["multi_agent_base", "multi_agent_debate"]:
            pydantic_parser = PydanticOutputParser(pydantic_object=ContextOutput)
            format_instructions = pydantic_parser.get_format_instructions()
            prompt_template = context_understanding_prompt_template
        else:
            pydantic_parser = PydanticOutputParser(
                pydantic_object=ContextOutputRoundtable
            )
            format_instructions = pydantic_parser.get_format_instructions()
            prompt_template = context_understanding_roundtable_cot_5

        # Start loop through dataset
        system_block_id = 1
        for block_index in range(start_block, len(dataset)):
            block = dataset[block_index]
            user_block = block["user_block"]
            try:
                # Determine starting point in user block
                if block_index == start_block:
                    system_blocks = block["system_block"][start_query:]
                else:
                    system_blocks = block["system_block"]

                for query_index, system_block_sample in enumerate(
                    system_blocks,
                    start=start_query if block_index == start_block else 0,
                ):
                    decision, token_usage = self.multi_agent_single_turn(
                        agents=context_understanding_agent_definitions,
                        user_block=user_block,
                        system_block=system_block_sample,
                        format_instructions=format_instructions,
                        use_case_template=prompt_template,
                    )
                    decision["id"] = system_block_id
                    decision["label"] = system_block_sample["definition_type"]
                    decision["query_index"] = query_index
                    decision["block_index"] = block_index
                    predicted_labels_per_agent = [
                        entry["predicted_label"]
                        for entry in decision["arguments"][
                            str(len(decision["arguments"]))
                        ]
                    ]
                    label_count = Counter(predicted_labels_per_agent)
                    decision["predicted_label"] = label_count.most_common(1)[0][0]

                    self.append_to_json_file(decision)
                    self.dump_token_usage(token_usage, query_index, block_index)
                    system_block_id += 1

                start_query = 0
                logging.info(
                    f"Block {block_index + 1}/{len(dataset)} evaluated - Passed time: {self.passed_time(start_time)}"
                )

            # Error
            except Exception as e:
                logging.error(
                    f"Error in user block {block_index}, system block {query_index} - {str(e)}"
                )
                logging.error(traceback.format_exc())

        # Save important facts and append at the end of list
        info = {
            "testing_date": datetime.now().strftime("%d/%m/%Y"),
            "time": self.passed_time(start_time, logging=False),
            "token_information": token_count_history,
            "agent_deployment_names": [
                llm.deployment_name
                if hasattr(llm, "deployment_name")
                else llm.get_model_info().model_name
                if hasattr(llm, "get_model_info")
                else llm.model_name
                if hasattr(llm, "model_name")
                else "unknown"
                for llm in self.agent_llms
            ],
        }
        self.append_to_json_file(info)
        logging.critical(
            f"Accuracy scores: {calculate_accuracy(self.open_json(self.output_path), multi_agent=True)}"
        )

    # Main function
    def run_evaluation(self):
        self.context_understanding_multi_turn()
