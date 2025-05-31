






Jina AI released their new multimodal embedding model - `jina-clip-v1` this week. It’s under an Apache 2.0 license and it can be downloaded/used via HuggingFace. You can find out more details about the model from their [blog](https://jina.ai/news/jina-clip-v1-a-truly-multimodal-embeddings-model-for-text-and-image/) and the [technical report](https://arxiv.org/abs/2405.20204).


At the same time, I’m co-organising the [Build Together Hackathon @ Singapore](https://lu.ma/igqisb0e) this weekend, and Ivan who was speaking managed to get the hackathon participants access to [LanceDB](https://lancedb.com/) Cloud, which I understand to be under technical preview. I last tried LanceDB at a hackathon, and thought trying the two tools would make a fun side quest today.


The objective of this blog post is to provide a simple code introduction and I highlight some of my learnings (e.g. how the embedding API does not automatically resize the image, using pydantic to define the db schema). The code below can certainly be further optimised with the batching of the API calls and data loading.




![](thumbnail.jpg)

Mandatory “a picture paints a thousand words” photo for a blog about image-type models. Photo is by [Daian Gan](https://www.pexels.com/photo/shallow-focus-photography-of-paintbrush-102127/




# Step 1: Connecting to LanceDB Cloud


Let’s begin by defining some constants related to LanceDB Cloud - the vector database’s URI and the API key. We can then connect to the database.


```
[](#cb1-1)import os
[](#cb1-2)import lancedb
[](#cb1-3)
[](#cb1-4)# Load API keys from environment variables
[](#cb1-5)LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
[](#cb1-6)LANCEDB_URI = os.getenv("LANCEDB_URI")
[](#cb1-7)
[](#cb1-8)# Connect to the database
[](#cb1-9)db = lancedb.connect(
[](#cb1-10)        uri=LANCEDB_URI,
[](#cb1-11)        api_key=LANCEDB_API_KEY,
[](#cb1-12)        region="us-east-1"
[](#cb1-13)    )**
```


The `lancedb.connect` line is the main difference between using LanceDB locally and via their cloud managed service - so transitioning between the two is that easy. If you’re using it locally, the URI will be the filepath of your choice, and you won’t need the api_key or region argument.. Also, do note that we’re using LanceDB’s synchronous API throughout this blog.


```
[](#cb2-1)LOCAL_FILE_PATH = "xxx"
[](#cb2-2)
[](#cb2-3)db = lancedb.connect(
[](#cb2-4)        uri=LOCAL_FILE_PATH,
[](#cb2-5)    )**
```




# Step 2: Helper functions to get multimodal embeddings


In this example, we’re using Jina AI’s API service. As part of the free trial, you have free credits to process up to 1M tokens.


Let’s go into the code. We begin by loading the API key too.


```
[](#cb3-1)JINA_API_KEY = os.getenv("JINA_API_KEY")**
```


According to the [docs](https://api.jina.ai/redoc#tag/embeddings/operation/create_embedding_v1_embeddings_post), the image sent to the API can either be a URL or bytes. Hence, we write the following helper code below to encode the image to base64.




![](jina_docs.png)

Screenshot of Jina API Docs



```
[](#cb4-1)import base64
[](#cb4-2)from io import BytesIO
[](#cb4-3)
[](#cb4-4)# Encode an image to base 64
[](#cb4-5)def image_to_base64(image):
[](#cb4-6)    buffered = BytesIO()
[](#cb4-7)    image.save(buffered, format="PNG")
[](#cb4-8)    return base64.b64encode(buffered.getvalue()).decode('utf-8')**
```


What about the size of the image? According to their [blog](https://jina.ai/news/jina-clip-v1-a-truly-multimodal-embeddings-model-for-text-and-image/), every 224x224 pixel tile in the image is 1,000 tokens. I didn’t know that initially and assumed that the image would be automatically resized to a suitable size in the backend. I accidentally sent in a ~1MB image, and used almost half of my free credits.


For how tokens are counted for images larger than 224x224, let’s refer to the example from their blog.



For an image with dimensions 750x500 pixels:


- The image is divided into 224x224 pixel tiles.

- To calculate the number of tiles, take the width in pixels and divide by 224, then round up to the nearest integer. 750/224 ≈ 3.35 → 4

- Repeat for the height in pixels: 500/224 ≈ 2.23 → 3

- The total number of tiles required in this example is: 4 (horizontal) x 3 (vertical) = 12 tiles

- The cost will be 12 x 1,000 = 12,000 tokens




Hence, I’ve written a simple helper function to resize the image to the lowest tile resolution the model takes in - which is 224x224


```
[](#cb5-1)from PIL import Image
[](#cb5-2)
[](#cb5-3)# Resize image to 214x214
[](#cb5-4)def resize_image(image_file_path, size=(224, 224)):
[](#cb5-5)    """ Resize image to fit within the given size (224, 224) """
[](#cb5-6)    with Image.open(image_file_path) as img:
[](#cb5-7)        img.thumbnail(size, Image.LANCZOS)
[](#cb5-8)        return img**
```


With these two helper functions, we can now write our main embedding function which does a POST request.


```
[](#cb6-1)import json
[](#cb6-2)import requests
[](#cb6-3)
[](#cb6-4)def get_embeddings(image_file_path):
[](#cb6-5)    headers = {
[](#cb6-6)        'Content-Type': 'application/json',
[](#cb6-7)        'Authorization': f'Bearer {JINA_API_KEY}'
[](#cb6-8)    }
[](#cb6-9)
[](#cb6-10)    resized_image = resize_image(image_file_path)
[](#cb6-11)
[](#cb6-12)    base64_image = image_to_base64(resized_image)
[](#cb6-13)    
[](#cb6-14)    data = {
[](#cb6-15)        'input': [{"bytes": base64_image}],
[](#cb6-16)        'model': 'jina-clip-v1',
[](#cb6-17)        'encoding_type': 'float'
[](#cb6-18)        }
[](#cb6-19)
[](#cb6-20)    response = requests.post(JINA_ENDPOINT,
[](#cb6-21)                             headers=headers,
[](#cb6-22)                             json=data)
[](#cb6-23)    
[](#cb6-24)    results = json.loads(response.text)
[](#cb6-25)
[](#cb6-26)    return results["data"][0]["embedding"]**
```




# Step 3: Loading the embeddings into the vector database


What’s nice about LanceDB is that we can use Pydantic to programmatically define how we want to store our data. For the `Vector` type, we set it to the length `768` and that is the resulting dimensionality of the embedding vectors from `jina-clip-v1`.


```
[](#cb7-1)from lancedb.pydantic import Vector, LanceModel
[](#cb7-2)
[](#cb7-3)# Create a schema for the table
[](#cb7-4)class Content(LanceModel):
[](#cb7-5)    file_id: int
[](#cb7-6)    file_name: str
[](#cb7-7)    vector: Vector(768)
[](#cb7-8)
[](#cb7-9)# Create a table called `demo` based on the above schema
[](#cb7-10)tbl = db.create_table("demo", schema=Content)**
```




# Step 4: Loading the embeddings into the vector database


Now that we can generate our embeddings and load it into the vector database.


For the code below, assume `list_of_files` is a list of file paths of the images we want to embed.


```
[](#cb8-1)# Loop through each file in the list
[](#cb8-2)for index, file_name in enumerate(LIST_OF_FILES):
[](#cb8-3)
[](#cb8-4)    # Create the embeddings
[](#cb8-5)    image_embedding = get_embeddings(file_name)
[](#cb8-6)
[](#cb8-7)    # Store this as a list of dictionaries to load into the vector database
[](#cb8-8)    img_data_to_add = [
[](#cb8-9)        {
[](#cb8-10)            "file_id": index
[](#cb8-11)            "vector": image_embedding,
[](#cb8-12)            "file_name": f"{file_name}",
[](#cb8-13)        }
[](#cb8-14)    ]
[](#cb8-15)
[](#cb8-16)    # Add to the db
[](#cb8-17)    tbl.add(img_data_to_add)**
```




# Full code


```
[](#cb9-1)# Load packages
[](#cb9-2)import base64
[](#cb9-3)import json
[](#cb9-4)import os
[](#cb9-5)from io import BytesIO
[](#cb9-6)
[](#cb9-7)import lancedb
[](#cb9-8)import requests
[](#cb9-9)from lancedb.pydantic import Vector, LanceModel
[](#cb9-10)from PIL import Image
[](#cb9-11)
[](#cb9-12)# Load secrets from environment variables
[](#cb9-13)LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
[](#cb9-14)LANCEDB_URI = os.getenv("LANCEDB_URI")
[](#cb9-15)JINA_API_KEY = os.getenv("JINA_API_KEY")
[](#cb9-16)LIST_OF_FILES = ["path/to/file1.png", "path/to/file2.png"] # list of file names
[](#cb9-17)
[](#cb9-18)# Encode an image to base 64
[](#cb9-19)def image_to_base64(image):
[](#cb9-20)    buffered = BytesIO()
[](#cb9-21)    image.save(buffered, format="PNG")
[](#cb9-22)    return base64.b64encode(buffered.getvalue()).decode('utf-8')
[](#cb9-23)
[](#cb9-24)# Resize image to 214x214
[](#cb9-25)def resize_image(image_file_path, size=(214, 214)):
[](#cb9-26)    """ Resize image to fit within the given size (214, 214) """
[](#cb9-27)    with Image.open(image_file_path) as img:
[](#cb9-28)        img.thumbnail(size, Image.LANCZOS)
[](#cb9-29)        return img
[](#cb9-30)
[](#cb9-31)# Get embeddings
[](#cb9-32)def get_embeddings(image_file_path):
[](#cb9-33)    headers = {
[](#cb9-34)        'Content-Type': 'application/json',
[](#cb9-35)        'Authorization': f'Bearer {JINA_API_KEY}'
[](#cb9-36)    }
[](#cb9-37)
[](#cb9-38)    resized_image = resize_image(image_file_path)
[](#cb9-39)
[](#cb9-40)    base64_image = image_to_base64(resized_image)
[](#cb9-41)    
[](#cb9-42)    data = {
[](#cb9-43)        'input': [{"bytes": base64_image}],
[](#cb9-44)        'model': 'jina-clip-v1',
[](#cb9-45)        'encoding_type': 'float'
[](#cb9-46)        }
[](#cb9-47)
[](#cb9-48)    response = requests.post("https://api.jina.ai/v1/embeddings",
[](#cb9-49)                             headers=headers,
[](#cb9-50)                             json=data)
[](#cb9-51)    
[](#cb9-52)    results = json.loads(response.text)
[](#cb9-53)
[](#cb9-54)    return results["data"][0]["embedding"]
[](#cb9-55)
[](#cb9-56)
[](#cb9-57)# Connect to the database
[](#cb9-58)db = lancedb.connect(
[](#cb9-59)        uri=LANCEDB_URI,
[](#cb9-60)        api_key=LANCEDB_API_KEY,
[](#cb9-61)        region="us-east-1"
[](#cb9-62)    )
[](#cb9-63)
[](#cb9-64)
[](#cb9-65)# Create a schema for the table
[](#cb9-66)class Content(LanceModel):
[](#cb9-67)    file_id: int
[](#cb9-68)    file_name: str
[](#cb9-69)    vector: Vector(768)
[](#cb9-70)
[](#cb9-71)# Create a table called `demo` based on the above schema
[](#cb9-72)tbl = db.create_table("demo", schema=Content)
[](#cb9-73)
[](#cb9-74)# Loop through list of file names to generate embedding and add to db
[](#cb9-75)for index, file_name in enumerate(LIST_OF_FILES):
[](#cb9-76)    
[](#cb9-77)    # Create the embeddings
[](#cb9-78)    image_embedding = get_embeddings(file_name)
[](#cb9-79)
[](#cb9-80)    # Store this as a list of dictionaries to load into the vector database
[](#cb9-81)    img_data_to_add = [
[](#cb9-82)        {
[](#cb9-83)            "file_id": index,
[](#cb9-84)            "vector": image_embedding,
[](#cb9-85)            "file_name": f"{file_name}",
[](#cb9-86)        }
[](#cb9-87)    ]
[](#cb9-88)
[](#cb9-89)    # Add to the db
[](#cb9-90)    tbl.add(img_data_to_add)**
```





 

