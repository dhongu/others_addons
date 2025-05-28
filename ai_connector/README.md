 [![License: LGPL-3](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

AI Connector
============

[<img src="./static/description/icon.png" alt="AI Connector Logo" style="width:160px;"/>](https://github.com/myrrkel/odoo-ai)

This technical module provides a connector for the AI platforms.

It can be used as a playground to test AI tools in Odoo but does not have standalone functionality.
The module is intended to be inherited by other modules for specific use cases.

## Configuration

In **Settings**, fill the **API Key** field with your generated key.

![image](./static/img/settings.png)

## Usage

### AI Completion

To create a new **AI Completion**, go to **Settings**, **Technical**, **AI Completion** and create a new record.

![image](./static/img/completion_params.png)

**Model**: The model on witch the completion will be applied.

**Target Field**: The field where the generated value will be saved.

**Domain**: The domain to select the records on witch the completion will be run.

For Completion results go to **Settings**, **Technical**, **AI Completion Results**

### Prompt template

Write a prompt template in Qweb.

Available functions in prompt template:
 - object : Current record
 - answer_lang : Function returning the language name
 - html2plaintext : Function to convert html to text

![image](./static/img/prompt.png)

### Tests

Test action will use the first record found with the domain set for the model.

Test first your prompt to adjust your template, then test the result of the Completion to adjust AI parameters.

![image](./static/img/tests.png)

### Tools (Function calling)

Many LLM (OpenAI, Mistral AI) allows to provide tools to AI model so the AI assistant will be able to get datas from Odoo to generate the correct answer.
By default, only one tool is available:

`search_question_answer` : When this tool is added to the completion, the AI will try when it's necessary to find by keywords the most relevant answers in the `AI Question Answers` table. Then the AI model can return a completion according to information in these answers.

It's possible to add more tools in **Settings**, **Technical**, **AI Tools**


### Question-Answers

To add a newQuestion-Answer go to **Settings**, **Technical**, **AI Question Answers** and create a new record.

It's also possible to generate a set of question-answer with a completion. 
In the prompt ask AI to return a JSON list of question-answer dictionary like [{'question': '...', 'answer': '...'}] and 
select the post-process function 'JSON to questions' to create the questions and answers records.


## Requirements

No requirements

## Maintainer

* This module is maintained by [Michel Perrocheau](https://github.com/myrrkel). 
* Contact me on [LinkedIn](https://www.linkedin.com/in/michel-perrocheau-ba17a4122). 

[<img src="./static/description/logo.png" style="width:200px;"/>](https://github.com/myrrkel)


