#!/usr/bin/env python3
"""Generate developer-dictation training pairs for fine-tuning S1-mini.

Each pair is (noisy ASR-style transcript, clean written text). Noise comes
from Whisper mishearings observed in Vox history and benchmarks, spoken
identifiers and paths, fillers, and self-corrections.

The private benchmark's sentences and identifiers are deliberately absent so
it stays a fair held-out test.

Usage: make_data.py OUT_DIR [--seed N]
Writes train.jsonl, eval.jsonl, and general.txt (non-technical inputs whose
targets are labelled by the base model, to keep its general behaviour).
"""

import argparse
import json
import random
import re
from pathlib import Path

# correct form -> ways Whisper writes it when it gets it wrong
TERMS = {
    "code": ["quote"],
    "GitHub": ["get hub", "git hub", "Git Hub"],
    "GitLab": ["git lab"],
    "kubectl": ["cube control", "cube cuddle", "kube control", "cube CTL"],
    "Kubernetes": ["Cooper Netties", "kubernetes", "Cuban eighties"],
    "Vitest": ["Vitus", "vite test", "vitetest"],
    "pytest": ["pie test", "pi test"],
    "Jest": ["jest", "just"],
    "useEffect": ["use effect", "use a fact"],
    "useState": ["use state"],
    "useMemo": ["use memo"],
    "useCallback": ["use callback"],
    "useRef": ["use ref", "use rep"],
    "TypeScript": ["type script", "typescript"],
    "JavaScript": ["java script"],
    "Next.js": ["next JS", "next js", "NextJS"],
    "Node.js": ["node JS", "node js", "nodejs"],
    "npm": ["NPM", "n p m"],
    "pnpm": ["PNPM", "p n p m", "P&PM"],
    "PostgreSQL": ["Postgres QL", "post gress QL", "postgresql"],
    "Postgres": ["post gress", "post grass"],
    "Redis": ["radish", "Reddis"],
    "Docker": ["docker", "doctor"],
    "Docker Compose": ["docker compose", "doctor compose"],
    "JSON": ["Jason", "json"],
    "YAML": ["yamel", "Yamal"],
    "README": ["read me", "readme"],
    ".env": ["dot env", "dotenv file"],
    "localhost": ["local host"],
    "API": ["a p i", "api"],
    "CLI": ["c l i", "cli"],
    "PR": ["P.R.", "pr"],
    "CI": ["C.I.", "ci"],
    "regex": ["rejects", "reg ex"],
    "async": ["a sink", "async"],
    "await": ["a weight", "await"],
    "OAuth": ["oh auth", "O auth"],
    "JWT": ["j w t", "JWT token"],
    "SQL": ["sequel"],
    "GraphQL": ["graph QL", "graph cool"],
    "Tailwind": ["tail wind", "tailwind"],
    "Prisma": ["prism a", "prisma"],
    "Vercel": ["versel", "Vercel's"],
    "Supabase": ["super base", "soup a base"],
    "Zod": ["sod", "zod"],
    "tRPC": ["t r p c", "TRPC"],
    "Go": ["go lang", "Golang"],
    "Rust": ["rust"],
    "Claude Code": ["clock code", "cloud code", "clod code"],
    "Cursor": ["cursor"],
    "Codex": ["codecs", "Codex's"],
    "rebase": ["re-base", "re base"],
    "ESLint": ["es lint", "e s lint", "easel int"],
    "Prettier": ["prettier"],
    "webpack": ["web pack"],
    "Vite": ["veet", "vite"],
    "monorepo": ["mono repo"],
    "sudo": ["pseudo", "sue do"],
    "cache": ["cash"],
    "enum": ["e-num", "ee num"],
    "boolean": ["bullion", "boolean"],
    "tuple": ["tupple", "two pull"],
    "grep": ["grip", "grape"],
    "chmod": ["ch mod", "c h mod"],
    "SSH": ["s s h", "ssh"],
    "WebSocket": ["web socket"],
    "refactor": ["re factor"],
    "schema": ["skima", "schema"],
    "Wispr Flow": ["whisper flow", "Whisperflow"],
    "stdout": ["standard out"],
    "nginx": ["engine x", "engine X"],
    "Terraform": ["terra form"],
    "AWS": ["a w s", "aws"],
    "S3": ["s three", "S 3"],
    "Lambda": ["lambda"],
    "CORS": ["cores", "course"],
    "middleware": ["middle ware"],
    "endpoint": ["end point"],
    "frontend": ["front end"],
    "backend": ["back end"],
    "Svelte": ["svelte", "svelt"],
    "Vue": ["view"],
    "Django": ["jango", "D jango"],
    "FastAPI": ["fast API", "fast a p i"],
    "Flask": ["flask"],
    "Rails": ["rails"],
}

# Names absent from TERMS: the right answer is to keep them exactly as heard.
# Without these the model learns that every unfamiliar name is a mishearing
# and replaces it with the closest known term ("ShedCN" became "schema").
KEEP = ["Bun", "Deno", "Hono", "Astro", "Remix", "Drizzle", "Turborepo", "Biome", "Ollama",
        "LangChain", "Pinia", "Zustand", "Jotai", "Expo", "Tauri", "Electron", "Bevy", "Axum",
        "Tokio", "Gin", "Echo", "Fiber", "Pydantic", "Polars", "Ruff", "Poetry", "Celery",
        "Sentry", "PostHog", "Resend", "Clerk", "Neon", "Turso", "Fly.io", "Railway", "Render",
        "Kafka", "RabbitMQ", "Temporal", "Grafana", "Prometheus", "Loki", "Traefik", "Caddy",
        "Mintlify", "Storybook", "Playwright", "Cypress", "Mocha", "Chai", "Sinon", "Zig",
        "Elixir", "Phoenix", "Gleam", "Kotlin", "Ktor", "Swift", "SwiftUI", "Flutter", "Dart"]

VERBS = ["fetch", "load", "parse", "render", "build", "validate", "format", "create", "update",
         "delete", "handle", "compute", "sync", "resolve", "normalize", "serialize", "get", "save"]
NOUNS = ["user", "order", "invoice", "session", "token", "payment", "profile", "cart", "message",
         "event", "report", "account", "product", "comment", "file", "draft", "team", "price"]
EXTRAS = ["data", "list", "state", "item", "request", "response", "id", "count", "status", "handler"]
DIRS = ["src", "lib", "app", "components", "utils", "api", "server", "pages", "hooks", "tests",
        "cmd", "pkg", "scripts", "docs", "config", "routes", "models", "services"]
EXTS = ["ts", "tsx", "js", "go", "py", "rs", "json", "md", "yaml", "css", "sql", "sh"]
SPOKEN_EXT = {"ts": "ts", "tsx": "tsx", "js": "js", "go": "go", "py": "py", "rs": "rs",
              "json": "json", "md": "md", "yaml": "yaml", "css": "css", "sql": "sql", "sh": "sh"}

# {T} technical term, {I} identifier, {F} file path, {T2} second term.
TEMPLATES = [
    "can you look at the code in {F} and tell me why it fails",
    "the code in {I} is wrong, it should return early when the list is empty",
    "I feel like the code you wrote for {I} is kind of messy, can you clean it up",
    "push the code to {T} and open a pull request",
    "run the tests with {T} and fix whatever breaks",
    "rename {I} to {I2} and update every caller",
    "add a test for {I} that covers the empty case",
    "move {I} into {F}",
    "the bug is in {F}, somewhere around the {I} function",
    "can you explain what {I} does and why we need it",
    "set up {T} with {T2} for this project",
    "we are using {T} on the backend and {T2} on the frontend",
    "check the {T} config, I think the port is wrong",
    "write a small script that calls {I} and prints the result",
    "don't touch the code in {F}, only change the tests",
    "why does {T} complain about this file",
    "open {F} and look at how {I} handles errors",
    "replace the custom hook with {T}",
    "deploy it with {T} and check the logs",
    "the code in {F} has a race condition",
    "make {I} async and await the call to {I2}",
    "install {T} and add it to the dev dependencies",
    "can we migrate from {T} to {T2} without breaking anything",
    "the {T} build is failing on the CI because of {I}",
    "keep the code simple, don't add another abstraction",
    "review my code and tell me what you would change",
    "copy the {T} example from the docs into {F}",
    "use {T} for the validation and keep the error messages",
    "I want {I} to return a {T} object instead of a string",
    "add logging to {I} so we can see what the request looks like",
    "go through the code base and find every place that calls {I}",
    "split {F} into two files, one for {I} and one for {I2}",
    "commit this and then rebase on top of main",
    "the {C} component re-renders too often, can you memoize it",
    "create a {C} component that shows the latest orders",
    "pass the user down to {C} as a prop",
    "the {T} query is slow, can you add an index",
    "explain this code to me like I am new to {T}",
]

SELF_CORRECTIONS = ["no wait", "I mean", "actually", "sorry", "no, actually", "or rather"]
FILLERS = ["um", "uh", "so", "like", "you know", "okay so", "basically"]


def identifier(rng, component=False):
    """Casing must be recoverable from speech: camelCase by default, PascalCase
    for components, snake_case only when the speaker says "underscore"."""
    if component:
        words = [rng.choice(NOUNS)] + [rng.choice(["card", "list", "form", "button", "table", "modal", "header"])]
        return "".join(w.title() for w in words), " ".join(words)
    words = [rng.choice(VERBS), rng.choice(NOUNS)] + ([rng.choice(EXTRAS)] if rng.random() < 0.5 else [])
    if rng.random() < 0.2:
        return "_".join(words), " underscore ".join(words)
    return words[0] + "".join(w.title() for w in words[1:]), " ".join(words)


def path(rng):
    parts = rng.sample(DIRS, rng.randint(1, 3))
    stem = rng.choice(NOUNS) + (rng.choice(["", "_test", "-utils", "_card", "-service"]) if rng.random() < 0.6 else "")
    ext = rng.choice(EXTS)
    written = "/".join(parts + [f"{stem}.{ext}"])
    spoken_stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem).replace("_", " underscore ").replace("-", " dash ").lower()
    if rng.random() < 0.5:
        spoken = " slash ".join(parts + [f"{spoken_stem} dot {SPOKEN_EXT[ext]}"])
    else:  # Whisper often writes the path itself; it must stay untouched
        spoken = written
    return written, spoken


def fill(template, rng):
    clean, noisy = template, template
    for slot in ("{I2}", "{I}", "{C}"):
        while slot in clean:
            written, spoken = identifier(rng, component=slot == "{C}")
            clean, noisy = clean.replace(slot, written, 1), noisy.replace(slot, spoken, 1)
    while "{F}" in clean:
        written, spoken = path(rng)
        clean, noisy = clean.replace("{F}", written, 1), noisy.replace("{F}", spoken, 1)
    for slot in ("{T2}", "{T}"):
        while slot in clean:
            if rng.random() < 0.3:
                name = rng.choice(KEEP)
                clean, noisy = clean.replace(slot, name, 1), noisy.replace(slot, name, 1)
                continue
            term = rng.choice(list(TERMS))
            misheard = rng.choice(TERMS[term]) if rng.random() < 0.75 else term
            clean, noisy = clean.replace(slot, term, 1), noisy.replace(slot, misheard, 1)
    # "code" itself is the most frequent real error.
    if rng.random() < 0.7:
        noisy = re.sub(r"\bcode\b", "quote", noisy)
    return clean, noisy


def add_self_correction(clean, noisy, rng):
    """Speaker says a wrong term then corrects it; only the correction is written."""
    for term in TERMS:
        if re.search(rf"\b{re.escape(term)}\b", clean) and term not in ("code",):
            wrong = rng.choice([t for t in TERMS if t != term])
            noisy = re.sub(rf"\b{re.escape(term)}\b", f"{wrong}, {rng.choice(SELF_CORRECTIONS)}, {term}", clean, count=1)
            return clean, noisy
    return clean, noisy


def add_fillers(noisy, rng):
    """Fillers go at the start or after a clause, never inside a name."""
    words = noisy.split()
    spots = [0] + [i + 1 for i, word in enumerate(words) if word.endswith(",")]
    for spot in sorted(rng.sample(spots, min(len(spots), rng.randint(1, 2))), reverse=True):
        words.insert(spot, rng.choice(FILLERS))
    return " ".join(words)


def finish(clean):
    clean = clean[0].upper() + clean[1:]
    question = re.search(r"(^|, )(can|could|why|what|how|do|does|is|are|should)\b", clean, re.I)
    return clean + ("?" if question else ".")


def whisper_style(noisy, rng):
    if rng.random() < 0.5:  # raw lowercase, the model's native input
        return re.sub(r"[.,?](?=\s|$)", "", noisy).lower()  # keep dots inside names
    return noisy[0].upper() + noisy[1:] + rng.choice([".", "", "?"])


def pair(rng):
    clean, noisy = fill(rng.choice(TEMPLATES), rng)
    if rng.random() < 0.1:  # Whisper got it right: the answer is to change nothing
        return {"input": finish(clean), "target": finish(clean)}
    if rng.random() < 0.25:
        clean, noisy = add_self_correction(clean, noisy, rng)
    if rng.random() < 0.5:
        noisy = add_fillers(noisy, rng)
    return {"input": whisper_style(noisy, rng), "target": finish(clean)}


GENERAL = """i need to pick up the groceries after work and then call my mom
can you remind me what we decided about the trip next weekend
i think the movie was good but the ending felt rushed
send a message to the team saying i will be ten minutes late
the meeting moved to thursday at three so update the calendar
honestly i am tired today so let's keep this short
what do you think about getting a dog this year
we should book the hotel before the prices go up
i loved the video you sent me yesterday it was hilarious
tell her that the package arrived and everything is fine
let's try another scene and see if it works better
i want the design to feel modern and clean like an apple app
help me understand the main features and which ones we are missing
from my view it lost a lot of detail so we need to improve that
the idea is for me to learn how it was recorded so i can do something similar
i feel like we lost the original idea somewhere along the way
can we plan the next steps before we start building anything
thanks for the help today i really appreciate it
make sure you check the weather before we leave
i don't know if this is the right approach but let's try it""".splitlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=4000)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    seen, pairs = set(), []
    while len(pairs) < args.count:
        item = pair(rng)
        if item["input"] not in seen:
            seen.add(item["input"])
            pairs.append(item)
    split = len(pairs) // 20
    for name, rows in (("eval.jsonl", pairs[:split]), ("train.jsonl", pairs[split:])):
        with open(args.out / name, "w") as file:
            for row in rows:
                file.write(json.dumps(row) + "\n")
    general = [add_fillers(line, rng) if rng.random() < 0.5 else line for line in GENERAL for _ in range(3)]
    (args.out / "general.txt").write_text("\n".join(sorted(set(general))) + "\n")
    print(f"{len(pairs) - split} train, {split} eval, {len(set(general))} general")


if __name__ == "__main__":
    main()
