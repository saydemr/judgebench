models="gpt-35-turbo-1106 gpt-35-turbo gpt-4 gpt-4.1 gpt-4o gpt-4o-mini o4-mini o3-mini o3 o1 DeepSeek-R1-qcbar DeepSeek-V3-0324 llama-8b llama-405b mistral-large mistral-nemo"

for model in $models; do
    for sc_rounds in 3 5; do
        python main.py --model $model --method "chain_of_thought" --cot_shots ?? --self_consistency --loops $sc_rounds
    done
done