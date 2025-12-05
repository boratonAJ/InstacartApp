# Instacart Basket
Instacart is an app for on-demand grocery shopping with same-day delivery service.

# Instacart Basket Analysis
* Problem: Predict the Items Instacart Costumers Purchase


## The Task
The dataset is an open-source dataset provided by Instacart ([source](https://tech.instacart.com/3-million-instacart-orders-open-sourced-d40d29ead6f2))

 > This anonymized dataset contains a sample of over 3 million grocery orders from more than 200,000 Instacart users.
For each user, we provide between 4 and 100 of their orders, with the sequence of products purchased in each order. We also provide the week and hour of day the order was placed, and a relative measure of time between orders.

* Data: [The Instacart Online Grocery Shopping Dataset](https://www.kaggle.com/api/v1/datasets/download/yasserh/instacart-online-grocery-basket-analysis-dataset)

# Download latest version
`import kagglehub
path = kagglehub.dataset_download("yasserh/instacart-online-grocery-basket-analysis-dataset")
print("Path to dataset files:", path)
`


## The Approach
The task was reformulated as a binary prediction task: Given a user, a product, and the user's prior purchase history, predict whether or not the given product will be reordered in the user's next order.  In short, the approach was to fit a variety of generative models to the prior data and use the internal representations from these models as features to second-level models.


## Requirements
64 GB RAM and 12 GB GPU (recommended), Python 2.7

Python packages:
  - lightgbm==2.0.4
  - numpy==1.13.1
  - pandas==0.19.2
  - scikit-learn==0.18.1
  - tensorflow==1.3.0