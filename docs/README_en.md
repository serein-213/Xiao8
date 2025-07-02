<div align="center">

![小八Logo](/assets/xiaoba_logo.jpg)

# Lanlan - A Voice-Native, All-Scenario AI Companion

**Beginner-friendly, voice-native, all-scenario AI <small><s>Catgirl</s></small> Companion that requires no dedicated graphics card.**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

**:neckbeard: Even my grandpa can set up this cyber catgirl in 3 minutes!**

</div>

-----

# Project Introduction

The goal of this project is to create a beginner-friendly, out-of-the-box AI ~~catgirl~~ companion with capabilities for hearing, seeing, tool use, and multi-device synchronization. This project was designed with three core objectives in mind:

1.  **Minimize Voice Latency**. The user interface of this project is primarily voice-based. All system-level designs must prioritize **reducing conversation latency**, and no service should block the conversation process.

2.  **All-Scenario Synchronization**. The catgirl can exist on your phone, computer, and smart glasses simultaneously. Furthermore, when the **same catgirl** exists on different devices at the same time, her **behavior should be completely synchronized**. (Imagine this scenario: If you have multiple monitors at home, each displaying the catgirl, we want you to be talking to the same one no matter where you go, creating a fully immersive, surround-sound experience.)

3.  **Lightweight**. Every new technology introduced must enhance the actual user experience, avoiding the addition of unnecessary plugins and options.

### Technical Approach

The backend is primarily Python, using a real-time multimodal API as the main processor, complemented by several text-based plugin modules. The frontend is mainly H5+JS, converted into an app using Electron and PWA.

# How to Run

1. *For Chinese one-click package users:* **Obtain an Alibaba Cloud API Key**. Register for an account on the Alibaba Cloud Bailian platform [official website](https://bailian.console.aliyun.com/). New users can receive a substantial amount of free credits after completing identity verification—be sure to look for the "New User Benefits" promotion on the page. After registration, visit the [console](https://www.google.com/search?q=https://bailian.console.aliyun.com/api-key%3Ftab%3Dmodel%23/api-key) to get your API Key. Paste this API Key into the `core_config.txt` file, within the quotes following `"coreApiKey":`.

    > *Note: All links provided are official and do not contain any affiliate codes; I do not benefit from them. The current state of Alibaba's official website is quite poor, please bear with it orz.*

    For *developers*, please copy `config/api_template.py` to `config/api.py` and enter your API Keys.
    
    For *user all over the world*, **Obtain an OpenAI Key**, and modify the default API URLs in `config/api.py` to OpenAI version.

2.  **Try the Web Version**. *For the one-click package*, after filling in the API KEY, run `启动网页版.bat` (`Run_Web_Version.bat`) to open the web version. **Please be patient and wait for the webpage to refresh on the first launch.**  
  For other users, please refer to devloper instructions below.

3.  **Try the Desktop Pet Mode**. If the web version works correctly, you can proceed to run `启动App版.bat` (`Run_App_Version.bat`) to enable the desktop overlay mode. Note: **Please do not use the web and app versions simultaneously. Ensure that the .exe file has not been quarantined by your system or antivirus software.** *However, do not run the .exe file directly. Running the .exe directly will trigger Xiaoba's virus mode, which can only be terminated manually through the Task Manager...*

> For developers: After cloning this project, (1) create a new Python 3.12 environment. (2) Run `pip install -r requirements.txt` to install dependencies. (3) Copy `config/api_template.py` to `config/api.py` and configure it as necessary. (4) Run `python memory_server.py` and `python main_server.py`. (5) Access the web version through the port specified in `main_server` (defaults to localhost:48911).*

# Advanced Configuration

## A. Modifying Character Persona

The basic persona is located in `config/__init__.py`. Please open it with a text editor. Change `MASTER_NAME` to your own name and `her_name` to your ~~catgirl~~ companion's name *(Note: this is a temporary measure, as the project supports multiple concurrent characters)*. Fill in the basic information in `master_basic_config` and `lanlan_basic_config` in JSON format. If you have questions about the JSON format, please consult an AI tool like Doubao.

The advanced persona is located in `config/prompts_chara.py`; please modify it with caution. A lengthy persona will reduce the system's performance and stability. The developer sincerely hopes you will follow the principle of Occam's Razor when defining the catgirl's persona: "Do not multiply settings without necessity."

## B. Changing the Live2D Model

The path for the Live2D model is currently hardcoded in `main_server.py` under the `"model_path"` section. You can modify it yourself (there are two instances; change the first one for now). After replacing the Live2D model, if you want to adjust its size and position, you will also need to modify the `model.scale` and `model.anchor` parameters in `templates/index.html`. Expression control is not yet ready for release and will be officially supported for custom Live2D models after the UI is improved.

## C. Changing the Voice

This project has built-in voice cloning functionality based on the CosyVoice API; the code is included and has been tested. Please follow the [official Alibaba Cloud Bailian Large Model Platform tutorial](https://help.aliyun.com/zh/model-studio/cosyvoice-clone-api) to clone a voice. After cloning, fill in the `VOICE_ID` in `config/api.py` and set `USE_TTS` to `True`.

## D. Contributing to Development

The environment dependencies for this project are very simple. Just run `pip install -r requirements.txt` in a `python3.12` environment. Please remember to copy `config/api_template.py` to `config/api.py`. The developer recommends joining the QQ group 1048307485. The catgirl's name is in the project title.

# TODO List (Development Plan)

## A. High Priority

1.  Add a frontend UI for managing personas (Live2D model/voice/personality, etc.) and memory (memory retrieval and correction).
2.  Support Live2D expression and motion control.
3.  Implement compatibility for tool calling or MCP (which is essentially tool calling; MCP compatibility is not strictly required).

## B. Medium Priority

1.  Catgirl Network. Allow catgirls to communicate with each other. This requires a certain user base, so its priority is lowered.
2.  Optimization for mobile devices. This would involve migrating the session manager backend to JS to communicate directly with the API server, keeping only the memory server on the PC to reduce mobile latency. However, this conflicts with the project's primary goal of "multi-device synchronization," so its priority is lowered.
3.  Refactor the Memory Server into an MCP server to allow the same character to be compatible with different models (the workload for this is not very large).

## C. Low Priority

1.  Enable non-visual models to "see" the screen through image annotation. Since a fully multimodal model is already available, I believe this work should be handled by the API service provider, hence the very low priority.
2.  Integrate with chat tools like QQ. Since the voice model is optimized for real-time interaction, integrating with QQ would mean only the memory part could be shared, and the core API would need to be replaced with a text model. This involves a significant amount of work and reinventing the wheel. It would be better to refactor the Memory Server into an MCP server and then integrate it with other chat AI frameworks.

# Q\&A

> *Why do you use Alibaba? Why not Deepseek?*

Because Alibaba's model is multimodal and it speaks fast.

> *Why do you use an 8B model? Don't you know 8B models are dumb?*

Because Alibaba currently only offers an 8B model, and it speaks fast.

> *Can you switch to another provider/run offline/use a different model/try xxx?*

I'm sorry, but it speaks fast.

> *Why does my AI seem a bit dumb?*

This project cannot be responsible for the AI's **level of intelligence**. It can only help you choose the solution with the best overall performance currently available. If you have seen the project's videos on Bilibili, the live demo version and the open-source version share the same code logic, differing only in the supported API interfaces. Those with the means can replace the `CORE_URL`/`CORE_API_KEY`/`CORE_MODEL` in `config/api.py` with OpenAI's `GPT-4o` version to upgrade the model from Qwen to `GPT-4o`. You can also **wait for updates and progress from Alibaba or other domestic providers**.

**Technological progress doesn't happen overnight. Please be patient and watch the AI grow\!**

> *Why doesn't the Live2D model's mouth open?*

This project is already compatible with both types of lip-sync methods for Live2D models. If lip-syncing isn't working, it is highly likely an issue with the Live2D model itself, not with this project.

> *Does it support MCP services, tools, or plugins?*

OpenAI's official Realtime API supports the `tool calling` feature. Therefore, this project is compatible with MCP services, and the live demo version has already implemented tools like web search. However, unlike conventional text models, using tools with a real-time model requires consideration of asynchronous coordination and blocking issues. Furthermore, the Alibaba platform does not currently support tool calling. Thus, there are no immediate plans for MCP compatibility in the open-source project; this will be revisited once domestic providers implement the relevant interfaces.

> *Which language models does this project support?*

This project relies on real-time, fully multimodal APIs. The live demo version uses the Gemini Live API, while the open-source version uses the [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime). Gemini Live provides better results but is currently **only supported by Google**. The OpenAI Realtime API is currently **supported by OpenAI and Alibaba Cloud**, with potential for more models in the future. The open-source version only supports the `Qwen-Omni-Realtime` and `GPT-4o-Realtime` models.

> *Why does project xxx have lower voice chat latency than yours?*

Factors affecting conversation latency include:

  - ***Context Length***: A major factor. A long persona text and memory pool will significantly increase conversation latency.
  - ***Model Size***: A major factor. Larger models are more intelligent, requiring a trade-off between intelligence and latency. Among the models used in this project, `Qwen-Omni` is currently the strongest at the `8B` level, while `GPT-4o` has activated parameters at the `30B` level. Models smaller than 8B may achieve lower response latency but will also be correspondingly less intelligent. Note that only the number of activated parameters in the Mixture-of-Experts (MoE) affects latency.
  - ***Cache Hit Rate***: When the input prefix remains unchanged, it can effectively hit the language model's KV cache, significantly reducing latency. Therefore, try to use incremental insertion and avoid frequently modifying previous parts of the conversation (especially the beginning).
  - *Network Latency*: Usually under 200ms and not a primary factor affecting *latency*. However, network fluctuations can cause voice *stuttering*.

If you have indeed found a solution with lower latency at the same context length and intelligence level, please submit an issue. Thank you for sharing.

> *What on earth is the title of this project about?*

Chat-chan was a QQ chat catgirl based on ChatGPT that I made in March 2023. Lanlan was a voice + vision multimodal AI catgirl based on GPT-4V and Discord that I made in March 2024. Xiaoba is an all-scenario AI catgirl I created in April 2025. The title carries my emotional journey over these three years. For now, I guess we'll stick with Project Lanlan?

> *Why did you design xxx/xxx/xxx?*

I suggest joining the group chat for a private discussion. Many designs that currently seem redundant have more uses in the live demo (preview) version.

# Special Thanks

Special thanks to *明天好像没什么*, *喵*, and *小韭菜饺* for their help with testing. Special thanks to *大毛怪灬嘎* for providing the logo assets.