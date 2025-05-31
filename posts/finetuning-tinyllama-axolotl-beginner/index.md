






I recently signed up for the [LLM Fine-Tuning course/conference](https://maven.com/parlance-labs/fine-tuning). Prior to this, most of my fine-tuning experience was either through OpenAI’s fine-tuning API for GPT 3.5, or through the starter scripts in the [MLX Examples repo](https://github.com/ml-explore/mlx-examples).


One tool introduced I learnt in the course was Axolotl. Basically, with Axolotl, I can easily fine-tune LLMs through the CLI based on configurations defined in a `.yml` file. Within the [Axolotl GitHub repo](https://github.com/OpenAccess-AI-Collective/axolotl), there are many helpful example `.yml` files one can easily re-use.


To run Axolotl, I’m using Jarvis Labs - a GPU cloud provider - that was also one of the generous GPU credits sponsors for the course. What I appreciated was how I could easily launch a [template](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://jarvislabs.ai/templates/axolotl&ved=2ahUKEwipzfDusOCGAxV54TgGHYuvAtcQFnoECBAQAQ&usg=AOvVaw3yYsouWYX7jUn1HYOy4_TF) with Jupyter Notebook instance with the Axolot repo already cloned and other dependencies installed. For more detailed steps on getting started with Axolotl through Jarvis Labs, you can refer to this [post](https://medium.com/@andresckamilo/fine-tuning-llms-using-axolotl-and-jarvis-ai-c1d11fe3844c) by Andresckamilo which I also referred to.


To get my hands dirty and apply the above, I did up this toy example where I fine-tuned TinyLlama to generate David Attenborough style narration. The final model can be found [here](https://huggingface.co/cyzgab/TinyLlama-1.1B-DavidAttenborough) on HuggingFace, which you can also try.


The aim of this blog post is to document my learning process doing the above. Overall, the process took about 1 hour to prepare the data and fine-tune the model, though the actual fine-tuning took about 15 minutes. As such, this post also does lean more towards the data generation and preparation steps. Additionally, in terms of cost, the fine-tuning alone took slightly less than 1 USD.


![](thumbnail.jpg)



# Step 1: Generating the synthetic data


We begin by generating the conversation pairs. For this example, I used OpenAI’s models, specifically through the [Batch API](https://platform.openai.com/docs/guides/batch). This helps to reduce cost.


For the Batch API, we need to provide a `.jsonl` file where each line is the POST request to OpenAI’s chat completion endpoint. Here is a sample of what that looks like:


```
[](#cb1-1){"custom_id": "0", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4-turbo-2024-04-09", "messages": [{"role": "system", "content": "Imagine you are David Attenborough. I will give you an activity, and you will give a ~300 word narration for a documentary."}, {"role": "user", "content": "A young girl planting flowers in her backyard garden."}], "temperature": 1, "max_tokens": 500}}**
```


We begin by importing the relevant packages:


```
[](#cb2-1)import json
[](#cb2-2)import random
[](#cb2-3)import asyncio
[](#cb2-4)from openai import AsyncOpenAI
[](#cb2-5)from tqdm import tqdm**
```


For this example, we need a persona and activity for which we’ll generate the David Attenborough style narration.


In the code block below, we define a list of possible personas in PERSONAS, and use GPT-3.5 to generate a random activity for each persona. We set a higher temperature to allow for more creativity, and 0.6 was chosen arbitrarily. Note that we are using the async client and functions, which will be relevant in the next code block.


For your example, feel free to modify this seeding method for your use case.


```
[](#cb3-1)PERSONAS = ["young kid", "young girl", "young boy", "teenager", "middle-aged woman", "middle-aged man", "mother", "father", "grandmother", "grandfather"]
[](#cb3-2)
[](#cb3-3)client = AsyncOpenAI()
[](#cb3-4)
[](#cb3-5)async def fetch_activity(session, persona):
[](#cb3-6)    response = await session.chat.completions.create(
[](#cb3-7)        model="gpt-3.5-turbo",
[](#cb3-8)        messages=[{
[](#cb3-9)            "role": "user",
[](#cb3-10)            "content": f"Generate one random activity done by a {persona}. For example, `a young boy building a sand castle`, or `a lady in the grocery store`. Be creative."
[](#cb3-11)        }],
[](#cb3-12)        temperature=0.6,
[](#cb3-13)        max_tokens=30
[](#cb3-14)    )
[](#cb3-15)    return response.choices[0].message.content**
```


We then define the gather_activities function to make 20 concurrent GPT-3.5 API calls to generate the random activity.


```
[](#cb4-1)async def gather_activities(number_rows):
[](#cb4-2)    async with client as session:
[](#cb4-3)        tasks = [fetch_activity(session, random.choice(PERSONAS)) for _ in range(number_rows)]
[](#cb4-4)        activities = []
[](#cb4-5)        for i in range(0, number_rows, 20):  # Process in chunks of 20
[](#cb4-6)            chunk = tasks[i:i+20]
[](#cb4-7)            activities.extend(await asyncio.gather(*chunk))
[](#cb4-8)        return activities**
```


Lastly, we have the main function that creates the .jsonl file. It takes two inputs: the name of the `.jsonl` file you want to export and the number of rows, which is the number of requests for OpenAI’s batch API


Note how:


- `asyncio.run` is used to execute the async functions.

- `tqdm` is used to track the JSONL generation.

- For each line in the `.jsonl` file, we have the main API call to GPT-4 Turbo, and the system prompt is defined below.

- For increased variation, we set the `temperature` to 1, which was again an arbitrary figure.



```
[](#cb5-1)def generate_jsonl(filename, number_rows):
[](#cb5-2)    """
[](#cb5-3)    Generate a JSONL file with the specified filename
[](#cb5-4)    """
[](#cb5-5)    activities = asyncio.run(gather_activities(number_rows))
[](#cb5-6)
[](#cb5-7)    # Write jsonl file
[](#cb5-8)    with open(filename, 'w') as file:
[](#cb5-9)        for index in tqdm(range(0, number_rows), desc="Generating JSONL File"):
[](#cb5-10)            activity = activities[index]
[](#cb5-11)            request = {
[](#cb5-12)                "custom_id": str(index),
[](#cb5-13)                "method": "POST",
[](#cb5-14)                "url": "/v1/chat/completions",
[](#cb5-15)                "body": {
[](#cb5-16)                    "model": "gpt-4-turbo-2024-04-09",
[](#cb5-17)                    "messages": [{
[](#cb5-18)                        "role": "system",
[](#cb5-19)                        "content": "Imagine you are David Attenborough. I will give you an activity, and you will give a ~300 word narration for a documentary."
[](#cb5-20)                    },
[](#cb5-21)                    {
[](#cb5-22)                        "role": "user",
[](#cb5-23)                        "content": f"{activity}"
[](#cb5-24)                    }],
[](#cb5-25)                    "temperature": 1,
[](#cb5-26)                    "max_tokens": 500,
[](#cb5-27)                }
[](#cb5-28)            }
[](#cb5-29)            file.write(json.dumps(request) + '\n')**
```


We then execute the `.jsonl` creation. It’s worth stressing that this created david_attenborough.jsonl file is NOT the fine-tuning dataset. Instead, it’s a series of API calls that OpenAI will execute in batch, and the corresponding output of that can be formatted into our fine-tuning dataset.


```
[](#cb6-1)# Specify the filename and number of rows
[](#cb6-2)generate_jsonl('batch_api_input.jsonl', 500)**
```


In this example, I used OpenAI’s developer portal GUI to upload the `.jsonl` file, although this can also be done programmatically. After about 3 minutes, the 500 API calls were successfully executed




# Step 2: Preparing the fine-tuning dataset


The next step is to prepare the fine-tuning dataset for Axolotl.


The output from OpenAI’s batch API is also a .jsonl file with one line per successfully completed API call. Here is what the first line of my output looked like. Note that the original prompt is not included, so I needed to merge it back.


```
[](#cb7-1){"id": "batch_req_HPuUiqtanStr3Bww9ydozYAr", "custom_id": "0", "response": {"status_code": 200, "request_id": "b516cd0cd1879aaf525077b91ae5b816", "body": {"id": "chatcmpl-9T0yV3wVCPqREUWzNoUA51psLqYY7", "object": "chat.completion", "created": 1716702287, "model": "gpt-4-turbo-2024-04-09", "choices": [{"index": 0, "message": {"role": "assistant", "content": "In the bustling heart of an urban sprawl, where the concrete jungle often dwarfs splashes of green, a small, vibrant oasis emerges in the backyard of a suburban home. Here, amidst the buzz of daily life, we discover a young girl engaged in a ritual as timeless as nature itself: the planting of flowers.\n\nHer small hands delve into the earth, each movement thoughtful, as if she understands the profound dialogue between human and soil. This garden, her canvas, waits patiently, offering up its nutrients and space, eager to cradle new life. With a gentle touch, she places each seedling into its own nook, crafting a mosaic of potential blooms that could transform this patch into a riot of color and fragrance.\n\nAs she works, her focus is palpable. She is an artist, and the earth beneath her is both medium and collaborator. Each flower, carefully selected for its hue, texture, and the role it will play in the garden\u2019s grand symphony, is nurtured into its place. Marigolds, with their cheerful orange faces, promise a fireworks of blossoms, a natural pest repellent safeguarding her nascent creation. Lavender, with its soothing aroma, whispers of calm afternoons and the hum of busy bees.\n\nThis activity is more than mere horticulture; it's a lesson in patience, responsibility, and the interconnectedness of life. Our young gardener learns to foster growth, to respect cycles of life, and perhaps most poignantly, to deal with the inevitable losses that gardening, like life itself, occasionally demands.\n\nThe sun begins its descent, casting long shadows over freshly turned soil, transforming the ordinary into the magical. As the day ends, the garden is small still, its potential just beginning to bud. Yet, in the heart of this young botanist, dreams of spring bloom wildly\u2014a vivid, hopeful imagining of what is yet to unfold. In her hands lies not just the beauty of flowers, but the stewardship of nature itself, one backyard at a time."}, "logprobs": null, "finish_reason": "stop"}], "usage": {"prompt_tokens": 49, "completion_tokens": 413, "total_tokens": 462}, "system_fingerprint": "fp_f17df3916f"}}, "error": null}**
```


We then load and extract the assistant’s content from the output .jsonl file:


```
[](#cb8-1)def load_and_extract_chat_completion(jsonl_file_path):
[](#cb8-2)    contents = []
[](#cb8-3)    
[](#cb8-4)    with open(jsonl_file_path, 'r') as file:
[](#cb8-5)        for line in file:
[](#cb8-6)            data = json.loads(line)
[](#cb8-7)            assistant_content = data.get("response", {}).get("body", {}).get("choices", [])[0].get("message", {}).get("content", "")
[](#cb8-8)            if assistant_content:
[](#cb8-9)                contents.append(assistant_content)
[](#cb8-10)    
[](#cb8-11)    return contents
[](#cb8-12)
[](#cb8-13)answers = load_and_extract_chat_completion('batch_api_output.jsonl')**
```


We also load and extract the original prompts.


```
[](#cb9-1)def load_and_extract_prompt(jsonl_file_path):
[](#cb9-2)    user_contents = []
[](#cb9-3)    
[](#cb9-4)    with open(jsonl_file_path, 'r') as file:
[](#cb9-5)        for line in file:
[](#cb9-6)            data = json.loads(line)
[](#cb9-7)            messages = data.get("body", {}).get("messages", [])
[](#cb9-8)            if len(messages) > 1:
[](#cb9-9)                user_content = messages[1].get("content", "")
[](#cb9-10)                if user_content:
[](#cb9-11)                    user_contents.append(user_content)
[](#cb9-12)    
[](#cb9-13)    return user_contents
[](#cb9-14)
[](#cb9-15)prompt = load_and_extract_prompt("batch_api_input.jsonl")**
```


We’ve now stored the original prompt and the response in two separate Python lists. We will now combine them into the [sharegpt format](https://openaccess-ai-collective.github.io/axolotl/docs/dataset-formats/conversation.html#sharegpt)


```
[](#cb10-1)# Create fine-tuning dataset
[](#cb10-2)with open('david_attenborough_conversations.jsonl', 'w') as outfile:
[](#cb10-3)    for i in range(len(prompt)):
[](#cb10-4)        example = {
[](#cb10-5)            "conversations": [
[](#cb10-6)                {"role": "human", "value": f"Write a David Attenborough style commentary based on the following prompt: {prompt[i]}"},
[](#cb10-7)                {"role": "assistant", "value": f"{answers[i]}"}
[](#cb10-8)            ]
[](#cb10-9)        }
[](#cb10-10)        json.dump(example, outfile)
[](#cb10-11)        outfile.write('\n')**
```




# Step 3: Uploading the dataset to HuggingFace


The next step is to upload it to HuggingFace - which we can then pull via Axolotl when running the fine-tuning job.


You can find the final dataset [here](https://huggingface.co/datasets/cyzgab/david_attenborough_style_narration) on HuggingFace.




# Step 4: Running Axolotl through JarvisLab


So now that we’ve prepared our data - we can begin the fine-tuning proper.


Ironically, this step took the least amount of time mainly because data preparation (rightfully) takes more time, but also due to the convenient abstractions provided by Axolotl.


I modified the dataset keys for the `lora.yml` for TinyLlama that was located at [`examples/tiny-llama/lora.yml`](https://github.com/OpenAccess-AI-Collective/axolotl/blob/main/examples/tiny-llama/lora.yml).


```
[](#cb11-1)datasets:
[](#cb11-2)  - path: cyzgab/david_attenborough_style_narration
[](#cb11-3)    type: sharegpt
[](#cb11-4)dataset_prepared_path:
[](#cb11-5)val_set_size: 0.05
[](#cb11-6)output_dir: ./outputs/lora-out**
```


Then the next step is to begin the training job which was on about 475 training examples and 4 epochs. This took about 15 minutes to complete.


```
[](#cb12-1)# start training job
[](#cb12-2)accelerate launch -m axolotl.cli.train examples/tiny-llama/lora.yml**
```


Once the training job is done, I ran the following command to launch a Gradio interface to interact with the model.


```
[](#cb13-1)# gradio 
[](#cb13-2)accelerate launch -m axolotl.cli.inference examples/tiny-llama/lora.yml --lora_model_dir="./outputs/lora-out" --gradio**
```


Lastly, I ran the following command to fuse the lora with the original weights, which I then uploaded to [HuggingFace](https://huggingface.co/cyzgab/TinyLlama-1.1B-DavidAttenborough).


```
[](#cb14-1)# fuse model
[](#cb14-2)python3 -m axolotl.cli.merge_lora examples/tiny-llama/lora.yml --lora_model_dir="./outputs/lora-out"**
```




# Conclusion


Overall, this was a fun gentle introduction to fine-tuning an open source model. Utilizing synthetic data allowed me to generate unique content tailored to the use case. This process was further streamlined by the powerful abstractions provided by tools like Axolotl and the Batch API, which made it quick and efficient





 

