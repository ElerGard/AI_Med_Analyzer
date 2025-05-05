import json

from unsloth import FastModel
from unsloth.chat_templates import get_chat_template, train_on_responses_only
import torch
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from transformers import TextStreamer
# import os
# from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
# os.environ['HF_HOME'] = r'F:\models_cache'
# print(torch.cuda.is_available())

def formatting_prompts_func(examples):
   convos = examples["conversations"]
   texts = [tokenizer.apply_chat_template(convo, tokenize = False, add_generation_prompt = False).removeprefix('<bos>') for convo in convos]
   return { "text" : texts, }

if __name__ == "__main__":
    XFORMERS_MORE_DETAILS = 1

    model, tokenizer = FastModel.from_pretrained(
        model_name = "unsloth/gemma-3-27b-it-unsloth-bnb-4bit",
        max_seq_length = 1024,
        load_in_4bit = True,
        load_in_8bit = False,
        full_finetuning = False
    )

    model = FastModel.get_peft_model(
        model,
        finetune_vision_layers     = False,
        finetune_language_layers   = True,
        finetune_attention_modules = True,
        finetune_mlp_modules       = True,

        r = 8,
        lora_alpha = 8,
        lora_dropout = 0,
        bias = "none",
        random_state = 3407,
    )


    tokenizer = get_chat_template(
        tokenizer,
        chat_template = "gemma-3",
    )


    with open("training_data.json", 'r', encoding='utf-8') as f:
        json_data = json.load(f)

        if 'conversations' in json_data:
            data_list = [{'conversations': conv} for conv in json_data['conversations']]
            dataset = Dataset.from_list(data_list)
        else:
            dataset = Dataset.from_dict(json_data)


    dataset = dataset.map(formatting_prompts_func, batched=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            per_device_train_batch_size=4,
            gradient_accumulation_steps=8,
            learning_rate=1e-5,
            max_steps=50,
            warmup_ratio=0.1,
            optim="adamw_8bit",
            bf16=True,
            logging_steps=10
        ),
        packing=True,
    )

    trainer = train_on_responses_only(
        trainer,
        instruction_part="<start_of_turn>user\n",
        response_part="<start_of_turn>model\n",
    )

    gpu_stats = torch.cuda.get_device_properties(0)
    start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
    print(f"GPU = {gpu_stats.name}. Максимально памяти = {max_memory} GB.")
    print(f"{start_gpu_memory} GB зарезервировано.")

    trainer_stats = trainer.train()

    used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
    used_percentage = round(used_memory / max_memory * 100, 3)
    lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
    print(f"{trainer_stats.metrics['train_runtime']} секунд обучалась")
    print(
        f"{round(trainer_stats.metrics['train_runtime'] / 60, 2)} минут обучалась"
    )
    print(f"Пик использованой памяти = {used_memory} GB.")
    print(f"Пик использованной памяти для обучения = {used_memory_for_lora} GB.")
    print(f"Процент зарезервированной памяти от максимальной = {used_percentage} %.")
    print(f"Процент зарезервированной памяти для обучения от максимальной = {lora_percentage} %.")


    # model.save_pretrained("gemma-3")  # Локальное сохранение модели
    # tokenizer.save_pretrained("gemma-3")

    # model.save_pretrained_merged("gemma-3-finetune", tokenizer) # Сохранение конфигов для перевода в GGUF

    # TODO Проблемы с версией llama.cpp, не хочет конвертить в GGUF
    # model.save_pretrained_gguf(
    #     "gemma-3-finetune",
    #     quantization_type="F16",  # Q8_0, BF16, F16
    # )

    messages = [
        {"role": "system", "content": """Отвечай на русском языке."""},
        {"role": "user", "content": rf"""Сформируй мне json из анамнеза жизни. Анамнез жизни: Вирусные гепатиты, ТВС, вен. заболевания отрицает. Другие заболевания: не отмечает.
Аллергологические реакции на лекарственные препараты и пищевые продукты: нет. Травмы: нет. Операции: нет. Наследственность: у матери ИМ в 77 лет с летальным исходом. Вредные привычки: курил много лет по 0,5 пачки в день, не курит месяц.
Выезд за пределы РФ/ПК за последние 6 месяцев:нет"""}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
    )

    _ = model.generate(
        **tokenizer([text], return_tensors="pt").to("cuda"),
        max_new_tokens=124,
        temperature=0.1, top_p=0.95, top_k=64,
        streamer=TextStreamer(tokenizer, skip_prompt=True),
    )

