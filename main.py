import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from methods.MultiAgentEvaluation.main import MultiAgentEvaluation
from methods.PromptEvaluation.main import PromptEvaluator
from utils.model_config import ModelManager

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate datasets using different AI reasoning methods."
    )
    ### Base
    parser.add_argument(
        "--method",
        required=True,
        choices=[
            "input_output",
            "chain_of_thought",
            "multi_agent_base",
            "multi_agent_debate",
            "agent_roundtable",
        ],
        help="The evaluation method to use.",
    )

    ### Prompt Evaluation
    parser.add_argument(
        "--model",
        choices=[
            "gpt-35-turbo-1106",
            "gpt-35-turbo",
            "gpt-4",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "o4-mini",
            "o3-mini",
            "o3",
            "o1",
            "llama-8b",
            "llama-405b",
            "mistral-large",
            "mistral-nemo",
            "DeepSeek-R1-qcbar",
            "DeepSeek-V3-0324",
        ],
        help="The AI model to use for evaluation.",
        default="o4-mini",
    )
    parser.add_argument(
        "--temp", type=float, default=0, help="Temperature setting for the model"
    )
    # Chain of Thought - choosing number of shots
    parser.add_argument(
        "--cot_shots",
        type=int,
        default=1,
        help="Number of shot prompting using chain of thought method",
    )
    # Self Consistency settings
    parser.add_argument(
        "--self_consistency", action="store_true", help="Use self-consistency method."
    )
    parser.add_argument(
        "--loops", type=int, default=3, help="Number of loops for self-consistency."
    )

    ### Multi Agent
    # Choose llms for different agents
    parser.add_argument(
        "--agent_llm",
        nargs="+",
        type=str,
        help="List of LLMs to use for the agents. Provide one model per agent, e.g., gpt-4 gpt-35-turbo gpt-4o.",
    )
    # Choose temperature for different agents
    parser.add_argument(
        "--agent_llm_temp",
        nargs="+",
        type=float,
        help="Temperature settings for the debator LLMs in agent_debate",
    )

    parser.add_argument(
        "--discussion_loops", type=int, default=1, help="Number of discussion rounds"
    )

    args = parser.parse_args()
    data_path = "data/context_understanding/dataset.json"
    # data_path = "data/context_understanding/test.json"
    dataset_name = "context_understanding"

    method_shortcuts = {
        "input_output": "IO",
        "chain_of_thought": "CoT",
        "multi_agent_base": "MAB",
        "multi_agent_debate": "MAD",
        "agent_debate": "AD",
        "agent_roundtable": "AR",
    }

    method_shortcut = method_shortcuts.get(args.method)
    if not method_shortcut:
        raise ValueError(f"Unsupported method: {args.method}")

    results_dir = Path("new_results")
    reasoning_models = set(["DeepSeek-R1-qcbar", "o3", "o1", "o3-mini", "o4-mini"])

    ## Start
    if args.method in ["input_output", "chain_of_thought"]:
        if args.self_consistency:
            results_dir = results_dir / "SC"
            method_shortcut = f"SC{args.loops}-{method_shortcut}"
        else:
            results_dir = results_dir / f"{method_shortcut}"

        # Include number of shots in the filename if using CoT method
        if args.method == "chain_of_thought":
            shots_suffix = args.cot_shots
        else:
            shots_suffix = ""

        output_filename = (
            f"{method_shortcut}{shots_suffix}_{args.model}_{args.temp}_results.json"
        )
        output_dir = results_dir / dataset_name
        output_path = results_dir / dataset_name / output_filename
        output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure unique filename by appending _2, _3, etc., if necessary
        # file_number = 1
        # while os.path.exists(output_path):
        #     file_number += 1
        #     output_filename = f"{method_shortcut}{shots_suffix}_{args.model}_{args.temp}_results{file_number}.json"
        #     output_path = results_dir / dataset_name / output_filename

        print(f"Results will be saved to: {output_path}")

        # Initialize model manager using create_chat_model
        if args.model in [
            "gpt-35-turbo-1106",
            "gpt-35-turbo",
            "gpt-4",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "o4-mini",
            "o3-mini",
            "o3",
            "o1",
        ]:
            model_type = "openai"
        elif args.model in ["llama-8b", "llama-405b", "mistral-large", "mistral-nemo"]:
            model_type = "opensource_api"
        elif args.model in ["DeepSeek-R1-qcbar", "DeepSeek-V3-0324"]:
            model_type = "deepseek"
        else:
            raise ValueError(f"Model {args.model} is not supported.")

        # Create the model using create_chat_model
        model_manager = ModelManager(model_type=model_type)
        llm = model_manager.create_chat_model(
            model_name=args.model, temperature=args.temp
        )

        # Initialize the evaluator and run the evaluation
        evaluator = PromptEvaluator(
            llm=llm,
            method=args.method,
            input_path=data_path,
            output_path=output_path,
            self_consistency=args.self_consistency,
            loops=args.loops,
            cot_shots=args.cot_shots,
        )
        evaluator.run_evaluation()

    elif args.method in ["multi_agent_base", "multi_agent_debate", "agent_roundtable"]:
        # Handle agent LLMs
        if len(args.agent_llm) == 1:
            agent_llms = args.agent_llm * 3
        elif len(args.agent_llm) == 3:
            agent_llms = args.agent_llm
        else:
            raise ValueError(
                "You must provide either 1 or exactly 3 models for the debator agents."
            )

        # Handle agent temperatures
        agent_temps = [None] * 3
        for idx, llm in enumerate(agent_llms):
            if llm in reasoning_models or args.agent_llm_temp is None:
                agent_temps[idx] = None
            else:
                if len(args.agent_llm_temp) == 1:
                    agent_temps[idx] = args.agent_llm_temp
                elif len(args.agent_llm_temp) == 3:
                    agent_temps[idx] = args.agent_llm_temp[idx]
                else:
                    raise ValueError(
                        "You must provide either 1 or exactly 3 temperatures for the debator agents."
                    )

        # Get agents
        created_agent_llms = []
        for i in range(3):
            model_type = (
                "openai"
                if "gpt" in agent_llms[i]
                or agent_llms[i] in ["o3", "o1", "o3-mini", "o4-mini"]
                else "opensource_api"
                if agent_llms[i]
                in ["llama-8b", "llama-405b", "mistral-large", "mistral-nemo"]
                else "deepseek"
                if agent_llms[i] in ["DeepSeek-R1-qcbar", "DeepSeek-V3-0324"]
                else "unknown"
            )
            model_manager = ModelManager(model_type=model_type)

            created_agent_llms.append(
                model_manager.create_chat_model(
                    model_name=agent_llms[i], temperature=agent_temps[i]
                )
            )

        if args.method == "multi_agent_base":
            discussion_loops = 1
            method_shortcut = "MAB"

        elif args.method == "multi_agent_debate":
            discussion_loops = args.discussion_loops
            method_shortcut = "MAD"

        elif args.method == "agent_roundtable":
            discussion_loops = args.discussion_loops
            method_shortcut = "AR"

        # output_filename = f"{method_shortcut}_{'+'.join(agent_llms)}_{(str(agent_temps[0]) + '+') * 2 + str(agent_temps[0])}_results.json"
        output_filename = (
            f"{method_shortcut}_{str(agent_llms[0])}_{str(agent_temps[0])}_results.json"
        )

        output_path = results_dir / method_shortcut / dataset_name / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Results will be saved to: {output_path}")

        evaluator = MultiAgentEvaluation(
            agent_llms=created_agent_llms,
            input_path=data_path,
            output_path=output_path,
            method=args.method,
            discussion_loops=discussion_loops,
        )
        evaluator.run_evaluation()


if __name__ == "__main__":
    main()
