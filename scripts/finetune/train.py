#!/usr/bin/env python3
"""LoRA fine-tune of S1-mini by Superwhisper on developer dictation.

Usage: train.py BASE_DIR DATA_DIR OUT_DIR
DATA_DIR holds train.jsonl and general.jsonl (base-model labels that keep its
general behaviour). Writes a merged Hugging Face model to OUT_DIR.
"""

import json
import random
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

# Must match internal/polish/llm.go: S1-mini was trained on this exact format.
SYSTEM = ("You are a text normalizer for speech-to-text transcripts. The input begins with a control line "
          "specifying the styling, structure, and context settings; clean the transcript to match those "
          "settings and output only the cleaned text.")
CONTROL = "[Styling: semi-formal] [Structure: prose] [Context: general]"


def prompt(text):
    return (f"<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{CONTROL}\n{text}<|im_end|>\n"
            "<|im_start|>assistant\n<think>\n\n</think>\n\n")


def main():
    base, data, out = map(Path, sys.argv[1:4])
    rows = [json.loads(line) for line in open(data / "train.jsonl")]
    general = [json.loads(line) for line in open(data / "general.jsonl")]
    rows += general * 8  # weight the base-behaviour anchors up
    random.Random(1).shuffle(rows)

    tokenizer = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16).cuda()
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    def encode(row):
        head = tokenizer(prompt(row["input"]), add_special_tokens=False)["input_ids"]
        tail = tokenizer(row["target"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
        return head + tail, [-100] * len(head) + tail  # loss on the answer only

    examples = [encode(row) for row in rows]
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=2e-4)
    batch, epochs = 16, 2
    steps = epochs * (len(examples) // batch)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: min(1.0, step / 30) * max(0.0, 1 - step / steps))
    model.train()
    step = 0
    for epoch in range(epochs):
        random.Random(epoch).shuffle(examples)
        for start in range(0, len(examples) - batch + 1, batch):
            # Micro-batches of 4: the 152k-token vocabulary makes the logits of a
            # full batch too large for a 4 GiB GPU.
            for micro in range(start, start + batch, 4):
                chunk = examples[micro:micro + 4]
                width = max(len(ids) for ids, _ in chunk)
                ids = torch.tensor([i + [tokenizer.pad_token_id] * (width - len(i)) for i, _ in chunk]).cuda()
                labels = torch.tensor([l + [-100] * (width - len(l)) for _, l in chunk]).cuda()
                mask = torch.tensor([[1] * len(i) + [0] * (width - len(i)) for i, _ in chunk]).cuda()
                loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
                (loss * len(chunk) / batch).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            step += 1
            if step % 25 == 0:
                print(f"epoch {epoch} step {step}/{steps} loss {loss.item():.4f}", flush=True)

    model = model.merge_and_unload()
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    for name in ("LICENSE", "NOTICE", "chat_template.jinja", "generation_config.json"):
        if (base / name).exists():
            (out / name).write_bytes((base / name).read_bytes())


if __name__ == "__main__":
    main()
