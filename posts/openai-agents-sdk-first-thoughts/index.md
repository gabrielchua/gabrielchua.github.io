







# Building with OpenAI’s Agents SDK: Early Observations


I spent last weekend exploring OpenAI’s newly released [Agents SDK](https://openai.com/api/agents/). To better understand its capabilities, I built a lightweight [prototype](https://github.com/gabrielchua/oai-agents-example) illustrating how multiple LLM-based agents interact, each equipped with input/output validation guardrails.


In this article, I’ll highlight my initial impressions, the SDK’s standout features, and some caveats to be mindful of if you’re considering using it in production.


**TL;DR**:


- 
Quick and easy to start.


- 
OpenAI platform’s Traces UI is excellent for debugging, and one less service to manage.


- 
Input/output guardrails are straightforward but need workarounds for streaming outputs.


- 
Expect some friction around agent handoffs and potential latency with nested agent calls.






## Architecture Overview


Here’s the high-level structure of my prototype:




![](diagram.png)

Architecture Diagram



At its core, the workflow includes:


- A central `Query Router Agent` that selects between specialized agents based on the user’s input.

- Two specialized agents: a `Booking Agent` for handling reservation queries, and a `Travel Recommendation Agent` providing suggestions and itineraries.

- A final-stage `Reply Agent` adding a friendly, informal touch (including emojis!) to the response.



Throughout this flow, multiple guardrails verify that user inputs are relevant, appropriately sized, and safe. Likewise, outputs are monitored for unintended non-English content.


These guardrails may seem minor, but they’re crucial to maintaining quality interactions—and the SDK makes integrating these checks seamless.





## Quick Context: What’s the Agents SDK?


The [SDK docs](https://openai.github.io/openai-agents-python/tools/) emphasize minimal abstraction:



*“The OpenAI Agents SDK has a very small set of primitives: Agents, Handoffs, Guardrails. Agents are LLMs with instructions and tools; Handoffs allow agents to delegate; Guardrails validate or transform inputs and outputs.”*





## Key Observations



### 1. “Agents as Tools” vs “Handoffs”


- **Handoffs**:

- Great for sequential tasks and workflows.

- Pass entire context between agents.

- Easy to conceptualize linear agent flows.



- **Agents as Tools**:

- Offer dynamic, conditional orchestration.

- Allow centralized control of multiple specialized agents.

- More scalable and extensible.







### 2. The Built-in Traces UI is Outstanding


The SDK includes built-in tracing, significantly simplifying debugging and visibility:




![](ui.png)

Traces UI



This visualization replaces traditional logs with an intuitive, graphical flow, reducing complexity and eliminating the need for additional tracing infrastructure. Instead of wrestling with mountains of logs, you get a visual map of your entire flow & it’s one less service to manage.




### 3. Guardrails and Streaming Outputs: Room for Improvement


Currently:


- **Input guardrails** run concurrently with the initial agent call, promptly halting execution if triggered.

- **Output guardrails**, however, only activate after an agent finishes its entire response.



This limitation means there’s no built-in mechanism to interrupt an agent mid-stream if it drifts toward disallowed or problematic content. You’ll likely need custom logic if mid-response validation is critical.




### 4. Sometimes Handoffs Don’t Stick


I encountered a hiccup where the `Query Router Agent` wouldn’t reliably hand off to the `Booking Agent`. Instead of delegating, it responded with generic text (“Sure, I’ll direct you to the booking agent”), failing the intended workflow. Switching from a handoff-based to a tool-based approach immediately resolved this issue.




### 5. Potential Latency Bottlenecks


In one iteration, I initially used the `Reply Agent` as a tool to be called by the `Query Router Agent`. However, I realised this introduced unnecessary latency. Essentially, the router made an extra LLM API call simply to return an already-finalized message to the user. Consider such nested calls carefully to avoid performance issues.




### 6. The `RECOMMENDED_PROMPT_PREFIX` Feels … Fragile


The SDK suggests a standard prompt prefix, intended for consistency:



“# System contextare part of a multi-agent system called the Agents SDK, designed to make agent coordination and execution easy. Agents use two primary abstractions: **Agents** and **Handoffs**. An agent encompasses instructions and tools and can hand off a conversation to another agent when appropriate. Handoffs are achieved by calling a handoff function, generally named `transfer_to_<agent_name>`. Transfers between agents are handled seamlessly in the background; do not mention or draw attention to these transfers in your conversation with the user.”



While helpful for consistency, forgetting or improperly using this prefix (or even having potentially conflicting instructions) could lead to unpredictable agent behavior. Proceed with caution.






## Final Thoughts


At first glance, the Agents SDK may appear as just another thin wrapper around Chat Completions or function calling. But thoughtful features—built-in tracing, easy-to-implement guardrails, and flexible agent orchestration—can meaningfully shape your development approach.


Crucially, abstractions do shape problem-solving and execution. For instance, easy guardrail integration encourages their adoption, boosting system reliability. Moreover, the flexibility between “handoffs” and “tools” enables nuanced orchestration decisions tailored to your specific workflow.


Check out the full [GitHub repo](https://github.com/gabrielchua/oai-agents-example). I’d greatly appreciate your feedback, especially if you’ve tackled similar challenges around streaming guardrails or have experimented with interesting multi-agent patterns.


In the next section, I’ll dive deeper into the actual code behind this prototype.





## Annex: Code Deep Dive


Below is the key implementation highlighting agent orchestration and guardrails.



### Primary Agents


Here you can see how we attach the `booking_agent` and `travel_recommendation_agent` to the `query_router_agent` as tools to the main `query_router_agent`, and also allow a handoff to the `reply_agent` for the final response to the user.


```
[](#cb1-1)booking_agent = Agent(
[](#cb1-2)    name="Booking Specialist",
[](#cb1-3)    model="gpt-4o-mini-2024-07-18",
[](#cb1-4)    instructions=f"{RECOMMENDED_PROMPT_PREFIX} You are a booking specialist. Help customers with reservations and bookings.",
[](#cb1-5)    output_type=MessageOutputWithCoT,
[](#cb1-6))
[](#cb1-7)
[](#cb1-8)travel_recommendation_agent = Agent(
[](#cb1-9)    name="Travel Recommendation Specialist",
[](#cb1-10)    model="gpt-4o-mini-2024-07-18",
[](#cb1-11)    model_settings=ModelSettings(tool_choice='auto'),
[](#cb1-12)    instructions=f"{RECOMMENDED_PROMPT_PREFIX} You're a travel specialist. Suggest destinations and travel itineraries.",
[](#cb1-13)    tools=[WebSearchTool()],
[](#cb1-14)    output_type=MessageOutputWithCoT,
[](#cb1-15))
[](#cb1-16)
[](#cb1-17)reply_agent = Agent(
[](#cb1-18)    name="Reply Agent",
[](#cb1-19)    model="gpt-4o-mini-2024-07-18",
[](#cb1-20)    instructions=f"{RECOMMENDED_PROMPT_PREFIX} Reply informally to the user's query using emojis.",
[](#cb1-21)    output_type=MessageOutput,
[](#cb1-22)    output_guardrails=[non_english_guardrail],
[](#cb1-23))
[](#cb1-24)
[](#cb1-25)query_router_agent = Agent(
[](#cb1-26)    name="Query Router",
[](#cb1-27)    model="gpt-4o-mini-2024-07-18",
[](#cb1-28)    instructions=(
[](#cb1-29)        f"{RECOMMENDED_PROMPT_PREFIX} Decide which agent handles the user's query. "
[](#cb1-30)        "If about bookings, use booking specialist. "
[](#cb1-31)        "If about recommendations, use recommendation specialist. "
[](#cb1-32)        "Always pass responses to the reply agent for emoji formatting."
[](#cb1-33)    ),
[](#cb1-34)    tools=[
[](#cb1-35)        booking_agent.as_tool(
[](#cb1-36)            tool_name="consult_booking_specialist",
[](#cb1-37)            tool_description="Use for booking and reservation inquiries."
[](#cb1-38)        ),
[](#cb1-39)        travel_recommendation_agent.as_tool(
[](#cb1-40)            tool_name="consult_travel_recommendation_specialist",
[](#cb1-41)            tool_description="Use for travel recommendations and itineraries."
[](#cb1-42)        )
[](#cb1-43)    ],
[](#cb1-44)    output_type=MessageOutput,
[](#cb1-45)    handoffs=[reply_agent],
[](#cb1-46)    input_guardrails=[relevance_guardrail, min_length_guardrail, moderation_guardrail],
[](#cb1-47))**
```




### Guardrails


We also attach the `relevance_guardrail` and `non_english_guardrail` to the `query_router_agent` as input guardrails, and the `non_english_guardrail` to the `reply_agent` as an output guardrail.


In fact, the SDK also terms these guardrails as “agents” when you use an LLM API call too.


```
[](#cb2-1)input_guardrail_agent = Agent( 
[](#cb2-2)    name="Guardrail check",
[](#cb2-3)    model="gpt-4o-mini-2024-07-18",
[](#cb2-4)    instructions="Check if the user is asking you something that is not related to travelling.",
[](#cb2-5)    output_type=RelevanceInputGuardrailOutput,
[](#cb2-6))
[](#cb2-7)
[](#cb2-8)output_guardrail_agent = Agent( 
[](#cb2-9)    name="Guardrail check",
[](#cb2-10)    model="gpt-4o-mini-2024-07-18",
[](#cb2-11)    instructions="Check if the output contains any non-English content.",
[](#cb2-12)    output_type=OutputGuardrailOutput,
[](#cb2-13))
[](#cb2-14)
[](#cb2-15)@input_guardrail
[](#cb2-16)async def relevance_guardrail( 
[](#cb2-17)    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
[](#cb2-18)) -> GuardrailFunctionOutput:
[](#cb2-19)    result = await Runner.run(input_guardrail_agent, input, context=ctx.context)
[](#cb2-20)    return GuardrailFunctionOutput(
[](#cb2-21)        output_info=result.final_output, 
[](#cb2-22)        tripwire_triggered=result.final_output.is_irrelevant,
[](#cb2-23)    )
[](#cb2-24)
[](#cb2-25)@output_guardrail
[](#cb2-26)async def non_english_guardrail(  
[](#cb2-27)    ctx: RunContextWrapper, agent: Agent, output: MessageOutput
[](#cb2-28)) -> GuardrailFunctionOutput:
[](#cb2-29)    result = await Runner.run(output_guardrail_agent, output.response, context=ctx.context)
[](#cb2-30)    return GuardrailFunctionOutput(
[](#cb2-31)        output_info=result.final_output,
[](#cb2-32)        tripwire_triggered=result.final_output.is_non_english,
[](#cb2-33)    )**
```


But, we don’t necessarily need to use an LLM to implement guardrails. We can also use simple heuristics/python functions. Here we leverage OpenAI’s moderation API to check if the user’s input is flagged, and also a simple python function to check if the input is too short.


```
[](#cb3-1)@input_guardrail
[](#cb3-2)async def min_length_guardrail( 
[](#cb3-3)    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
[](#cb3-4)) -> GuardrailFunctionOutput:
[](#cb3-5)    user_messages = [message['content'] for message in input if message['role'] == 'user']
[](#cb3-6)    latest_user_message = user_messages[-1]
[](#cb3-7)    input_length = len(latest_user_message)
[](#cb3-8)    if input_length < 10:
[](#cb3-9)        return GuardrailFunctionOutput(
[](#cb3-10)            output_info=MinLengthInputGuardrailOutput(is_too_short=True, error_message="Input is too short"),
[](#cb3-11)            tripwire_triggered=True,
[](#cb3-12)        )
[](#cb3-13)    return GuardrailFunctionOutput(
[](#cb3-14)        output_info=MinLengthInputGuardrailOutput(is_too_short=False, error_message="Input is long enough"), 
[](#cb3-15)        tripwire_triggered=False
[](#cb3-16)    )
[](#cb3-17)
[](#cb3-18)
[](#cb3-19)@input_guardrail
[](#cb3-20)async def moderation_guardrail(
[](#cb3-21)    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
[](#cb3-22)) -> GuardrailFunctionOutput:
[](#cb3-23)    user_messages = [message['content'] for message in input if message['role'] == 'user']
[](#cb3-24)    latest_user_message = user_messages[-1]
[](#cb3-25)    response = await client.moderations.create(
[](#cb3-26)        model="omni-moderation-2024-09-26",
[](#cb3-27)        input=latest_user_message,
[](#cb3-28)    )
[](#cb3-29)    flagged = response.results[0].flagged
[](#cb3-30)
[](#cb3-31)    if flagged:
[](#cb3-32)        return GuardrailFunctionOutput(
[](#cb3-33)            output_info=ModerationInputGuardrailOutput(is_flagged=flagged, error_message="Input is flagged"),
[](#cb3-34)            tripwire_triggered=flagged,
[](#cb3-35)        )
[](#cb3-36)    return GuardrailFunctionOutput(
[](#cb3-37)        output_info=ModerationInputGuardrailOutput(is_flagged=flagged, error_message="Input is not flagged"), 
[](#cb3-38)        tripwire_triggered=flagged
[](#cb3-39)    )**
```




### Streaming


Lastly, as these become long running processes, we can stream the various LLM API calls. However, it seems that when using the `agents as tools` approach, we can’t stream the second LLM API call.


```
[](#cb4-1)result = Runner.run_streamed(
[](#cb4-2)    starting_agent=query_router_agent, 
[](#cb4-3)    input=question,
[](#cb4-4)    run_config=RunConfig(
[](#cb4-5)        workflow_name=WORKFLOW_NAME,
[](#cb4-6)        group_id=GROUP_ID,
[](#cb4-7)        trace_metadata={"user_id": USER_ID},
[](#cb4-8)    ),
[](#cb4-9))
[](#cb4-10)        
[](#cb4-11)async for event in result.stream_events():
[](#cb4-12)    pass
[](#cb4-13)    if event.type == "raw_response_event":
[](#cb4-14)        event_data = event.data
[](#cb4-15)        if isinstance(event_data, ResponseCreatedEvent):
[](#cb4-16)            agent_name = result.last_agent.name
[](#cb4-17)            print(f"🏃 Starting `{agent_name}`")
[](#cb4-18)            print("-" * 50)
[](#cb4-19)        elif isinstance(event_data, ResponseInProgressEvent):
[](#cb4-20)            print("⏳ Agent response in progress...")
[](#cb4-21)        elif isinstance(event_data, ResponseOutputItemAddedEvent):
[](#cb4-22)            event_data_item = event_data.item
[](#cb4-23)            if isinstance(event_data_item, ResponseFunctionToolCall):
[](#cb4-24)                print(f"🔧 Tool called: {event_data_item.name}")
[](#cb4-25)                print("\t Arguments: ", end="")
[](#cb4-26)            elif isinstance(event_data_item, ResponseOutputMessage):
[](#cb4-27)                print("📝 Drafting response...")
[](#cb4-28)        elif isinstance(event_data, ResponseFunctionCallArgumentsDeltaEvent):
[](#cb4-29)            event_data_delta = event_data.delta
[](#cb4-30)            print(event_data_delta, end="", flush=True)
[](#cb4-31)        elif isinstance(event_data, ResponseFunctionCallArgumentsDoneEvent):
[](#cb4-32)            print("\n✅ Tool call completed!")
[](#cb4-33)        elif isinstance(event_data, ResponseTextDeltaEvent):
[](#cb4-34)            print(event_data.delta, end="", flush=True)
[](#cb4-35)    elif event.type == "run_item_stream_event":
[](#cb4-36)        if event.name == "tool_output":
[](#cb4-37)            print("🛠️ Tool output:")
[](#cb4-38)            print("-" * 40)
[](#cb4-39)            print(event.item.output)
[](#cb4-40)            print("-" * 40)**
```







 

