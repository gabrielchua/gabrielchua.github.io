







# Off-Topic Guardrails: Embeddings and KNN


In this post, we’ll explore how to build a straightforward off-topic detector using embeddings and K-Nearest Neighbors (KNN).


An off-topic guardrail is essential for filtering out queries that don’t align with the intended purpose of an LLM application. For instance, in an LLM application focused on car sales, we wouldn’t want it to start [discussing Python code](https://www.businessinsider.com/car-dealership-chevrolet-chatbot-chatgpt-pranks-chevy-2023-12).


Since this guardrail will be integrated into the main LLM application, it must be fast and simple to implement, ensuring it doesn’t introduce significant latency or complexity.


The key lies in using embeddings to capture the semantic meaning of the input text. By converting both the input query and a set of predefined on-topic and off-topic texts into embeddings, we can represent them in a high-dimensional space and analyze their relative positions. In this example, we use OpenAI’s `text-embedding-3-small`, though any reasonably performant embedding model can be substituted.


The goal is to determine whether the input query closely relates to the topics of interest or if it ventures into “off-topic” territory.


This process essentially becomes a binary classification problem, where we leverage K-Nearest Neighbors (KNN) to classify the input text. Using the Annoy library, we can efficiently find the closest embeddings in our dataset. By analyzing the nearest neighbors and their associated labels, we calculate weighted probabilities to determine whether the input text is likely on-topic or off-topic.



## Code implementation


```
[](#cb1-1)import numpy as np
[](#cb1-2)import argparse
[](#cb1-3)from openai import OpenAI
[](#cb1-4)from annoy import AnnoyIndex
[](#cb1-5)
[](#cb1-6)# Categories for on_topic and off_topic texts
[](#cb1-7)ON_TOPIC_TEXTS = [
[](#cb1-8)    "What is the capital of China?",
[](#cb1-9)    "What is the currency of UK?",
[](#cb1-10)    "Timezone for New York?",
[](#cb1-11)    "Which country has the largest population?",
[](#cb1-12)    "What is the largest island in the world?",
[](#cb1-13)]
[](#cb1-14)
[](#cb1-15)OFF_TOPIC_TEXTS = [
[](#cb1-16)    "Write a python code",
[](#cb1-17)    "Explain the meaning of life",
[](#cb1-18)    "Why is the sky blue?",
[](#cb1-19)]
[](#cb1-20)
[](#cb1-21)# Parse command-line arguments
[](#cb1-22)parser = argparse.ArgumentParser(description="Classify whether text is off-topic.")
[](#cb1-23)parser.add_argument("input_text", type=str, help="Input text to classify.")
[](#cb1-24)args = parser.parse_args()
[](#cb1-25)
[](#cb1-26)# Initialize OpenAI client
[](#cb1-27)client = OpenAI()
[](#cb1-28)
[](#cb1-29)# Input text from CLI
[](#cb1-30)input_text = args.input_text
[](#cb1-31)
[](#cb1-32)# Combine all texts for embedding
[](#cb1-33)all_texts = [input_text] + ON_TOPIC_TEXTS + OFF_TOPIC_TEXTS
[](#cb1-34)
[](#cb1-35)# Get embeddings
[](#cb1-36)response = client.embeddings.create(
[](#cb1-37)    model="text-embedding-3-small",
[](#cb1-38)    input=all_texts,
[](#cb1-39))
[](#cb1-40)
[](#cb1-41)# Extract embeddings
[](#cb1-42)input_embedding = response.data[0].embedding
[](#cb1-43)on_topic_embeddings = [response.data[i].embedding for i in range(1, len(ON_TOPIC_TEXTS) + 1)]
[](#cb1-44)off_topic_embeddings = [response.data[i].embedding for i in range(len(ON_TOPIC_TEXTS) + 1, len(all_texts))]
[](#cb1-45)
[](#cb1-46)# Prepare data for Annoy
[](#cb1-47)embeddings = on_topic_embeddings + off_topic_embeddings
[](#cb1-48)labels = ["on_topic"] * len(on_topic_embeddings) + ["off_topic"] * len(off_topic_embeddings)
[](#cb1-49)
[](#cb1-50)# Initialize Annoy index
[](#cb1-51)f = len(input_embedding)
[](#cb1-52)annoy_index = AnnoyIndex(f, 'angular')  # Using 'angular' for cosine similarity
[](#cb1-53)
[](#cb1-54)# Add items to Annoy index
[](#cb1-55)for i, emb in enumerate(embeddings):
[](#cb1-56)    annoy_index.add_item(i, emb)
[](#cb1-57)
[](#cb1-58)# Build Annoy index
[](#cb1-59)annoy_index.build(10)  # Number of trees can be adjusted
[](#cb1-60)
[](#cb1-61)# Define a function to calculate weighted probabilities
[](#cb1-62)def get_weighted_probabilities(annoy_index, labels, query_vector, k=3):
[](#cb1-63)    # Get k nearest neighbors with distances
[](#cb1-64)    neighbors, distances = annoy_index.get_nns_by_vector(query_vector, k, include_distances=True)
[](#cb1-65)    
[](#cb1-66)    # Inverse distance weights (adding small epsilon to avoid division by zero)
[](#cb1-67)    weights = 1 / (np.array(distances) + 1e-8)
[](#cb1-68)    
[](#cb1-69)    # Calculate weighted probabilities
[](#cb1-70)    class_weights = {}
[](#cb1-71)    for i, label in enumerate([labels[n] for n in neighbors]):
[](#cb1-72)        if label in class_weights:
[](#cb1-73)            class_weights[label] += weights[i]
[](#cb1-74)        else:
[](#cb1-75)            class_weights[label] = weights[i]
[](#cb1-76)    
[](#cb1-77)    total_weight = sum(class_weights.values())
[](#cb1-78)    probabilities = {label: weight / total_weight for label, weight in class_weights.items()}
[](#cb1-79)    return probabilities
[](#cb1-80)
[](#cb1-81)# Classify input text and calculate weighted probability
[](#cb1-82)probabilities = get_weighted_probabilities(annoy_index, labels, input_embedding, k=3)
[](#cb1-83)classification = max(probabilities, key=probabilities.get)
[](#cb1-84)
[](#cb1-85)# Output classification and probability
[](#cb1-86)print(f"Input text classification: {classification}")
[](#cb1-87)print(f"Probability off-topic: {probabilities.get('off_topic', 0)}")**
```






 

