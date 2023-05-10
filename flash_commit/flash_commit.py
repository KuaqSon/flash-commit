from ast import Dict
import os
from typing import Optional
from typing_extensions import Annotated
import typer
from pathlib import Path
from os.path import exists, join
from rich.console import Console
import subprocess
import tiktoken
import openai

tik_encoding = tiktoken.get_encoding("cl100k_base")

console = Console()

app = typer.Typer(help="Automatically generate commit messages using ChatGPT")


INIT_PROMPTS = [
    {
        "role": "system",
        "content": "You are to act as the author of a commit message in git. Your mission is to create clean and comprehensive commit messages in the conventional commit convention and explain WHAT were the changes and WHY the changes were done. I'll send you an output of 'git diff --staged' command, and you convert it into a commit message. Don't add any descriptions to the commit, only commit message. Use the present tense. Lines must not be longer than 74 characters. Use English to answer.",
    },
    {
        "role": "user",
        "content": """diff --git a/src/server.ts b/src/server.ts
index ad4db42..f3b18a9 100644
--- a/src/server.ts
+++ b/src/server.ts
@@ -10,7 +10,7 @@
import {
  initWinstonLogger();

  const app = express();
 -const port = 7799;
 +const PORT = 7799;

  app.use(express.json());

@@ -34,6 +34,6 @@
app.use((_, res, next) => {
  // ROUTES
  app.use(PROTECTED_ROUTER_URL, protectedRouter);

 -app.listen(port, () => {
 -  console.log(\`Server listening on port \${\port\}\`);
 +app.listen(process.env.PORT || PORT, () => {
 +  console.log(\`Server listening on port \${\PORT\}\`);
  });""",
    },
    {
        "role": "assistant",
        "content": "feat(server.ts): add support for process.env.PORT environment variable to be able to run app on a configurable port",
    },
]


def token_count(text: str):
    return len(tik_encoding.encode(text))


INIT_PROMPT_LENGTH = 0
for prompt in INIT_PROMPTS:
    INIT_PROMPT_LENGTH += token_count(prompt["content"])

MAX_ALLOW_TOKENS = 3900 - INIT_PROMPT_LENGTH


def get_config_path():
    home_path = Path.home()
    config_path = join(home_path, ".flash_commit")
    file_exists = exists(config_path)

    if not file_exists:
        fle = Path(config_path)
        fle.touch()

    return config_path


def save_config(c):
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf8") as file:
        for key, value in c.items():
            line = "{key}={value}\n".format(key=key, value=value)
            file.write(line)


def get_config():
    config_path = get_config_path()
    c: Dict[str, str] = dict()

    with open(config_path, "r", encoding="utf8") as f:
        text = f.read()
        lines = text.split("\n")
        for line in lines:
            if line != "" and line.strip() != "":
                key, value = line.split("=")
                c[key] = value

    return c


def get_staged_files():
    wd = os.getcwd()
    git_dir = subprocess.getoutput("git rev-parse --show-toplevel")
    os.chdir(git_dir)
    diff = subprocess.getoutput("git diff --name-only --cached --relative")
    console.print("Generating commit message for:", style="bold green")
    console.print(diff)
    os.chdir(wd)
    staged_files = diff.split("\n")
    lock_files = []
    non_lock_files = []
    for file_name in staged_files:
        if file_name == "" or file_name.strip() == "":
            continue

        if ".lock" in file_name or "-lock." in file_name:
            lock_files.append(file_name)
        else:
            non_lock_files.append(file_name)

    if len(lock_files) > 0:
        console.print(
            "\nIgnoring lock files:",
            style="bold yellow",
        )
        for file_name in lock_files:
            console.print("- {f}".format(f=file_name), style="bold yellow")

    return non_lock_files


def get_staged_file_names_status():
    wd = os.getcwd()
    git_dir = subprocess.getoutput("git rev-parse --show-toplevel")
    os.chdir(git_dir)
    diff = subprocess.getoutput("git diff --staged --name-status")
    os.chdir(wd)
    return diff[:MAX_ALLOW_TOKENS]


def get_diff(staged_files: list[str]):
    wd = os.getcwd()
    git_dir = subprocess.getoutput("git rev-parse --show-toplevel")
    os.chdir(git_dir)
    diff = subprocess.getoutput(
        "git diff --staged -- {files}".format(files=" ".join(staged_files))
    )
    os.chdir(wd)
    return diff


def generate_commit_message(diff: str, configs: dict[str, str]):
    try:
        messages = [*INIT_PROMPTS, {"role": "user", "content": diff}]
        openai.api_key = configs["openai_key"]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0,
            top_p=0.1,
            max_tokens=196,
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        console.print("\nError generating commit message!", style="bold red")
        console.print(str(e), style="red")
        return None


def do_commit():
    c = get_config()

    openai_key = c.get("openai_key", None)
    if openai_key is None:
        console.print("\nOPEN AI KEY NOT FOUND!", style="bold red")
        console.print(
            "Please run `flash_commit --openai-key <your-openai-key>` to save your key"
        )
        return

    staged_files = get_staged_files()
    if len(staged_files) == 0:
        console.print("No files staged for commit!", style="bold red")
        return

    console.print("", style="bold magenta")

    diff = get_diff(staged_files)

    if token_count(diff) > MAX_ALLOW_TOKENS:
        console.print(
            "\nDiff too large! Use <git diff --staged --name-status> for get commit message!",
            style="bold yellow",
        )
        diff = get_staged_file_names_status()

    commit_msg = None
    with console.status("[bold green]Generating commit message..."):
        while True:
            commit_msg = generate_commit_message(diff, c)
            break

    if not commit_msg:
        console.print("\nCommit message not generated!", style="bold red")
        return

    console.print("\nCommit message generated!", style="bold green")
    console.print(commit_msg)
    console.print("")
    accept = typer.confirm("Are you want to commit with this message?", default=True)
    if not accept:
        return

    subprocess.run(["git", "commit", "-m", commit_msg])

    console.print("")
    run_push = typer.confirm("Are you want to push to remote?", default=True)
    if not run_push:
        return

    subprocess.run(["git", "push", "--verbose"])
    # END


def typer_run(openai_key: Annotated[Optional[str], typer.Option()] = None):
    try:
        if openai_key is not None:
            save_config({"openai_key": openai_key})
            console.print("\nOPEN AI KEY SAVED!", style="bold green")
        else:
            do_commit()
    except Exception as e:
        console.print("\nERROR!", style="bold red")
        console.print(str(e), style="red")


def main():
    typer.run(typer_run)


if __name__ == "__main__":
    main()
