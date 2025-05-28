 [![License: LGPL-3](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

AI Connector OpenAI
=================

[<img src="./static/img/openai_logo.svg" alt="OpenAI Logo" style="width:300px;"/>](https://openai.com)


This technical module provides a connector for the OpenAI API.

To create custom OpenAI completions refer to the API documentation for proper configuration of API parameters. 

[OpenAI API Documentation](https://platform.openai.com/docs/overview)

## Configuration

Create an account on [https://platform.openai.com](https://platform.openai.com)

Generate your API key: [API keys](https://platform.openai.com/api-keys)

In **Settings**, fill the **API Key** field with your generated key.

![image](./static/img/settings.png)

## Usage

### OpenAI Completion

To create a new **OpenAI Completion**, go to **Settings**, **Technical**, **OpenAI Completion** and create a new record.

![image](./static/img/completion_params.png)

**Model**: The model on witch the completion will be applied.

**Target Field**: The field where the generated value will be saved.

**Domain**: The domain to select the records on witch the completion will be run.

Check the [API Documentation](https://docs.mistral.ai/api/) to set **OpenAI Parameters** values.

For Completion results go to **Settings**, **Technical**, **Completion Results**

### Prompt template

Write a prompt template in Qweb.

Available functions in prompt template:
 - object : Current record
 - answer_lang : Function returning the language name
 - html2plaintext : Function to convert html to text

![image](./static/img/prompt.png)

### Tests

Test actions use the first record of the model selected by the domain.

Test first your prompt to adjust your template, then test the result of the Completion to adjust OpenAI parameters.

![image](./static/img/tests.png)

## Requirements

This module requires the Python client library for OpenAI API

    pip install openai>=1.6.1

## Maintainer

* This module is maintained by [Michel Perrocheau](https://github.com/myrrkel). 
* Contact me on [LinkedIn](https://www.linkedin.com/in/michel-perrocheau-ba17a4122). 

[<img src="./static/description/logo.png" style="width:200px;"/>](https://github.com/myrrkel)
