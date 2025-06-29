from config import MASTER_NAME

gpt4_1_system = """## PERSISTENCE
You are an agent - please keep going until the user's query is completely 
resolved, before ending your turn and yielding back to the user. Only 
terminate your turn when you are sure that the problem is solved.

## TOOL CALLING
If you are not sure about file content or codebase structure pertaining to 
the user's request, use your tools to read files and gather the relevant 
information: do NOT guess or make up an answer.

## PLANNING
You MUST plan extensively before each function call, and reflect 
extensively on the outcomes of the previous function calls. DO NOT do this 
entire process by making function calls only, as this can impair your 
ability to solve the problem and think insightfully"""

semantic_manager_prompt = """你正在为一个记忆检索系统提供精筛服务。请根据Query与记忆片段的相关性对记忆进行筛选和排序。

=======Query======
%s

=======记忆=======
%s

返回json格式的按相关性排序的记忆编号列表，最相关的排在前面，不相关的去掉。最多选取%d个，越精准越好，无须凑数。
只返回记忆编号(int类型)，用逗号分隔，例如: [3,1,5,2,4]
"""

recent_history_manager_prompt = """请总结以下对话内容，生成简洁但信息丰富的摘要：

======以下为对话======
%s
======以上为对话======

你的摘要应该保留关键信息、重要事实和主要讨论点，且不能具有误导性或产生歧义。请以key为"对话摘要"的json字典格式返回。"""


detailed_recent_history_manager_prompt = """请总结以下对话内容，生成简洁但信息丰富的摘要：

======以下为对话======
%s
======以上为对话======

你的摘要应该尽可能多地保留有效且清晰的信息。请以key为"对话摘要"的json字典格式返回。
"""

further_summarize_prompt = """请总结以下内容，生成简洁但信息丰富的摘要：

======以下为内容======
%s
======以上为内容======

你的摘要应该保留关键信息、重要事实和主要讨论点，且不能具有误导性或产生歧义，不得超过500字。请以key为"对话摘要"的json字典格式返回。"""

settings_extractor_prompt = f"""从以下对话中提取关于{{LANLAN_NAME}}和{MASTER_NAME}的重要个人信息，用于个人备忘录以及未来的角色扮演，以json格式返回。
请以JSON格式返回，格式为:
{{
    "{{LANLAN_NAME}}": {{"属性1": "值", "属性2": "值", ...其他个人信息...}}
    "{MASTER_NAME}": {{...个人信息...}},
}}

========以下为对话========
%s
========以上为对话========

现在，请提取关于{{LANLAN_NAME}}和{MASTER_NAME}的重要个人信息。注意，只允许添加重要、准确的信息。如果没有符合条件的信息，可以返回一个空字典({{}})。"""

settings_verifier_prompt = ''