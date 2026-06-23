import numpy as np


def cost_per_method(metrics):
    """
    Calculate the cost in dollars based on the input and output tokens
    and the deployment name.
    """
    # Pricing information for the models
    pricing = {
        "gpt-4": {"input_tokens": 10 / 1_000_000, "output_tokens": 30 / 1_000_000},
        "gpt-4.1": {"input_tokens": 2 / 1_000_000, "output_tokens": 8 / 1_000_000},
        "gpt-35-turbo": {
            "input_tokens": 0.5 / 1_000_000,
            "output_tokens": 1.5 / 1_000_000,
        },
        "gpt-4o": {"input_tokens": 5 / 1_000_000, "output_tokens": 15 / 1_000_000},
        "gpt-4o-mini": {
            "input_tokens": 0.15 / 1_000_000,
            "output_tokens": 0.60 / 1_000_000,
        },
        "o4-mini": {"input_tokens": 1.1 / 1_000_000, "output_tokens": 4.4 / 1_000_000},
        "o3-mini": {"input_tokens": 1.1 / 1_000_000, "output_tokens": 4.4 / 1_000_000},
        "o3": {"input_tokens": 10 / 1_000_000, "output_tokens": 40 / 1_000_000},
        "o1": {"input_tokens": 15 / 1_000_000, "output_tokens": 60 / 1_000_000},
        "Meta-Llama-3-8B-Instruct": {
            "input_tokens": 0.3 / 1_000_000,
            "output_tokens": 0.61 / 1_000_000,
        },
        "Meta-Llama-3-405B-Instruct": {
            "input_tokens": 5.33 / 1_000_000,
            "output_tokens": 16 / 1_000_000,
        },
        "mistral-nemo": {
            "input_tokens": 0.3 / 1_000_000,
            "output_tokens": 0.3 / 1_000_000,
        },
        "mistral-large-2407": {
            "input_tokens": 3 / 1_000_000,
            "output_tokens": 9 / 1_000_000,
        },
        "DeepSeek-V3-0324": {
            "input_tokens": 0.27 / 1_000_000,
            "output_tokens": 1.10 / 1_000_000,
        },
        "DeepSeek-R1-qcbar": {
            "input_tokens": 0.55 / 1_000_000,
            "output_tokens": 2.19 / 1_000_000,
        },
    }

    deployment_name = metrics["deployment_name"]
    input_tokens = metrics["input_tokens"]
    output_tokens = metrics["output_tokens"]

    # Calculate the cost
    input_cost = input_tokens * pricing[deployment_name]["input_tokens"]
    output_cost = output_tokens * pricing[deployment_name]["output_tokens"]
    total_cost = input_cost + output_cost

    metrics["cost_USD"] = total_cost

    return metrics


def calculate_accuracy(result_list, multi_agent=False):
    # Check if the result_list is empty
    if not result_list:
        return {}

    # Store scores and totals for the categories
    category_scores = {
        "positive": {"correct": 0, "total": 0},
        "time_error": {"correct": 0, "total": 0},
        "location_error": {"correct": 0, "total": 0},
        "utterance_error_cuisine": {"correct": 0, "total": 0},
        "utterance_error_cost": {"correct": 0, "total": 0},
        "utterance_error_rating": {"correct": 0, "total": 0},
    }

    # Ground truth expectations
    expected_truths = {
        "positive": True,
        "time_error": False,
        "location_error": False,
        "utterance_error_cuisine": False,
        "utterance_error_cost": False,
        "utterance_error_rating": False,
    }

    decisions_to_analyze = result_list[:-1]
    model_token_usage = {}

    # Loop through the decision list
    for decision in decisions_to_analyze:
        label = decision["label"]
        decision_value = decision["decision"]
        model_name = decision.get("llm_model") if multi_agent else None

        category_scores[label]["total"] += 1
        if decision_value == expected_truths[label]:
            category_scores[label]["correct"] += 1

        if multi_agent and model_name:
            if model_name not in model_token_usage:
                model_token_usage[model_name] = {"input_tokens": 0, "output_tokens": 0}
            model_token_usage[model_name]["input_tokens"] += decision.get(
                "input_tokens", 0
            )
            model_token_usage[model_name]["output_tokens"] += decision.get(
                "output_tokens", 0
            )

    accuracy_scores = {}
    for label, scores in category_scores.items():
        accuracy = scores["correct"] / scores["total"] if scores["total"] > 0 else 0
        accuracy_scores[label] = round(accuracy, 3)

    accuracies = [accuracy_scores[label] for label in category_scores.keys()]
    accuracy_scores["acc_mean"] = round(np.mean(accuracies), 3)
    accuracy_scores["length"] = len(decisions_to_analyze)

    last_element = result_list[-1]
    accuracy_scores["time_min"] = last_element["time"]["time_min"]
    accuracy_scores["time_sec"] = last_element["time"]["time_sec"]
    accuracy_scores["date"] = last_element["testing_date"]

    # Handle deployment name based on multi-agent setup
    if multi_agent:
        accuracy_scores["deployment_name"] = last_element["agent_deployment_names"][0]
        depl_name = last_element["agent_deployment_names"][0]
    else:
        accuracy_scores["deployment_name"] = last_element["deployment_name"]
        depl_name = last_element["deployment_name"]

    # Handle token usage either from token_count_history or input/output tokens
    if (
        "token_count_history" in last_element
        and depl_name in last_element["token_count_history"]
    ):
        tokens = last_element["token_count_history"][depl_name]
        accuracy_scores["input_tokens"] = tokens["input_tokens"]
        accuracy_scores["output_tokens"] = tokens["output_tokens"]
    elif (
        "token_information" in last_element
        and depl_name in last_element["token_information"]
    ):
        tokens = last_element["token_information"][depl_name]
        accuracy_scores["input_tokens"] = tokens["input_tokens"]
        accuracy_scores["output_tokens"] = tokens["output_tokens"]
    else:
        accuracy_scores["input_tokens"] = last_element.get("input_tokens", 0)
        accuracy_scores["output_tokens"] = last_element.get("output_tokens", 0)

    # Handle multi-agent token usage and cost calculations
    if multi_agent:
        token_information = last_element.get("token_information", {})
        accuracy_scores["model_token_usage"] = token_information

        # Add costs for each model
        accuracy_scores["costs_per_model"] = {}
        for model, tokens in token_information.items():
            cost_data = cost_per_method(
                {
                    "deployment_name": model,
                    "input_tokens": tokens["input_tokens"],
                    "output_tokens": tokens["output_tokens"],
                }
            )
            accuracy_scores["costs_per_model"][model] = cost_data["cost_USD"]
    else:
        cost_data = cost_per_method(
            {
                "deployment_name": depl_name,
                "input_tokens": accuracy_scores["input_tokens"],
                "output_tokens": accuracy_scores["output_tokens"],
            }
        )
        accuracy_scores["cost_USD"] = cost_data["cost_USD"]

    return accuracy_scores