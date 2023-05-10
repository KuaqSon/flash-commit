# flash-commit

Automatically generate commit messages using ChatGPT

# How to install

> Requires: Python3.7 or later installed

1. Download the latest version of [release](https://github.com/KuaqSon/flash-commit/releases).
2. Extract the latest version build
3. run the following command

```
python3 -m pip install <path to downloaded release>/flash_commit-<version>-py3-none-any.whl
```

For example:

```
python3 -m pip install ls ~/Downloads/flash_commit-0.0.1/flash_commit-0.0.1-py3-none-any.whl
```

# Usage

1. Setup the OpenAI API key
   Get help for OpenAI at: https://help.openai.com/en/

2. Save the key by running the following command

```
flash_commit --openai-key sk-xxxx
```

3. Whenever you want to commit please staged the files changes and then just run the simple command

```
flash_commit
```

Happy coding :wink:
