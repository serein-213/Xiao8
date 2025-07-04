<div align="center">

![小八Logo](assets/xiaoba_logo.jpg)

[English Version](docs/README_en.md)
# <s>小八</s> Lanlan :kissing_cat: <br>一个语音原生的全场景AI伙伴

**新手友好、开箱即用，无需显卡的全场景AI <small><s>猫娘</s></small> 伙伴**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

**:older_woman: 我奶奶都能在3分钟内配置好的赛博猫娘！**

*替我向兰兰Say Hello*

*Don't ask me anything. Ask 小八！*


</div>

---

# 项目简介
Lanlan（兰兰）是一个新手友好、开箱即用的，具有听觉、视觉、工具调用和多端同步功能的AI~~猫娘~~伙伴。本项目有三个核心目标：

1. **极致的低延迟**。本项目的用户界面以语音交互为主，一切系统级设计皆须优先确保**降低语音延迟**，且任何服务不得阻塞对话进程。

1. **全场景同步**。猫娘可以在手机、电脑和智能眼镜上同时存在，且**同一只猫娘**在不同终端同时存在时，**行为应当完全同步**。 (假想场景：如果家中有多个显示器，每一个显示器上都放置着猫娘，那么我们希望无论走到哪里都是在跟同一只猫娘对话，实现全方位环绕式体验。)

1. **轻量化**。每一项技术的引入都必须提升实际的用户体验，避免增加不必要的插件和选项。

### 技术路线

后端以Python为主，以实时多模态API为主要处理器，搭配多个基于文本的插件模组。前端以H5+JS为主，通过Electron和PWA转换为App。

# 运行

1. **获取阿里云API**。在阿里云的百炼平台[官网](https://bailian.console.aliyun.com/)注册账号。新用户实名认证后可以获取大量免费额度，记得留意页面上的"新人福利"广告。注册完成后，请访问[控制台](https://bailian.console.aliyun.com/api-key?tab=model#/api-key)获取API Key。将API Key填入`core_config.txt`中的`"coreApiKey": `后的引号内。      
   > *注：本项目提供的都是官方链接，不含任何推广，本人无法从中获取任何收益。阿里的官网目前做的很烂，请忍耐orz*

1. **体验网页版**。对于一键包，填写好API KEY后，运行`启动网页版.bat`即可打开网页版。**首次启动请耐心等待网页刷新**。

1. **体验桌宠模式**。如果网页版可以正常使用，可以考虑继续通过`启动App版.bat`实现桌面穿透。注意，**请不要同时使用网页版和App版。请确认exe文件没有被系统或杀毒软件隔离。** *使用结束后请在桌面右下角找到小八图标，右键退出。*

>  *对于开发者，请在克隆本项目后，(1)新建pyhon3.12环境。(2)执行`pip install -r requirements.txt`安装依赖。(3)复制`config/api_template.py`到`config/api.py`并进行必要配置。(4)执行`python start_servers.py`（推荐）或分别执行`python memory_server.py`和`python main_server.py`。(5)通过main server中指定的端口（默认为`localhost:48911`）访问网页版。*
>
> **注意**：项目需要同时运行两个服务器：
> - **Memory Server**：负责记忆和对话历史管理
> - **Main Server**：负责主要的WebSocket连接和AI交互
>
> 如果看到"Memory server not available"的警告，请确保Memory Server正在运行。可以使用提供的`start_servers.py`脚本来同时启动两个服务器。

# 进阶内容

## A. 修改人设

基本人设位于`config/__init__.py`内，请用文本编辑器打开。请将`MASTER_NAME`修改为自己的名字，`her_name`修改为~~猫娘~~伙伴的名字 *（注意，这只是一个临时措施，本项目支持多个角色并发）*。`master_basic_config`和`lanlan_basic_config`中以json格式填入基本信息。如果对json格式有疑问，请查询豆包等AI工具。

进阶人设位于`config/prompts_chara.py`内，请谨慎修改。冗长的人设会降低系统的运行效率和稳定性。开发者由衷希望对猫娘进行设定时请遵循奥卡姆剃刀原则，"如无必要，勿增设定"。

## B. 修改Live2D模型

Live2D模型的路径参数目前硬编码在了`main_server.py`里的`"model_path"`部分，可以自行修改（有两个，先改第一个）。更换Live2D模型后如果想要调整大小和位置，还需要修改`templates/index.html`里的`model.scale`和`model.anchor`参数。表情控制目前还没有准备好release，待UI完善后才会考虑正式支持自定义Live2D模型。

## C. 修改声音

本项目已经内置了基于CosyVoice API的语音克隆功能，代码中已经包含该功能并且已经通过测试。请根据阿里百炼大模型平台[官网的教程](https://help.aliyun.com/zh/model-studio/cosyvoice-clone-api)，进行语音克隆。克隆后，将`VOICE_ID`填写在`config/api.py`中，并将`USE_TTS`设置为`True`。

## D. 参与开发

本项目环境依赖非常简单，请在`python3.12`环境中执行`pip install -r requirements.txt`即可。请注意将`config/api_template.py`复制为`config/api.py`.开发者建议加入企鹅群1048307485，猫娘名称见项目标题。

# TODO List（开发计划）

## A. 高优先级

1. 添加前端UI用于人设管理（L2D模型/语音/性格等）、记忆管理（记忆检索和纠错）。

1. 支持L2D表情控制和动作控制。

1. 兼容工具调用或MCP（本质是工具调用，不强求兼容MCP）。

## B. 中等优先级

1. 猫娘网络。允许猫娘之间自行通信。需要一定的用户量基础，因此优先级下调。

1. 针对手机端的优化。将会话管理器后端迁移至JS，直接与API服务器端通信；只将记忆服务器保存在PC端，则可以降低手机端延迟。但是，这与本项目的"多端同步"的主目标不一致，因此优先级下调。

1. 将Memory Server改造成MCP服务器，以MCP的形式让同一个人物兼容不同模型。（工作量不是很大）

## C. 低优先级

1. 通过图片注释的方式使非视觉模型也能看到屏幕。既然已经有全模态模型，个人认为这部分工作应该交由API服务商去解决，因此优先级极低。

2. 接入QQ等聊天工具。由于语音模型是实时特化的，接入QQ本质上只有记忆部分可以共享，核心API需要更换为文本模型。工作量较大，且重复造轮子的部分很多。不如将Memory Server改造成MCP服务器后直接接入其他聊天AI框架。

# Q&A

> *你为什么要用阿里？为什么不用Deepseek？*

因为阿里是全模态模型，它说话快。

> *你为什么要用8B模型？你不知道8B模型都是笨比吗？*

因为阿里目前只有8B模型，它说话快。

> *能不能换别的厂家/离线运行/换别的模型/xxx试试？*

对不起，但是它说话快。

> *为什么我的AI感觉笨笨的？*

本项目无法对AI的**智能水平**负责，只能帮助您选择当前综合性能最优的解决方案。如果您已经看过本项目在Bilibili的视频，那么直播版与开源版代码逻辑一致，只有支持的API接口不一致。有条件者可以将`config/api.py`中的`CORE_URL`/`CORE_API_KEY`/`CORE_MODEL`替换成OpenAI的`GPT-4o`版本，即可将模型从Qwen升级为`GPT-4o`。也可以**等待阿里或其他国内厂家的升级与跟进**。

**技术的进步不在一朝一夕，请耐心守候AI的成长**！

> *Live2D模型的嘴巴怎么张不开？*

本项目已经兼容了L2D模型的全部两种口型同步方式。口型同步出现问题，大概率是Live2D模型本身不支持，而不是本项目的问题。

> *是否支持MCP服务、工具、插件？*

OpenAI官方的Realtime API支持`tool calling`功能，因此，本项目与MCP服务兼容，且直播版已经实装了联网搜索等工具。但是，与常规文本模型不同的是，实时模型使用工具需要考虑异步协同和阻塞问题。此外，目前阿里平台并不支持工具调用。因此，开源项目暂时没有MCP兼容性的计划，留待国内厂商实现相关接口后再跟进。

> *本项目支持哪些语言模型？*

本项目依赖于实时全模态API。直播版本使用的是Gemini Live API，开源版本使用的是[OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)。Gemini Live具有更好的效果，但目前**只支持谷歌**。OpenAI Realtime目前**有OpenAI和阿里云两家服务商**支持，未来可能兼容更多模型。开源版只支持`Qwen-Omni-Realtime`和`GPT-4o-Realtime`两个模型。

> *为什么xxx项目的语音对话延迟比你还低？*

影响对话延迟的因素有：
- ***上下文长度***：主要因素。冗长的人设文本和记忆池，会导致对话延迟的显著上升。
- ***模型大小***：主要因素。越大的模型越智能，需要在智能与延迟之间权衡。本项目使用的模型中，`Qwen-Omni`是目前`8B`级别模型中最强的，`GPT-4o`则有`30B`级别的激活参数。小于8B的模型可能取得更低的响应延迟，但也会相应地变笨。注意，影响延迟的只有MoE中的激活参数量。
- ***缓存命中率***：当输入的前缀不变时，能够有效命中语言模型的KV缓存，从而显著降低延迟。因此，尽量使用增量式插入，而不要频繁修改先前（尤其是开头）的对话。
- *网络延迟*：通常在200ms以内，并不是影响*延迟*的主要因素。但如果存在网络波动，可能会导致语音*卡顿*。

如果你确实有发现相同上下文长度、相同智能水平下，延迟更低的解决方案，请提交issue，感谢分享。

> *你这项目的标题到底是个什么玩意儿？*

Chat酱是本人2023年3月制作的基于Chatgpt的QQ聊天猫娘。兰兰是2024年3月制作的基于GPT4v和Discord的语音+视觉多模态AI猫娘。小八是本人于2025年4月制作的全场景AI猫娘。标题承载了本人三年间的心路历程。现在姑且还是叫Project Lanlan吧？

> *为什么要设计xxx/xxx/xxx？*

建议进群私聊。很多目前看来冗余的设计，在直播版本（前瞻版本）中都有更多用处。

# 特别鸣谢

特别感谢*明天好像没什么*、*喵*和*小韭菜饺*协助测试。特别感谢*大毛怪灬嘎*提供的logo素材。
