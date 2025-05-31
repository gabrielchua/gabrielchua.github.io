






You can have a HuggingFace model up and running on SageMaker in just a few lines of code.


===


First, you need to import the necessary modules:


```
[](#cb1-1)from sagemaker import get_execution_role
[](#cb1-2)from sagemaker.huggingface.model import HuggingFaceModel**
```


Set up the necessary environment variables, including the model ID, instance type, and versions.


```
[](#cb2-1)ENDPOINT_NAME = "baai-bge-large-en-v1-5"
[](#cb2-2)
[](#cb2-3)HF_ENV = {
[](#cb2-4)    'HF_MODEL_ID':'BAAI/bge-large-en-v1.5',
[](#cb2-5)    'HF_TASK':'feature-extraction'
[](#cb2-6)}
[](#cb2-7)
[](#cb2-8)INSTANCE_TYPE = "ml.m5.xlarge"
[](#cb2-9)
[](#cb2-10)TRANSFORMER_VER = "4.26"
[](#cb2-11)
[](#cb2-12)PY_VERSION = "py39"
[](#cb2-13)
[](#cb2-14)PYTORCH_VERSION = "1.13"**
```


Create a HuggingFaceModel model with the specified configurations.


Here we are using SageMaker’s built-in container images with specific versions of python, pytorch and transformers. A full list of available images can be found [here](https://github.com/aws/deep-learning-containers/blob/master/available_images.md).


```
[](#cb3-1)huggingface_model = HuggingFaceModel(
[](#cb3-2)   env=HF_ENV,
[](#cb3-3)   role=get_execution_role(),
[](#cb3-4)   transformers_version=TRANSFORMER_VER,
[](#cb3-5)   pytorch_version=PYTORCH_VERSION,
[](#cb3-6)   py_version=PY_VERSION,
[](#cb3-7))**
```


Then use the `.deploy` method.


```
[](#cb4-1)predictor = huggingface_model.deploy(
[](#cb4-2)    endpoint_name=ENDPOINT_NAME,
[](#cb4-3)    initial_instance_count=1,
[](#cb4-4)    instance_type=INSTANCE_TYPE
[](#cb4-5))**
```


And that’s it! With just a few lines of code, your HuggingFace model is live on AWS SageMaker. It’s incredibly fast to get started and deploy.




 

